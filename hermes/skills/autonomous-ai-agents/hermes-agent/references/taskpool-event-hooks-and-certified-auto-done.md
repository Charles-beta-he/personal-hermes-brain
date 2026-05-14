# Taskpool event hooks and certified auto-done

Update: keep `task_added` event hooks bounded by default. Do not run long multi-model certification from every add hook; require `HERMES_TASKPOOL_EVENT_HOOK_MULTIMODEL=1` to opt in. When `dispatch_tick` calls post-autorun `auto-close-review` inside a hook, inject `HERMES_AUTO_CLOSE_REVIEW_TRIGGER_CERT=0` so auto-close consumes existing certification instead of spawning nested model discussions. See `references/taskpool-event-hook-debugging.md` for the returncode-2 diagnosis and verification recipe.

Session-derived pattern for Hermes taskpool automation.

## Event hook should be primary; cron is fallback

For taskpool flow, do not rely on periodic cron as the main progress mechanism. Use event hooks after durable task mutations, with cron only as recovery/fallback.

Recommended chain:

1. `brain_task_orchestrator.py add` / `ingest-inbox` / `transition` writes the task mutation.
2. Fire a non-recursive event hook.
3. Event hook runs `brain_task_dispatch_tick.py --summary --autorun-step --no-state --print-always`.
4. If model certification may be needed, include `--multimodel-step` and set `HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1`.
5. Keep cron such as `local-brain-taskpool-auto-completer` as a delayed safety net only.

Non-recursion guard:

- Use an env depth flag such as `HERMES_TASKPOOL_EVENT_HOOK_DEPTH`.
- Allow opt-out such as `HERMES_TASKPOOL_EVENT_HOOK_DISABLED=1`.
- Log hook results under `~/.hermes/state/taskpool_event_hooks/`.

## Project-level autorun policy

If event hooks require manual insertion of every new task id into policy, the flow is not truly event-driven. Prefer project-level policy plus allowlist:

- `auto_run_policy.json` supports `projects` in addition to exact `task_ids`.
- Validate against `auto_run_allowlist.json` as a second gate.
- Keep bounded command ids, workspace roots, max seconds, and close mode (`review_only` unless certified closeout is intended).

## Certified auto-done boundary

For review -> done automation, distinguish advisory consensus from completion authority.

Fail-closed rule:

- `advisory_passed` / `PASS_ADVISORY_ONLY` may consume weak advisory triggers but must not authorize `done`.
- Tasks routed through `task_multimodel_intervention_required(task)` must satisfy strong certification before auto-close.
- Strong certification means `task_multimodel_passed(task)` is true: local JSON ratification artifact exists, `ratification_gate_result(...)` returns `PASS`, and decision is `LOOP_DONE`.
- Then still run normal `lifecycle_gate(task, "done", ...)`, mint autorun proof, and run the lifecycle gate again before applying `done`.

Closeout escalation:

- Treat `closeout_ratification` as a certification trigger, not advisory-only.
- Prior `PASS_ADVISORY_ONLY` should not suppress review/running closeout certification.
- If certification fails, keep task in `review` with `multimodel_status: not_certified`, `multimodel_round_status: failed`, and a visible skip reason such as `multimodel_certification_required_for_auto_done`.

## Verification checklist

- `python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py`
- `python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json`
- `brain_task_orchestrator.py multimodel-intervention-dry-run --json` should show closeout tasks as `advisory_only: false` with `certification_reasons: ["closeout_ratification"]`.
- `brain_task_orchestrator.py auto-close-review --json` should skip un-certified intervention tasks, not close them.
