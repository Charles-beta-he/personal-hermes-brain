# Taskpool certified auto-done loop

Session learning: when Hermes taskpool review tasks require multi-model certification, fail-closed must not mean "skip forever". The automated loop should analyze, pass, or return the task for another implementation round.

## Desired flow

1. Task reaches `review`.
2. `auto-close-review` checks whether the task trips the multi-model intervention router.
3. If no multi-model intervention is required, use the normal completion gate.
4. If multi-model intervention is required and `task_multimodel_passed(task)` is already true:
   - require a local JSON ratification artifact;
   - require ratification gate `PASS`;
   - require decision `LOOP_DONE`;
   - then continue through normal done gate and only then mark `done`.
5. If multi-model intervention is required and strong certification is missing:
   - trigger the multi-model certification step instead of only appending a skip;
   - `PASS + LOOP_DONE + artifact` continues to done gate;
   - `FAIL`, `ERROR`, or persisted `not_certified` returns the task to `retry` with evidence and retry metadata;
   - advisory-only statuses (`advisory_passed`, `PASS_ADVISORY_ONLY`) never authorize `done`.
6. Reconcile promotes due `retry` tasks back to `pending`; dispatch/autorun can then perform another correction loop.
7. Repeated or unsafe failures should eventually land in `blocked`, not spin silently.

## Status semantics

- Active: `proposed`, `pending`, `claimed`, `running`, `retry`, `review`, `blocked`.
- Terminal: `done`, `archived`, `expired`.
- `done` means the taskpool execution for that task is complete; it should not automatically re-enter active states. It may later be archived.
- `archived` is a quiet terminal state with no further lifecycle transitions.
- `expired` is terminal for execution and may be archived; it should not auto-resume.
- `blocked` is active but normally requires human/policy intervention before returning to `pending` or `retry`.

## Implementation checklist

- Ensure event hooks can call dispatch tick with both `--multimodel-step` and `--autorun-step`.
- Treat closeout ratification as strong certification, not advisory-only.
- Do not let prior advisory completion mask `review`/`running` closeout certification.
- In `auto-close-review`, replace pure skip-on-missing-certification with:
  - prior `FAIL`/`not_certified` -> save lifecycle transition to `retry`;
  - missing prior result -> run certification step;
  - certification `PASS/LOOP_DONE` -> continue done path;
  - certification `FAIL/ERROR` -> save lifecycle transition to `retry`;
  - ambiguous/no-result -> keep fail-closed and surface diagnostic.
- After `apply_lifecycle_status(..., "retry", ...)`, call `save_task(task)`; otherwise the command output may say `retry` while the task file remains `review`.

## Verification

- `python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py`
- `python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json`
- Run `auto-close-review --json` on a review task with persisted `multimodel_last_gate_status: FAIL` and verify:
  - `closed_count == 0`;
  - action is `return_to_retry`;
  - task file status is actually `retry`;
  - `retry_count` increments and `next_attempt_at` is set.
- Run the pass path only with a real local ratification artifact that satisfies `PASS + LOOP_DONE`.
