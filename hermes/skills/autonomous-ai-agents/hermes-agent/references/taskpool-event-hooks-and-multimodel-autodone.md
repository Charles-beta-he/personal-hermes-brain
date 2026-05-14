# Taskpool event hooks + multi-model certified auto-done

Use this reference when extending Hermes/local-brain taskpool dispatch, autorun, or review->done automation.

## Durable workflow lesson

The taskpool should be event-driven first, with cron only as a fallback. When users expect tasks to "walk down the pipeline", do not only inspect cron. Check and repair the event path:

1. `brain_task_orchestrator.py` mutations (`add`, `ingest-inbox`, `transition`) should call an event hook after successful state changes.
2. The hook should run a bounded tick similar to:
   `brain_task_dispatch_tick.py --summary --autorun-step --no-state --print-always`
3. Guard recursion with an env var such as `HERMES_TASKPOOL_EVENT_HOOK_DEPTH`.
4. Write hook logs under `~/.hermes/state/taskpool_event_hooks/`.
5. Keep cron jobs such as `local-brain-taskpool-auto-completer` as missed-event/host-sleep fallback, not the primary driver.

## Autorun policy lesson

Event hooks are not enough if policy requires pre-known task IDs. For newly created tasks, support project-level policy:

- `auto_run_policy.json` may include `projects` entries like `project:local-brain`.
- Validate against both exact `task_ids` and project membership.
- Still fail closed through allowlist, lane, command ID, workspace root, timeout, and close-mode checks.

## Multi-model auto-done safety boundary

For review->done automation, distinguish advisory from certification:

- `PASS_ADVISORY_ONLY` / `advisory_passed` means the advisory round completed; it must not authorize `done`.
- Strong auto-done for multi-model intervention tasks requires a certified result, e.g. `task_multimodel_passed(task)`.
- A robust `task_multimodel_passed` check should require:
  1. pass status in the task frontmatter;
  2. a local JSON ratification artifact path;
  3. artifact parses successfully;
  4. `ratification_gate_result(...)` returns `status == PASS` and `decision == LOOP_DONE`.
- For tasks where `task_multimodel_intervention_required(task)` is true, `auto-close-review` should skip unless the strong certified check passes.
- Skip reason should be explicit, e.g. `multimodel_certification_required_for_auto_done`.
- After certification, still run the normal lifecycle/completion gate and mint an autorun proof before `apply_lifecycle_status(..., "done")`.

## Verification pattern

Verify both sides:

1. Static checks:
   - `python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py`
   - `python3 -m py_compile ~/.hermes/scripts/brain_task_autorun_step.py`
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json`
2. Negative path:
   - Put a multi-model-required task in `review` without a PASS/LOOP_DONE artifact.
   - Run `auto-close-review --json`.
   - Expect `closed_count == 0` and skip reason `multimodel_certification_required_for_auto_done`.
3. Event path:
   - Add a safe test task under an allowlisted project.
   - Confirm event-hook log shows the dispatch tick command and autorun result.
4. Positive path:
   - Only after a real local JSON ratification artifact passes `PASS/LOOP_DONE`, confirm `auto-close-review` can close the task.

## Pitfalls

- Do not treat `advisory_passed` as completion authority.
- Do not make cron the only scheduler when the user expects immediate flow-through.
- Do not require exact task ID policy for future tasks unless the event creator also updates policy; prefer project-level policy plus allowlist for event-driven flows.
- Do not let hook failures break the original successful mutation; log them and fail soft.
- Do not recursively trigger hooks from hooks.