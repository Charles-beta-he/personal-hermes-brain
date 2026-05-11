# Provider quota observability and diversity rebalance

Use this reference when multi-model certification, router readiness, budget-handoff, or autonomy gates are blocked by provider quota/diversity evidence rather than by deterministic test failures.

## Core principle

Do not turn provider unobservability into certification. Unknown/unobservable quota may be acceptable for low-risk routing, but budget-handoff and broad autonomous execution must fail closed unless quota evidence is exact/estimated with sufficient confidence, or there is an explicit reviewed policy that scopes the risk.

## Exact quota evidence must not be downgraded

Observed pitfall: a provider balance probe can produce a fresh exact snapshot, then a later successful chat/completions response may contain no quota counters. If `record_call()` blindly writes a response-header snapshot, it can overwrite exact balance evidence with low-confidence `unknown` and create a false blocker.

Required behavior:
- Rank quota evidence before replacing snapshots.
- Safety blockers (`429`, rate-limit, exhausted) must always replace optimistic prior OK snapshots.
- Fresh higher-confidence exact/estimated evidence must be preserved against lower-confidence empty-header evidence.
- Empty response headers should be ignored for quota state unless recognizable quota/rate-limit headers exist.
- Regression tests should cover both directions:
  1. fresh exact balance survives empty successful response headers;
  2. safety blocker still overwrites exact OK evidence.

Useful quality ordering:
1. exhausted/rate_limited safety evidence
2. exact/window_exact balance or rate-limit-window evidence
3. estimated evidence
4. low evidence
5. unobservable/unknown evidence

## Live diversity rebalance must be real, not synthetic

If router readiness is blocked by dominance in the recent model-call window, prefer bounded real provider smoke/warm-up calls over synthetic trace edits.

Pattern:
- Use a bounded smoke runner with explicit `--model`, `--repeat`, `--route`, timeout, and real route-outcome recording (`is_synthetic=0`).
- Tag warm-up calls with a route such as `probe:warmup:{model}` so they remain auditable.
- Keep the task low-cost and side-effect-free (for example a minimal ACK prompt).
- Re-run the diversity gate after each bounded batch; stop once dominance is under threshold.
- Never claim full budget-handoff certification just because diversity passes; quota confidence and autonomy preconditions must pass separately.

## Actionable gate output

Quota/readiness blockers should emit exact next actions:
- `probe_deepseek_balance` only when DeepSeek lacks fresh usable exact balance evidence.
- `record_provider_response_headers` when a provider may expose rate-limit headers but current evidence is unknown/stale/low-confidence.
- `provider_unobservable_lower_risk_tier_or_documented_policy` when a direct API smoke succeeds but returned headers contain no quota/rate-limit/balance evidence.
- `use_api_route_for_headers_or_lower_risk_tier` when an external CLI/OAuth route succeeds but hides response headers from Hermes.
- `manual_budget_confirmation_or_lower_risk_tier` for inherently unobservable subscription-cap providers.

Avoid stale or impossible actions. For example, once DeepSeek exact balance is fresh and usable, do not keep asking for `probe_deepseek_balance` in the blocker list. Also do not treat a successful call with no quota headers as budget evidence; record it as `unobservable` runtime availability evidence and keep budget-handoff/autonomous-execution gates fail-closed unless an explicit scoped policy accepts the risk.

## Verification checklist

Before claiming improvement:
- `python3 -m py_compile` on changed scripts and tests.
- quota unit tests, including downgrade-prevention and safety-blocker replacement.
- router/readiness quota tests.
- diversity/autonomy gate tests.
- live smoke/probe only if credentials/provider availability are part of the claim.
- `model_quota.py confidence-gate --json --gate`.
- `model-router.py readiness --json --gate`.
- `autonomy-precondition.py --mode budget-handoff --json --gate`.
- top-level self-test/p10-health if the change affects Hermes control plane.

Interpretation rule: a fail-closed gate with precise blockers is a valid successful hardening outcome. Do not relabel it as PASS unless provider facts actually support PASS.
