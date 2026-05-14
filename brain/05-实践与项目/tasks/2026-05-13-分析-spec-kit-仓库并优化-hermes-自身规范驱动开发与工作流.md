---
type: task
lane: evolution
layer: L3
status: done
priority: P2
created: 2026-05-13T23:49:34+08:00
updated: 2026-05-14T09:59:43+08:00
expires_at: 2026-06-12T23:49:34+08:00
project: hermes-agent
architecture_target: local-brain
capability_delta: 通过分析 https://github.com/github/spec-kit 的规范驱动开发方法、产物结构与执行流程，增强 Hermes 在 spec-first、任务编排与执行闭环方面的自我进化能力。
anti_drift_check: 必须基于 spec-kit 仓库实际代码/文档与当前 Hermes 现状做差距分析；优先复用和 patch 既有 umbrella/class-level skill、references 或控制面机制，避免平行重复建设。
acceptance_evidence: spec-kit 仓库分析摘要、与 Hermes 对照差距清单、明确优化项与落地证据、任务池留痕与后续可派发记录。
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: certified
multimodel_ratification_artifact: /Users/charles/.hermes/tick-20260514-003851-001226-p50999-ac9aeb22-afc1534a/discussion_result.json
multimodel_last_checked_at: 2026-05-14T08:42:12+08:00
multimodel_round_status: passed
multimodel_last_gate_status: PASS
multimodel_last_decision: LOOP_DONE
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260514-003851-001226-p50999-ac9aeb22-afc1534a/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-13-分析-spec-kit-仓库并优化-hermes-自身规范驱动开发与工作流-state.json
multimodel_last_failures: []
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 3
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - proof:sha256:4d5a13c7b4747553efdcb552872e6ad7e3b1403f0bce6d8904575a74840e9d46
  - command:py_compile_taskpool PASS
  - artifact:/Users/charles/.hermes/tick-20260513-155927-695847-p5956-3cc0df84-720db875/discussion_result.json
  - command:multimodel_gate PASS
  - command:multimodel_decision LOOP_DONE
  - command:multimodel_status certified
  - command:multimodel_auto_outcome certification_passed
  - proof:sha256:863ea1698954cf902043e3cae53d6e53ac8e5114bf3577ea16b458657653694e
  - proof:sha256:727bc726530955f20618563c855c8f2a4f70375a0b80fac7214ec9c5842970b7
  - proof:sha256:036fd6f6f974f7f86b3d7e58ce852b8b5fc6fa3aa7de93ba087d8f1b945df1f0
  - artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260514-003851-001226-p50999-ac9aeb22-afc1534a/discussion_result.json
  - proof:sha256:80b11d0487d8baf2eb7556ec15cab6180a318789eba4c4556df3c81800a12c6a
concepts: ["spec-kit", "spec-driven-development", "hermes-self-optimization", "workflow-improvement"]
multimodel_advisory_only: False
multimodel_certification_authority: True
multimodel_advisory_reasons: ["architecture_target", "evolution_lane"]
multimodel_certification_reasons: ["loop_non_convergence"]
multimodel_auto_uncertain_count: 0
blocked_resolve_last_checked_at: 2026-05-14T09:59:21+08:00
blocked_resolve_multimodel_required: False
blocked_resolve_reasons: []
blocked_resolve_last_action: resolved_to_review
blocked_resolve_reason: "blocked resolver: evidence/certification now sufficient; send to review for normal auto-close gates"
blocker_status: resolved
blocker_summary: "blocked resolver: multimodel certification still not PASS (gate=PASS_ADVISORY_ONLY, decision=CONTINUE_LOOP, cert_reasons=['loop_non_convergence'])"
---

# Task - 分析 spec-kit 仓库并优化 Hermes 自身规范驱动开发与工作流

## Objective

分析 https://github.com/github/spec-kit ，提炼可迁移的规范驱动开发、产物组织与工作流设计，并映射为 Hermes 自身能力、技能体系或控制面优化。

## Acceptance Criteria

- [ ] 完成仓库分析；对比 Hermes 当前能力与工作流；形成可执行优化方案；必要时更新相关技能、references 或控制面；任务池留痕可继续自动派发。

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-13T23:49:34+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-13T23:59:27+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-autorun-step`. Reason: auto-claim-and-handoff

- 2026-05-13T23:59:27+08:00: Lifecycle transition `claimed` -> `running` by `hermes-autorun-step`.

- 2026-05-13T23:59:27+08:00: Lifecycle transition `running` -> `review` by `hermes-autorun-step`. Evidence: proof:sha256:4d5a13c7b4747553efdcb552872e6ad7e3b1403f0bce6d8904575a74840e9d46, command:py_compile_taskpool PASS

- 2026-05-14T00:02:18+08:00: Multimodel PUA-loop round `failed`. Gate `FAIL`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-155927-546576-p5944-002857ce-21fa0fd2/discussion_result.json`. Failures: ["missing_required_model_consulted:gpt-5.5", "missing_required_model_vote:gpt-5.5", "model_count_below_required:3/4", "models_consulted_below_required:3/4"]

