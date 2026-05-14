# Taskpool event-hook rc=2 and certification routing

Durable lesson from debugging `task_added` hook failures:

## Symptom

`brain_task_orchestrator.py add ...` succeeds and the task is created, but the event-hook log under `~/.hermes/state/taskpool_event_hooks/` records:

- `event: task_added`
- `status: ERROR`
- `returncode: 2`
- empty stderr
- stdout is valid JSON from `brain_task_dispatch_tick.py`

Do not stop at the add command's return code. Inspect the hook JSON and then parse the embedded dispatch tick stdout.

## Diagnosis pattern

1. Open the latest hook log:
   - `ls -t ~/.hermes/state/taskpool_event_hooks/*.json | head`
2. Inspect top-level `returncode`, `cmd`, `stderr`, and parse `stdout` as JSON.
3. Look for the child step with non-OK status:
   - `multimodel_step`
   - `autorun`
   - `auto_close_review`
   - `dispatch`
4. If `auto_close_review.status == ERROR` with no per-task errors, suspect nested certification or timeout/resource churn rather than task creation failure.

## Fix pattern

Keep certification responsibility single-owner inside event-hook ticks:

- `--multimodel-step` may trigger multi-model certification.
- post-autorun `auto-close-review` should consume existing certification results only.
- Disable nested certification in dispatch-tick auto-close with `HERMES_AUTO_CLOSE_REVIEW_TRIGGER_CERT=0`.

Standalone/manual `auto-close-review` may keep `HERMES_AUTO_CLOSE_REVIEW_TRIGGER_CERT=1` so it can close the loop:

- missing certification -> trigger cert
- PASS + LOOP_DONE + local artifact -> done gate -> done
- FAIL/not_certified -> retry
- repeated inconclusive/over retry -> blocked

## Pitfall

Do not simply whitelist rc=2 as harmless just because the task was created. `created + derived_refresh` proves add succeeded, but the event-hook automation may still have a real downstream failure. Classify by embedded JSON step status first, then decide whether to tolerate, retry, or patch routing.
