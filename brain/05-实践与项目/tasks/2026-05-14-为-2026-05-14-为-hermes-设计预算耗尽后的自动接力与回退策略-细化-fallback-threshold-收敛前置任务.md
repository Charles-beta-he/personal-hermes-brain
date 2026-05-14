---
type: task
lane: evolution
layer: L3
status: done
priority: P1
created: 2026-05-14T17:09:43+08:00
updated: 2026-05-14T17:26:26+08:00
expires_at: 2026-06-13T01:37:20+08:00
project: hermes-agent
architecture_target: local-brain
capability_delta: fallback threshold narrowed brief
anti_drift_check: separate threshold policy from relay implementation so the parent scope does not drift
acceptance_evidence: proof log states threshold semantics and the evidence gate for noop-vs-change
workflow_contract: "['[08-模板/task-workflow-contract-template]']"
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: advisory_completed
multimodel_last_checked_at: 2026-05-14T17:26:05+08:00
multimodel_round_status: advisory_passed
multimodel_last_gate_status: PASS_ADVISORY_ONLY
multimodel_last_decision: CONTINUE_LOOP
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260514-092229-074141-p91410-aafec0fd-2fe10542/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-14-为-2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略-细化-fallback-threshold-收敛前置任务-state.json
multimodel_last_failures: []
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - /Users/charles/Documents/brain/05-实践与项目/tasks/2026-05-14-fallback-threshold-policy-brief.md
  - "proof: /Users/charles/Documents/brain/05-实践与项目/tasks/2026-05-14-fallback-threshold-policy-brief.md; deterministic selfcheck: threshold semantics, fallback actions, noop-vs-change criteria, evidence gate present"
concepts: ["task", "auto-subtask", "non-convergence", "fallback-thresholds"]
auto_subtask_parent: 2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略
auto_subtask_kind: non_convergence_narrowing
auto_subtask_issue_ids: ["I-001", "I-002", "I-003", "I-004", "I-005", "I-006"]
multimodel_advisory_only: True
multimodel_certification_authority: True
multimodel_advisory_reasons: ["architecture_target", "evolution_lane"]
multimodel_certification_reasons: ["closeout_ratification"]
---

# Task - 为 2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略 细化 fallback threshold 收敛前置任务

## Objective

Auto-generated convergence slice for parent `2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略`. Do not change the parent objective. Define fallback thresholds, downgrade policy, and the minimum evidence required to justify noop vs change on budget exhaustion behavior.

## Acceptance Criteria

- [x] Produce a narrowed brief covering trigger thresholds, allowed fallback actions, and explicit noop-vs-change decision criteria.

## Plan / Workpad

- [x] Reconcile current state before execution.
- [x] Execute the smallest verifiable slice.
- [x] Record proof and update status.

## Parent Link

- Parent task: 2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略

## Narrowed Scope

- Only resolve threshold semantics and noop-vs-change decision criteria.
- Do not redesign the full handoff workflow here.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-14T17:28+08:00 — Completed narrowed fallback threshold brief. Evidence: `/Users/charles/Documents/brain/05-实践与项目/tasks/2026-05-14-fallback-threshold-policy-brief.md`.
- Defines GREEN/AMBER/RED/BLACK threshold bands, allowed fallback actions, explicit noop-vs-change criteria, and minimum evidence gate.
- Boundary preserved: threshold semantics only; no relay-order implementation, no quota instrumentation change, no automatic runtime handoff.

- 2026-05-14T17:09:43+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

Fallback threshold semantics are ready for parent integration. Parent should consume this as the policy layer and wait for quota-observability + relay-ordering slices before implementing the full automatic handoff state machine.

Recommended next dependency: finish quota observability, then reconcile relay ordering review.

- Status:
- Evidence:
- Residual risk:

- 2026-05-14T17:22:28+08:00: Lifecycle transition `pending` -> `claimed` by `hermes`. Reason: 推进 fallback threshold 收敛前置任务

- 2026-05-14T17:26:05+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260514-092229-074141-p91410-aafec0fd-2fe10542/discussion_result.json`. Failures: []

- 2026-05-14T17:26:26+08:00: Lifecycle transition `review` -> `done` by `hermes`. Reason: 完成 fallback threshold narrowed brief Evidence: proof: /Users/charles/Documents/brain/05-实践与项目/tasks/2026-05-14-fallback-threshold-policy-brief.md; deterministic selfcheck: threshold semantics, fallback actions, noop-vs-change criteria, evidence gate present
