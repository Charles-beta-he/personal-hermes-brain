#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v hermes >/dev/null 2>&1; then
  echo "FAIL: hermes CLI not found. Install first:"
  echo "curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"
  exit 1
fi

bash bootstrap/sync_import.sh
bash bootstrap/verify.sh
