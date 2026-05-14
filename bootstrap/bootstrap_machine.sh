#!/usr/bin/env bash
set -euo pipefail
bash bootstrap/verify.sh
bash bootstrap/sync_import.sh
echo "Bootstrap verified and portable artifacts restored. Restore credentials manually."
