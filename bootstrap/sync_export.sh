#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRAIN="${HERMES_BRAIN_VAULT:-$HOME/Documents/brain}"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
cd "$ROOT"

mkdir -p brain hermes/skills hermes/scripts hermes/config

if [ ! -d "$BRAIN" ]; then
  echo "FAIL: brain vault not found: $BRAIN" >&2
  exit 1
fi
if [ ! -d "$HERMES_HOME/skills" ]; then
  echo "FAIL: skills dir not found: $HERMES_HOME/skills" >&2
  exit 1
fi

# Markdown-first brain export; include Obsidian config because it affects usability.
rsync -a --delete \
  --include='*/' --include='*.md' --include='.obsidian/***' --exclude='*' \
  "$BRAIN/" brain/

# Skills: keep skill source assets, drop runtime usage/cache state.
rsync -a --delete \
  --exclude='.usage.json' --exclude='.usage.json.lock' --exclude='.curator_state' \
  --exclude='.hub/' --exclude='index-cache/' --exclude='__pycache__/' --exclude='*.pyc' \
  --exclude='.git/' \
  "$HERMES_HOME/skills/" hermes/skills/

# Scripts: selected top-level scripts only; no pycache, no secret/token/oauth named files.
rsync -a --delete --prune-empty-dirs \
  --include='*/' --include='*.py' --include='*.sh' --include='*.json' --include='*.yaml' --include='*.yml' \
  --exclude='__pycache__/' --exclude='*.pyc' \
  --exclude='*secret*' --exclude='*token*' --exclude='*oauth*' \
  --exclude='*' \
  "$HERMES_HOME/scripts/" hermes/scripts/

# Sanitized config template: redact likely values; keep structure.
if [ -f "$HERMES_HOME/config.yaml" ]; then
  python3 - "$HERMES_HOME/config.yaml" hermes/config/config.example.yaml <<'PY'
from pathlib import Path
import re, sys
src=Path(sys.argv[1]); dst=Path(sys.argv[2])
text=src.read_text(errors='ignore')
# Redact common scalar secret-ish fields without requiring yaml deps.
text=re.sub(r'(?im)^([ \t]*(api_key|token|secret|password|client_secret|bot_token|webhook_url|base_url)[ \t]*:[ \t]*).+$', r'\1<SET_LOCALLY>', text)
text=re.sub(r'(?i)(sk-[A-Za-z0-9_-]{8,}|gh[op]_[A-Za-z0-9_]{8,}|AIza[0-9A-Za-z_-]{8,})', '<REDACTED>', text)
dst.write_text('# Sanitized template. Fill real values locally; do not commit secrets.\n' + text)
PY
fi

cat > hermes/config/env.example <<'EOF'
# Copy to ~/.hermes/.env on each machine and fill locally.
# Do not commit real values.
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OPENROUTER_API_KEY=
DEEPSEEK_API_KEY=
XIAOMI_API_KEY=
GITHUB_TOKEN=
TELEGRAM_BOT_TOKEN=
EOF

bash bootstrap/validate_safe_tree.sh
printf 'PASS: export complete\n'
