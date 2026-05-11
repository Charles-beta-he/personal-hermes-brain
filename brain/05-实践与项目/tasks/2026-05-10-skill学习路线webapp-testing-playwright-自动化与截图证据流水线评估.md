---
type: task
lane: evolution
layer: L3
status: pending
priority: P1
created: 2026-05-10T18:29:12+08:00
updated: 2026-05-11T08:20:08+08:00
expires_at: 2026-06-09T18:29:12+08:00
project: hermes-skill-learning
architecture_target: local-brain
capability_delta: 评估 Playwright 脚本、截图证据、console/network/storage 采集如何标准化到 browser-harness 与 UI 回归验收。
anti_drift_check: 不以 mock 成功替代真实后端/真实浏览器证据；截图必须可追溯到命令、环境和 URL。
acceptance_evidence: "截图 OCR: Playwright 自动化，写脚本跑测试截屏一条龙; linked state: /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/multi-model-state-linked-2026-05-10.json; multi-model artifact: /Users/charles/.hermes/tick-20260510-102539; truth gate grounded, fanout quorum met, consensus weak/advisory only."
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: evolution:skill-learning:webapp-testing
evidence: []
concepts: ["skill-learning", "webapp-testing", "multi-model", "evidence-first"]
---

# Task - Skill学习路线：Webapp Testing Playwright 自动化与截图证据流水线评估

## Objective

对截图候选 skill `webapp-testing` 走 evidence-first 分析学习路线：先核验来源/许可/能力，再评估 Hermes 适配，最后输出 adopt/borrow/reject 决策；本任务不安装、不导入、不宣称已采用。截图说明：Playwright 自动化，写脚本跑测试截屏一条龙。

## Acceptance Criteria

- [ ] 确认来源与许可；映射到现有 browser-harness；设计一条脚本+截图+日志证据链；在本地示例页或现有项目上给出 dry-run 方案

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

- 2026-05-11T01:45:17+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T02:12:49+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: timeout_cleanup

- 2026-05-11T05:07:33+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T06:10:45+08:00: Reconcile action `stale_claim_released` by `hermes-reconcile`. Previous status `claimed`.

- 2026-05-11T07:19:13+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T08:20:08+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup
