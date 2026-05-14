# Multi-model certified auto-close loop

Use this reference when improving or debugging Hermes taskpool review→done automation.

## Desired state machine

For review tasks that require multi-model intervention, auto-close must be a full loop, not a passive skip:

1. If strong certification already passed, continue to the normal done gate.
2. If certification is missing, trigger the certification step.
3. If certification returns PASS + LOOP_DONE with a local JSON ratification artifact, write/refresh the task certification fields and continue to the done gate.
4. If certification returns FAIL/ERROR or the task already records `multimodel_status: not_certified` / `multimodel_last_gate_status: FAIL|ERROR`, move the task to `retry` with evidence and zero delay.
5. If certification is inconclusive (`no_discussion_result`, `SKIP`, `PASS_ADVISORY_ONLY`, missing artifact/status, parse ambiguity), move to `retry` and increment an uncertainty counter.
6. If uncertainty repeats (e.g. >=3) or retry budget is exceeded, move to `blocked` to avoid infinite automation.
7. If the certification worker reports a different task than the one being auto-closed, leave the current task in `review` with diagnostics; do not apply another task's certification result.

## Non-negotiable done authority

`advisory_passed` / `PASS_ADVISORY_ONLY` is not done authority. Strong done authority requires:

- local JSON ratification artifact;
- ratification gate status PASS;
- decision LOOP_DONE;
- task identity matches the task being closed;
- normal lifecycle `done` gate still passes after certification.

## Evidence to persist on retry/blocked

Add compact evidence markers so later ticks and humans can explain the decision:

- `artifact:<discussion-or-ratification-path>` when available;
- `multimodel_gate:<PASS|FAIL|ERROR|SKIP|PASS_ADVISORY_ONLY>`;
- `multimodel_decision:<LOOP_DONE|continue_loop|...>`;
- `multimodel_status:<certified|not_certified|advisory_completed|...>`;
- `multimodel_auto_outcome:<certification_failed|certification_inconclusive|...>`.

## Terminal statuses

`done`, `archived`, and `expired` are terminal for execution. `done` means the taskpool execution for that task is finished; it may later be archived, but should not automatically re-enter pending/retry/review. `expired` may archive but should not auto-resume. `archived` has no lifecycle exits.

## Pitfalls

- Do not implement “missing certification ⇒ skip” as the final behavior. That is fail-closed but not automated. It must trigger certification or a retry/blocked transition.
- Always save the task after calling lifecycle mutation helpers; mutating in memory without `save_task(...)` makes JSON output look successful while the task file remains unchanged.
- Avoid global certification result leakage: if the certification step selected another task, do not retry/done the current task based on that result.
- Keep PASS path and FAIL path separate: PASS may proceed to done gate; FAIL/inconclusive may only retry or block.
