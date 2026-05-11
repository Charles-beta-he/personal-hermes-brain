#!/usr/bin/env python3
"""Cron-friendly local-brain dispatch heartbeat.

The scheduler cannot pass CLI arguments in the script field, so this wrapper
runs the safe dispatch tick with --summary to produce a compact non-empty
heartbeat instead of relying on the tick's default noteworthy-only stdout.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(HOME / ".hermes"))).expanduser()
TICK = HERMES_HOME / "scripts" / "brain_task_dispatch_tick.py"


def main() -> int:
    proc = subprocess.run([sys.executable, str(TICK), "--summary"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
