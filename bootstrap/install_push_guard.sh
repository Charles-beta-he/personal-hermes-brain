#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .git/hooks
cat > .git/hooks/pre-push <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail
if [ "${HERMES_ALLOW_PUSH:-}" != "1" ]; then
  echo "Push blocked. Run validation and set HERMES_ALLOW_PUSH=1 only after guarded approval." >&2
  exit 1
fi
bash bootstrap/validate_safe_tree.sh
HOOK
chmod +x .git/hooks/pre-push
