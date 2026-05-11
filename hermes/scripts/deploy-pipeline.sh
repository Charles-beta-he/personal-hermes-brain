#!/bin/bash
# Evolution System Deploy Pipeline
set -e
cd ~/.hermes
echo "[1/4] Running tests..."
python3 scripts/test_evolution_system.py
echo "[2/4] Running emergency check..."
python3 scripts/emergency-recovery.py --check-only
echo "[3/4] Committing changes..."
bash scripts/auto-commit-evolution.sh "auto: deploy pipeline"
echo "[4/4] Syncing to Obsidian..."
python3 scripts/sync-to-obsidian.py --push
echo "✅ Deploy pipeline complete"
