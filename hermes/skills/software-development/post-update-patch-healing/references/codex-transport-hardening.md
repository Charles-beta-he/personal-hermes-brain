# Codex Transport Hardening After Hermes Updates

Session pattern captured from the 2026-05-12 self-update loop.

## Problem

OpenAI Codex/OAuth traffic can fail as transport-level timeouts or connection errors. If the agent retries without containment, a single slow residential/VPN/TLS path can create a retry storm against the Codex backend and leave poisoned cached clients in the auxiliary-client pool.

## Durable fix shape

1. Add a small file-backed circuit breaker for Codex transport failures.
   - Key by provider/model, not globally.
   - Persist state under `HERMES_HOME` so process restarts respect cooldown.
   - Count only transport failures such as timeout/connection errors, not normal model responses.
   - Clear the breaker on success.

2. Use split HTTP timeouts for Codex/OpenAI-Codex defaults.
   - `connect=30s`
   - `read=600s`
   - `write=60s`
   - `pool=60s`
   - Keep provider/model config overrides higher priority than these defaults.

3. Close and evict poisoned cached clients on all timeout paths.
   - Foreground deadline timeouts must run the same cleanup path as timer/API timeouts.
   - Tests should assert the cached client is closed/evicted after the deadline branch too.

4. Wire the breaker into both paths.
   - Main `run_agent.py` Codex stream path: fail-fast when breaker is open; record transport failure; clear on success.
   - `agent/auxiliary_client.py` Codex completions adapter: same behavior for auxiliary tasks.

5. Make it update-safe.
   - Store a dedicated patch/apply script outside the repo, for example `~/.hermes/scripts/apply-codex-transport-hardening-patch.py` plus `~/.hermes/scripts/patches/codex-transport-hardening.patch`.
   - Teach `post-update-check.py` to detect the markers and reapply with `--fix` when missing.

## Verification checklist

Run from `~/.hermes/hermes-agent` with the repo venv:

```bash
./venv/bin/python -m py_compile agent/codex_circuit_breaker.py agent/auxiliary_client.py hermes_cli/timeouts.py run_agent.py
./venv/bin/python -m pytest tests/agent/test_codex_circuit_breaker.py tests/agent/test_auxiliary_client.py tests/hermes_cli/test_timeouts.py -q -o 'addopts='
python3 ~/.hermes/scripts/post-update-check.py
python3 ~/.hermes/scripts/post-update-check.py --fix
```

If MCP code was also touched in the same update, include:

```bash
./venv/bin/python -m pytest tests/tools/test_mcp_tool.py -q -o 'addopts='
```

## Certification caveat

Do not call the result fully multi-model certified unless the certification manifest says all expected providers passed. A `discussion_result.json` that says approved is not enough if the manifest reports fanout count mismatch, planner parse failure, or `can_claim_complete_certification=false`. Report deterministic gates separately from multi-model certification.
