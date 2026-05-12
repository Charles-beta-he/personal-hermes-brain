# Provider Adapter Fallback Ratification

Use this when a multi-model certification is blocked by an orchestration adapter/runtime failure, but the same model is reachable through a separate authenticated official CLI or provider route.

## Trigger

- `consult_models.py run --discussion` completes evidence/truth gates for the state, but one model's Hermes adapter fails during discussion/ratification.
- The failure is infrastructure-shaped (routing/session/adapter/API wrapper), not a model dissent.
- Other models have ratified the same grounded state and the issue ledger has no unresolved severity>=3 blockers.

Example symptom from a session:

- Hermes Anthropic adapter for `claude-opus-4-7` failed with `session_id` / API-routing output.
- Claude Code CLI was authenticated and could read the exact same grounded state in read-only mode.

## Safe fallback pattern

1. Preserve the native `consult_models.py` tick exactly as-is. Do not edit `discussion_result.json` or `certification_manifest.json` to hide adapter failure.
2. Build or locate a single grounded state file with explicit `claims`, `evidence`, claim/evidence links, constraints, acceptance criteria, and non-goals.
3. Invoke the same model family through the official CLI in read-only mode against that exact state.

Claude Code example:

```bash
claude -p "$(cat /tmp/ratification-prompt.txt)" \
  --add-dir /tmp \
  --allowedTools 'Read' \
  --max-turns 3 \
  --output-format json > /tmp/claude-ratification.json
```

Prompt requirements:

- Ask for ratification only, not implementation.
- Scope the judgment to the exact target lifecycle gate (for example, P0 documentation/control-plane landing only).
- Require JSON with `vote`, `best_within_constraints`, `unresolved_severity_ge_3_blockers`, and concise evidence-citing reasoning.
- State that absence of future implementation phases is not a P0 blocker unless it violates source-of-truth/safety constraints.

4. Combine the supplemental vote with the original ratification votes in a separate certification artifact, not by mutating the native tick.
5. Label status precisely, for example `certified_with_runtime_adapter_caveat`, and include:
   - original tick path;
   - native manifest status/reasons;
   - supplemental model route;
   - approval/reject counts;
   - unresolved severity>=3 count;
   - whether the loop gate can be claimed as passed.
6. Record the caveat in the local review/evolution/task log.

## Interpretation rules

- This can certify the target decision/landing gate if all models approve the same grounded state and no severity>=3 blocker remains.
- It does not certify that the native orchestration runtime is healthy.
- It does not permit saying `consult_models.py` native certification passed when its manifest says `not_certified`.
- If the fallback model cannot read the same state, changes scope, asks for missing evidence, or emits `amend/reject`, the status remains `not_certified`.
- If the alternate route also fails for provider/runtime reasons (for example Hermes adapter returns `400 Param Incorrect: Not supported model xiaomi`, then direct `XIAOMI_BASE_URL /chat/completions` returns `429 quota exhausted`), preserve both failures as provider evidence and keep the final closeout as `not_fully_certified_provider_blocked` / `not_certified`. Do not count `models_consulted` or a failed provider attempt as an approval vote.
- For MiMo/Xiaomi specifically, distinguish concurrency/timeout symptoms from quota exhaustion. Empty content or parse retries may justify sequential retry; `HTTP 429` with body `quota exhausted` is a hard provider quota blocker. A bounded long retry is still useful as evidence when the user suspects it “needs more time”: run the Hermes adapter smoke once, then direct OpenAI-compatible Xiaomi calls sequentially with backoff (for example 0s/30s/90s/180s/240s) against the exact same `state_sha256`; if all attempts return 429 and no `Retry-After`/quota headers indicate recovery, write a supplemental artifact and keep status `not_fully_certified_provider_blocked`.
- The supplemental MiMo artifact should include `state_path`, `state_sha256`, native tick/discussion/manifest paths, `attempt_count`, per-attempt delay/start/duration/http_status/error/header evidence, `parsed_vote`, and an explicit closeout rule: only `approve + best_within_constraints=true + no severity>=3 blockers` can close the four-model gap, and it does not certify the broken Hermes xiaomi adapter.
- Treat `final/certification_manifest.json` as the conservative boundary: when it reports missing expected participants, unsigned/non-true `best_within_constraints`, approval quorum shortfall, or `discussion status is not_certified`, the target remains not certified even if truth grounding is 1.0 and deterministic gates all pass.

## Common pitfall

Do not confuse "adapter caveat" with "evidence caveat".

- Adapter caveat: model route failed, but the same grounded state was reviewed through a safe alternate route.
- Evidence caveat: claims are unsupported/contradicted/missing links. This cannot be patched by manual voting; collect evidence first.

## Deterministic selfcheck drift

When a landing task transitions from `running` to `done`, update self-check scripts that assert lifecycle phrases. A verifier that still expects `status: running` after completion is stale. Re-run the self-check after status transitions, not only before them.
