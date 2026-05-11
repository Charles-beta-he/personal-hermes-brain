#!/usr/bin/env python3
"""Cron wrapper generated to keep Hermes cron script field argument-free."""
from pathlib import Path
import os
import sys

scripts = Path(__file__).resolve().parent
target = scripts / 'envelope_executor.py'
argv = [sys.executable, str(target)] + ['run', '1']
os.chdir(scripts)
os.execv(sys.executable, argv)
