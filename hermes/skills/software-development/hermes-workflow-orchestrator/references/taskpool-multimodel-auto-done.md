# Taskpool multi-model auto-done loop

Session learning: a fail-closed auto-done gate is not enough if it only skips review tasks that lack certification. For taskpool automation, missing certification must drive the next state transition.

Desired closed loop:

1. Review task enters auto-close-review.
2. If the task does not require multi-model intervention, use the normal lifecycle_gate + proof + second lifecycle_gate path.
3. If the task requires multi-model intervention and is not strongly certified:
   - trigger the multi-model certification step immediately;
   - treat advisory_passed / PASS_ADVISORY_ONLY as non-authoritative;
   - require PASS + LOOP_DONE + a local JSON ratification artifact before done.
4. If certification passes, refresh the task and continue the done gate.
5. If certification fails/errors or the task is already marked not_certified/FAIL, automatically return the task to retry with evidence and failure reasons; do not leave it indefinitely in review and do not silently skip.
6. Cron remains a fallback; event hooks should trigger dispatch with both --multimodel-step and --autorun-step where safe.

Implementation notes from the Hermes taskpool codebase:

- `auto-close-review` should not stop at `multimodel_certification_required_for_auto_done`; it should attempt certification or convert prior certification failure into `retry`.
- `closeout_ratification` should be a certification trigger, not advisory-only, for review/running tasks.
- A consumed advisory round must not mask later review/running closeout certification.
- When mutating a task via `apply_lifecycle_status(...)` inside helper paths, call `save_task(task)`; otherwise the returned status may appear in the result object but not persist to the task file.
- Safety invariant: advisory-only rounds may guide next action, but never authorize `done`.

Verification pattern:

```bash
python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py auto-close-review --max-tasks 2 --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py list --json
```

Expected outcomes:

- PASS + LOOP_DONE + artifact: task may proceed to done gate.
- FAIL / ERROR / not_certified: task moves to retry with evidence.
- PASS_ADVISORY_ONLY: no done authorization.