- 2026-05-14T00:02:21+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-155927-376892-p5934-c152efc1-077f82ec/discussion_result.json`. Failures: []

- 2026-05-14T00:07:17+08:00: Multimodel PUA-loop round `failed`. Gate `FAIL`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-155927-695847-p5956-3cc0df84-720db875/discussion_result.json`. Failures: ["agreement_below_threshold:approach:0.65", "agreement_below_threshold:framing:0.65", "agreement_below_threshold:implementation_order:0.65", "best_within_constraints_missing:claude-opus-4-7", "best_within_constraints_missing:mimo-v2.5-pro", "missing_required_model_consulted:gpt-5.5", "missing_required_model_vote:gpt-5.5", "model_count_below_required:3/4"]

- 2026-05-14T00:28:15+08:00: Lifecycle transition `review` -> `retry` by `hermes-autorun-review-close`. Reason: multimodel closeout certification_failed; returned to retry for correction: previous_multimodel_certification_failed Evidence: proof:sha256:4d5a13c7b4747553efdcb552872e6ad7e3b1403f0bce6d8904575a74840e9d46, command:py_compile_taskpool PASS, artifact:/Users/charles/.hermes/tick-20260513-155927-695847-p5956-3cc0df84-720db875/discussion_result.json, multimodel_gate:FAIL, multimodel_decision:CONTINUE_LOOP, multimodel_status:not_certified, multimodel_auto_outcome:certification_failed

- 2026-05-14T00:28:16+08:00: Reconcile action `retry_due_promoted` by `hermes-reconcile`. Previous status `retry`.

- 2026-05-14T00:29:34+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-autorun-step`. Reason: auto-claim-and-handoff

- 2026-05-14T00:29:34+08:00: Lifecycle transition `claimed` -> `running` by `hermes-autorun-step`.

- 2026-05-14T00:29:34+08:00: Lifecycle transition `running` -> `review` by `hermes-autorun-step`. Evidence: proof:sha256:863ea1698954cf902043e3cae53d6e53ac8e5114bf3577ea16b458657653694e, command:py_compile_taskpool PASS

- 2026-05-14T00:29:34+08:00: Lifecycle transition `review` -> `retry` by `hermes-autorun-review-close`. Reason: multimodel closeout certification_failed; returned to retry for correction: previous_multimodel_certification_failed Evidence: proof:sha256:4d5a13c7b4747553efdcb552872e6ad7e3b1403f0bce6d8904575a74840e9d46, command:py_compile_taskpool PASS, artifact:/Users/charles/.hermes/tick-20260513-155927-695847-p5956-3cc0df84-720db875/discussion_result.json, multimodel_gate:FAIL, multimodel_decision:CONTINUE_LOOP, multimodel_status:not_certified, multimodel_auto_outcome:certification_failed, proof:sha256:863ea1698954cf902043e3cae53d6e53ac8e5114bf3577ea16b458657653694e, artifact:/Users/charles/.hermes/tick-20260513-155927-695847-p5956-3cc0df84-720db875/discussion_result.json, multimodel_gate:FAIL, multimodel_decision:CONTINUE_LOOP, multimodel_status:not_certified, multimodel_auto_outcome:certification_failed

- 2026-05-14T00:29:36+08:00: Reconcile action `retry_due_promoted` by `hermes-reconcile`. Previous status `retry`.

- 2026-05-14T00:29:40+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-autorun-step`. Reason: auto-claim-and-handoff

- 2026-05-14T00:29:40+08:00: Lifecycle transition `claimed` -> `running` by `hermes-autorun-step`.

- 2026-05-14T00:29:40+08:00: Lifecycle transition `running` -> `review` by `hermes-autorun-step`. Evidence: proof:sha256:727bc726530955f20618563c855c8f2a4f70375a0b80fac7214ec9c5842970b7, command:py_compile_taskpool PASS

- 2026-05-14T00:29:40+08:00: Lifecycle transition `review` -> `retry` by `hermes-autorun-review-close`. Reason: multimodel closeout certification_failed; returned to retry for correction: previous_multimodel_certification_failed Evidence: proof:sha256:4d5a13c7b4747553efdcb552872e6ad7e3b1403f0bce6d8904575a74840e9d46, command:py_compile_taskpool PASS, artifact:/Users/charles/.hermes/tick-20260513-155927-695847-p5956-3cc0df84-720db875/discussion_result.json, multimodel_gate:FAIL, multimodel_decision:CONTINUE_LOOP, multimodel_status:not_certified, multimodel_auto_outcome:certification_failed, proof:sha256:863ea1698954cf902043e3cae53d6e53ac8e5114bf3577ea16b458657653694e, proof:sha256:727bc726530955f20618563c855c8f2a4f70375a0b80fac7214ec9c5842970b7, artifact:/Users/charles/.hermes/tick-20260513-155927-695847-p5956-3cc0df84-720db875/discussion_result.json, multimodel_gate:FAIL, multimodel_decision:CONTINUE_LOOP, multimodel_status:not_certified, multimodel_auto_outcome:certification_failed

