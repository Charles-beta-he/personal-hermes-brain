# Local Brain Autorun Bridge — fail-closed pattern

Use when analyzing or implementing automatic dispatch/execution for the local-brain Markdown task pool.

## Session learning

A safe task pool can already have `dispatch-dry-run` and a no-agent cron but still lack an execution bridge. Distinguish these layers:

- **Safe dispatch hint**: ingest/reconcile/dashboard/proof-check/next-task hint; no mutation beyond derived dashboard/reconcile.
- **Auto-claim and handoff**: optional, kill-switch-gated bridge that claims exactly one eligible task and writes a bounded handoff/proof head.
- **Execution runner**: external bounded agent/process that performs work under scope/budget constraints.
- **Proof-gated completion**: status can reach `done` only through review/proof gates, not because a tick says execution succeeded.
- **Explicit permission taxonomy**: classify taskpool authority separately from lifecycle status. Minimum tiers: `dispatch-hint` (read/control-plane hint only), `claim-and-handoff` (bounded local task-state mutation), `budget-handoff` (model/quota/router-certified budget delegation), `autonomous-execution` (write-capable execution with explicit enable file), and `yolo-execution` / `--yolo` (highest-risk no-approval Hermes/Codex execution). `HERMES_YOLO_MODE=1` or Codex `--yolo` only bypasses approval prompts; it is not a completion proof and must not bypass ownership, structured evidence, or autorun proof-hash gates.
- **Known surface vs allowlist**: `autonomy-write-guard.py` requires both a known write surface and allowlist membership. If `taskpool` appears in `autonomy-write-allowlist.json` but is absent from `WRITE_SURFACES`, the guard still fails with `known_write_surface`; fix the taxonomy rather than treating the allowlist as sufficient.
- **Yolo invariant from T3 advisory**: a 4-planner run can ground the facts but still return `not_certified` if any proposed patch lets `yolo-execution` bypass lifecycle/approval/proof gates. The safe invariant is: `--yolo`/`HERMES_YOLO_MODE=1` is an execution-approval authority tier only; it must never satisfy `review -> done`, structured evidence, owner/lease, boundary, or autorun `proof:sha256` requirements. Add regression tests for this invariant before landing taxonomy code.

## Evidence checklist

Check these files/behaviors before answering or changing anything:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
sed -n '1,120p' ~/.hermes/scripts/brain_task_dispatch_tick.py
sed -n '1,260p' ~/.hermes/scripts/brain_task_budget_tick.py
```

Look for explicit wording such as:

- `brain_task_dispatch_tick.py`: control-plane tick, not autonomous executor; never executes task Markdown; calls `dispatch-dry-run` only.
- `brain_task_orchestrator.py dispatch-dry-run`: safety says dry-run only; does not claim or execute.
- `brain_task_budget_tick.py`: handoff helper, not executor; default no claim/execute; mutation policy requires explicit proof-gated claim/done/retry.
- `Agent技能树路由矩阵`: Safe Dispatch and Execution are separate stages.
- Evolution log: safe tick can find next task but does not cron auto-execute.

## P10 design rule

Do **not** implement or recommend “execute Markdown task body then mark done.” Task notes are workpads, not scripts. Arbitrary Markdown hooks are hook overreach unless explicitly allowlisted in a workflow contract.

Prefer the name and behavior:

```text
auto-claim-and-handoff
```

Avoid:

```text
auto-claim-and-execute
execute task Markdown body
mark done on runner success
```

## Minimal merged patch sequence

### P0 — deterministic eligibility and handoff only

Add/read an orchestrator command shaped like:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py eligibility-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py auto-claim-and-handoff --json
```

Required behavior:

- default deny unless `HERMES_LOCAL_BRAIN_AUTORUN=1`;
- default deny when allowlist file is missing or empty;
- verify dispatchable, no active/stale claim, retry ceiling, non-expired, budget availability, and proof checklist;
- atomically claim exactly one task and read back `claimed_by/run_id/claim_expires_at`;
- write handoff artifact and append proof head;
- do not read task body, spawn arbitrary subprocesses, or write `done`.

### P1 — optional bridge in safe tick

Keep the existing safe tick hint-only by default. Only when kill switch and eligibility pass, add an optional `autorun` event that calls `auto-claim-and-handoff`. If ingest/reconcile/dashboard/proof-check/dispatch has an error, skip autorun and log denial reasons.

### P2 — proof and observability

- `~/.hermes/state/auto_run_allowlist.json`: empty/missing means deny all.
- `~/.hermes/state/auto_run_proof.jsonl`: append-only sha256 chain with `{ts, task_id, run_id, action, prev_hash, hash}`.
- If actor/run_id indicates autorun, `done` requires structured evidence like `proof:<sha256>` and must pass through `review -> done`.
- Selfcheck covers: dry-run no mutation, autorun off no mutation, empty allowlist no claim, low-confidence quota fail-closed, proof hash-chain validation, runner error never done.

## Fail-closed gates

Apply in order:

1. kill switch unset/0 ⇒ deny;
2. allowlist missing/empty ⇒ deny;
3. eligibility check fail ⇒ deny before claim;
4. upstream tick status not OK/PASS ⇒ deny autorun;
5. budget doctor/quota unknown or advisory ⇒ deny or handoff-only;
6. lease read-back mismatch ⇒ release/retry + alert;
7. retry ceiling exceeded ⇒ block/review;
8. proof missing/hash-chain broken ⇒ block done;
9. selfcheck fail ⇒ autorun disabled;
10. runner error ⇒ release/retry, never done.

## Implementation lessons from landed P0 bridge

- After `command_claim`, re-read the task and verify `status=claimed`, `claimed_by`, `run_id`, and `claim_expires_at`. On mismatch, fail closed and attempt a force release back to `pending` with an audit reason. Do not write a handoff against an unverified lease.
- Treat proof/handoff creation as part of the claim transaction boundary: if append-only proof JSONL or handoff write fails, fail closed and attempt to release the claim. Never leave a claimed autorun task without a durable handoff/proof head.
- Test isolation matters: make state/log dirs overrideable (`HERMES_BRAIN_AUTORUN_STATE_DIR`, `HERMES_BRAIN_DISPATCH_TICK_STATE_DIR`, `HERMES_BRAIN_DISPATCH_TICK_LOG_DIR`) so regression tests do not touch production `~/.hermes/state` or logs.
- Add tests for both disabled production mode and enabled fixture mode: default tick has no `autorun` block; `--autorun` with kill switch off denies with no claim; kill switch + allowlist claims exactly one fixture task and writes proof/handoff only.
- Certification evidence should include both deterministic commands and claim-linked evidence. If a multi-model discussion emits an evidence request to inspect its own `discussion_result.json`, inspect it before finalizing and confirm `issue_ledger=[]`, votes approve, and `remaining_risks=[]`.

## Multi-model interpretation

If multi-model truth gate verifies “autorun is missing” but the implementation plan has unresolved severity>=3 issues, keep the result `not_certified`. Do not upgrade to certified merely because the factual diagnosis is grounded. Truth grounded ≠ design certified.
