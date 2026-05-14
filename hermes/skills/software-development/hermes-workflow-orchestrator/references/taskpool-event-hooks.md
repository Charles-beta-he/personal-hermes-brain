# Taskpool event-hook routing pattern

Session learning: for Hermes/local-brain taskpool automation, cron should be treated as a fallback, not the primary flow trigger. When the user expects “一步接一步” task progression, inspect both the periodic runner and event hooks.

Durable pattern:

1. Keep the periodic cron runner as safety net:
   - `local-brain-taskpool-auto-completer`
   - script: `taskpool_dynamic_runner.py`
   - internally calls `brain_task_dispatch_tick.py --summary --autorun-step --no-state`

2. Add event hooks at mutation boundaries, not inside claim loops:
   - after `brain_task_orchestrator.py add`
   - after `ingest-inbox` creates tasks
   - after explicit `transition`
   - avoid firing from `claim` itself to prevent claim → hook → claim recursion

3. Event hook command should be bounded and non-recursive:
   - `brain_task_dispatch_tick.py --summary --autorun-step --no-state --print-always`
   - set a recursion guard env var such as `HERMES_TASKPOOL_EVENT_HOOK_DEPTH=1`
   - support `HERMES_TASKPOOL_EVENT_HOOK_DISABLED=1`
   - fail-soft: return hook status/log in the parent command result, but do not fail task creation/transition solely because the hook failed

4. Write event logs for later inspection:
   - `~/.hermes/state/taskpool_event_hooks/event-*.json`
   - include event, task_id, command, stdout/stderr tail, parsed summary, return code, timestamps

5. Avoid per-task-id policy bottlenecks for future tasks:
   - `auto_run_policy.json` should support project-scoped allow rules such as `projects: ["project:local-brain", ...]`
   - keep safety gates: allowlist, lane, command_id, workspace_roots, close_mode, max_seconds
   - bounded commands only; default to `review_only`, not automatic done

6. Verification recipe:
   - run `python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/brain_task_autorun_step.py`
   - run `python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json`
   - create a low-risk evolution/taskpool verification task under an allowlisted project
   - confirm add result includes `event_hook.status: OK`
   - confirm `event_hook.autorun.eligible/claimed/advanced == true`
   - confirm `to_status: review` and handoff/proof paths exist

Pitfalls:

- If a task is dispatchable but not progressing, check `auto_run_allowlist.json`, `auto_run_policy.json`, and `eligibility-check` before assuming the scheduler is broken.
- A cron schedule existing is not enough; event expectations require immediate mutation-triggered hooks.
- A policy that only lists concrete `task_ids` cannot support newly-created tasks without manual edits; use project-scoped policy plus strict command/workspace gates.
- Historical done-task proof debt should remain visible but should not block current active-task event dispatch if selfcheck/boundary checks pass.
