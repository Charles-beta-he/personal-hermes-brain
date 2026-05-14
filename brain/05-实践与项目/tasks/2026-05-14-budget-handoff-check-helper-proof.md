---
type: proof
lane: evolution
status: accepted
created: 2026-05-14T18:03:00+08:00
task: 2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略
concepts: ["budget-handoff-check", "automation-helper", "default-safe", "continuation-packet"]
---

# Budget Handoff Automation Helper Proof

## Implemented

Added deterministic helper to:

/Users/charles/.hermes/scripts/brain_task_orchestrator.py

New CLI:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py budget-handoff-check \
  --quota-state limited \
  --confidence high \
  --signal 'circuit open cooldown' \
  --task 'TASK_ID' \
  --json
```

## Behavior

The helper maps quota/fallback evidence to:

- fallback_band: GREEN / AMBER / RED / BLACK
- recommended_action
- recommended_transition
- packet_required / packet_optional
- required_packet_fields
- evidence_gate
- safety flags

## Safety Boundary

The helper is recommendation-only:

```json
{
  "mutates_task": false,
  "switches_provider": false,
  "releases_claim": false,
  "auto_purchases_quota": false,
  "fail_soft": true
}
```

It does not mutate taskpool state, buy quota, switch providers, release claim, or execute handoff.

## Validation

Commands run:

```bash
python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py
python3 ~/.hermes/scripts/test_budget_handoff_check.py
python3 ~/.hermes/scripts/brain_task_orchestrator.py budget-handoff-check --quota-state limited --confidence high --signal 'circuit open cooldown' --task '2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略' --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py budget-handoff-check --quota-state unknown --confidence unknown --non-idempotent --signal 'unobservable after bounded retry' --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py budget-handoff-check --quota-state healthy --confidence high --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py budget-handoff-check --quota-state exhausted --confidence high --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
```

Observed:

- `PASS budget_handoff_check tests=7`
- healthy/high -> GREEN, continue, packet_required=false
- limited/high/circuit-open -> RED, retry, packet_required=true
- exhausted/high -> BLACK, blocked, packet_required=true
- unknown/unknown/non-idempotent -> RED, packet_required=true
- selfcheck PASS

## Files

- Implementation: /Users/charles/.hermes/scripts/brain_task_orchestrator.py
- Tests: /Users/charles/.hermes/scripts/test_budget_handoff_check.py

## Acceptance Mapping

This completes Phase 2 from the parent final design: a deterministic `budget-handoff-check` helper with same-input same-output transition recommendation and default-safe no-mutation behavior.
