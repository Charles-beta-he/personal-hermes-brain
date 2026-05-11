---
type: task
lane: evolution
layer: L3
status: pending
priority: P1
created: 2026-05-10T18:29:12+08:00
updated: 2026-05-11T16:10:52+08:00
expires_at: 2026-06-09T18:29:12+08:00
project: hermes-skill-learning
architecture_target: skill-graph
capability_delta: 评估多 Agent review、置信度阈值、反证检查如何强化 Hermes requesting-code-review 与多模型架构。
anti_drift_check: 不把模型共识当真相；高危结论必须有文件/命令证据，低置信 findings 不自动进入修复。
acceptance_evidence: "截图 OCR: 多 Agent 并行审查，置信度过滤减少假阳性; linked state: /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/multi-model-state-linked-2026-05-10.json; multi-model artifact: /Users/charles/.hermes/tick-20260510-102539; truth gate grounded, fanout quorum met, consensus weak/advisory only."
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: evolution:skill-learning:code-review
evidence: []
concepts: ["skill-learning", "code-review", "multi-model", "evidence-first"]
---

# Task - Skill学习路线：Code Review 多 Agent 并行审查与置信度过滤评估

## Objective

对截图候选 skill `code-review` 走 evidence-first 分析学习路线：先核验来源/许可/能力，再评估 Hermes 适配，最后输出 adopt/borrow/reject 决策；本任务不安装、不导入、不宣称已采用。截图说明：多 Agent 并行审查，置信度过滤减少假阳性。

## Acceptance Criteria

- [ ] 确认来源与许可；设计并行 review rubric；在一个历史 diff 上回放比较假阳性/漏报；形成 confidence gate 与 evidence bundle 规范

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

- 2026-05-11T01:15:51+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T01:39:48+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: deadlock_fix_release

- 2026-05-11T01:40:32+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T02:12:48+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: timeout_cleanup

- 2026-05-11T02:53:24+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T03:57:53+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-11T03:59:13+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T05:00:13+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-11T05:03:39+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T06:04:49+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-11T06:11:13+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T07:19:15+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-11T07:20:30+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T08:32:10+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-11T11:26:00+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T12:28:54+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-11T12:31:04+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T13:51:01+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-11T13:53:20+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T15:01:02+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-11T15:02:19+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T16:10:52+08:00: Reconcile action `stale_claim_released` by `hermes-reconcile`. Previous status `claimed`.
