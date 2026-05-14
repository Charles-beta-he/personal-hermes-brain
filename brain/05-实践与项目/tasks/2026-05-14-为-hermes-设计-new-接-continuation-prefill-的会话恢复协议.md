---
type: task
lane: evolution
layer: L3
status: done
priority: P1
created: 2026-05-14T01:37:00+08:00
updated: 2026-05-14T04:50:20+08:00
expires_at: 2026-06-13T01:37:00+08:00
project: hermes-agent
architecture_target: local-brain
capability_delta: 定义 /new 后承接 continuation packet 的恢复协议，使新 session 能以预填充消息稳定接棒旧 session，延续目标、证据、约束与下一步动作。
anti_drift_check: 必须复用当前 /new session reset、prefill_messages、session boundary hook 与 conversation history 真实实现，禁止抽象出脱离现有 CLI/agent 流程的平行恢复入口。
acceptance_evidence: 恢复协议设计、prefill 注入点、消息角色方案、CLI/agent 接口映射、兼容人工触发与自动触发的样例、回退路径。
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: certified
multimodel_ratification_artifact: /Users/charles/.hermes/tick-20260513-193642-129306-p64502-4cc85655-30267191/discussion_result.json
multimodel_last_checked_at: 2026-05-14T03:40:05+08:00
multimodel_round_status: passed
multimodel_last_gate_status: PASS
multimodel_last_decision: LOOP_DONE
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260513-193642-129306-p64502-4cc85655-30267191/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-14-为-hermes-设计-new-接-continuation-prefill-的会话恢复协议-state.json
multimodel_last_failures: []
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - proof:sha256:c38275ee87ee16589a2b4d22565596e2678622158dcfe71206eaff1ea69dc064
  - command:py_compile_taskpool PASS
  - proof:sha256:17608fde6bb5bbab7993e9eb1d41614e6481741e032fbb6514828ca87a894e51
  - artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260513-193642-129306-p64502-4cc85655-30267191/discussion_result.json
concepts: ["new-session", "prefill-messages", "continuation-resume", "session-protocol", "resume-handoff"]
multimodel_advisory_only: False
multimodel_certification_authority: True
multimodel_advisory_reasons: ["architecture_target", "evolution_lane"]
multimodel_certification_reasons: ["closeout_ratification"]
---

# Task - 为 Hermes 设计 /new 接 continuation prefill 的会话恢复协议

## Objective

设计 /new 与 continuation prefill 的正式恢复协议，打通新旧 session 的接力边界。

## Acceptance Criteria

- [ ] 明确恢复协议、消息格式、注入顺序、状态重建边界，以及最小落地实现方案。

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-14T01:37:00+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-14T02:50:17+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-autorun-step`. Reason: auto-claim-and-handoff

- 2026-05-14T02:50:17+08:00: Lifecycle transition `claimed` -> `running` by `hermes-autorun-step`.

- 2026-05-14T02:50:17+08:00: Lifecycle transition `running` -> `review` by `hermes-autorun-step`. Evidence: proof:sha256:c38275ee87ee16589a2b4d22565596e2678622158dcfe71206eaff1ea69dc064, command:py_compile_taskpool PASS

- 2026-05-14T02:53:45+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260513-185017-707563-p17653-998ef227-8d6fbd27/discussion_result.json`. Failures: []

- 2026-05-14T02:53:52+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260513-185017-587487-p17645-a42f0787-115eb026/discussion_result.json`. Failures: []

- 2026-05-14T02:56:18+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-185017-461062-p17635-eef4a3cf-ae7ecc6c/discussion_result.json`. Failures: []

- 2026-05-14T03:40:05+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260513-193642-129306-p64502-4cc85655-30267191/discussion_result.json`. Failures: []

- 2026-05-14T04:50:20+08:00: Lifecycle transition `review` -> `done` by `hermes-autorun-review-close`. Reason: auto-close review after proof-gated evidence Evidence: proof:sha256:17608fde6bb5bbab7993e9eb1d41614e6481741e032fbb6514828ca87a894e51, proof:sha256:c38275ee87ee16589a2b4d22565596e2678622158dcfe71206eaff1ea69dc064, command:py_compile_taskpool PASS, artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260513-193642-129306-p64502-4cc85655-30267191/discussion_result.json
