---
type: task
lane: evolution
layer: L3
status: done
priority: P2
created: 2026-05-13T23:07:50+08:00
updated: 2026-05-14T10:43:04+08:00
expires_at: 2026-06-12T23:07:50+08:00
project: hermes-agent
architecture_target: local-brain
capability_delta: 研究 https://github.com/thedotmack/claude-mem 的记忆组织、检索、上下文注入与 Claude Code 工作流，提炼可迁移机制并优化 Hermes 自身 memory/skill/session_search/taskpool context。
anti_drift_check: 不盲目照搬；先验证 license/API/安装方式/数据结构；对照 Hermes 现有 MEMORY/USER/skills/session_search/brainctl/taskpool；不破坏现有记忆边界与 token 优化。
acceptance_evidence: artifact:claude-mem-analysis-report；command:repo_inspection_or_web_extract；proof:implementation_or_design_patch；selfcheck:memory_boundary_and_token_budget_pass
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: certified
multimodel_ratification_artifact: /Users/charles/.hermes/tick-20260514-010623-331714-p76297-2b020e7f-cac64c33/discussion_result.json
multimodel_last_checked_at: 2026-05-14T09:09:28+08:00
multimodel_round_status: passed
multimodel_last_gate_status: PASS
multimodel_last_decision: LOOP_DONE
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260514-010623-331714-p76297-2b020e7f-cac64c33/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-13-分析-claude-mem-并优化-hermes-自身记忆-上下文机制-state.json
multimodel_last_failures: []
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 1
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - proof:sha256:8b16bde6fdfcfb8df5d6cb8b9fb9b4f30b0cb9e89cf7cdea01c9625a86b9bc23
  - command:py_compile_taskpool PASS
  - artifact:/Users/charles/.hermes/tick-20260514-010623-331714-p76297-2b020e7f-cac64c33/discussion_result.json
  - proof:sha256:bde9234f56a19588b230ee48cfadc6bc7e314cc17f58aac80af3627fe504f7b6
  - proof:sha256:7079488e78e5f061ea8cf930408e145c89a7b7b083497501bd30669fc37a9020
  - artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260514-010623-331714-p76297-2b020e7f-cac64c33/discussion_result.json
concepts: ["claude-mem", "agent-memory", "context-engineering", "semantic-memory", "hermes-self-improvement"]
multimodel_advisory_only: False
multimodel_certification_authority: True
multimodel_advisory_reasons: ["architecture_target", "evolution_lane"]
multimodel_certification_reasons: ["closeout_ratification"]
---

# Task - 分析 claude-mem 并优化 Hermes 自身记忆/上下文机制

## Objective

分析 https://github.com/thedotmack/claude-mem，并基于其方法优化 Hermes 自身的长期记忆、项目记忆、上下文注入、缓存友好前缀和任务池 evidence/context 路由。输出可落地方案，优先小步实现。

## Acceptance Criteria

- [ ] 1. 获取并阅读 claude-mem README/核心代码/数据模型；2. 对比 Hermes 现有 memory、skills、session_search、brain control-plane；3. 识别可迁移机制与不适用机制；4. 落地至少一个低风险改进或形成明确 patch plan；5. 更新相关 skill/文档/自检。

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-13T23:07:50+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-13T23:08:08+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-autorun-step`. Reason: auto-claim-and-handoff

- 2026-05-13T23:08:08+08:00: Lifecycle transition `claimed` -> `running` by `hermes-autorun-step`.

- 2026-05-13T23:08:08+08:00: Lifecycle transition `running` -> `review` by `hermes-autorun-step`. Evidence: proof:sha256:8b16bde6fdfcfb8df5d6cb8b9fb9b4f30b0cb9e89cf7cdea01c9625a86b9bc23, command:py_compile_taskpool PASS

- 2026-05-13T23:11:00+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-150808-717757-p24166-367c49c2-9408537f/discussion_result.json`. Failures: []

- 2026-05-13T23:11:35+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260513-150808-858046-p24175-d3791048-a61dba85/discussion_result.json`. Failures: []

- 2026-05-13T23:17:57+08:00: Multimodel PUA-loop round `failed`. Gate `FAIL`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-150808-984835-p24182-de14dcbe-8612820a/discussion_result.json`. Failures: ["agreement_below_threshold:approach:0.65", "agreement_below_threshold:framing:0.65", "agreement_below_threshold:implementation_order:0.65", "best_within_constraints_missing:claude-opus-4-7", "best_within_constraints_missing:gpt-5.5", "best_within_constraints_missing:mimo-v2.5-pro", "non_approve_vote:claude-opus-4-7:amend", "non_approve_vote:deepseek-v4-pro:amend"]

- 2026-05-13T23:39:27+08:00: Lifecycle transition `review` -> `retry` by `hermes-autorun-review-close`. Reason: multimodel closeout certification previously failed; returned to retry for correction Evidence: proof:sha256:8b16bde6fdfcfb8df5d6cb8b9fb9b4f30b0cb9e89cf7cdea01c9625a86b9bc23, command:py_compile_taskpool PASS, artifact:/Users/charles/.hermes/tick-20260513-150808-984835-p24182-de14dcbe-8612820a/discussion_result.json, multimodel_gate:FAIL, multimodel_status:not_certified

- 2026-05-13T23:40:43+08:00: Reconcile action `retry_due_promoted` by `hermes-reconcile`. Previous status `retry`.

- 2026-05-13T23:52:11+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-autorun-step`. Reason: auto-claim-and-handoff

- 2026-05-13T23:52:11+08:00: Lifecycle transition `claimed` -> `running` by `hermes-autorun-step`.

- 2026-05-13T23:52:11+08:00: Lifecycle transition `running` -> `review` by `hermes-autorun-step`. Evidence: proof:sha256:bde9234f56a19588b230ee48cfadc6bc7e314cc17f58aac80af3627fe504f7b6, command:py_compile_taskpool PASS

- 2026-05-13T23:58:57+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-155211-971753-p90144-ac35bf15-b9b092fc/discussion_result.json`. Failures: []

- 2026-05-13T23:59:23+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-155212-245206-p90163-fa1a3b86-d3364273/discussion_result.json`. Failures: []

- 2026-05-13T23:59:39+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-155212-123730-p90154-5b26d966-0f579434/discussion_result.json`. Failures: []

- 2026-05-14T09:09:28+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260514-010623-331714-p76297-2b020e7f-cac64c33/discussion_result.json`. Failures: []

- 2026-05-14T10:43:04+08:00: Lifecycle transition `review` -> `done` by `hermes`. Reason: auto-close review after proof-gated evidence Evidence: proof:sha256:7079488e78e5f061ea8cf930408e145c89a7b7b083497501bd30669fc37a9020, proof:sha256:8b16bde6fdfcfb8df5d6cb8b9fb9b4f30b0cb9e89cf7cdea01c9625a86b9bc23, command:py_compile_taskpool PASS, artifact:/Users/charles/.hermes/tick-20260514-010623-331714-p76297-2b020e7f-cac64c33/discussion_result.json, proof:sha256:bde9234f56a19588b230ee48cfadc6bc7e314cc17f58aac80af3627fe504f7b6, artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260514-010623-331714-p76297-2b020e7f-cac64c33/discussion_result.json
