#!/bin/bash
# Session Close — 对话结束时执行的全套收尾
set -e
echo "═══════════════════════════════════════════════════"
echo "  Session Close — 自动化收尾"
echo "═══════════════════════════════════════════════════"
TASK_TYPE="${1:-general}"
ROUNDS="${2:-1}"
CORRECTIONS="${3:-0}"
echo "[1/5] Recording session..."
python3 /Users/charles/.hermes/scripts/session-end-recorder.py "$TASK_TYPE" "$ROUNDS" "$CORRECTIONS"
echo "[2/5] Triggering PA evolution..."
python3 /Users/charles/.hermes/scripts/pa-evolution-trigger.py
echo "[3/5] Generating daily report..."
python3 /Users/charles/.hermes/scripts/pa-daily-report.py
echo "[4/5] Syncing to Obsidian..."
python3 /Users/charles/.hermes/scripts/sync-to-obsidian.py --push
echo "[5/5] Done"
echo ""
echo "Session close complete"
echo "═══════════════════════════════════════════════════"
