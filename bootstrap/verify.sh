#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
cd "$ROOT"

bash bootstrap/validate_safe_tree.sh
hermes config path
hermes config env-path
hermes doctor || true
hermes skills list >/tmp/personal-hermes-brain-skills.txt
head -20 /tmp/personal-hermes-brain-skills.txt
python3 "$HERMES_HOME/scripts/brainctl.py" --json status
python3 "$HERMES_HOME/scripts/brainctl.py" --json reindex
python3 "$HERMES_HOME/scripts/brainctl.py" --json search "Hermes" --limit 5
printf 'PASS: bootstrap verification complete\n'
