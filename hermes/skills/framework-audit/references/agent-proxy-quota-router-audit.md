# Agent Proxy / Quota Router Audit Notes

Use when evaluating repositories that manage local AI proxies, multi-account routing, quota/rate-limit handling, model remapping, OAuth/token pools, or provider compatibility layers.

## Minimum evidence to collect

1. Pin provenance
   - Repo URL, commit SHA, branch/tag, license file.
   - Treat non-commercial/share-alike licenses as reference-only until separately reviewed.

2. Map proxy/router surface
   - README and architecture docs.
   - Proxy config files, token/account manager, rate-limit modules, monitor/stats modules, model mapping docs, auth docs, API/admin docs.
   - Search terms: `quota`, `rate_limit`, `retry-after`, `reset`, `sticky`, `health_score`, `remaining_quota`, `mapped_model`, `token`, `account`, `oauth`, `proxy`, `monitor`, `stats`, `circuit`.

3. Compare against Hermes native stack
   - `~/.hermes/config/quorum.yaml` for tier/model diversity.
   - `~/.hermes/scripts/consult_models.py` for fan-out/quorum/consensus and quota integration.
   - `~/.hermes/scripts/model_quota.py` for quota snapshots, confidence, reset parsing, state/log paths.
   - `~/.hermes/hermes-agent/agent/model_health.py` for provider circuit breakers and failure recovery.
   - Existing router tests such as `~/.hermes/scripts/test_model_router_quota.py` if present.

4. Validate live signals when possible
   - Run `python3 ~/.hermes/scripts/consult_models.py status`.
   - Inspect recent quota snapshots/logs. Low confidence `unknown`/`unobservable` quota on active quorum models is a P0 routing-observability gap.
   - If using multi-model consult, treat weak consensus or `truth_not_certified` as advisory only; final claims must cite files.

## Hermes-native extraction patterns

Prefer clean-room implementation into Hermes components, not wholesale import.

P0 patterns:
- Quota confidence-gated routing: unknown/unobservable quota is not abundance. Low-confidence models may be allowed with caution, but known exhausted/rate-limited models with future reset should be skipped or locked out.
- Reset-aware lockouts: parse `Retry-After`, reset headers, and provider error bodies from 429/503/529/quota errors; key cooldown by provider/model, not just provider.
- Routing decision ledger: emit JSONL records for candidate models, selected/skipped models, health state, quota status/confidence, reset_at, latency, error class, and fallback reason.

P1 patterns:
- Capability-aware model mapping: record tool-use, vision, long-context, JSON/schema, streaming, reasoning-budget support, cost/latency tier, allowed/forbidden fallbacks.
- Quorum fan-out skip: consult fan-out should avoid known exhausted models and record skip reasons, with optional probe behavior for high-priority tiers.
- Sticky session / conversation affinity: preserve successful provider/model for long-running threads unless health/quota forces fallback.

P2 patterns:
- Protocol compatibility regression suite: test role/message normalization, tool calls, streaming/non-streaming, structured output, reasoning/thinking config propagation, image parameters, error normalization, and rate-limit parsing.
- Config/gateway sync selfcheck: log config hashes so CLI, gateway, and router can detect stale provider/quorum config.
- External reference license firewall: document allowed clean-room ideas vs forbidden source copying.

## What not to adopt by default

- Do not import a desktop/Tauri proxy manager into Hermes just to gain routing ideas.
- Do not copy token/OAuth/account UI unless Hermes explicitly becomes a credential manager and receives a security review.
- Do not add an extra local proxy layer when Hermes-native gateway/router hooks can solve the issue.
- Do not downgrade Hermes truth gates: multi-model consensus is not truth, especially when consult reports weak consensus or missing evidence links.

## Output shape

Final reports should include:
- Evidence table with concrete file paths.
- Existing Hermes capability vs external capability.
- P0/P1/P2 Hermes-native optimization items.
- License/security risks and explicit non-adoption list.
- Implementation targets using actual inspected Hermes file paths; avoid invented module paths from model suggestions.