- 2026-05-14T00:29:53+08:00: Lifecycle transition `retry` -> `claimed` by `hermes-autorun-step`. Reason: auto-claim-and-handoff

- 2026-05-14T00:29:54+08:00: Lifecycle transition `claimed` -> `running` by `hermes-autorun-step`.

- 2026-05-14T00:29:54+08:00: Lifecycle transition `running` -> `review` by `hermes-autorun-step`. Evidence: proof:sha256:036fd6f6f974f7f86b3d7e58ce852b8b5fc6fa3aa7de93ba087d8f1b945df1f0, command:py_compile_taskpool PASS

- 2026-05-14T00:29:54+08:00: Lifecycle transition `review` -> `blocked` by `hermes-autorun-review-close`. Reason: multimodel closeout certification_failed; blocked to avoid unsafe/indefinite automation: previous_multimodel_certification_failed Evidence: proof:sha256:4d5a13c7b4747553efdcb552872e6ad7e3b1403f0bce6d8904575a74840e9d46, command:py_compile_taskpool PASS, artifact:/Users/charles/.hermes/tick-20260513-155927-695847-p5956-3cc0df84-720db875/discussion_result.json, multimodel_gate:FAIL, multimodel_decision:CONTINUE_LOOP, multimodel_status:not_certified, multimodel_auto_outcome:certification_failed, proof:sha256:863ea1698954cf902043e3cae53d6e53ac8e5114bf3577ea16b458657653694e, proof:sha256:727bc726530955f20618563c855c8f2a4f70375a0b80fac7214ec9c5842970b7, proof:sha256:036fd6f6f974f7f86b3d7e58ce852b8b5fc6fa3aa7de93ba087d8f1b945df1f0, artifact:/Users/charles/.hermes/tick-20260513-155927-695847-p5956-3cc0df84-720db875/discussion_result.json, multimodel_gate:FAIL, multimodel_decision:CONTINUE_LOOP, multimodel_status:not_certified, multimodel_auto_outcome:certification_failed

- 2026-05-14T07:42:01+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-233814-759546-p95545-8f9ef39a-5084b446/discussion_result.json`. Failures: []

- 2026-05-14T08:42:12+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260514-003851-001226-p50999-ac9aeb22-afc1534a/discussion_result.json`. Failures: []

- 2026-05-14T09:59:21+08:00: Lifecycle transition `blocked` -> `review` by `hermes`. Force: true. Reason: blocked resolver: evidence/certification now sufficient; send to review for normal auto-close gates Evidence: proof:sha256:4d5a13c7b4747553efdcb552872e6ad7e3b1403f0bce6d8904575a74840e9d46, command:py_compile_taskpool PASS, artifact:/Users/charles/.hermes/tick-20260513-155927-695847-p5956-3cc0df84-720db875/discussion_result.json, command:multimodel_gate PASS, command:multimodel_decision LOOP_DONE, command:multimodel_status certified, command:multimodel_auto_outcome certification_passed, proof:sha256:863ea1698954cf902043e3cae53d6e53ac8e5114bf3577ea16b458657653694e, proof:sha256:727bc726530955f20618563c855c8f2a4f70375a0b80fac7214ec9c5842970b7, proof:sha256:036fd6f6f974f7f86b3d7e58ce852b8b5fc6fa3aa7de93ba087d8f1b945df1f0, artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260514-003851-001226-p50999-ac9aeb22-afc1534a/discussion_result.json

- 2026-05-14T09:59:43+08:00: Lifecycle transition `review` -> `done` by `hermes-autorun-review-close`. Reason: auto-close review after proof-gated evidence Evidence: proof:sha256:80b11d0487d8baf2eb7556ec15cab6180a318789eba4c4556df3c81800a12c6a, proof:sha256:4d5a13c7b4747553efdcb552872e6ad7e3b1403f0bce6d8904575a74840e9d46, command:py_compile_taskpool PASS, artifact:/Users/charles/.hermes/tick-20260513-155927-695847-p5956-3cc0df84-720db875/discussion_result.json, command:multimodel_gate PASS, command:multimodel_decision LOOP_DONE, command:multimodel_status certified, command:multimodel_auto_outcome certification_passed, proof:sha256:863ea1698954cf902043e3cae53d6e53ac8e5114bf3577ea16b458657653694e, proof:sha256:727bc726530955f20618563c855c8f2a4f70375a0b80fac7214ec9c5842970b7, proof:sha256:036fd6f6f974f7f86b3d7e58ce852b8b5fc6fa3aa7de93ba087d8f1b945df1f0, artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260514-003851-001226-p50999-ac9aeb22-afc1534a/discussion_result.json
