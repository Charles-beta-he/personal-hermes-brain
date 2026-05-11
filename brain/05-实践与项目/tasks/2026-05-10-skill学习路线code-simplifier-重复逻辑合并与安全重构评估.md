---
type: task
lane: evolution
layer: L3
status: pending
priority: P2
created: 2026-05-10T18:29:12+08:00
updated: 2026-05-11T02:12:49+08:00
expires_at: 2026-06-09T18:29:12+08:00
project: hermes-skill-learning
architecture_target: skill-graph
capability_delta: 评估写后简化、重复逻辑识别、通用函数提取如何接入 code-simplification/TDD 流程。
anti_drift_check: 不为简化而降精度/删功能；任何重构必须先有测试或可执行回归门。
acceptance_evidence: "截图 OCR: 写完再看一遍，重复逻辑合并成通用函数; linked state: /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/multi-model-state-linked-2026-05-10.json; multi-model artifact: /Users/charles/.hermes/tick-20260510-102539; truth gate grounded, fanout quorum met, consensus weak/advisory only."
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: evolution:skill-learning:code-simplifier
evidence: []
concepts: ["skill-learning", "code-simplifier", "multi-model", "evidence-first"]
---

# Task - Skill学习路线：Code Simplifier 重复逻辑合并与安全重构评估

## Objective

对截图候选 skill `code-simplifier` 走 evidence-first 分析学习路线：先核验来源/许可/能力，再评估 Hermes 适配，最后输出 adopt/borrow/reject 决策；本任务不安装、不导入、不宣称已采用。截图说明：写完再看一遍，重复逻辑合并成通用函数。

## Acceptance Criteria

- [ ] 确认来源与许可；整理简化模式与反模式；选一个小型代码样本做 before/after 方案；定义 test+build+diff 安全门

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-10T18:29:12+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-11T02:02:36+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T02:12:49+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: timeout_cleanup
