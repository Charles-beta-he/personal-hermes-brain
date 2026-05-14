---
type: task
lane: advisory
layer: L3
status: archived
priority: P3
created: 2026-05-14T01:14:53+08:00
updated: 2026-05-14T01:15:35+08:00
expires_at: 2026-06-13T01:14:53+08:00
project: hermes-agent
architecture_target: 
capability_delta: 
anti_drift_check: 
acceptance_evidence: 
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: dispatch-hint
max_authority: budget-handoff
permission_tier: dispatch-hint
write_surfaces: ["taskpool", "brain"]
completion_gate: advisory-evidence-review-done
lane_semantics: "research/advisory: evidence deposition; no execution closeout without promotion"
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - artifact:/tmp/hook_smart_advisory_add.json
concepts: ["taskpool", "event-hook", "smart-routing"]
---

# Task - 测试 event hook 智能路由 advisory 不跑多模型

## Objective

测试 event hook 智能路由 advisory 不跑多模型

## Acceptance Criteria

- [ ] Observable result is recorded in Proof Log.

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-14T01:14:53+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-14T01:15:35+08:00: Lifecycle transition `pending` -> `archived` by `hermes`. Force: true. Reason: cleanup verification task after smart routing test Evidence: artifact:/tmp/hook_smart_advisory_add.json
