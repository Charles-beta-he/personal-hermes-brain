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
capability_delta: Represent missions as parent mission notes plus child task DAG/checkpoints, route ready nodes through existing eligibility/boundary/dry-run gates, and surface mission progress in dashboard.
anti_drift_check: Use current taskpool lifecycle primitives rather than replacing them; mission completeness is a tie-breaker/gate, not a global priority override; work lane non-starvation preserved.
acceptance_evidence: mission->child task dry-run generates DAG/checkpoint metadata without claiming/executing; dashboard shows mission progress; P0/P1 work remains selected ahead of evolution when applicable; tests/selfcheck PASS.
workflow_contract: [[08-模板/task-workflow-contract-template]]
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - /tmp/missions-task-planning-mm-state.json
  - /Users/charles/.hermes/tick-20260510-101903/merged_plan.json
  - /Users/charles/.hermes/tick-20260510-102004/merged_plan.json
  - /tmp/current_taskpool_summary.json
concepts: ["missions", "mission-command", "opord", "taskpool", "evolution", "proof-gate"]
---

# Task - Task - P1 Mission DAG 分解、路由与任务池 dashboard 可视化

## Objective

Add mission decomposition semantics: parent_mission_id, dag_edges, checkpoints, readiness gates, progress dashboard, and router rules that keep product/work delivery from being starved by evolution missions.

## Acceptance Criteria

- [ ] Dry-run can decompose a mission into bounded child tasks with dependencies and show next executable nodes; no Markdown body is executed; no task is auto-done without proof.

## Multi-model Advisory Result

Status: `truth_grounded_advisory / weak_consensus`, not full certification. Multiple planners converged on mission envelope + DAG/checkpoints + router/dashboard as the safe middle slice, while preserving existing taskpool lifecycle primitives.

Key constraints from review:
- Mission completeness is a readiness/tie-breaker gate, not a global override of work priority.
- Work lane P0/P1 non-starvation remains hard invariant.
- DAG/router output is dry-run/readiness metadata first; no claim/execute/write until later proof-gated runner work.
- Dashboard is derived from task notes; it must not become a second source of truth.

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Add parent mission metadata such as `mission_id`, `parent_mission_id`, `dag_edges`, `checkpoint_state`, and `ready_when`.
- [ ] Add dry-run mission decomposition that writes no tasks unless an explicit write mode is later approved.
- [ ] Route ready child nodes through existing `eligibility-check`, `boundary-check`, and `dispatch-dry-run` primitives.
- [ ] Add dashboard mission progress view: pending/running/review/done by mission and blocker summary.
- [ ] Add scheduler/router regression proving work P0/P1 cannot be skipped solely because an evolution mission is more complete.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-10T18:25:11+08:00: Task created from local-brain control point.
- 2026-05-10T18:29:00+08:00: Archived as duplicate; absorbed into `2026-05-10-mission方法论p1mission-dag-分解路由与-dashboard-进度视图`.

## Blockers / Confusions

- Depends on P0 mission envelope schema being available or mocked behind a compatibility adapter.
- Full multi-model certification missing; keep this as advisory until deterministic tests and a ratification artifact exist.

## Final Handoff

- Status:
- Evidence:
- Residual risk:
