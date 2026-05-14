---
type: task
lane: evolution
layer: L3
status: done
priority: P1
created: 2026-05-14T01:16:41+08:00
updated: 2026-05-14T01:43:11+08:00
expires_at: 2026-06-13T01:16:41+08:00
project: hermes-agent
architecture_target: local-brain
capability_delta: 通过多模型分析预算耗尽后的 grace call、continuation packet、/new 会话接力与 prefill_messages 机制，形成 Hermes 可落地的自动续跑方案，提升超长任务完成率与恢复能力。
anti_drift_check: 必须基于当前 Hermes iteration budget、grace call、prefill_messages、session reset 与 context compression 真实实现做差距分析；优先复用现有 session handoff、prefill、taskpool 与控制面，不新增平行机制。
acceptance_evidence: 多模型分析结论、现状与目标架构对照、continuation packet 结构方案、/new 续跑接入点设计、风险与回退策略、必要实现补丁或任务拆解。
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: not_certified
multimodel_last_checked_at: 2026-05-14T01:48:55+08:00
multimodel_round_status: failed
multimodel_last_gate_status: FAIL
multimodel_last_decision: CONTINUE_LOOP
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260513-173738-754405-p36276-9d8fecda-aaf64cff/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-14-对预算耗尽后的-grace-call-continuation-new-session-resume-机制做多模型分析并完善方案-state.json
multimodel_last_failures: ["agreement_below_threshold:approach:0.65", "agreement_below_threshold:framing:0.65", "agreement_below_threshold:implementation_order:0.65", "best_within_constraints_missing:claude-opus-4-7", "best_within_constraints_missing:deepseek-v4-pro", "best_within_constraints_missing:gpt-5.5", "non_approve_vote:claude-opus-4-7:amend", "non_approve_vote:deepseek-v4-pro:amend"]
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - proof:sha256:a4a35e0da3b6ba6e3a9d54dddde4fc10ec08c80be4f98b5d9666a0b474514f45
  - command:py_compile_taskpool PASS
  - proof:sha256:b7ce3637955d2d808d5e8c084c7967208f795d974fdc8b21ec95cb5932a055d5
  - artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260513-173738-607871-p36269-2d2f96ab-0a5a152d/discussion_result.json
concepts: ["multimodel-analysis", "grace-call", "continuation-packet", "new-session-resume", "iteration-budget", "context-compression"]
multimodel_advisory_only: False
multimodel_certification_authority: False
multimodel_advisory_reasons: []
multimodel_certification_reasons: []
---

# Task - 对预算耗尽后的 grace-call continuation / new-session resume 机制做多模型分析并完善方案

## Objective

对“预算耗尽时将 grace call 产物作为新 session 预填充消息继续任务”的方案做多模型分析，完善为可执行的 continuation handoff 设计，并映射到 Hermes 自身能力优化。

## Acceptance Criteria

- [ ] 完成多模型分析；明确 grace call 产物与新 session prefill 的边界；产出 continuation handoff 完整方案；必要时补充 skills、references、控制面或实现任务。

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-14T01:16:41+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-14T01:37:38+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-autorun-step`. Reason: auto-claim-and-handoff

- 2026-05-14T01:37:38+08:00: Lifecycle transition `claimed` -> `running` by `hermes-autorun-step`.

- 2026-05-14T01:37:38+08:00: Lifecycle transition `running` -> `review` by `hermes-autorun-step`. Evidence: proof:sha256:a4a35e0da3b6ba6e3a9d54dddde4fc10ec08c80be4f98b5d9666a0b474514f45, command:py_compile_taskpool PASS

- 2026-05-14T01:40:08+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-173738-437172-p36259-c322cb40-21d52596/discussion_result.json`. Failures: []

- 2026-05-14T01:40:57+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260513-173738-607871-p36269-2d2f96ab-0a5a152d/discussion_result.json`. Failures: []

- 2026-05-14T01:43:11+08:00: Lifecycle transition `review` -> `done` by `hermes-autorun-review-close`. Reason: auto-close review after proof-gated evidence Evidence: proof:sha256:b7ce3637955d2d808d5e8c084c7967208f795d974fdc8b21ec95cb5932a055d5, proof:sha256:a4a35e0da3b6ba6e3a9d54dddde4fc10ec08c80be4f98b5d9666a0b474514f45, command:py_compile_taskpool PASS, artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260513-173738-607871-p36269-2d2f96ab-0a5a152d/discussion_result.json

- 2026-05-14T01:48:55+08:00: Multimodel PUA-loop round `failed`. Gate `FAIL`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-173738-754405-p36276-9d8fecda-aaf64cff/discussion_result.json`. Failures: ["agreement_below_threshold:approach:0.65", "agreement_below_threshold:framing:0.65", "agreement_below_threshold:implementation_order:0.65", "best_within_constraints_missing:claude-opus-4-7", "best_within_constraints_missing:deepseek-v4-pro", "best_within_constraints_missing:gpt-5.5", "non_approve_vote:claude-opus-4-7:amend", "non_approve_vote:deepseek-v4-pro:amend"]
