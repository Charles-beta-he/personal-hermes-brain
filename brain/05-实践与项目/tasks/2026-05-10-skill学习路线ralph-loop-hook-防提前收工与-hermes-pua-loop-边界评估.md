---
type: task
lane: evolution
layer: L3
status: pending
priority: P1
created: 2026-05-10T18:29:13+08:00
updated: 2026-05-11T02:12:49+08:00
expires_at: 2026-06-09T18:29:13+08:00
project: hermes-skill-learning
architecture_target: taskpool
capability_delta: 评估 hook/stop-condition/继续执行机制如何强化 Hermes loop、PUA、任务池 proof gate 与长时自运行。
anti_drift_check: 不能无限循环或绕过用户停止；必须有预算、kill switch、证据门和 handoff 边界。
acceptance_evidence: "截图 OCR: Claude 想提前收工? Hook 拦截塞回去直到做完; linked state: /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/multi-model-state-linked-2026-05-10.json; multi-model artifact: /Users/charles/.hermes/tick-20260510-102539; truth gate grounded, fanout quorum met, consensus weak/advisory only."
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: evolution:skill-learning:ralph-loop
evidence: []
concepts: ["skill-learning", "ralph-loop", "multi-model", "evidence-first"]
---

# Task - Skill学习路线：Ralph Loop Hook 防提前收工与 Hermes PUA/Loop 边界评估

## Objective

对截图候选 skill `ralph-loop` 走 evidence-first 分析学习路线：先核验来源/许可/能力，再评估 Hermes 适配，最后输出 adopt/borrow/reject 决策；本任务不安装、不导入、不宣称已采用。截图说明：Claude 想提前收工? Hook 拦截塞回去直到做完。

## Acceptance Criteria

- [ ] 确认来源与许可；拆解 hook 触发条件；映射到 Hermes loop/PUA/iteration-budget；设计有界继续执行策略与停止条件测试

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-10T18:29:13+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-11T01:58:54+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T02:12:49+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: timeout_cleanup
