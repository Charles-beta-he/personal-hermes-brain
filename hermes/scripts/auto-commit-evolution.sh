#!/bin/bash
cd /Users/charles/.hermes
MSG="${1:-auto: evolution update $(date +%Y-%m-%d-%H:%M)}"
git add -A
git commit -m "$MSG" || echo "Nothing to commit"
