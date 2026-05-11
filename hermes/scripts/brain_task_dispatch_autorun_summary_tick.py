#!/usr/bin/env python3
"""Cron/no_agent wrapper for bounded local-brain autorun summaries.

Explicit opt-in counterpart to brain_task_dispatch_summary_tick.py. It keeps the
same compact summary shape, but asks the dispatch tick to run one bounded
allowlisted autorun step after safe gates pass.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

TICK = Path.home() / ".hermes" / "scripts" / "brain_task_dispatch_tick.py"

if __name__ == "__main__":
    os.environ.setdefault("HERMES_LOCAL_BRAIN_AUTORUN", "1")
    raise SystemExit(subprocess.run([sys.executable, str(TICK), "--summary", "--autorun-step"]).returncode)
