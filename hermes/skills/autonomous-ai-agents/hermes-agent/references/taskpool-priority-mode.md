# Local-brain taskpool priority mode

Use this reference when the user asks to globally prefer Hermes self-optimization/evolution tasks over normal work tasks, or to switch back to work-first behavior.

## Durable switch

The durable state file is:

```text
~/.hermes/state/taskpool_priority_mode.json
```

Supported modes:

```json
{"mode":"work-first"}
{"mode":"evolution-first"}
```

`evolution-first` means dispatch ordering, parallel-dispatch preemption, eligibility reasons, boundary gates, and autonomy-readiness all treat `lane=evolution` as the priority lane. This is better than relying on a shell-only env var because cron/no-agent ticks inherit the state file.

The orchestrator also accepts `HERMES_TASKPOOL_PRIORITY_MODE`, but prefer the state file for user-level global switches.

## Verification commands

After writing the state file, verify all four surfaces:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py boundary-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py next --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py parallel-dispatch-dry-run --max-agents 3 --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py eligibility-check --json
```

Expected `evolution-first` evidence:

- `boundary.gates.priority_mode == "evolution-first"`
- `boundary.gates.evolution_preempted_by_work == false`
- `boundary.gates.work_preempted_by_evolution == true` when both lanes have dispatchable tasks
- `next.next.lane == "evolution"` when evolution tasks are dispatchable
- `parallel-dispatch-dry-run.priority_mode == "evolution-first"`
- work-lane skipped items use `reason: lane_preempted_by_evolution`
- `eligibility-check.priority_mode == "evolution-first"`

## Implementation pattern

If implementing or repairing this behavior in `brain_task_orchestrator.py`, keep it centralized:

1. Add one normalizer/helper for priority mode (`work-first` default; aliases OK).
2. Make the dispatch sort key read `lane_sort_weight()` from that helper.
3. Make `select_parallel_dispatch()` mode-aware; do not hardcode work-lane preemption only.
4. Make `eligibility-check` mode-aware so an explicit evolution task is not blocked by `work_lane_available` under `evolution-first`.
5. Expose mode in `boundary-check`, `parallel-dispatch-dry-run`, `eligibility-check`, and evidence/autonomy-readiness summaries.
6. Update tests first: one test for `next` + eligibility, one for parallel dry-run selection and skip reasons.

## Pitfalls

- Do not just set an env var in the current shell; scheduled ticks and no-agent jobs may not inherit it.
- Do not remove work-lane safety gates entirely. They should remain active under `work-first`; `evolution-first` is an explicit mode, not deletion of the guard.
- Do not mark business tasks done or mutate task notes while switching modes. The priority switch should be scheduler state plus verification only.
- Preserve boundary isolation. Priority mode chooses the lane first; it must not allow same-workspace/conflict-boundary co-dispatch unless existing parallel-group rules allow it.
