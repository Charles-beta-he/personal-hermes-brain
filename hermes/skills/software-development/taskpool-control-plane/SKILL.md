---
name: taskpool-control-plane
description: Diagnose and operate the local brain/taskpool control plane — dispatch tick, autorun, eligibility, proof/evidence governance, and fail-safe claim behavior when the pool is stalled.
---

# Taskpool Control Plane

Use when:
- The user asks why the task pool is stalled, empty-running, or has no in-progress work.
- `dashboard`/`status` shows active tasks but nothing is `running`/`claimed`.
- You need to inspect `brain_task_dispatch_tick.py`, `autorun-runner`, `eligibility-check`, proof/evidence gates, or reconcile state.
- See `references/reconcile-gating-and-proof-debt.md` for the proven triage path when dispatch recovers from historical proof debt but still appears stalled behind reconcile/allowlist gates.


## Core principle

The fail-safe objective is: taskpool must not idle-spin when there is a dispatchable priority task.

Treat these as separate concerns:
1. Can a concrete task be safely claimed right now?
2. Is the control plane globally healthy/governed?

Global governance warnings should be surfaced, but they should not automatically block bounded claim-and-handoff for an otherwise dispatchable P1 task.

## Fast triage flow

1. Inspect whether the pool is actually empty.
   - Check active task count and status distribution (`pending`, `blocked`, `claimed`, `running`, `done`).
   - Do not assume `0 running` means `0 work`.

2. Check whether a dispatchable task exists.
   - Run `eligibility-check` and inspect the selected task id / reasons.
   - Inspect `dashboard` or `list` output to confirm the highest-priority candidate.

3. Check whether the control plane is blocked by hard safety gates or only soft governance warnings.
   - Hard blockers usually include: kill switch, permission gate pending, write allowlist/guard failure, current task not dispatchable, invalid autorun proof chain, or self-check failure that affects safe claim.
   - Soft governance warnings include: historical `done` tasks missing evidence, proof-check failures unrelated to the current candidate, evidence-spine `WARN`, or dry-run multimodel advisories.

4. If active work exists but nothing is `claimed`/`running`, manually advance one highest-priority dispatchable P1 task to `claimed` as fail-safe.
   - This is a temporary anti-idle action, not a substitute for fixing automation.
   - Prefer the same task `eligibility-check` nominates.

5. Then fix the automation path.
   - Inspect `brain_task_dispatch_tick.py` behavior and taskpool dynamic-runner logs.
   - Verify the tick distinguishes hard errors from soft governance warnings.

## Manual anti-idle rule

If all of the following are true:
- active tasks exist,
- no task is currently `claimed` or `running`,
- at least one P1 task is dispatchable,
- no hard safety blocker is present,

then manually push one highest-priority P1 task to `claimed`.

Rationale: the scheduler’s fail-safe job is to prevent taskpool empty-spin. `blocked` siblings or historical `done`-task evidence debt should not freeze the entire pool.

## Control-plane diagnosis checklist

Use this order:
1. `dashboard` / `list` / status distribution
2. `eligibility-check`
3. `autorun-runner`
4. `proof-check`
5. `evidence-spine`
6. `selfcheck`
7. taskpool dynamic-runner JSONL logs
8. dispatch tick source/tests if behavior still looks wrong

This ordering keeps you from over-indexing on historical governance debt before confirming whether a concrete task can already be claimed.

## Implementation guidance for dispatch tick fixes

When patching dispatch logic:
- Separate `warnings` from `errors`.
- Keep fail-closed behavior for true safety blockers only.
- Allow bounded `autorun_step` / claim-and-handoff to proceed when only soft governance warnings are present.
- Return a visible non-OK status such as `WARN` when governance is unhealthy, but do not convert that into an execution stop by default.
- Preserve observability: emit warning/error counts and retain the specific failing governance step in the payload/log.

## Pitfalls

- Do not equate `proof-check FAIL` with `current task unsafe to claim` without checking why it failed.
- Do not let historical `done task missing evidence` automatically block the only dispatchable priority task.
- Do not “fix” the symptom only by manual claim; always inspect and repair the tick/runner policy afterward.
- Do not collapse all non-PASS control-plane signals into one fatal bucket.

## Verification

After a fix or manual intervention, verify:
1. A previously dispatchable P1 task moves to `claimed` (or `running` if your flow does that next).
2. The tick payload/log shows either `OK` or `WARN`, not a false `ERROR` caused only by unrelated governance debt.
3. Governance issues remain visible in logs/payloads for later cleanup.
4. Dynamic-runner / cron continues to make forward progress on subsequent ticks.

## References
- `references/dispatch-gate-triage.md` — triage flow for taskpool stalls where historical evidence debt is already softened but `next`/`eligibility-check` still block on reconcile or apparent allowlist misses.
- `references/dispatch-tick-soft-governance-gating.md` — distinguishes historical proof/evidence debt from live eligibility gates (`allowlist_miss`, `reconcile_required`) when tick is OK but no task is claimed.
- `references/taskpool-dispatch-soft-governance-gating.md` — how to distinguish historical proof/evidence debt from safety-critical dispatch blockers; includes the runtime-only pitfall where `unstructured evidence in ...` still trips dispatch tick.

- `references/fail-safe-claim-vs-governance-warnings.md` — policy note on separating anti-idle claim behavior from historical proof/evidence debt.