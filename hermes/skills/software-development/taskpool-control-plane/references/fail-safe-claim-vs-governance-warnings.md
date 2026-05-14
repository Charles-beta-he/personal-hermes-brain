# Fail-safe claim vs governance warnings

Durable lesson from taskpool control-plane debugging:

## Symptom
- Active tasks exist, but none are `running`/`claimed`.
- `eligibility-check` can still nominate a dispatchable P1 task.
- Dynamic-runner / dispatch tick reports `ERROR` and skips autorun advancement.

## Root cause pattern
The control plane may incorrectly treat global governance debt as a hard runtime blocker. Typical example:
- historical `done` tasks missing evidence
- `proof-check` becomes `FAIL`
- `evidence-spine` becomes `WARN`/non-PASS
- dispatch tick collapses that into fatal `errors`
- `autorun_step` is skipped even though the current P1 candidate is otherwise safe to claim

## Correct policy split
Hard blockers:
- kill switch enabled
- permission gate pending
- write allowlist / write guard failure
- current candidate is not dispatchable
- invalid autorun proof chain
- self-check failure that materially affects safe claim-and-handoff

Soft governance warnings:
- historical proof/evidence debt on unrelated completed tasks
- non-PASS `evidence-spine` caused by unrelated history
- multimodel dry-run advisories
- blocked sibling tasks that do not affect the current candidate

## Operational rule
If the pool has active work but nothing is in progress, and a P1 task is dispatchable with no hard blocker, manually advance one highest-priority P1 task to `claimed` as a fail-safe anti-idle action while you fix automation.

## Patch pattern
In dispatch-tick logic:
1. maintain separate `warnings` and `errors`
2. permit bounded autorun claim when only `warnings` exist
3. surface `warning_count` and detailed warning records in summary/log output
4. reserve `ERROR` exit semantics for genuine safety blockers
