#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -d .git ]; then
  echo "FAIL: not a git repository: $ROOT" >&2
  exit 1
fi

mkdir -p .git/hooks
cat > .git/hooks/pre-push <<'HOOK'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if [ "${HERMES_ALLOW_PUSH:-}" != "1" ]; then
  echo "Push blocked by personal-hermes-brain guard." >&2
  echo "Run validation and set HERMES_ALLOW_PUSH=1 only after explicit user approval." >&2
  echo "Example: HERMES_ALLOW_PUSH=1 git push origin main" >&2
  exit 1
fi

bash bootstrap/validate_safe_tree.sh
HOOK
chmod +x .git/hooks/pre-push
printf 'PASS: installed push guard at %s/.git/hooks/pre-push\n' "$ROOT"
