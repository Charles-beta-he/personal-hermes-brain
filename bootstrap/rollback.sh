#!/usr/bin/env bash
set -euo pipefail
git status --short
echo "Rollback manually with git reset/revert after review."
