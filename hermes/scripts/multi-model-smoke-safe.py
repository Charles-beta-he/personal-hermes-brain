#!/usr/bin/env python3
"""Bounded wrapper for multi-model-smoke.py cron jobs.

The raw smoke script may take several minutes across models and exits non-zero on
partial failures. For cron observability we want bounded execution, JSON output,
JSONL audit evidence, and exit code 0 even when the underlying smoke is partial.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

HERMES_HOME = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()
DEFAULT_SCRIPT = HERMES_HOME / "scripts" / "multi-model-smoke.py"
DEFAULT_LOG = HERMES_HOME / "logs" / "multi-model-smoke-safe.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def redact(text: str) -> str:
    import re
    out = text or ""
    out = re.sub(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^\s'\"]+", r"\1=[REDACTED]", out)
    out = re.sub(r"sk-[A-Za-z0-9_-]{10,}", "[REDACTED]", out)
    return out[:4000]


def parse_json_lines(stdout: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            records.append(obj)
    return records


def append_log(path: str, payload: Dict[str, Any]) -> None:
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _summarize(records: List[Dict[str, Any]], returncode: Optional[int]) -> Dict[str, Any]:
    summary = next((r for r in reversed(records) if "status" in r and "passed" in r), {})
    model_records = [r for r in records if "model" in r and "ok" in r]
    passed = sum(1 for r in model_records if r.get("ok"))
    failed_models = [str(r.get("model")) for r in model_records if not r.get("ok")]
    if not summary and model_records:
        summary = {"models": len(model_records), "passed": passed, "status": "pass" if passed == len(model_records) else "partial_fail"}
    status = "ok" if returncode == 0 and summary.get("status") == "pass" else "partial_fail_recorded"
    if returncode not in (0, 2):
        status = "error_recorded"
    return {
        "status": status,
        "summary": summary,
        "model_records": len(model_records),
        "failed_models": failed_models,
    }


def run_smoke(script: str = str(DEFAULT_SCRIPT), script_args: Optional[List[str]] = None, timeout_s: int = 240, log_file: str = str(DEFAULT_LOG)) -> Dict[str, Any]:
    script_args = list(script_args or [])
    script_path = str(Path(script).expanduser())
    started = time.time()
    payload: Dict[str, Any] = {
        "schema_version": 1,
        "timestamp": now_iso(),
        "script": script_path,
        "script_args": script_args,
        "timeout_s": int(timeout_s),
        "duration_ms": 0,
        "ok": False,
        "status": "unknown",
    }
    cmd = [sys.executable, script_path] + script_args
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                stdout, stderr = proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout, stderr = proc.communicate()
            records = parse_json_lines(stdout or "")
            payload.update({
                "status": "timeout_recorded",
                "ok": False,
                "records": records,
                "summary": _summarize(records, returncode=None).get("summary", {}),
                "stdout_snippet": redact(stdout or ""),
                "stderr_snippet": redact(stderr or ""),
            })
            payload["duration_ms"] = int((time.time() - started) * 1000)
            append_log(log_file, payload)
            return payload

        records = parse_json_lines(stdout or "")
        summary = _summarize(records, returncode)
        payload.update(summary)
        payload.update({
            "ok": summary["status"] == "ok",
            "returncode": returncode,
            "records": records,
            "stdout_snippet": redact(stdout or "") if not records else "",
            "stderr_snippet": redact(stderr or ""),
        })
    except Exception as e:  # pragma: no cover - defensive cron guard
        payload.update({"status": "wrapper_error_recorded", "ok": False, "error": redact(str(e))})
    payload["duration_ms"] = int((time.time() - started) * 1000)
    append_log(log_file, payload)
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Bounded multi-model-smoke.py cron wrapper")
    parser.add_argument("--script", default=str(DEFAULT_SCRIPT), help="Smoke script path")
    parser.add_argument("--timeout", type=int, default=240, help="Wrapper wall-clock timeout")
    parser.add_argument("--log-file", default=str(DEFAULT_LOG), help="JSONL audit log path")
    parser.add_argument("script_args", nargs=argparse.REMAINDER, help="Arguments forwarded after -- to the smoke script")
    args = parser.parse_args(argv)
    forwarded = args.script_args
    if forwarded and forwarded[0] == "--":
        forwarded = forwarded[1:]
    payload = run_smoke(script=args.script, script_args=forwarded, timeout_s=args.timeout, log_file=args.log_file)
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
