---
type: task
lane: evolution
layer: L3
status: done
priority: P1
created: 2026-05-14T16:46:58+08:00
updated: 2026-05-14T17:09:15+08:00
expires_at: 2026-06-13T16:46:58+08:00
project: hermes-agent
architecture_target: local-brain
capability_delta: 为预算耗尽自动接力/回退任务增加 blocked 自动解题桥接层：识别 loop_non_convergence，自动抽取 failure taxonomy，收窄为状态机优先的 narrowed brief，再触发下一轮 ratification，减少无限 CONTINUE_LOOP。
anti_drift_check: 不是放开无限自动重试；必须 fail-closed；先缩题再重试；保留人工确认边界；不绕过 ratification/proof gate；优先复用现有 blocked_resolve/multimodel_intervention/auto_close_review。
acceptance_evidence: 定义 non-convergence->auto-narrowing->re-ratify 状态机；明确触发阈值/失败分类/自动与人工边界/rollback；补最小 orchestrator patch 或形成可执行拆解；selfcheck/proof gate 兼容。
workflow_contract: "[08-模板/task-workflow-contract-template]"
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: certified
multimodel_ratification_artifact: /Users/charles/.hermes/tick-20260514-085042-917991-p37127-66d88ef0-e70899f1/discussion_result.json
multimodel_last_checked_at: 2026-05-14T16:55:42+08:00
multimodel_round_status: passed
multimodel_last_gate_status: PASS
multimodel_last_decision: LOOP_DONE
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260514-085042-917991-p37127-66d88ef0-e70899f1/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-14-为预算耗尽自动接力设计-non-convergence-auto-narrowing-unblock-shim-state.json
multimodel_last_failures: []
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: evolution:local-brain
evidence:
  - proof:sha256:1c3a6bc53d4e28754cc505ed1bec0d9e2441f02e3e0740c99cec50a0ca8ab77b
  - command:py_compile_taskpool PASS
  - proof:sha256:7dfea0d8c04f287fd41e183db79e7ffd6553c776149d944d7c192cc8e9e2ad9e
  - artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260514-085042-917991-p37127-66d88ef0-e70899f1/discussion_result.json
concepts: ["budget-exhaustion", "auto-handoff", "non-convergence", "auto-narrowing", "ratification", "taskpool"]
multimodel_advisory_only: False
multimodel_certification_authority: True
multimodel_advisory_reasons: []
multimodel_certification_reasons: []
---

# Task - 为预算耗尽自动接力设计 non-convergence auto-narrowing unblock shim

## Objective

为 blocked 的预算耗尽自动接力任务提供半自动 unblock 机制，先自动缩小问题空间再重试 ratification，而不是无限 full discussion 重跑。建议执行顺序：先完成本 shim，再回到父任务 2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略。该 shim 为父任务前置依赖。

## Acceptance Criteria

- [ ] 1. 明确 loop_non_convergence 的检测条件与证据来源；2. 定义 failure taxonomy -> narrowed brief 映射；3. 定义何时自动重试、何时转人工 review；4. 记录与父任务的依赖关系及回写点；5. 若实现补丁，提供 proof/selfcheck。

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-14T16:46:58+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-14T16:50:42+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-autorun-step`. Reason: auto-claim-and-handoff

- 2026-05-14T16:50:42+08:00: Lifecycle transition `claimed` -> `running` by `hermes-autorun-step`.

- 2026-05-14T16:50:42+08:00: Lifecycle transition `running` -> `review` by `hermes-autorun-step`. Evidence: proof:sha256:1c3a6bc53d4e28754cc505ed1bec0d9e2441f02e3e0740c99cec50a0ca8ab77b, command:py_compile_taskpool PASS

- 2026-05-14T16:53:33+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260514-085042-659302-p37109-91b1b409-933b0a74/discussion_result.json`. Failures: []

- 2026-05-14T16:54:52+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260514-085042-794812-p37119-db82d395-ec94463c/discussion_result.json`. Failures: []

- 2026-05-14T16:55:42+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260514-085042-917991-p37127-66d88ef0-e70899f1/discussion_result.json`. Failures: []

- 2026-05-14T17:09:15+08:00: Lifecycle transition `review` -> `done` by `hermes-autorun-review-close`. Reason: auto-close review after proof-gated evidence Evidence: proof:sha256:7dfea0d8c04f287fd41e183db79e7ffd6553c776149d944d7c192cc8e9e2ad9e, proof:sha256:1c3a6bc53d4e28754cc505ed1bec0d9e2441f02e3e0740c99cec50a0ca8ab77b, command:py_compile_taskpool PASS, artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260514-085042-917991-p37127-66d88ef0-e70899f1/discussion_result.json
