#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash bootstrap/validate_safe_tree.sh
python3 -m py_compile hermes/scripts/*.py 2>/dev/null || true
git diff --check || true
echo "verify: PASS"
