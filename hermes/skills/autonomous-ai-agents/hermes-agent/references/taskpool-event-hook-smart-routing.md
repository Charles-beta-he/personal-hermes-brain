# Taskpool event hook smart routing

Use this reference when debugging or extending Hermes taskpool `task_added` / dispatch tick behavior.

## Durable pattern

`task_added` hooks should not be simply always-on or always-off for multi-model work. Use deterministic local smart routing before invoking expensive model steps:

- Default mode should be `auto`.
- Light/P3/advisory tasks should skip the expensive multi-model step and keep the hook bounded.
- High-value tasks should enable multi-model review automatically, especially:
  - P0/P1 priority
  - P2 `evolution` lane
  - tasks with certification reasons from `task_multimodel_certification_reasons`
  - explicit `multimodel_required` / `requires_multimodel`
- When enabled from an event hook, scope the model step to the triggering task id. Do not let the hook select a global top intervention task.

## Known-good shape

In `brain_task_orchestrator.py`:

- Add/maintain an `event_hook_multimodel_route(event, task_id)` classifier.
- Use existing deterministic signals:
  - `task_multimodel_intervention_reasons(task)`
  - `task_multimodel_certification_reasons(task)`
  - `task_multimodel_advisory_reasons(task)`
- Support env controls:
  - `HERMES_TASKPOOL_EVENT_HOOK_MULTIMODEL=auto` default smart route
  - `=0/false/off` force disabled
  - `=1/true/force` force enabled
- Include `multimodel_route` in event hook logs and concise add/transition output.

In `brain_task_dispatch_tick.py`:

- Support `--multimodel-task <task_id>`.
- If `--multimodel-step` is enabled and a task id is supplied, call `multimodel-intervention-step --task <task_id> --json`.

## Avoiding returncode 2 regressions

A common failure shape is:

`task_added -> dispatch_tick --multimodel-step -> long model work or wrong global task -> auto-close-review spawns another certification -> timeout/ERROR -> hook returncode 2`

Mitigations:

- Keep event-hook multi-model work smart-routed and task-scoped.
- In dispatch tick, run post-autorun auto-close with `HERMES_AUTO_CLOSE_REVIEW_TRIGGER_CERT=0` so it consumes existing certification but does not spawn nested model work.
- Give routed multi-model hooks their own bounded budget, e.g. `HERMES_TASKPOOL_EVENT_HOOK_MULTIMODEL_TIMEOUT` and `HERMES_TASKPOOL_EVENT_HOOK_MULTIMODEL_COMMAND_TIMEOUT`.

## Verification checklist

1. `python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/brain_task_dispatch_tick.py`
2. `python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json`
3. Add a P3 advisory test task and verify the event hook log has:
   - `status: OK`
   - `returncode: 0`
   - `multimodel_route.enabled: false`
   - no `--multimodel-step` in `cmd`
4. Check a known P2 evolution / certification task via the classifier and verify:
   - `multimodel_route.enabled: true`
   - `reason: smart_route_matched`
   - if actually invoked, `cmd` contains `--multimodel-step --multimodel-task <task_id>`
5. Archive any test task created for verification.
