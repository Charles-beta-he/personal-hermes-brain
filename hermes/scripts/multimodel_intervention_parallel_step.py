#!/usr/bin/env python3
"""Cron-safe wrapper for local-brain multimodel intervention.

Hermes cron script fields are argument-free and do not source interactive shell
rc files. This wrapper makes the intended autorun gate explicit while keeping
the scheduler containment model: no shell, no arbitrary argv parsing.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(HOME / ".hermes"))).expanduser().resolve()
ORCH = HERMES_HOME / "scripts" / "brain_task_orchestrator.py"


def main() -> int:
    env = os.environ.copy()
    env.setdefault("HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL", "1")
    env.setdefault("HERMES_BRAIN_VAULT", str(HOME / "Documents" / "brain"))
    cmd = [
        sys.executable,
        str(ORCH),
        "multimodel-intervention-parallel-step",
        "--max-workers",
        "3",
        "--json",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(HERMES_HOME),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.stderr:
        print(proc.stderr.rstrip(), file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
