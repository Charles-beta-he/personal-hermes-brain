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
architecture_target: skill-graph
capability_delta: 评估四阶段 MCP server 创建流程是否能补强 mcp-server-from-scratch/native-mcp/mcporter 文档与测试模板。
anti_drift_check: 不直接暴露 secrets 或任意工具；新 MCP server 必须 stdio 最小权限、schema 清晰、可测试。
acceptance_evidence: "截图 OCR: 四阶段引导，从零写 MCP Server 不再踩坑; linked state: /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/multi-model-state-linked-2026-05-10.json; multi-model artifact: /Users/charles/.hermes/tick-20260510-102539; truth gate grounded, fanout quorum met, consensus weak/advisory only."
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: evolution:skill-learning:mcp-builder
evidence: []
concepts: ["skill-learning", "mcp-builder", "multi-model", "evidence-first"]
---

# Task - Skill学习路线：MCP Builder 四阶段 MCP Server 引导与 Hermes MCP skill 补强评估

## Objective

对截图候选 skill `mcp-builder` 走 evidence-first 分析学习路线：先核验来源/许可/能力，再评估 Hermes 适配，最后输出 adopt/borrow/reject 决策；本任务不安装、不导入、不宣称已采用。截图说明：四阶段引导，从零写 MCP Server 不再踩坑。

## Acceptance Criteria

- [ ] 确认来源与许可；提取四阶段流程；对比现有 MCP skills 缺口；产出 MCP server 最小模板/测试清单建议

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

- 2026-05-11T01:58:21+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T02:12:49+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: timeout_cleanup
