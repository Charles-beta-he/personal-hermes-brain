#!/usr/bin/env python3
"""Bounded wrapper for p10-health.sh.

Runs the existing health script with an explicit timeout and always emits a
non-empty JSON object. This prevents cron/gateway health checks from hanging or
returning an empty agent response when p10-health.sh stalls.
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
from typing import Any, Dict, Optional

HERMES_HOME = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()
DEFAULT_SCRIPT = HERMES_HOME / "scripts" / "p10-health.sh"
DEFAULT_LOG = HERMES_HOME / "logs" / "p10-health-safe.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _redact(text: str) -> str:
    # Defensive scrub for errors/stdout snippets. Keep it deliberately simple and
    # stdlib-only; this wrapper should never leak tokens into Telegram/cron output.
    import re
    patterns = [
        r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^\s'\"]+",
        r"sk-[A-Za-z0-9_-]{10,}",
    ]
    out = text or ""
    for pat in patterns:
        out = re.sub(pat, r"\1=[REDACTED]" if "(" in pat else "[REDACTED]", out)
    return out[:4000]


def _parse_json(stdout: str) -> Optional[Dict[str, Any]]:
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {"value": data}
    except json.JSONDecodeError:
        # Some shells may prepend progress lines; recover the outermost JSON object.
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                return data if isinstance(data, dict) else {"value": data}
            except json.JSONDecodeError:
                return None
    return None


def append_log(log_file: str, payload: Dict[str, Any]) -> None:
    p = Path(log_file).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def run_health(script: str = str(DEFAULT_SCRIPT), timeout_s: int = 45, log_file: str = str(DEFAULT_LOG)) -> Dict[str, Any]:
    """Run p10-health.sh --json with timeout and return auditable JSON."""
    script_path = str(Path(script).expanduser())
    started = time.time()
    payload: Dict[str, Any] = {
        "schema_version": 1,
        "timestamp": now_iso(),
        "script": script_path,
        "timeout_s": int(timeout_s),
        "status": "unknown",
        "ok": False,
        "duration_ms": 0,
    }

    try:
        proc = subprocess.Popen(
            ["bash", script_path, "--json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            # Kill the whole process group, not just bash. Real p10-health.sh can
            # have nested Python helpers; killing only the parent may leave a
            # grandchild holding stdout/stderr pipes open and hang the wrapper.
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
            payload["duration_ms"] = int((time.time() - started) * 1000)
            payload.update({
                "status": "timeout_recorded",
                "ok": False,
                "stdout_snippet": _redact(stdout or ""),
                "stderr_snippet": _redact(stderr or ""),
            })
            append_log(log_file, payload)
            return payload

        payload["duration_ms"] = int((time.time() - started) * 1000)
        payload["returncode"] = returncode
        health = _parse_json(stdout)
        if returncode == 0 and health is not None:
            payload.update({"status": "ok", "ok": True, "health": health})
        elif returncode == 0:
            payload.update({
                "status": "invalid_json_recorded",
                "ok": False,
                "stdout_snippet": _redact(stdout),
                "stderr_snippet": _redact(stderr),
            })
        else:
            payload.update({
                "status": "error_recorded",
                "ok": False,
                "stdout_snippet": _redact(stdout),
                "stderr_snippet": _redact(stderr),
            })
    except Exception as e:  # pragma: no cover - defensive guard for cron reliability
        payload["duration_ms"] = int((time.time() - started) * 1000)
        payload.update({"status": "wrapper_error_recorded", "ok": False, "error": _redact(str(e))})

    append_log(log_file, payload)
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Bounded p10-health.sh JSON wrapper")
    parser.add_argument("--script", default=str(DEFAULT_SCRIPT), help="Health script path")
    parser.add_argument("--timeout", type=int, default=45, help="Timeout in seconds")
    parser.add_argument("--log-file", default=str(DEFAULT_LOG), help="JSONL audit log path")
    args = parser.parse_args(argv)

    payload = run_health(script=args.script, timeout_s=args.timeout, log_file=args.log_file)
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
