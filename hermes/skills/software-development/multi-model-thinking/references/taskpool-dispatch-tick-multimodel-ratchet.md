# Taskpool dispatch tick multimodel ratchet

Use this when hardening `brain_task_dispatch_tick.py`, cron safe-summary ticks, or taskpool multimodel autorun wrappers.

## Problem pattern

A safe cron/summary tick can accidentally start an expensive long-running T3 multimodel step when it inherits ambient `HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1`. This violates the expected cheap/safe tick semantics and can leave orphan `consult_models.py` processes after a wrapper timeout.

## Fail-closed contract

1. Require a deliberate CLI flag and an env gate for expensive multimodel work:
   - flag: `--multimodel-step`
   - env: `HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1`
   - ambient env alone must return a structured `SKIP`, not start the step.
2. The step status `SKIP` must be an allowed/non-error status for safe ticks when the explicit flag/env gate is absent.
3. Long-running subprocesses must run in a new process group/session.
4. On timeout, terminate the whole process group, not only the parent process:
   - send `SIGTERM` to the process group;
   - wait a small grace period;
   - send `SIGKILL` to the process group if still alive;
   - return structured JSON with `reason=subprocess_timeout`, `timeout_seconds`, `terminate_grace_seconds`, and process-group cleanup flags.
5. Do not traceback on timeout in cron/tick output; cron artifacts should remain parseable.
6. Static ratchets that inspect generated commands must parse with `shlex` and require exact flags/values. Substring checks are unsafe: `--tier T30` must not satisfy `--tier T3`, and `--quorum 40` must not satisfy `--quorum 4`.

## Verification pattern

Run both deterministic and real-process tests:

- `py_compile` for the wrapper and tests.
- Unit tests for:
  - ambient env without `--multimodel-step` returns `SKIP`;
  - `--multimodel-step` without env returns `SKIP`;
  - env + flag starts the intended step path;
  - timeout returns structured JSON and leaves no orphan child.
- A stubborn child fixture that ignores `SIGTERM` proves process-group `SIGKILL` cleanup really happens.
- Real-vault gates after the patch:
  - `brain_task_orchestrator.py selfcheck --json`
  - `brain_task_orchestrator.py lifecycle --json`
  - `brain_task_orchestrator.py proof-check --json`
  - evidence-spine/selfcheck/proof/lifecycle/autonomy-readiness
  - dispatch tick safe summary
  - multimodel keypoint coverage ratchet should remain 100%.

## Commit discipline

If the tool/context budget is near exhaustion, commit immediately after deterministic gates and scoped diff checks pass. Stage only the patched wrapper/ratchet/test files, run `git diff --cached --check`, then commit locally; do not push by default.