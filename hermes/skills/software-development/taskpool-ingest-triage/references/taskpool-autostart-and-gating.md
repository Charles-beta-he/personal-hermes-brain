# Taskpool autorun bootstrap and non-blocking governance

Durable lessons from diagnosing a taskpool that had active tasks but no in-progress work.

## User operating preference
- Goal of the fallback path is to prevent the taskpool from idling.
- If active tasks exist but nothing is in progress, manually advance one highest-priority dispatchable P1 task to `claimed` as a fail-safe bootstrap.

## Diagnostic pattern
1. Confirm the pool is not empty: inspect active count and per-task statuses.
2. Separate `pending/blocked/claimed/running` counts; do not equate `active` with `in progress`.
3. Run `eligibility-check` to verify a concrete dispatchable task exists.
4. If the timer/tick path says `dispatchable: true` but no task advances, inspect the dispatch tick summary/log and compare it with `autorun-runner`.
5. If needed, run the bounded autorun path manually to claim one task and verify the pool is no longer idle.

## Critical implementation lesson
The timer/dispatch-tick path may be stricter than the bounded autorun runner.

Observed durable pattern:
- `dispatch tick` can treat global governance failures as hard blockers before autorun executes.
- Historical `done` tasks missing evidence can make `proof-check` fail.
- That can degrade `evidence-spine` to WARN/FAIL and make the tick return `ERROR`.
- Result: no automatic claim occurs even when a specific next task is dispatchable.
- Meanwhile `autorun-runner` / `auto-claim-and-handoff` can still successfully claim a task because they validate task eligibility and autorun proof-chain safety, not all historical done-task evidence.

## Operational rule
When diagnosing "why is nothing in progress?", do not conclude that blocked tasks or unrelated done-task evidence gaps should semantically block execution. Treat this as a control-plane coupling bug or over-strict gate unless the current task itself fails safety/permission/dispatchability checks.

## Recommended remedy shape
- Keep fail-closed blocking only for current-task safety issues: kill switch, permission gate, write guard, current task not dispatchable, broken autorun proof chain, selfcheck failure relevant to claiming.
- Downgrade unrelated historical governance gaps to warnings/telemetry for bootstrap claim flow.
- Preserve a manual P1-to-claimed fallback when the taskpool has active work but no in-progress task.
