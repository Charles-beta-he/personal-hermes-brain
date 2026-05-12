#!/usr/bin/env python3
"""Dynamic no-agent taskpool runner.

Cron may call this frequently, but actions are event-gated by taskpool state,
not by the wall clock. It emits no stdout when nothing changed.
"""
from __future__ import annotations

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
STATE = HERMES_HOME / "state" / "taskpool_dynamic_runner.json"
LOG = HERMES_HOME / "logs" / "taskpool_dynamic_runner.jsonl"
LOCK = HERMES_HOME / "state" / "taskpool_dynamic_runner.pid"
TICK = HERMES_HOME / "scripts" / "brain_task_dispatch_tick.py"
MM_DYNAMIC = HERMES_HOME / "scripts" / "multimodel_intervention_dynamic_step.py"


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str], timeout: int = 240, env: dict[str, str] | None = None) -> dict[str, Any]:
    proc = subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True, env=env)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            pass
        try:
            out, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                pass
            out, err = proc.communicate()
        return with_output_tails({"cmd": cmd, "returncode": "timeout", "reason": "subprocess_timeout", "stdout": out or "", "stderr": err or ""})
    return with_output_tails({"cmd": cmd, "returncode": proc.returncode, "stdout": out or "", "stderr": err or ""})


def with_output_tails(result: dict[str, Any], stdout_limit: int = 4000, stderr_limit: int = 4000) -> dict[str, Any]:
    """Keep full output for internal parsing while exposing bounded tails for logs."""
    stdout = result.get("stdout") or ""
    stderr = result.get("stderr") or ""
    result["stdout_tail"] = stdout[-stdout_limit:]
    result["stderr_tail"] = stderr[-stderr_limit:]
    result["stdout_bytes"] = len(stdout.encode("utf-8", errors="replace"))
    result["stderr_bytes"] = len(stderr.encode("utf-8", errors="replace"))
    return result


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    compact = dict(result)
    compact["stdout"] = compact.get("stdout_tail", (compact.get("stdout") or "")[-4000:])
    compact["stderr"] = compact.get("stderr_tail", (compact.get("stderr") or "")[-4000:])
    return compact


def load_state() -> dict[str, Any]:
    try: return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception: return {}


def save_state(obj: dict[str, Any]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append(obj: dict[str, Any]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def alive(pid: int) -> bool:
    try: os.kill(pid, 0); return True
    except Exception: return False


def acquire_lock() -> bool:
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        try:
            pid = int(LOCK.read_text().strip() or "0")
            if pid and alive(pid):
                return False
        except Exception:
            pass
    LOCK.write_text(str(os.getpid()), encoding="utf-8")
    return True


def release_lock() -> None:
    try:
        if LOCK.read_text().strip() == str(os.getpid()):
            LOCK.unlink()
    except Exception:
        pass


def parse_json_tail(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text: return {}
    try: return json.loads(text)
    except Exception: return {}


def signature(summary: dict[str, Any]) -> str:
    payload = {
        "status": summary.get("status"),
        "next": summary.get("next_task_id"),
        "dispatchable": summary.get("dispatchable"),
        "errors": summary.get("error_count"),
        "reconcile": summary.get("reconcile_action_count"),
        "ingested": summary.get("ingested_count"),
        "mm": (summary.get("multimodel_intervention") or {}).get("task_id"),
        "mmq": (summary.get("multimodel_intervention") or {}).get("queued_count"),
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def main() -> int:
    if not acquire_lock():
        return 0
    try:
        env = os.environ.copy()
        env.setdefault("HERMES_LOCAL_BRAIN_AUTORUN", "1")
        event: dict[str, Any] = {"schema": "taskpool_dynamic_runner_v1", "ts": utc()}
        tick = run([sys.executable, str(TICK), "--summary", "--autorun-step", "--no-state"], timeout=int(os.environ.get("HERMES_TASKPOOL_DYNAMIC_TIMEOUT", "240")), env=env)
        event["tick"] = compact_result(tick)
        summary = parse_json_tail(tick.get("stdout", ""))
        if tick.get("returncode") in (0, "0") and tick.get("stdout") and not summary:
            event.update({"status": "ERROR", "action": "summary_parse_failed", "parse_error": "tick_stdout_not_json"})
            prev_state = load_state()
            save_state({"updated_at": event["ts"], "signature": prev_state.get("signature", ""), "last_mm_probe_epoch": prev_state.get("last_mm_probe_epoch", 0), "last_summary": {}})
            append(event)
            print(json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True))
            return 2
        event["summary"] = {k: summary.get(k) for k in ["status", "next_task_id", "dispatchable", "error_count", "reconcile_action_count", "ingested_count"]}
        event["autorun"] = summary.get("autorun", {}) if isinstance(summary.get("autorun"), dict) else {}
        sig = signature(summary)
        prev = load_state()
        changed = sig != prev.get("signature")
        event["changed"] = changed
        event["signature"] = sig
        should_print = changed or tick.get("returncode") not in (0, "0") or bool((summary.get("error_count") or 0)) or bool(event["autorun"].get("advanced"))
        # Start/advance multimodel worker opportunistically, but never block this tick.
        mm = summary.get("multimodel_intervention") if isinstance(summary.get("multimodel_intervention"), dict) else {}
        if mm.get("intervention_required") and (changed or time.time() - float(prev.get("last_mm_probe_epoch") or 0) > 1800):
            mm_dynamic = run([sys.executable, str(MM_DYNAMIC), "--json"], timeout=60, env=env)
            event["multimodel_dynamic"] = compact_result(mm_dynamic)
            should_print = True if mm_dynamic.get("stdout") else should_print
            prev["last_mm_probe_epoch"] = time.time()
        state = {"updated_at": event["ts"], "signature": sig, "last_mm_probe_epoch": prev.get("last_mm_probe_epoch", 0), "last_summary": event["summary"]}
        save_state(state); append(event)
        if should_print:
            print(json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if tick.get("returncode") in (0, "0") else 2
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
