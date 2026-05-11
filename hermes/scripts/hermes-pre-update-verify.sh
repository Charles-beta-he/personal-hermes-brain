#!/bin/sh
# Verify Hermes local patches before/after a controlled update.
set -eu

REPO="${HERMES_REPO:-$HOME/.hermes/hermes-agent}"
CHECKER="$HOME/.hermes/scripts/post-update-check.py"

if [ -x "$REPO/venv/bin/python" ]; then
  PY="$REPO/venv/bin/python"
elif [ -x "$REPO/.venv/bin/python" ]; then
  PY="$REPO/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
else
  echo "No python found" >&2
  exit 1
fi

echo "== Hermes pre-update verify =="
echo "repo=$REPO"
echo "python=$PY"

cd "$REPO"

echo "== git diff --check =="
git diff --check

echo "== post-update-check dry run =="
python3 "$CHECKER"

echo "== py_compile patched runtime files =="
"$PY" -m py_compile \
  agent/model_health.py \
  agent/task_classifier.py \
  agent/spl.py \
  agent/context_compressor.py \
  agent/memory_manager.py \
  agent/prompt_builder.py \
  agent/transports/chat_completions.py \
  cli.py \
  hermes_cli/commands.py \
  run_agent.py \
  tools/mcp_tool.py \
  tools/skill_manager_tool.py

echo "== isolated pytest for local custom modules =="
TMP_HOME="$(mktemp -d)"
trap 'rm -rf "$TMP_HOME"' EXIT HUP INT TERM
HERMES_HOME="$TMP_HOME" "$PY" -m pytest \
  tests/test_model_health.py \
  tests/test_task_classifier.py \
  -q -o 'addopts='

echo "== OK =="
