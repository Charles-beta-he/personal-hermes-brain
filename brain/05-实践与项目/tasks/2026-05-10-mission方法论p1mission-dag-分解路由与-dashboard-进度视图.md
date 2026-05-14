---
type: task
lane: evolution
layer: L3
status: done
priority: P1
created: 2026-05-10T18:23:40+08:00
updated: 2026-05-10T20:00:51+08:00
expires_at: 2026-06-09T18:23:40+08:00
project: Hermes-local-brain
architecture_target: taskpool
capability_delta: 将单条任务拆成 mission DAG/checkpoints/child task links；router 按 ready/blocked/review 状态和 work-vs-evolution 优先级选择下一节点；dashboard 显示 mission 级进度/阻塞/证据
anti_drift_check: DAG 不得有环；blocked/permission 等状态不得被 dispatch；work/product delivery P0/P1 不被 evolution Mission 抢占；parallel-boundary 与 boundary-check 必须参与 ready 判定
acceptance_evidence: 新增 decomposition/router/dashboard 测试；boundary-check 与 parallel-dispatch-dry-run 覆盖 mission nodes；dashboard --write --json 输出 mission 汇总；dispatch-dry-run 仍 fail-closed
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
  - file:/tmp/missions-taskpool-mm-state.json
  - file:/tmp/missions-task-planning-mm-state.json
  - artifact:tick-20260510-102004/merged_plan.json (historical advisory provenance; source file GC'd)
  - artifact:tick-20260510-101903/merged_plan.json (historical advisory provenance; source file GC'd)
  - "command: mission DAG/dashboard regression PASS"
  - "command: real vault selfcheck/boundary/proof/dashboard PASS"
  - artifact:mission-dag-dashboard-implementation
concepts: ["missions", "dag", "router", "dashboard", "work-priority", "parallel-boundary"]
---

# Task - Mission方法论P1：Mission DAG 分解、路由与 Dashboard 进度视图

## Objective

把任务规划从线性 TODO 升级为 mission DAG，让可并行、阻塞、待人审、可调度节点都有机器可读状态。

补充调度约束：mission 完整度只能作为 readiness/tie-breaker，不能覆盖 work lane P0/P1 优先级；ready node 必须继续经过 eligibility-check、boundary-check、dispatch-dry-run，dashboard 仍是 derived view 而不是第二事实源。

## Acceptance Criteria

- [x] 可从一个 mission note 生成/链接 child tasks；next/dispatch 只返回 ready 节点；dashboard 能看到 mission 完成率和 blockers。

## Plan / Workpad

- [x] Reconcile current state before execution.
- [x] Execute the smallest verifiable slice.
- [x] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| python3 ~/.hermes/scripts/test_brain_task_orchestrator.py | PASS | command: regression suite includes mission DAG dashboard + autorun-runner permission pause |
| python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/test_brain_task_orchestrator.py | PASS | command: py_compile PASS |
| python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json | PASS | command: real vault selfcheck PASS |
| python3 ~/.hermes/scripts/brain_task_orchestrator.py boundary-check --json | PASS | command: real vault boundary-check PASS |
| python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --include-active --json | PASS | command: proof-check PASS; only legacy body-evidence warnings |
| python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write --json | PASS | command: dashboard regenerated with Mission DAG Progress section |
| python3 ~/.hermes/scripts/brain_task_orchestrator.py autorun-runner --json | PASS | command: default-off denied; no claim/no execution |


## Proof Log

- 2026-05-10T18:23:40+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status: implemented and closing through lifecycle gates.
- Evidence: Mission DAG fields, dependency blockers/cycle validation, ready-node dispatch, dashboard mission progress summary landed in brain_task_orchestrator.py.
- Residual risk: live multi-model T3 discussion was not rerun for this final patch; deterministic gates are PASS. MiMo provider remains a separate adapter issue for full four-model certification.

## Multi-model Missions synthesis

Status: truth-grounded advisory, not patch-level certification.

Artifacts:
- State: `/tmp/missions-taskpool-mm-state.json`
- Tick: `/Users/charles/.hermes/tick-20260510-102004/`
- Merged plan: `/Users/charles/.hermes/tick-20260510-102004/merged_plan.json`
- Source repo reference: `rowboatlabs/rowboat` cloned at `/tmp/rowboat-missions`, commit `10995ebed69f56db899619b8636c8c14b5f9b6cb`

Consensus summary:
- Truth gate grounded 4/4 claims: current Hermes taskpool has lifecycle primitives; Rowboat contributes local-first KG/run/permission/scheduled-agent patterns; safe Missions landing is envelope + DAG + proof/permission gates, not direct Markdown execution.
- Planner consensus was dissent/low score because planners named patches differently, but all useful concrete proposals converged on P0 envelope, P1 DAG/router/dashboard, P2 proof-gated autorun/handoff, plus local-first artifacts.
- Therefore this task is an executable taskpool landing slice, not a claim that implementation is already certified.

Mission rules to preserve:
- Mission notes are data/workpads, not scripts.
- Safe dispatch, claim/handoff, executor, and proof-gated completion remain separate stages.
- Evolution Missions must not starve work/product P0/P1 tasks.
- Canonical source is `~/Documents/brain`; SQLite/FTS/dashboard are derived caches.

## Implementation notes

DAG/router must answer three questions deterministically:
1. Which mission node is ready?
2. Why are other nodes blocked?
3. Which lane/priority wins when work/product tasks compete with evolution Missions?

Smallest safe slice:
1. Add read-only DAG validation: missing parent, cycle, invalid status, expired lease.
2. Extend dashboard with mission-level progress and blockers.
3. Extend dispatch-dry-run to show selected ready node without claiming it.
4. Add starvation guard proving work/product P0/P1 keeps priority over open-ended evolution.


- 2026-05-10T20:00:00+08:00: Implementation complete: Mission DAG fields, dependency blockers/cycle validation, ready-node dispatch, dashboard mission progress summary landed in brain_task_orchestrator.py.

- 2026-05-10T20:00:51+08:00: Lifecycle transition `pending` -> `claimed` by `hermes`.

- 2026-05-10T20:00:51+08:00: Lifecycle transition `claimed` -> `running` by `hermes`.

- 2026-05-10T20:00:51+08:00: Lifecycle transition `running` -> `review` by `hermes`. Evidence: command: mission DAG/dashboard regression PASS, command: real vault selfcheck/boundary/proof/dashboard PASS

- 2026-05-10T20:00:51+08:00: Lifecycle transition `review` -> `done` by `hermes`. Evidence: artifact:mission-dag-dashboard-implementation

- 2026-05-12T02:54:24+08:00: Permission taxonomy defaults applied by `permission-migrate --apply`. Changes: {"required_authority": "budget-handoff", "max_authority": "autonomous-execution", "permission_tier": "budget-handoff", "write_surfaces": ["taskpool", "hermes-scripts", "brain"], "completion_gate": "ratification-or-selfcheck-review-done", "lane_semantics": "self-evolution: deterministic gates plus ratification/proof before review->done"}
