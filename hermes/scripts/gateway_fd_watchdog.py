#!/usr/bin/env python3
"""Hermes Gateway file-descriptor watchdog.

Default mode is cron-safe: record a bounded sample, stay silent when healthy,
and print a short report only on warning/critical/new Errno 24 evidence.
No restarts, no kills, no recursive Hermes calls.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import plistlib
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

HERMES = Path.home() / ".hermes"
STATE_DIR = HERMES / "state"
STATE_PATH = STATE_DIR / "gateway_fd_watchdog_state.json"
HISTORY_PATH = STATE_DIR / "gateway_fd_history.jsonl"
ALERTS_PATH = STATE_DIR / "gateway_fd_alerts.jsonl"
SNAPSHOT_DIR = STATE_DIR / "gateway_fd_snapshots"
JOBS_PATH = HERMES / "cron" / "jobs.json"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / "ai.hermes.gateway.plist"
TZ = timezone(timedelta(hours=8))
HISTORY_MAX_LINES = 1008  # 7 days at 10-minute cadence
ALERT_DEBOUNCE_MINUTES = 30


def now() -> datetime:
    return datetime.now(TZ)


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    tmp.replace(path)


def append_jsonl(path: Path, obj: dict[str, Any], max_lines: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    with path.open("a") as f:
        f.write(line + "\n")
    if max_lines is not None:
        try:
            lines = path.read_text().splitlines()
            if len(lines) > max_lines:
                atomic_write(path, "\n".join(lines[-max_lines:]) + "\n")
        except Exception:
            pass


def run(cmd: list[str], timeout: int = 15) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return p.returncode, p.stdout or "", p.stderr or ""
    except Exception as exc:
        return 99, "", repr(exc)


def find_gateway_pid() -> tuple[int | None, list[str]]:
    rc, out, err = run(["ps", "axo", "pid,ppid,stat,etime,command"], timeout=10)
    rows: list[str] = []
    if rc != 0:
        return None, [f"ps_failed rc={rc} err={err[:200]}"]
    candidates: list[tuple[int, str]] = []
    for line in out.splitlines()[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split(None, 4)
        if len(parts) < 5:
            continue
        pid_s, _ppid, _stat, _etime, cmd = parts
        # Avoid matching shell/hermes tool commands that merely contain the search string.
        if " -m hermes_cli.main gateway run" not in f" {cmd}" and "python -m hermes_cli.main gateway run" not in cmd:
            continue
        if "/bin/bash -c" in cmd or "gateway_fd_watchdog" in cmd:
            continue
        try:
            pid = int(pid_s)
        except ValueError:
            continue
        candidates.append((pid, stripped))
        rows.append(stripped)
    if not candidates:
        return None, rows
    # Prefer oldest/lowest PID if duplicate service processes briefly overlap.
    candidates.sort(key=lambda item: item[0])
    return candidates[0][0], rows


def plist_limits() -> dict[str, Any]:
    result = {"path": str(PLIST_PATH), "exists": PLIST_PATH.exists(), "soft": None, "hard": None}
    if not PLIST_PATH.exists():
        return result
    try:
        with PLIST_PATH.open("rb") as f:
            data = plistlib.load(f)
        result["soft"] = (data.get("SoftResourceLimits") or {}).get("NumberOfFiles")
        result["hard"] = (data.get("HardResourceLimits") or {}).get("NumberOfFiles")
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def parse_lsof(pid: int) -> dict[str, Any]:
    rc, out, err = run(["lsof", "-p", str(pid), "-n", "-P"], timeout=25)
    if rc != 0:
        return {"ok": False, "returncode": rc, "stderr": err[-1000:]}
    fds: set[int] = set()
    by_type: collections.Counter[str] = collections.Counter()
    by_name: collections.Counter[str] = collections.Counter()
    suspicious: collections.Counter[str] = collections.Counter()
    lines = out.splitlines()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 4:
            m = re.match(r"^(\d+)", parts[3])
            if m:
                fds.add(int(m.group(1)))
        typ = parts[4] if len(parts) >= 5 else "UNKNOWN"
        by_type[typ] += 1
        name = " ".join(parts[8:]) if len(parts) >= 9 else ""
        if name:
            by_name[name] += 1
            if any(marker in name for marker in [".hermes/sessions", ".hermes/cron", ".channel_directory", ".db", ".sqlite", ".tmp"]):
                suspicious[name] += 1
    return {
        "ok": True,
        "raw_line_count": max(0, len(lines) - 1),
        "numeric_fd_count": len(fds),
        "max_numeric_fd": max(fds) if fds else None,
        "by_type": dict(by_type.most_common(12)),
        "top_names": by_name.most_common(12),
        "suspicious_names": suspicious.most_common(20),
        "raw": out,
    }


def scan_errno24_jobs() -> list[dict[str, Any]]:
    if not JOBS_PATH.exists():
        return []
    try:
        data = json.loads(JOBS_PATH.read_text())
    except Exception as exc:
        return [{"id": "jobs_json_read_failed", "name": str(JOBS_PATH), "last_error": repr(exc)}]
    rows = []
    for job in data.get("jobs", []):
        err = str(job.get("last_error") or "")
        if "Errno 24" in err or "Too many open files" in err:
            rows.append({
                "id": job.get("id"),
                "name": job.get("name"),
                "last_run_at": job.get("last_run_at"),
                "last_status": job.get("last_status"),
                "last_error": err[:500],
            })
    return rows


def classify(fd_count: int | None, soft_limit: int | None) -> tuple[str, list[str]]:
    if fd_count is None:
        return "unknown", ["fd_count_unavailable"]
    soft = soft_limit or 256
    warn_threshold = min(int(soft * 0.70), 1024) if soft >= 1024 else int(soft * 0.70)
    critical_threshold = min(int(soft * 0.85), 2048) if soft >= 2048 else int(soft * 0.85)
    reasons = []
    if fd_count >= critical_threshold:
        reasons.append(f"fd_count {fd_count} >= critical_threshold {critical_threshold}")
        return "critical", reasons
    if fd_count >= warn_threshold:
        reasons.append(f"fd_count {fd_count} >= warn_threshold {warn_threshold}")
        return "warning", reasons
    return "healthy", [f"fd_count {fd_count} below warn_threshold {warn_threshold}"]


def build_sample(include_raw: bool = False) -> dict[str, Any]:
    sampled_at = now().isoformat(timespec="seconds")
    pid, process_rows = find_gateway_pid()
    limits = plist_limits()
    jobs = scan_errno24_jobs()
    lsof_data: dict[str, Any]
    if pid is None:
        lsof_data = {"ok": False, "error": "gateway_pid_not_found"}
        status, reasons = "critical", ["gateway_pid_not_found"]
        fd_count = None
    else:
        lsof_data = parse_lsof(pid)
        fd_count = lsof_data.get("numeric_fd_count") if lsof_data.get("ok") else None
        status, reasons = classify(fd_count if isinstance(fd_count, int) else None, limits.get("soft"))
    if jobs and status == "healthy":
        # Old job errors are operational evidence but not necessarily current FD pressure.
        status = "attention"
        reasons = ["cron job(s) record Errno 24 / Too many open files"] + reasons
    sample = {
        "schema_version": 1,
        "sampled_at": sampled_at,
        "status": status,
        "reasons": reasons,
        "pid": pid,
        "process_rows": process_rows[:5],
        "limits": limits,
        "fd": {k: v for k, v in lsof_data.items() if k != "raw"},
        "errno24_jobs": jobs,
        "actions": {"auto_restart": False, "auto_kill": False, "mode": "observe_and_report_only"},
    }
    if include_raw and lsof_data.get("raw"):
        sample["raw_lsof"] = lsof_data["raw"]
    return sample


def fingerprint(sample: dict[str, Any]) -> str:
    fd_count = (sample.get("fd") or {}).get("numeric_fd_count")
    # Do not page repeatedly because a healthy gateway fluctuates by a few FDs.
    # For historical cron Errno24 attention, the stable signal is the job-error
    # tuple. For live pressure, bucket FD count by 100 so large movements alert.
    if sample.get("status") == "attention":
        key = {
            "status": sample.get("status"),
            "errno24_jobs": [(j.get("id"), j.get("last_run_at"), j.get("last_error")) for j in sample.get("errno24_jobs", [])],
        }
    else:
        fd_bucket = (int(fd_count) // 100) if isinstance(fd_count, int) else None
        key = {
            "status": sample.get("status"),
            "pid": sample.get("pid"),
            "fd_bucket_100": fd_bucket,
            "errno24_jobs": [(j.get("id"), j.get("last_run_at"), j.get("last_error")) for j in sample.get("errno24_jobs", [])],
        }
    return json.dumps(key, ensure_ascii=False, sort_keys=True)


def write_snapshot(sample: dict[str, Any]) -> str | None:
    pid = sample.get("pid")
    if not pid:
        return None
    parsed = parse_lsof(int(pid))
    raw = parsed.get("raw")
    if not raw:
        return None
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = now().strftime("%Y%m%d-%H%M%S")
    path = SNAPSHOT_DIR / f"gateway_fd_{ts}_pid{pid}.txt"
    path.write_text(raw)
    snapshots = sorted(SNAPSHOT_DIR.glob("gateway_fd_*.txt"))
    for old in snapshots[:-50]:
        try:
            old.unlink()
        except Exception:
            pass
    return str(path)


def human_report(sample: dict[str, Any], snapshot: str | None = None) -> str:
    fd = sample.get("fd") or {}
    limits = sample.get("limits") or {}
    lines = [
        f"Hermes Gateway FD watchdog: {sample.get('status')} at {sample.get('sampled_at')}",
        f"pid={sample.get('pid')} fd={fd.get('numeric_fd_count')} max_fd={fd.get('max_numeric_fd')} soft={limits.get('soft')} hard={limits.get('hard')}",
        "reasons: " + "; ".join(sample.get("reasons") or []),
        "by_type: " + json.dumps(fd.get("by_type") or {}, ensure_ascii=False),
    ]
    jobs = sample.get("errno24_jobs") or []
    if jobs:
        lines.append("errno24_jobs: " + "; ".join(f"{j.get('id')} {j.get('name')} @{j.get('last_run_at')}" for j in jobs[:5]))
    top = fd.get("top_names") or []
    if top:
        lines.append("top_names: " + "; ".join(f"{name} x{count}" for name, count in top[:5]))
    if snapshot:
        lines.append(f"snapshot: {snapshot}")
    lines.append("action: observe/report only; no unattended restart was performed.")
    return "\n".join(lines)


def cron_mode(args: argparse.Namespace) -> int:
    sample = build_sample(include_raw=False)
    append_jsonl(HISTORY_PATH, sample, HISTORY_MAX_LINES)
    prev = load_json(STATE_PATH, {})
    fp = fingerprint(sample)
    previous_fp = prev.get("fingerprint")
    last_alert_at_s = prev.get("last_alert_at")
    current = now()
    debounced = False
    if last_alert_at_s:
        try:
            last_alert_at = datetime.fromisoformat(last_alert_at_s)
            debounced = (current - last_alert_at) < timedelta(minutes=ALERT_DEBOUNCE_MINUTES)
        except Exception:
            debounced = False
    should_print = sample.get("status") in {"warning", "critical", "attention", "unknown"} and (fp != previous_fp or not debounced)
    snapshot = None
    if sample.get("status") in {"warning", "critical"}:
        snapshot = write_snapshot(sample)
        if snapshot:
            sample["snapshot"] = snapshot
    state = {
        "fingerprint": fp,
        "last_sample_at": sample.get("sampled_at"),
        "last_status": sample.get("status"),
        "last_fd_count": (sample.get("fd") or {}).get("numeric_fd_count"),
        "last_alert_at": prev.get("last_alert_at"),
    }
    if should_print:
        state["last_alert_at"] = current.isoformat(timespec="seconds")
        append_jsonl(ALERTS_PATH, sample)
    atomic_write(STATE_PATH, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    if should_print:
        print(human_report(sample, snapshot=snapshot))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes Gateway FD watchdog")
    parser.add_argument("--json", action="store_true", help="print JSON sample regardless of health")
    parser.add_argument("--snapshot", action="store_true", help="include/write full lsof snapshot")
    parser.add_argument("--no-record", action="store_true", help="do not append history in --json mode")
    args = parser.parse_args()
    if args.json:
        sample = build_sample(include_raw=args.snapshot)
        if args.snapshot:
            snap = write_snapshot(sample)
            if snap:
                sample["snapshot"] = snap
        if not args.no_record:
            append_jsonl(HISTORY_PATH, sample, HISTORY_MAX_LINES)
        print(json.dumps(sample, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if sample.get("status") in {"healthy", "attention"} else 2
    return cron_mode(args)


if __name__ == "__main__":
    raise SystemExit(main())
