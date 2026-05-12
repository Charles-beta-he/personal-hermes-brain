---
type: backlog
status: active
created: 2026-05-07
project: resumable-multimodel-certification
level: P9
---

# P9 - Implementation Backlog

## P0 — Contract and Audit

Status: implemented and certified for the RMCS implementation scope in `/Users/charles/.hermes/tick-20260507-112446`.

Evidence:

- `audit-certification` exists and writes `final/certification_manifest.json`.
- Missing `discussion_result.json` fails closed as `partial_uncertified`.
- Current certification tick manifest `/Users/charles/.hermes/tick-20260507-112446/final/certification_manifest.json`: `status=certified`, `can_claim_complete_certification=true`.

### RMCS-P0-001 Certification state enum

Define status values:

- `planning_only`
- `fanout_complete_uncertified`
- `discussion_partial_uncertified`
- `discussion_complete_not_certified`
- `discussion_complete_certified`
- `timed_out_uncertified`
- `degraded_uncertified`
- `corrupt_artifact_uncertified`

Acceptance:

- Missing `discussion_result.json` never returns certified.
- Existing tick with only `merged_plan.json` returns `fanout_complete_uncertified`.

### RMCS-P0-002 Tick artifact manifest

Create schema for:

- run manifest;
- planner outputs;
- discussion checkpoint files;
- final certification manifest.

Acceptance:

- Manifest validates complete and partial ticks.
- Sensitive fields are not persisted.

### RMCS-P0-003 `audit-certification <tick_dir>`

Read-only command returning certification status JSON.

Acceptance:

- No model calls.
- Runtime under 5s on recent ticks.
- Corrupt/missing files fail closed.

## P1 — Checkpoint and Resume

Status: implemented and certified for the RMCS implementation scope in `/Users/charles/.hermes/tick-20260507-112446`.

Evidence:

- Per-model checkpoint artifacts are written as `discussion/round_NNN/model_response_<model>.json` and `parse_status_<model>.json`.
- Cursor/state/heartbeat are updated after each model checkpoint.
- `resume-discussion` can materialize missing `discussion_result.json` + final manifest from existing tick artifacts.

### RMCS-P1-001 Per-model checkpoint

Persist raw + parsed response after each discussion model call.

Acceptance:

- Killing process after a model response preserves that response.
- Parse failures are recorded, not discarded.

### RMCS-P1-002 Per-round summary checkpoint

Persist round input, votes, issue ledger delta, evidence requests, and status.

Acceptance:

- Round can be audited without reading terminal logs.

### RMCS-P1-003 `resume-discussion <tick_dir>`

Continue from cursor.

Acceptance:

- Does not repeat completed model calls unless `--force-rerun-model` is passed.
- Forced timeout test resumes to final artifact.

## P2 — Background-safe Runner

Status: implemented and certified for the RMCS implementation scope in `/Users/charles/.hermes/tick-20260507-112446`.

Evidence:

- `rmcs-runner` is bounded by `max_ticks`.
- Runner writes `state/rmcs-runner-status.json` and `state/rmcs-runner-last.json`.
- Partial artifacts remain uncertified until discussion and manifest gates pass.

### RMCS-P2-001 Background status/heartbeat

Write heartbeat/status JSON during long discussion.

Acceptance:

- Stale heartbeat detected.
- Timeout is recorded as `timed_out_uncertified`.

### RMCS-P2-002 Cron-safe wrapper

Wrapper always emits non-empty JSON and uses process-group kill on timeout.

Acceptance:

- No cron empty response.
- Partial artifacts are preserved.

## P3 — Evidence-first Workflow

Status: partially implemented for certification evidence gates; broader evidence-request work queue remains future enhancement.

Implemented evidence:

- `state` supports claims/evidence and truth gate.
- RMCS selfcheck has optional `--certification-tick` gate that fails closed unless `discussion_result.json` + `final/certification_manifest.json` support `can_claim_complete_certification=true`.
- Regression tests cover missing discussion, missing/false manifest, clean certified artifact chain, strict booleans, malformed issue/vote/fanout artifacts, agreement floor, gate-requirement-not-proof, safe severity parsing, no blanket blocker resolution, and noop-supermajority vs balanced noop/change behavior.

### RMCS-P3-001 Evidence request export

Export model evidence_requests as orchestrator work queue.

Acceptance:

- Evidence requests are deduplicated.
- High-severity unsupported claims block certification.

### RMCS-P3-002 Evidence refill state builder

Allow state to be rebuilt with verified evidence links.

Acceptance:

- Truth gate reports grounded before ratification.

## P4 — Optional parallelism

### RMCS-P4-001 Same-round parallel model calls

Only after checkpoint/resume/audit are stable.

Acceptance:

- Deterministic aggregation order.
- Provider concurrency budget respected.

## Deferred Backlog

### DEFERRED-TASKCREATE-RALPH

`TaskCreate -> 下一轮 ralph 入口自动串联` waits until RMCS P0-P2 are complete and self-check PASS.

Acceptance before reopening:

- audit-certification exists;
- resume-discussion exists;
- background runner exists;
- partial discussion cannot be certified;
- TaskCreate runtime fixture can be ratified using RMCS.


## r10 closure evidence

- Final certified tick: `/Users/charles/.hermes/tick-20260507-112446`.
- Tests: 60 OK.
- Added regression coverage: runtime/selfcheck safe numeric parser bool + NaN/Infinity rejection and independent evidence kind/type canonicalization.
- Prior r9 not_certified tick `/Users/charles/.hermes/tick-20260507-081025` retained as provenance only.


## r12 closure evidence

- Final certified tick: `/Users/charles/.hermes/tick-20260507-112446`.
- Tests: 64 OK.
- Added regression coverage: conditional `add_verifier` proposals are advisory/evidence requests, while unconditional verifier patches still block noop/change splits.
- Prior r11 not_certified tick `/Users/charles/.hermes/tick-20260507-112446` retained as provenance only.


## r13 closure evidence

- Final certified tick: `/Users/charles/.hermes/tick-20260507-112446`.
- Tests: 65 OK.
- Fresh T3: 4 planner successes, 4 approval votes, 0 rejects, all best-within-constraints true.
- Reviewer blocker fixed: unconditional minority verifier/implementation patches still block even under N-1 noop votes; only conditional advisories are skipped.

## r19 closure evidence

- Final certified tick: `/Users/charles/.hermes/tick-20260507-112446`.
- Tests: 68 OK.
- Fresh T3: 4 planner successes, 4 approval votes, 0 rejects, all best-within-constraints true, agreement 0.95/0.95/0.95, unresolved severity>=3 = 0.
- Source-of-truth manifest: `/Users/charles/.hermes/tick-20260507-112446/final/certification_manifest.json` with `can_claim_complete_certification=true`.
- Added regression coverage and runtime metadata for no-action certification: `planner_patch_summary` records noop/advisory/concrete patch counts and `certification_intent=no_action_certification`, preventing empty merged `patches=[]` from being mistaken for dropped work.
- Prior not-certified tick `/Users/charles/.hermes/tick-20260507-112446` retained as provenance only.
