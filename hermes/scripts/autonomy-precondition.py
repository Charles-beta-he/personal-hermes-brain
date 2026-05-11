#!/usr/bin/env python3
"""Fail-closed autonomy precondition gate for Hermes post-update surfaces.

Modes:
- dispatch-hint: safe default; verifies local health only.
- budget-handoff: requires health + model diversity gate + quota confidence + router readiness.
- autonomous-execution: additionally requires an explicit local kill-switch/enable file.

This script does not execute tasks, mutate task state, or perform external writes.
It only reports whether a caller may promote a surface beyond advisory dispatch.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", HOME / ".hermes")).expanduser()
SCRIPTS = HERMES_HOME / "scripts"
DEFAULT_ENABLE_FILE = HERMES_HOME / "state" / "autonomy-execution.enabled"
T3_MODELS = {"claude-opus-4-7", "gpt-5.5", "deepseek-v4-pro", "mimo-v2.5-pro"}


def run_json(cmd: list[str], timeout: int = 120) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    meta = {"cmd": cmd, "ok": False, "returncode": None, "stderr": "", "stdout_tail": ""}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        meta["error"] = repr(e)
        return None, meta
    meta["returncode"] = proc.returncode
    meta["stderr"] = (proc.stderr or "")[-1000:]
    meta["stdout_tail"] = (proc.stdout or "")[-1000:]
    if proc.returncode != 0:
        return None, meta
    try:
        data = json.loads(proc.stdout)
    except Exception as e:
        meta["error"] = f"json_parse_failed: {e}"
        return None, meta
    meta["ok"] = True
    return data, meta


def check_p10() -> dict[str, Any]:
    data, meta = run_json(["bash", str(SCRIPTS / "p10-health.sh"), "--json"], timeout=180)
    ok = bool(data and data.get("components", {}).get("self_test") == 1.0 and data.get("grade") in {"A", "B"})
    return {"name": "p10_health", "ok": ok, "data": data, "meta": meta}


def check_diversity(threshold: float, window: int) -> dict[str, Any]:
    cmd = [sys.executable, str(SCRIPTS / "model-diversity-monitor.py"), "--json", "--gate", "--threshold", str(threshold), "--window", str(window)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    data = None
    try:
        data = json.loads(proc.stdout)
    except Exception:
        pass
    return {
        "name": "model_diversity_gate",
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "data": data,
        "stderr": (proc.stderr or "")[-1000:],
    }


def check_quota(min_confidence: float) -> dict[str, Any]:
    cmd = [sys.executable, str(SCRIPTS / "model_quota.py"), "confidence-gate", "--json", "--gate", "--min-confidence", str(min_confidence)]
    for model in sorted(T3_MODELS):
        cmd.extend(["--model", model])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        data = json.loads(proc.stdout or "{}")
    except Exception:
        data = {"parse_error": (proc.stdout or "")[-1000:]}
    return {
        "name": "quota_confidence",
        "ok": proc.returncode == 0 and bool(data.get("ok")),
        "data": data,
        "min_confidence": min_confidence,
        "returncode": proc.returncode,
        "stderr": (proc.stderr or "")[-1000:],
    }


def check_router_readiness(threshold: float, window: int, min_confidence: float) -> dict[str, Any]:
    cmd = [
        sys.executable, str(SCRIPTS / "model-router.py"), "readiness",
        "--json", "--gate", "--threshold", str(threshold), "--window", str(window),
        "--min-quota-confidence", str(min_confidence),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        data = json.loads(proc.stdout or "{}")
    except Exception:
        data = {"parse_error": (proc.stdout or "")[-1000:]}
    return {
        "name": "router_readiness",
        "ok": proc.returncode == 0 and bool(data.get("ok")),
        "data": data,
        "returncode": proc.returncode,
        "stderr": (proc.stderr or "")[-1000:],
    }


def check_enable_file(path: Path) -> dict[str, Any]:
    exists = path.exists()
    content = ""
    if exists:
        try:
            content = path.read_text(encoding="utf-8").strip()
        except Exception:
            content = ""
    ok = exists and content == "I_UNDERSTAND_AUTONOMOUS_EXECUTION_RISK"
    return {"name": "explicit_autonomy_enable_file", "ok": ok, "path": str(path), "exists": exists}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail-closed precondition gate before Hermes autonomy promotion")
    parser.add_argument("--mode", choices=["dispatch-hint", "budget-handoff", "autonomous-execution"], default="dispatch-hint")
    parser.add_argument("--json", action="store_true", help="Accepted for CLI consistency; output is always JSON")
    parser.add_argument("--gate", action="store_true", help="Accepted for CLI consistency; non-zero on FAIL_CLOSED")
    parser.add_argument("--threshold", type=float, default=0.80)
    parser.add_argument("--window", type=int, default=500)
    parser.add_argument("--min-quota-confidence", type=float, default=0.50)
    parser.add_argument("--enable-file", default=str(DEFAULT_ENABLE_FILE))
    args = parser.parse_args(argv)

    checks = [check_p10()]
    required = ["p10_health"]

    if args.mode in {"budget-handoff", "autonomous-execution"}:
        checks.append(check_diversity(args.threshold, args.window))
        checks.append(check_quota(args.min_quota_confidence))
        checks.append(check_router_readiness(args.threshold, args.window, args.min_quota_confidence))
        required.extend(["model_diversity_gate", "quota_confidence", "router_readiness"])

    if args.mode == "autonomous-execution":
        checks.append(check_enable_file(Path(args.enable_file).expanduser()))
        required.append("explicit_autonomy_enable_file")

    by_name = {c["name"]: c for c in checks}
    failed = [name for name in required if not by_name.get(name, {}).get("ok")]
    result = {
        "schema_version": 1,
        "mode": args.mode,
        "status": "PASS" if not failed else "FAIL_CLOSED",
        "ok": not failed,
        "failed_required_checks": failed,
        "required_checks": required,
        "checks": checks,
        "policy": {
            "dispatch_hint": "local health only; no task execution or external writes",
            "budget_handoff": "requires diversity, quota confidence, and router readiness gates",
            "autonomous_execution": "requires budget_handoff gates plus explicit local enable file",
        },
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
