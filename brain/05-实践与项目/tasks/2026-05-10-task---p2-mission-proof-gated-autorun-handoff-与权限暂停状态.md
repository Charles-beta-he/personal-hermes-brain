---
type: task
lane: evolution
layer: L3
status: archived
priority: P2
created: 2026-05-10T18:25:11+08:00
updated: 2026-05-10T18:25:11+08:00
expires_at: 2026-06-09T18:25:11+08:00
project: hermes-self-improvement
architecture_target: taskpool
capability_delta: Extend auto-claim-and-handoff into a mission-aware bounded runner handoff that pauses on permission/ask-human gates, persists run/proof events, and only advances after proof-check.
anti_drift_check: Default-off, fail-closed, bounded by existing allowlist/autonomy-write-guard/proof gates; workers cannot mark done directly; mission notes remain canonical and runtime indexes derived.
acceptance_evidence: Default dry-run denies write execution without allowlist; permission_gate pauses are persisted; proof artifacts hash-chain verifies closure; proof-check/lifecycle/selfcheck PASS; no tick/worker can directly mark done.
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - file:/tmp/missions-task-planning-mm-state.json
  - file:/Users/charles/.hermes/tick-20260510-101903/merged_plan.json
  - file:/Users/charles/.hermes/tick-20260510-102004/merged_plan.json
  - file:/tmp/current_taskpool_summary.json
concepts: ["missions", "mission-command", "opord", "taskpool", "evolution", "proof-gate"]
---

# Task - Task - P2 Mission proof-gated autorun handoff 与权限暂停状态

## Objective

Implement the safe execution edge of Missions: handoff bundles, ask-human/permission pause states, persisted run logs, proof artifacts, and review->done only through deterministic proof gates.

## Acceptance Criteria

- [ ] A mission child node can be handed off in dry-run/default-off mode; missing permission/proof causes blocked/review state, not silent success; proof-check is the only completion gate.

## Multi-model Advisory Result

Status: `truth_grounded_advisory / weak_consensus`, not full certification. Reviewers agreed the execution edge must be last: Missions should improve intent/persistence/proof, not turn Markdown notes into directly executable scripts.

Safety invariants:
- Default-off and dry-run first.
- Handoff bundles are data; workers cannot mark `done` directly.
- Permission/ask-human states pause into `blocked`/`review` with exact unblock condition.
- Runtime indexes/logs are derived; canonical source remains Markdown task notes plus proof artifacts.
- Completion path is proof-check/lifecycle/review, never raw tick success.

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Define mission handoff bundle schema with mission id, child node id, allowed paths/tools, proof requirements, abort conditions, and report cadence.
- [ ] Extend `auto-claim-and-handoff` or a sibling dry-run command to emit mission handoff bundles without execution by default.
- [ ] Persist run/proof events and permission/ask-human pause states.
- [ ] Add fail-closed tests: missing allowlist, missing proof, permission required, worker attempted direct done, stale claim, and proof hash mismatch.
- [ ] Integrate with proof-check/lifecycle/dashboard only after deterministic gates pass.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-10T18:25:11+08:00: Task created from local-brain control point.
- 2026-05-10T18:29:00+08:00: Archived as duplicate; absorbed into `2026-05-10-mission方法论p2proof-gated-auto-claim-and-handoff-mission-runner-集成`.

## Blockers / Confusions

- Depends on P0 schema and P1 DAG/router slices.
- Must not be enabled until autonomy-write-guard/proof gates are caller-integrated and ratified; current task is an implementation target, not permission to autorun.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-12T02:54:26+08:00: Permission taxonomy defaults applied by `permission-migrate --apply`. Changes: {"required_authority": "budget-handoff", "max_authority": "autonomous-execution", "permission_tier": "budget-handoff", "write_surfaces": ["taskpool", "hermes-scripts", "brain"], "completion_gate": "ratification-or-selfcheck-review-done", "lane_semantics": "self-evolution: deterministic gates plus ratification/proof before review->done"}
