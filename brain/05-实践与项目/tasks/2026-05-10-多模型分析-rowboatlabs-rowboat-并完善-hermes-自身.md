---
type: task
lane: evolution
layer: L3
status: pending
priority: P1
created: 2026-05-10T13:44:57+08:00
updated: 2026-05-11T23:29:37+08:00
expires_at: 2026-06-09T13:44:57+08:00
project: hermes-self-improvement
architecture_target: taskpool
capability_delta: Evidence-first Rowboat review may produce bounded Hermes-native taskpool/orchestration improvements.
anti_drift_check: Must read upstream evidence before adoption; no cloud lock-in, secret copying, or weakened fail-closed boundaries.
acceptance_evidence: 现有 /Users/charles/.hermes/tick-20260511-081522/discussion_result.json 为 not_certified 且内容疑似 OpenAI/provider-quota 错绑；本任务必须重新收集 Rowboat 上游证据包并产出 target-bound Claude+GPT+DeepSeek+MiMo 四模型 ratification 后才可 closeout。
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
mission_schema_version: 1.0
mission_id: rowboat-hermes-taskpool-self-improvement-review
mission_title: 多模型分析 rowboatlabs/rowboat 并完善 Hermes 自身
mission_objective: 将 Rowboat 编排设计审计转化为 Hermes-native 任务池/证明链/多 Agent 协同的有界改进候选；pending 阶段只允许证据化推进，不自动采纳云端锁定或降低 fail-closed 边界。
mission_constraints: ["先读上游代码/文档证据再提炼借鉴点", "仅采纳 Hermes-native 有界小切片", "保留本地优先与 fail-closed 证明链"]
red_lines: ["不复制 secrets 或供应商云端锁定机制", "不绕过 selfcheck/proof/boundary/multimodel gate", "不把外部 README 印象当事实证据"]
non_goals: ["不整体迁移到 Rowboat runtime", "不直接启用无人值守写入生产路径"]
evidence_refs: ["file:/Users/charles/.hermes/tick-20260511-081522/discussion_result.json"]
acceptance_criteria: ["Rowboat 架构/能力/风险证据包带具体文件或文档引用", "多模型按风险路由输出采纳/拒绝/spike ledger", "如采纳则提交最小可验证 Hermes-native 增益补丁并跑 selfcheck/test/proof"]
dag_nodes: ["id: upstream-evidence-review"]
checkpoint_states: ["pending", "claimed", "running", "review", "done"]
permission_gates: ["external-framework-adoption requires evidence-first review", "implementation requires scoped local commit and deterministic gates"]
handoff_artifacts: ["artifact:rowboat-hermes-taskpool-review-handoff"]
proof_artifacts: ["proof:multimodel-ratification-rowboat-20260511-081522"]
rollback_signal: revert any Rowboat-inspired runtime hook or write-surface change if selfcheck/proof/boundary or four-model ratification rejects it
certification_status: not_certified
ratification_artifact: file:/Users/charles/.hermes/tick-20260511-081522/discussion_result.json
claimed_by:
claim_expires_at:
run_id:
retry_count: 0
next_attempt_at:
workspace: /Users/charles/.hermes
evidence: []
concepts: ["multi-model", "rowboat", "hermes", "self-improvement", "taskpool"]
multimodel_status: not_certified
multimodel_ratification_artifact: file:/Users/charles/.hermes/tick-20260511-081522/discussion_result.json
---

# Task - 多模型分析 rowboatlabs/rowboat 并完善 Hermes 自身

## Objective

基于 evidence-first 多模型分析审计 https://github.com/rowboatlabs/rowboat 的 agent/workflow/task orchestration 设计；提炼可安全借鉴到 Hermes 本地大脑任务池、任务自动推进、证明链、UI/控制台与多 Agent 协同的改进点；需要先独立阅读上游项目资料/代码，不得凭 README 印象下结论。

## Acceptance Criteria

- [ ] 1) 形成 Rowboat 架构/能力/风险证据包，含具体文件/commit/文档引用；2) 多模型 T1/T2/T3 按风险路由完成评审，明确哪些建议可采纳、拒绝或进入 spike；3) 如采纳，提交 Hermes 本地脚本/skill/文档的最小可验证增益补丁；4) 运行相关 selfcheck/test，更新 evidence ledger；5) 不引入云端锁定、不复制 secrets、不降低现有 fail-closed 安全边界。

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list/selfcheck/proof/boundary | PASS | 2026-05-11T22:29 +08:00 after target-bound gate repair |

## Proof Log

- 2026-05-10T13:44:57+08:00: Task created from local-brain control point.

- 2026-05-11T22:25:07+08:00: 流转校准：多模型 artifact 重新验真，当前仅保留为 provenance/advisory；未满足 target-bound 4/4 Claude+GPT+DeepSeek+MiMo 认证，任务继续进入多模型介入/证据补齐队列。

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-10T23:55:11+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T01:35:39+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: stale_claim_cleanup_ttl_expired

- 2026-05-11T01:43:56+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T02:12:48+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: timeout_cleanup

- 2026-05-11T17:52:31+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T18:58:40+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-11T20:02:01+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T20:06:48+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: orphan_worker_cleaned_after_manual_agent_cycle_timeout

- 2026-05-11T21:18:06+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T22:18:40+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-11T22:25:09+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T23:29:37+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup
