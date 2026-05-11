#!/usr/bin/env bash
# OpenAI Admin Usage/Quota Wrapper
# Uses Go openai-cli (v1.1.2) installed at ~/.hermes/tools/openai-cli/openai
# Security: OPENAI_ADMIN_KEY must be injected per invocation, never stored in shell profile
#
# Usage:
#   OPENAI_ADMIN_KEY=sk-admin-xxx ./openai_admin_quota.sh costs [--project-id PID]
#   OPENAI_ADMIN_KEY=sk-admin-xxx ./openai_admin_quota.sh completions [--project-id PID]
#   OPENAI_ADMIN_KEY=sk-admin-xxx ./openai_admin_quota.sh embeddings [--project-id PID]
#
# Output: JSON (--format json + --transform for pipeline integration)

set -euo pipefail

OPENAI_CLI="${OPENAI_CLI:-$HOME/.hermes/tools/openai-cli/openai}"
SUBCMD="${1:-costs}"
shift 2>/dev/null || true

if [[ -z "${OPENAI_ADMIN_KEY:-}" ]]; then
  echo '{"error":"OPENAI_ADMIN_KEY not set. Inject per invocation, never store globally."}' >&2
  exit 1
fi

# Map friendly names to admin:organization:usage subcommands
case "$SUBCMD" in
  costs|completions|embeddings|images|audio-speeches|audio-transcriptions|code-interpreter-sessions|moderations|vector-stores)
    ;;
  *)
    echo "{\"error\":\"Unknown subcommand: $SUBCMD. Valid: costs, completions, embeddings, images, audio-speeches, audio-transcriptions, code-interpreter-sessions, moderations, vector-stores\"}" >&2
    exit 1
    ;;
esac

exec "$OPENAI_CLI" admin:organization:usage "$SUBCMD" --format json "$@"
