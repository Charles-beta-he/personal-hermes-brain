#!/usr/bin/env python3
"""No-argument cron wrapper for the daily full multi-model smoke check."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import importlib.util

SCRIPT_DIR = Path(__file__).resolve().parent
SAFE = SCRIPT_DIR / "multi-model-smoke-safe.py"


def load_safe():
    spec = importlib.util.spec_from_file_location("multi_model_smoke_safe", SAFE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    mod = load_safe()
    payload = mod.run_smoke(
        script=str(SCRIPT_DIR / "multi-model-smoke.py"),
        script_args=["--timeout", "60"],
        timeout_s=300,
        log_file=str(Path.home() / ".hermes" / "logs" / "multi-model-smoke-daily-full-wrapper.jsonl"),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
