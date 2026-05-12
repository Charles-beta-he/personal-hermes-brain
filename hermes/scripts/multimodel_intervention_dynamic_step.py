#!/usr/bin/env python3
"""Dynamic starter for long-running multi-model taskpool intervention.

The cron-facing invocation is intentionally short: it checks whether a new
intervention state exists and starts a detached worker if needed. The detached
worker can exceed cron/LLM response time without blocking the scheduler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(HOME / ".hermes"))).expanduser()
ORCH = HERMES_HOME / "scripts" / "brain_task_orchestrator.py"
STATE_DIR = HERMES_HOME / "state" / "multimodel_dynamic"
STATE = STATE_DIR / "state.json"
PID = STATE_DIR / "worker.pid"
LOG = HERMES_HOME / "logs" / "multimodel_intervention_dynamic_step.jsonl"
WORKER_LOG = HERMES_HOME / "logs" / "multimodel_intervention_dynamic_worker.log"


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str], timeout: int = 90, env: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, env=env)
        return with_output_tails({"cmd": cmd, "returncode": p.returncode, "stdout": p.stdout or "", "stderr": p.stderr or ""})
    except subprocess.TimeoutExpired as exc:
        return with_output_tails({"cmd": cmd, "returncode": "timeout", "reason": "subprocess_timeout", "stdout": (exc.stdout or "") if isinstance(exc.stdout, str) else "", "stderr": (exc.stderr or "") if isinstance(exc.stderr, str) else ""})


def with_output_tails(result: dict[str, Any], stdout_limit: int = 8000, stderr_limit: int = 4000) -> dict[str, Any]:
    stdout = result.get("stdout") or ""
    stderr = result.get("stderr") or ""
    result["stdout_tail"] = stdout[-stdout_limit:]
    result["stderr_tail"] = stderr[-stderr_limit:]
    result["stdout_bytes"] = len(stdout.encode("utf-8", errors="replace"))
    result["stderr_bytes"] = len(stderr.encode("utf-8", errors="replace"))
    return result


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    compact = dict(result)
    compact["stdout"] = compact.get("stdout_tail", (compact.get("stdout") or "")[-8000:])
    compact["stderr"] = compact.get("stderr_tail", (compact.get("stderr") or "")[-4000:])
    return compact


def summarize_parallel_step(payload: dict[str, Any]) -> dict[str, Any]:
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    return {
        "status": payload.get("status"),
        "tasks_processed": payload.get("tasks_processed"),
        "tasks_passed": payload.get("tasks_passed"),
        "tasks_failed": payload.get("tasks_failed"),
        "tasks_errors": payload.get("tasks_errors"),
        "task_ids": [r.get("task_id") for r in results[:5] if isinstance(r, dict)],
        "gate_statuses": [(r.get("gate") or {}).get("status") for r in results[:5] if isinstance(r, dict)],
        "decisions": [(r.get("gate") or {}).get("decision") for r in results[:5] if isinstance(r, dict)],
        "convergence": payload.get("convergence") if isinstance(payload.get("convergence"), dict) else {},
    }


def summarize_worker_result(result: dict[str, Any]) -> dict[str, Any]:
    payload = parse_json(result.get("stdout", ""))
    if not payload:
        return {
            "status": "PARSE_FAILED" if result.get("returncode") == 0 and result.get("stdout") else "NO_STDOUT",
            "returncode": result.get("returncode"),
            "stdout_bytes": result.get("stdout_bytes"),
            "stderr_bytes": result.get("stderr_bytes"),
        }
    summary = summarize_parallel_step(payload)
    summary["returncode"] = result.get("returncode")
    summary["stdout_bytes"] = result.get("stdout_bytes")
    summary["stderr_bytes"] = result.get("stderr_bytes")
    return summary


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0); return True
    except Exception:
        return False


def worker_running() -> int:
    if not PID.exists(): return 0
    try:
        pid = int(PID.read_text().strip() or "0")
        return pid if pid and alive(pid) else 0
    except Exception:
        return 0


def load_state() -> dict[str, Any]:
    try: return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception: return {}


def save_state(obj: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append(obj: dict[str, Any]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def parse_json(text: str) -> dict[str, Any]:
    try: return json.loads((text or "").strip())
    except Exception: return {}


def signature(dry: dict[str, Any]) -> str:
    conv = dry.get("convergence") if isinstance(dry.get("convergence"), dict) else {}
    payload = {
        "selected": dry.get("selected_task_id"),
        "queued": dry.get("queued_count"),
        "passed": conv.get("multimodel_passed"),
        "triggered": conv.get("multimodel_triggered"),
        "pending": (conv.get("pending_ids") or [])[:8],
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def start_worker(max_workers: int) -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL"] = "1"
    cmd = [sys.executable, str(Path(__file__).resolve()), "--worker", "--max-workers", str(max_workers)]
    logf = WORKER_LOG.open("a", encoding="utf-8")
    proc = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT, text=True, start_new_session=True, env=env)
    PID.write_text(str(proc.pid), encoding="utf-8")
    return proc.pid


def worker(max_workers: int) -> int:
    event = {"schema": "multimodel_dynamic_worker_v1", "started_at": utc(), "max_workers": max_workers}
    env = os.environ.copy(); env["HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL"] = "1"
    cmd = [sys.executable, str(ORCH), "multimodel-intervention-parallel-step", "--max-workers", str(max_workers), "--json"]
    result = run(cmd, timeout=int(os.environ.get("HERMES_MULTIMODEL_WORKER_TIMEOUT", "7200")), env=env)
    event["finished_at"] = utc(); event["worker_summary"] = summarize_worker_result(result); event["result"] = compact_result(result)
    append(event)
    print(json.dumps(event, ensure_ascii=False, indent=2))
    try: PID.unlink()
    except Exception: pass
    return 0 if result.get("returncode") == 0 else 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--worker", action="store_true")
    ap.add_argument("--max-workers", type=int, default=1)
    ap.add_argument("--cooldown-seconds", type=int, default=int(os.environ.get("HERMES_MULTIMODEL_DYNAMIC_COOLDOWN", "1800")))
    args = ap.parse_args()
    if args.worker:
        return worker(max(1, args.max_workers))

    event: dict[str, Any] = {"schema": "multimodel_intervention_dynamic_step_v1", "ts": utc()}
    running = worker_running()
    if running:
        event.update({"status": "OK", "action": "worker_already_running", "pid": running})
        append(event)
        if args.json: print(json.dumps(event, ensure_ascii=False, indent=2))
        return 0

    env = os.environ.copy(); env["HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL"] = "1"
    dry_cmd = [sys.executable, str(ORCH), "multimodel-intervention-dry-run", "--max-tasks", "6", "--json"]
    dry_res = run(dry_cmd, timeout=90, env=env)
    event["dry_run"] = {"returncode": dry_res.get("returncode"), "stdout_bytes": dry_res.get("stdout_bytes"), "stderr": dry_res.get("stderr_tail", "")[-1000:]}
    dry = parse_json(dry_res.get("stdout", "")) if dry_res.get("returncode") == 0 else {}
    if dry_res.get("returncode") == 0 and dry_res.get("stdout") and not dry:
        event.update({"status": "ERROR", "action": "dry_run_parse_failed", "intervention_required": True, "selected_task_id": "", "queued_count": -1})
        append(event)
        if args.json:
            print(json.dumps(event, ensure_ascii=False, indent=2))
        return 2
    event["intervention_required"] = bool(dry.get("intervention_required"))
    event["selected_task_id"] = dry.get("selected_task_id", "")
    event["queued_count"] = int(dry.get("queued_count") or 0)
    if not event["intervention_required"]:
        event.update({"status": "OK", "action": "no_intervention_needed"})
        save_state({"updated_at": event["ts"], "signature": "", "last_start_epoch": load_state().get("last_start_epoch", 0)})
        append(event)
        return 0

    sig = signature(dry)
    prev = load_state()
    now = time.time()
    cooldown_ok = now - float(prev.get("last_start_epoch") or 0) >= args.cooldown_seconds
    changed = sig != prev.get("signature")
    event["changed"] = changed; event["cooldown_ok"] = cooldown_ok; event["signature"] = sig
    if not changed and not cooldown_ok:
        event.update({"status": "OK", "action": "suppressed_no_change_cooldown"})
        append(event)
        return 0

    # Keep worker count conservative to avoid provider timeouts and rate-limit cascades.
    max_workers = 1 if event["queued_count"] < 8 else min(2, args.max_workers or 2)
    pid = start_worker(max_workers)
    event.update({"status": "OK", "action": "started_worker", "pid": pid, "max_workers": max_workers, "worker_log": str(WORKER_LOG)})
    save_state({"updated_at": event["ts"], "signature": sig, "last_start_epoch": now, "selected_task_id": event["selected_task_id"], "queued_count": event["queued_count"]})
    append(event)
    if args.json:
        print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
