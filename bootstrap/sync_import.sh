#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRAIN="${HERMES_BRAIN_VAULT:-$HOME/Documents/brain}"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
TS="$(date +%Y%m%d-%H%M%S)"
cd "$ROOT"

backup_if_exists() {
  local path="$1"
  if [ -e "$path" ] && [ ! -L "$path" ]; then
    local backup="${path}.backup-${TS}"
    echo "Backup: $path -> $backup"
    mv "$path" "$backup"
  fi
}

bash bootstrap/validate_safe_tree.sh
mkdir -p "$HERMES_HOME"
backup_if_exists "$BRAIN"
backup_if_exists "$HERMES_HOME/skills"
backup_if_exists "$HERMES_HOME/scripts"

mkdir -p "$(dirname "$BRAIN")" "$HERMES_HOME"
rsync -a brain/ "$BRAIN/"
rsync -a hermes/skills/ "$HERMES_HOME/skills/"
rsync -a hermes/scripts/ "$HERMES_HOME/scripts/"

if [ ! -f "$HERMES_HOME/.env" ] && [ -f hermes/config/env.example ]; then
  cp hermes/config/env.example "$HERMES_HOME/.env"
  chmod 600 "$HERMES_HOME/.env"
  echo "Created local env template at $HERMES_HOME/.env; fill credentials locally."
fi

python3 "$HERMES_HOME/scripts/brainctl.py" --json sync || true
python3 "$HERMES_HOME/scripts/brainctl.py" --json reindex || true
printf 'PASS: import complete\n'
