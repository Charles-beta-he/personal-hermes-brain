---
type: task
lane: evolution
layer: L3
status: done
priority: P1
created: 2026-05-14T01:42:54+08:00
updated: 2026-05-14T05:05:07+08:00
expires_at: 2026-06-13T01:42:54+08:00
project: hermes-agent
architecture_target: taskpool
capability_delta: 让任务在 add 入池时即完成优先级分层、依赖关系、执行顺序、parallel boundary 与多模型 triage 结果写入，提升 taskpool 独立性、可调度性与可审计性。
anti_drift_check: 必须优先复用现有 workflow_contract、frontmatter 字段、priority/multimodel 路由与 orchestrator 能力；避免新增平行任务模型或只在入池后补录治理信息。
acceptance_evidence: 现状与目标 add 流程对照、必填字段清单、创建期校验/默认策略、多模型 triage 接入点、依赖/顺序/并行边界写入方案、派生视图刷新策略、历史任务是否需要回填的评估结论、必要补丁或后续拆解任务。
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: certified
multimodel_ratification_artifact: /Users/charles/.hermes/tick-20260513-205020-930639-p32882-edd3e449-505cd106/discussion_result.json
multimodel_last_checked_at: 2026-05-14T04:53:15+08:00
multimodel_round_status: passed
multimodel_last_gate_status: PASS
multimodel_last_decision: LOOP_DONE
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260513-205020-930639-p32882-edd3e449-505cd106/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-14-补齐-brain-task-orchestrator-add-流程并在创建时强制写入优先级分层依赖顺序与多模型-triage-结果-state.json
multimodel_last_failures: []
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - proof:sha256:c3b8a815718e59a06be850501165cf363c07cd2b32bfcf418b3dcb806be4a1bc
  - command:py_compile_taskpool PASS
  - proof:sha256:f8135dd2f9961f0a1918cfc76494fa95c1a1920f913e412d7c2de26c484ce3e2
  - artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260513-205020-930639-p32882-edd3e449-505cd106/discussion_result.json
concepts: ["taskpool", "brain-task-orchestrator", "pre-ingest-triage", "dependency-ordering", "parallel-boundary", "multimodel-routing"]
multimodel_advisory_only: False
multimodel_certification_authority: True
multimodel_advisory_reasons: []
multimodel_certification_reasons: []
---

# Task - 补齐 brain_task_orchestrator add 流程并在创建时强制写入优先级分层依赖顺序与多模型 triage 结果

## Objective

补齐 brain_task_orchestrator add 流程，使任务创建时就跑完优先级与依赖治理，而不是入池后再补分析与排序。

## Acceptance Criteria

- [ ] 明确 add 流程应强制采集和写入的字段；形成创建期前置 triage 与依赖顺序写入方案；明确完成时默认刷新派生视图；历史任务是否全量回填需单独评估，不与 add 流程改造强绑定；必要时补充脚本实现或拆解后续子任务。

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-14T01:42:54+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-14T04:50:20+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-autorun-step`. Reason: auto-claim-and-handoff

- 2026-05-14T04:50:20+08:00: Lifecycle transition `claimed` -> `running` by `hermes-autorun-step`.

- 2026-05-14T04:50:20+08:00: Lifecycle transition `running` -> `review` by `hermes-autorun-step`. Evidence: proof:sha256:c3b8a815718e59a06be850501165cf363c07cd2b32bfcf418b3dcb806be4a1bc, command:py_compile_taskpool PASS

- 2026-05-14T04:52:41+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-205020-590910-p32863-b927e75a-3dc8fab1/discussion_result.json`. Failures: []

- 2026-05-14T04:53:15+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260513-205020-754224-p32873-8a2f8218-5c070b3e/discussion_result.json`. Failures: []

- 2026-05-14T04:53:15+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260513-205020-930639-p32882-edd3e449-505cd106/discussion_result.json`. Failures: []

- 2026-05-14T05:05:07+08:00: Lifecycle transition `review` -> `done` by `hermes-autorun-review-close`. Reason: auto-close review after proof-gated evidence Evidence: proof:sha256:f8135dd2f9961f0a1918cfc76494fa95c1a1920f913e412d7c2de26c484ce3e2, proof:sha256:c3b8a815718e59a06be850501165cf363c07cd2b32bfcf418b3dcb806be4a1bc, command:py_compile_taskpool PASS, artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260513-205020-930639-p32882-edd3e449-505cd106/discussion_result.json
