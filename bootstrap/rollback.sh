#!/usr/bin/env bash
set -euo pipefail
cat <<'EOF'
Rollback is manual-by-design to avoid destructive mistakes.

Look for backups:
  ls -d ~/Documents/brain.backup-* ~/.hermes/skills.backup-* ~/.hermes/scripts.backup-* 2>/dev/null

Restore example:
  rm -rf ~/Documents/brain
  mv ~/Documents/brain.backup-YYYYMMDD-HHMMSS ~/Documents/brain
  python3 ~/.hermes/scripts/brainctl.py --json reindex
EOF
