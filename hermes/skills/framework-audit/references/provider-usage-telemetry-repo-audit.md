# Provider Usage Telemetry / Token Accounting Repo Audit

Use when evaluating repositories that track LLM token usage, local agent usage logs, pricing/cost estimates, quota snapshots, statusline/live usage displays, or provider usage CLIs. This is adjacent to proxy/quota-router audits, but the primary surface is observability and metering rather than request proxying.

## Minimum evidence to collect

1. Pin provenance
   - Repo URL, commit SHA, branch/tag, license, package version, binary/CLI entry points.
   - Record whether the repo is a library, CLI, TUI/GUI product, wrappers/distribution package, or provider admin/official API client.

2. Map data sources and privacy surface
   - README usage/source list.
   - Config paths and default scanned directories (for example local Claude/Codex/session JSONL paths).
   - Auth/credential readers, official quota endpoints, token structs, env vars, debug/body logging.
   - Search terms: `jsonl`, `usage`, `token`, `cache`, `pricing`, `cost`, `quota`, `limit`, `rate`, `auth`, `access_token`, `refresh_token`, `id_token`, `Authorization`, `credentials`, `official`, `statusline`, `live`, `tui`, `gui`.

3. Inspect parser and cache semantics
   - Discovery patterns: glob roots, ignore rules, parallelism, symlink behavior.
   - Record schema: timestamp, provider/source, model, input/output/cache tokens, cost, session/project IDs.
   - Incremental cache keys: path, size, mtime, inode/hash, pricing-version key.
   - Pricing cache: source, TTL, stale behavior, model alias normalization.
   - Redaction behavior: prompt/completion text, file paths, credentials, account IDs, response bodies.

4. Run non-destructive quality gates when practical
   - Build/check/test default features.
   - If optional/no-default features exist, run both `check` and `test`; feature-gated test imports are a reference-quality caveat, not necessarily a blocker to borrowing ideas.
   - Capture exact command outcomes in the task note; do not hide failing modes if the adoption decision is selective.

5. Compare with Hermes native quota stack
   - `~/.hermes/scripts/model_quota.py` for quota snapshots/confidence.
   - `~/.hermes/hermes-agent/agent/model_health.py` for provider circuit breakers.
   - `~/.hermes/scripts/consult_models.py` for fan-out/routing decisions and certification manifests.
   - Existing state/log directories and secret-redaction helpers.

## Hermes-native extraction patterns

Default decision: selective clean-room adoption, not full product import.

P0 patterns:
- Redaction gate before any quota/probe/log output. Synthetic tests must prove fake `access_token`, `refresh_token`, `id_token`, API keys, `Authorization` headers, cookies, prompts, and completion text do not appear in stdout/stderr/state/JSONL/errors except as `[REDACTED]`.
- Local usage parser for Claude/Codex-like JSONL logs that emits only structured metering fields. Empty directory and malformed record fixtures must not crash.
- Incremental cache keyed by file identity/size/mtime plus pricing/schema version; append and pricing-version changes must invalidate correctly.

P1 patterns:
- Pricing cache with TTL and stale downgrade. Use it to produce `estimated` cost/quota confidence when exact provider quota is unavailable.
- Opt-in official quota probe only after P0 redaction gate lands. Default off, env-gated, redacted error classes, and no raw credential file printing.
- Synthetic rate-limit/header tests for `Retry-After`, reset windows, remaining tokens/requests, and exhausted states.

P2 patterns:
- Routing/consult decision ledger: JSONL per candidate model with tier, provider, selected/skipped, quota status/confidence, reset_at, latency_ms, cost estimate, and fallback/skip reason.
- Live/top/statusline-style summaries as observability only; they must not mutate router state without a separate fail-closed gate.
- Distribution wrappers (npm/pypi/downloader/GUI) are usually non-adoption unless Hermes explicitly needs packaging work.

## Decision guardrails

- Do not copy external parser/probe code into Hermes unless license and supply-chain review explicitly allow it; prefer clean-room reimplementation from observed behavior and tests.
- Do not let official quota probes read or print provider credential files by default.
- Do not treat unknown/unobservable quota as abundance. Upgrade to `estimated` only with explicit usage/pricing evidence; upgrade to `exact` only with direct provider evidence.
- If multi-model discussion is truth-grounded but not ratified, seed a taskpool advisory only. Do not implement probe/credential patches from a not-certified artifact.

## Output shape

A good advisory task note includes:
- Pinned repo evidence and license.
- Evidence table with README/manifest/parser/probe/cache/test file references.
- Default/non-default test results and caveats.
- Hermes-native P0/P1/P2 slices with concrete target files.
- Explicit non-adoption list: full GUI/TUI product, credential manager, distribution wrappers, direct source copying.
- Redaction-first dependency order: redaction gate before official probe.
