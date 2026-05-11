---
type: task
lane: evolution
layer: L3
status: pending
priority: P2
created: 2026-05-10T18:29:13+08:00
updated: 2026-05-10T18:29:13+08:00
expires_at: 2026-06-09T18:29:13+08:00
project: hermes-skill-learning
architecture_target: skill-graph
capability_delta: 评估 PPTX 生成 skill 对 powerpoint/productivity/slide 工作流的补强，重点是从结构化内容到可编辑 pptx 的证据链。
anti_drift_check: 不把生成图片当可编辑 pptx；必须验证文件可打开、可编辑、版式一致并保留源数据。
acceptance_evidence: "截图 OCR: 直接生成 pptx 文件，解决从零开始太痛苦的问题; linked state: /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/multi-model-state-linked-2026-05-10.json; multi-model artifact: /Users/charles/.hermes/tick-20260510-102539; truth gate grounded, fanout quorum met, consensus weak/advisory only."
workflow_contract: [[08-模板/task-workflow-contract-template]]
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: evolution:skill-learning:pptx
evidence: []
concepts: ["skill-learning", "pptx", "multi-model", "evidence-first"]
---

# Task - Skill学习路线：PPTX 直接生成 pptx 文件与 Hermes productivity 流程评估

## Objective

对截图候选 skill `pptx` 走 evidence-first 分析学习路线：先核验来源/许可/能力，再评估 Hermes 适配，最后输出 adopt/borrow/reject 决策；本任务不安装、不导入、不宣称已采用。截图说明：直接生成 pptx 文件，解决从零开始太痛苦的问题。

## Acceptance Criteria

- [ ] 确认来源与许可；核验是否真生成 .pptx；设计最小 deck 生成验收；给出与现有 powerpoint skill 的合并或扩展建议

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
