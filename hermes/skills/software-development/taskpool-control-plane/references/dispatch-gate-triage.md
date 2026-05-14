# Dispatch gate triage: proof debt vs reconcile vs allowlist

Use this when the taskpool has pending P1/P2 tasks but no claimed/running task.

## Symptom pattern
- `brain_task_dispatch_tick.py --summary --autorun-step --no-state` returns `status=OK` or `WARN`, but `autorun.claimed=false`.
- `eligibility-check --json` reports reasons like `reconcile_required` or `allowlist_miss`.
- `next --json` returns `next: null` with `Reconcile is required before dispatch...`.

## Root-cause split
1. Historical governance debt in `evidence_spine`:
   - `done task missing evidence:`
   - `unstructured evidence in `
   These should be soft warnings for tick/autorun triage, not global fatal errors.
2. Reconcile gate in `command_next()`:
   - Current candidate selection can be blocked whenever `command_reconcile(..., write=False)` returns any `action_count`.
   - Not every reconcile action is truly blocking.
3. Allowlist check only matters after a concrete task candidate exists.
   - If `next` is null because reconcile short-circuited, `allowlist_miss` can be misleading secondary noise.

## Durable diagnosis pattern
1. Run both:
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py next --json`
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py next --no-reconcile --json`
2. If `--no-reconcile` yields a task but default `next` returns reconcile-required, diff the reconcile actions.
3. Inspect whether the actions are only `auto_subtask_progress_synced` with:
   - `ready=false`
   - `missing_children=[]`
   This means the parent is merely recording open child progress; it is not a canonical-fix blocker.
4. Verify the candidate task's `project`/`task_id` against `~/.hermes/state/auto_run_allowlist.json` before changing allowlist logic.

## Safe fix boundary
- Keep fail-closed behavior for:
  - kill switch
  - permission/write guards
  - proof hash invalidation
  - truly blocking reconcile mutations
- Safe to relax only this case:
  - non-blocking `auto_subtask_progress_synced` actions that have no missing children and are not ready yet
- Reason: they are telemetry/progress-sync artifacts for parent tasks, not prerequisites for dispatching the child task itself.

## Verification checklist
- `next --json` returns a task without `--no-reconcile`
- `eligibility-check --json` becomes `eligible=true`
- `brain_task_dispatch_tick.py --summary --autorun-step --no-state` shows:
  - `status=OK`
  - `autorun.claimed=true`
  - non-empty `next_task_id`
- Confirm the selected task leaves `pending` and advances to `review` or `done`
