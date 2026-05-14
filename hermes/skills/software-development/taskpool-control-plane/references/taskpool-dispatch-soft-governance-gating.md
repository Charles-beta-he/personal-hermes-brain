# Taskpool dispatch tick: soft governance gating vs fail-closed safety

Use this when the taskpool has dispatchable work but `brain_task_dispatch_tick.py --summary --autorun-step --no-state` still returns `ERROR` and no task advances.

## What failed in this session

Observed pattern:
- `proof-check` failed mainly on historical done-task evidence debt.
- `evidence-spine` reported `gate_status: WARN` because `proof_check: FAIL`.
- dispatch tick surfaced `errors` for `proof_check` + `evidence_spine` and skipped `autorun_step` entirely.
- manual `autorun-runner` could still claim a P1 task, proving the pool was dispatchable and the blockage lived in tick gating, not task eligibility.

## Durable diagnosis pattern

1. Run the real runtime path, not just repo copies:
   - `python3 ~/.hermes/scripts/brain_task_dispatch_tick.py --summary --autorun-step --no-state`
2. Compare with narrower executors:
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json`
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py evidence-spine --json`
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py eligibility-check --json`
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py autorun-runner --json`
3. If `autorun-runner` can advance work but dispatch tick returns `ERROR`, inspect whether tick is promoting governance debt into fatal dispatch blockers.
4. Differentiate:
   - hard blockers: kill switch, permission/write guard failure, invalid current-task proof chain, current task not dispatchable
   - soft governance debt: historical done-task evidence gaps, legacy body-only evidence, unstructured evidence on old done tasks, evidence-spine WARN caused only by historical proof debt

## Important pitfall found

The runtime tick already had a `historical_proof_debt_only` tolerance path, but it was too narrow. It tolerated:
- `done task missing evidence:`
- `autorun done task missing proof evidence:`

It still failed closed on historical lines like:
- `unstructured evidence in <task-id>: multimodel_gate:FAIL`
- `unstructured evidence in <task-id>: multimodel_decision:CONTINUE_LOOP`
- `unstructured evidence in <task-id>: multimodel_status:not_certified`
- `unstructured evidence in <task-id>: multimodel_auto_outcome:certification_failed`

Fix: extend tolerated historical proof-debt prefixes so old done-task `unstructured evidence in ...` entries are treated as governance debt, not current dispatch blockers.

## Verification target

After widening tolerance, expect:
- dispatch tick exit code `0`
- tick no longer returns `ERROR` solely because of historical done-task evidence debt
- remaining non-advancement reasons shift to legitimate current guards such as `allowlist_miss`, `reconcile_required`, or autonomy write-guard checks

## Testing note

For regression tests, model the historical debt with a done task containing non-structured evidence entries instead of only `evidence: []`, because the runtime tolerance path can differ between those cases.

## User-specific operating rule reinforced

When the pool has no active/running task and automation is stalled, manually advance one eligible P1 task to `claimed` as a fail-safe while continuing root-cause analysis of the timer/control-plane path.
