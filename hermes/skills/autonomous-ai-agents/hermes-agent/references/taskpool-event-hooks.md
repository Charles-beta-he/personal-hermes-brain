# Taskpool event hooks: smart routing, returncode 2, and blocked closure

Use this reference when debugging Hermes taskpool event hooks, especially `task_added` logs in `~/.hermes/state/taskpool_event_hooks/`.

## Returncode 2 triage

`task_added` can create the task and refresh derived views successfully while the post-add hook returns `returncode: 2`. Do not assume the task add failed. Inspect the hook JSON:

- `status` / `returncode`
- `cmd`
- parse `stdout` as JSON and inspect `status`, `errors`, `multimodel_step`, `autorun`, and `auto_close_review`
- `stderr` is often empty; the useful signal is usually in structured stdout

Typical failure mode found in this session:

```text
task_added
→ brain_task_dispatch_tick.py --autorun-step --multimodel-step
→ multimodel step or auto-close-review triggers long/nested certification
→ dispatch_tick status=ERROR
→ event hook returncode=2
```

Fix pattern:

- Keep hook work bounded, but not blind-off.
- Default `HERMES_TASKPOOL_EVENT_HOOK_MULTIMODEL=auto`.
- Route by local deterministic task signals (`task_multimodel_intervention_reasons`, certification reasons, priority, lane, explicit requires flags).
- Enable multimodel in hook for P0/P1, P2 evolution, certification reasons, or explicit `multimodel_required` / `requires_multimodel`.
- Defer P3/advisory/light tasks.
- When hook enables multimodel, scope it to the current task with `--multimodel-task <task_id>`; do not let event hooks select a global top task.
- In dispatch tick post-autorun auto-close, set `HERMES_AUTO_CLOSE_REVIEW_TRIGGER_CERT=0` so auto-close consumes existing certification and does not spawn nested model rounds.

Useful fields to include in hook logs/summary:

- `multimodel_route.enabled`
- `multimodel_route.reason`
- `multimodel_route.reasons`
- `multimodel_route.certification_reasons`
- `timeout_seconds`
- actual `cmd`

## Verification recipe

1. `python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/brain_task_dispatch_tick.py`
2. `python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json`
3. Add a low-risk P3 advisory test task and inspect the latest hook log.
   Expected: `returncode: 0`, `multimodel_route.enabled: false`, no `--multimodel-step` in `cmd`.
4. Test routing for an existing P2 evolution/certification task without necessarily running real models.
   Expected route: `enabled: true`, `reason: smart_route_matched`, task-scoped multimodel command if executed.
5. Archive the test task afterward so the pool is not polluted.

## Blocked task closure model

`blocked` is an isolation state, not an automatic close state.

Current safe lifecycle shape:

```text
blocked → pending/retry → claimed/running → review → done
```

Do not normally shortcut `blocked → done`. `auto-close-review` only scans `review`, not `blocked`. `reconcile` promotes due retries but does not automatically solve blockers without a resolver signal.

When debugging blocked tasks, inspect:

- `retry_count`
- `next_retry_at`
- `blocked_reason` / `blocker`
- `multimodel_last_gate_status`
- `multimodel_round_status`
- `multimodel_last_decision`
- evidence / acceptance fields

Recommended future mechanism: `blocked-resolve-step` that diagnoses blocked tasks, checks whether blocker evidence/certification is now satisfied, then moves to `retry` or `review`; existing auto-close-review can then close `review → done` through normal gates.
