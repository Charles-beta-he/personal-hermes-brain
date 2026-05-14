# Dispatch tick soft-governance gating and no-claimed-task diagnosis

Use this when `brain_task_dispatch_tick.py --summary --autorun-step --no-state` returns `OK` but no task is claimed, or when historical governance debt appears to block dispatch.

## Key lesson

Separate two classes of failure:

1. Historical governance debt (soft warnings)
   - Examples: `done task missing evidence: ...`, `autorun done task missing proof evidence: ...`, `unstructured evidence in ...`
   - These can come from already-done tasks and should not block current bounded autorun/dispatch.
   - In `brain_task_dispatch_tick.py`, treat them as tolerated historical proof debt, not fatal dispatch errors.

2. Current execution safety gates (hard deny for claim)
   - Examples: `allowlist_miss`, `reconcile_required`, autonomy write guard / surface allowlist failures.
   - These should still fail closed for claim/advance.

## Diagnostic sequence

1. Run:
   - `python3 ~/.hermes/scripts/brain_task_dispatch_tick.py --summary --autorun-step --no-state`
2. If tick is `ERROR`, inspect whether the fatal errors are only `proof_check` / `evidence_spine` from historical done-task debt.
3. If failures include `unstructured evidence in ...`, extend the tolerated historical-proof-debt prefixes; otherwise tick may still incorrectly return `ERROR`.
4. Re-run tick and confirm:
   - `returncode == 0`
   - `status == OK` (or non-fatal warning semantics if implemented)
   - `error_count == 0`
5. If there is still no claimed task, check:
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py eligibility-check --json`
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json`
6. If eligibility says `allowlist_miss` / `reconcile_required`, the problem is no longer governance gating; it is normal execution gating.
7. Run reconcile with writes when dispatch requires it:
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py reconcile --write --json`
   Then re-run eligibility and dispatch-dry-run.
8. Check allowlist/policy state:
   - `~/.hermes/state/auto_run_allowlist.json`
   - `~/.hermes/state/auto_run_policy.json`
   Make sure the selected task/project/lane/profile actually matches what the autorun step expects.

## Verification pattern

- Runtime script:
  - `~/.hermes/scripts/brain_task_dispatch_tick.py`
- Repo script may differ from runtime; compare/sync both before declaring victory.
- Validate with:
  - `python3 /path/to/test_brain_task_dispatch_tick.py`
  - `python3 -m py_compile ...dispatch_tick.py ...test_brain_task_dispatch_tick.py`

## Durable pitfall

A successful tick (`status=OK`) with `autorun.present=true` but `claimed=false` often means the original governance bug is already fixed; do not keep debugging proof/evidence. Pivot immediately to eligibility/allowlist/reconcile analysis.