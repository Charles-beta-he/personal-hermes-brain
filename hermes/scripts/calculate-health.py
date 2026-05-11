#!/usr/bin/env python3
"""Compatibility wrapper for the canonical Agent health monitor.

Historical local-brain docs referenced `calculate-health.py`; the maintained
implementation is `agent-health-monitor.py`. Keep this thin shim so old docs,
cron prompts, or manual commands remain runnable while preserving a single
canonical implementation.
"""
from __future__ import annotations

import runpy
from pathlib import Path

TARGET = Path(__file__).with_name("agent-health-monitor.py")

if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
