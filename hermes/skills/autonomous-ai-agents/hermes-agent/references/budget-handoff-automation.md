# Budget handoff automation pattern

Session learning from extending Hermes taskpool automation for budget/context exhaustion handoff.

## Trigger

Use this when a Hermes/taskpool task asks for automatic relay, fallback, quota exhaustion handling, context-pressure handoff, or continuation packet policy.

## Durable pattern

1. First split the policy into three narrow proof layers before mutating orchestration code:
   - fallback threshold: GREEN / AMBER / RED / BLACK and noop-vs-change criteria
   - quota observability: `quota_state`, confidence, evidence source hierarchy, unknown handling
   - relay ordering: when to write continuation packet, transition task, retry/block/review, and resume
2. Integrate those briefs into a parent final design covering:
   - state machine
   - trigger conditions
   - automatic vs human authority boundaries
   - failure fallback
   - observability metrics
   - minimum implementation slice
3. Implement the first automation slice as a deterministic recommendation-only helper, not a mutating runner.
4. Keep the helper default-safe:
   - does not mutate task state
   - does not switch provider/model
   - does not release claim
   - does not buy quota
   - fail-soft on unknowns
5. Add direct deterministic tests for the decision table before marking the parent task done.

## Concrete implementation shape

For `brain_task_orchestrator.py`, the useful CLI shape was:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py budget-handoff-check \
  --quota-state limited \
  --confidence high \
  --signal 'circuit open cooldown' \
  --task 'TASK_ID' \
  --json
```

The command should output at least:

- `fallback_band`
- `recommended_action`
- `recommended_transition`
- `packet_required`
- `packet_optional`
- `local_check_first`
- `required_packet_fields`
- `evidence_gate`
- `safety`

Safety flags should be explicit in JSON so downstream automation can gate on them:

```json
{
  "mutates_task": false,
  "switches_provider": false,
  "releases_claim": false,
  "auto_purchases_quota": false,
  "fail_soft": true
}
```

## Decision table minimum

- healthy/high -> GREEN, continue, packet not required
- degraded/medium -> AMBER, continue, packet optional, local check first
- limited/high with circuit/cooldown/rate-limit signal -> RED, retry or review if side effects are pending, packet required
- exhausted/high -> BLACK, blocked, packet required
- unknown/unknown + non-idempotent -> RED, packet required

## Pitfalls

- Do not fake multi-model ratification votes. If real votes are unavailable or economy-paused, move the task through proof/selfcheck evidence or human review boundaries instead.
- Avoid turning the first slice into a mutating runner. A recommendation-only helper is the safer Phase 2 bridge between design and autonomous relay.
- If `done` requires deterministic proof wording, include the word `proof:` plus the artifact path and selfcheck evidence in `--evidence`.
