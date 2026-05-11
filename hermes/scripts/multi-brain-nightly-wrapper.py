#!/usr/bin/env python3
"""No-argument cron wrapper for nightly multi-brain consult.

The underlying safe script accepts arguments, but cron `script` must remain a
plain file path. Arguments are pinned here.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SAFE = SCRIPT_DIR / "multi-brain-nightly-safe.py"


def load_safe():
    spec = importlib.util.spec_from_file_location("multi_brain_nightly_safe", SAFE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    mod = load_safe()
    # main(argv) is not supported by the older script, so call through a tiny
    # argparse-compatible shim only if a future version adds it.
    if getattr(mod.main, "__code__", None) and mod.main.__code__.co_argcount:
        return int(mod.main(["--timeout", "60", "--state-timeout", "45"]) or 0)
    import sys
    old = sys.argv[:]
    try:
        sys.argv = [str(SAFE), "--timeout", "60", "--state-timeout", "45"]
        return int(mod.main() or 0)
    finally:
        sys.argv = old


if __name__ == "__main__":
    raise SystemExit(main())
