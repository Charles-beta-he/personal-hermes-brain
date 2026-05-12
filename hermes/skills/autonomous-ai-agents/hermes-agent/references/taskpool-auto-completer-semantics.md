# Taskpool auto-completer semantic ratchet

Use this when local-brain/task-pool health gates fail because `local-brain-taskpool-auto-completer` has `last_status=error`.

## Core lesson

Do not equate every auto-completer cron `error` with scheduler health failure. Some errors are task-level certification states and should keep the scheduler/evidence-spine healthy while the task remains blocked/retryable.

Known scheduler-safe semantic statuses:

- `ok`
- `ok_with_task_blocker`
- `retryable_runtime_timeout`
- `truth_grounded_advisory_not_ratified`
- `certification_not_certified`
- `certification_long_running`

Unknown auto-completer errors should still fail closed.

## Classification signals

Treat as `retryable_runtime_timeout` when the cron tail contains:

- `Request timed out`
- `RuntimeError: Request timed out`
- `subprocess_timeout`
- `timeout_recorded`

Treat as `truth_grounded_advisory_not_ratified` when advisory evidence exists but ratification is still blocked/pending, for example:

- `truth_grounded_advisory_not_ratified`
- `advisory evidence` / `advisory report` / `evidence化 advisory`
- missing or pending `discussion_result.json`
- `cannot closeout`, `cannot done`, `不能 closeout`, `不能 done`
- `T3 still running`, `T3 仍在运行`

Treat as `certification_not_certified` when ratification explicitly failed:

- `not_certified`
- `not certified`
- `vote_reject`
- `agreement_low`
- `ratification failed`
- `未通过认证` / `认证失败`

Treat as `certification_long_running` when certification is still running:

- `still running`
- `background process`
- `waiting for ratification`
- pending `certification_manifest.json`

## Patch pattern

1. Centralize scheduler-safe semantics in a shared constant such as `SAFE_AUTO_COMPLETER_SEMANTIC_STATUSES`.
2. Use the same constant in both:
   - `build_taskpool_evidence_spine()` gate logic
   - `command_autonomy_readiness()` / CHK-AUTO-COMPLETER-SEMANTICS
3. Extend C-TP/E-TP evidence claims so the proof spine states these are task-level blockers, not scheduler crashes.
4. Add regression fixtures for every safe error class, plus one missing/unknown cron case that still fails closed.
5. Run real gates, not just unit tests:

```bash
python3 ~/.hermes/scripts/test_brain_task_orchestrator.py
python3 ~/.hermes/scripts/test_brain_task_dispatch_tick.py
python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/test_brain_task_orchestrator.py ~/.hermes/scripts/brain_task_dispatch_tick.py ~/.hermes/scripts/test_brain_task_dispatch_tick.py ~/.hermes/scripts/autonomy-precondition.py ~/.hermes/scripts/autonomy-write-guard.py ~/.hermes/scripts/permission_taxonomy.py
python3 ~/.hermes/scripts/brain_task_orchestrator.py evidence-spine --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py lifecycle --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py boundary-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py autonomy-readiness --json
python3 ~/.hermes/scripts/brain_task_dispatch_tick.py --summary --no-state
```

Expected healthy real-gate shape:

- evidence-spine: `status=OK`, `gate_status=PASS`
- selfcheck: `status=PASS`, failures=0
- proof-check: `status=PASS`, failures=0
- lifecycle: `status=PASS`, invalid_count=0
- boundary-check: `status=PASS`, invalid_count=0
- autonomy-readiness: `status=PASS`, `architecture_complete=true`
- dispatch tick summary: `status=OK`, `error_count=0`

## Permission taxonomy coupling

When taskpool write guard changes from legacy `kanban-worker` to `taskpool`, update tests and allowlist fixtures too. Otherwise fail-closed guards will correctly block `auto-claim-and-handoff` with `surface_allowlisted` despite P10 health passing.
