# Autonomy Write Guard Caller Integration Pattern

Use this reference when hardening local-brain taskpool autorun, budget handoff, gateway actions, or any caller that can mutate external state.

## Core lesson

A standalone write guard CLI/API is not enough. The real mutating caller must invoke the guard immediately before it claims, hands off, writes proof, posts externally, or otherwise mutates state. Certification remains advisory until caller-level integration is proven by regression tests.

Safe shape:

```text
caller receives intent -> guard_or_raise(surface, operation, mode, allowlist) -> bounded mutation -> proof/audit event
```

For local brain taskpool autorun, the bounded control-plane operation is `claim-and-handoff`, not general task execution.

## Required semantics

1. Keep control-plane handoff separate from external writes.
   - Example control-plane operation: `claim-and-handoff`.
   - It may claim a task, create a bounded handoff, and write a proof event.
   - It must not execute Markdown task bodies, run arbitrary hooks, or mark tasks done.
2. `claim-and-handoff` should be allowed only in `dispatch-hint` mode unless a later certified design adds stronger gates.
3. Surface allowlist still applies in dispatch-hint mode. Do not let `mode == dispatch-hint` bypass the central write-surface allowlist.
4. Missing/empty allowlist must fail closed before any mutation.
5. Missing dispatch precondition must fail closed before any mutation.
6. External write surfaces such as `google-workspace write` remain blocked unless autonomy preconditions, quota confidence, router readiness, and surface allowlist all pass.
7. Caller output should preserve machine-readable guard evidence, for example `status=FAIL_CLOSED`, `reason=autonomy_write_guard_failed`, `claimed=false`, and a nested `write_guard` object.

## Regression tests to require

For the caller that invokes the guard:

- Without the central write-surface allowlist entry, `auto-claim-and-handoff` or equivalent returns fail-closed and leaves the task pending/unmodified.
- With the required surface allowlist entry, the positive path still performs only the bounded control-plane mutation: claim + handoff + proof; no execution and no automatic done.
- The cron/tick bridge with `--autorun` also requires the same central write-surface allowlist; CLI opt-in alone is insufficient.
- A representative external write, such as `google-workspace write` in `budget-handoff` mode, still fails closed while router/quota/autonomy gates are not certified.
- Add py_compile or equivalent import checks for both guard and caller files.

## Evidence commands

Typical Hermes verification slice:

```bash
python3 -m py_compile ~/.hermes/scripts/autonomy-write-guard.py ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/brain_task_dispatch_tick.py ~/.hermes/scripts/test_brain_task_orchestrator.py ~/.hermes/scripts/test_brain_task_dispatch_tick.py
python3 ~/.hermes/scripts/test_brain_task_orchestrator.py
python3 ~/.hermes/scripts/test_brain_task_dispatch_tick.py
python3 ~/.hermes/scripts/autonomy-write-guard.py --surface google-workspace --operation write --mode budget-handoff --json --gate
python3 ~/.hermes/scripts/autonomy-precondition.py --mode budget-handoff --json --gate
python3 ~/.hermes/scripts/model_quota.py confidence-gate --json --gate
python3 ~/.hermes/scripts/model-router.py readiness --json --gate
python3 ~/.hermes/scripts/ratification_gate.py --json
```

Expected current safe interpretation: deterministic caller tests may pass, while quota/router/autonomy/ratification gates still fail closed. Report this as `truth_grounded_advisory` / `not_certified_for_autonomous_execution`, not as autonomous execution certification.

## Commit/evidence pitfall

If updating the local brain evidence note during this work, sync before editing or verify/reapply after sync: `brainctl sync` can pull remote note content and overwrite unsynced local edits. After syncing, reindex/search for the new section so the evidence ledger is actually retrievable.
