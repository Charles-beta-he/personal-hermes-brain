---
type: task
lane: evolution
layer: L3
status: done
priority: P1
created: 2026-05-14T01:36:41+08:00
updated: 2026-05-14T01:49:50+08:00
expires_at: 2026-06-13T01:36:41+08:00
project: hermes-agent
architecture_target: local-brain
capability_delta: 将预算耗尽后的 grace call 从普通总结升级为结构化 continuation packet 生成器，为新 session 续跑提供稳定、可机读、可复用的接力材料。
anti_drift_check: 必须基于当前 _handle_max_iterations、tools stripped final summary、上下文压缩与真实消息结构设计，避免引入与现有 summary 路径并行冲突的新机制。
acceptance_evidence: continuation packet 字段设计、与当前 grace call 总结路径差异分析、注入样例、失败/降级策略、必要实现补丁或接口变更。
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: advisory_completed
multimodel_last_checked_at: 2026-05-14T01:50:43+08:00
multimodel_round_status: advisory_passed
multimodel_last_gate_status: PASS_ADVISORY_ONLY
multimodel_last_decision: CONTINUE_LOOP
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260513-174310-966372-p45778-0ea0fdd0-a186faeb/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-14-为-hermes-设计-grace-call-输出结构化-continuation-packet-机制-state.json
multimodel_last_failures: []
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - proof:sha256:cd56ee89cfae563231169ede3d3a54badf855f9fccfcba2995327735180c2dcc
  - command:py_compile_taskpool PASS
  - proof:sha256:cacbd806629b629e19f0c826c23fd84d7d20e59ea77c1a9ed6a5a19bb762d35f
  - artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260513-174311-169248-p45788-890a09c2-1ab51b5b/discussion_result.json
concepts: ["grace-call", "continuation-packet", "iteration-budget", "resume-brief", "structured-summary"]
multimodel_advisory_only: True
multimodel_certification_authority: False
multimodel_advisory_reasons: []
multimodel_certification_reasons: []
---

# Task - 为 Hermes 设计 grace call 输出结构化 continuation packet 机制

## Objective

把预算耗尽时的 grace call 产物设计成适合自动续跑的结构化 continuation packet，而不是松散自然语言总结。

## Acceptance Criteria

- [ ] 明确 packet schema、生成时机、与现有总结路径的兼容关系、最小实现方案与风险控制。

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-14T01:36:41+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-14T01:43:10+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-autorun-step`. Reason: auto-claim-and-handoff

- 2026-05-14T01:43:10+08:00: Lifecycle transition `claimed` -> `running` by `hermes-autorun-step`.

- 2026-05-14T01:43:10+08:00: Lifecycle transition `running` -> `review` by `hermes-autorun-step`. Evidence: proof:sha256:cd56ee89cfae563231169ede3d3a54badf855f9fccfcba2995327735180c2dcc, command:py_compile_taskpool PASS

- 2026-05-14T01:46:37+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260513-174311-368437-p45796-8c718072-d5a3de45/discussion_result.json`. Failures: []

- 2026-05-14T01:46:39+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260513-174311-169248-p45788-890a09c2-1ab51b5b/discussion_result.json`. Failures: []

- 2026-05-14T01:49:50+08:00: Lifecycle transition `review` -> `done` by `hermes-autorun-review-close`. Reason: auto-close review after proof-gated evidence Evidence: proof:sha256:cacbd806629b629e19f0c826c23fd84d7d20e59ea77c1a9ed6a5a19bb762d35f, proof:sha256:cd56ee89cfae563231169ede3d3a54badf855f9fccfcba2995327735180c2dcc, command:py_compile_taskpool PASS, artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260513-174311-169248-p45788-890a09c2-1ab51b5b/discussion_result.json

- 2026-05-14T01:50:43+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-174310-966372-p45778-0ea0fdd0-a186faeb/discussion_result.json`. Failures: []
