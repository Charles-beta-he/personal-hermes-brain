---
type: task
lane: evolution
layer: L3
status: done
priority: P1
created: 2026-05-14T21:17:06+08:00
updated: 2026-05-14T23:38:00+08:00
expires_at: 2026-06-12T21:36:05+08:00
project: hermes-agent-cache-optimization
architecture_target: provider-quota
capability_delta: fallback threshold narrowed brief
anti_drift_check: separate threshold policy from relay implementation so the parent scope does not drift
acceptance_evidence: proof log states threshold semantics and the evidence gate for noop-vs-change
workflow_contract: "['[08-模板/task-workflow-contract-template]']"
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: advisory_completed
multimodel_last_checked_at: 2026-05-14T23:20:42+08:00
multimodel_round_status: advisory_passed
multimodel_last_gate_status: PASS_ADVISORY_ONLY
multimodel_last_decision: CONTINUE_LOOP
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260514-151133-976755-p31404-54c1dfc2-f7183421/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-14-为-2026-05-13-优化-agent-多模型-子-agent-调度的缓存命中率固定全局前缀分层上下文避免-prompt-工具序列漂移-细化-fallbac-state.json
multimodel_last_failures: []
multimodel_failure_taxonomy: ["no_claims"]
multimodel_recommended_axes: ["quota_observability", "framing"]
multimodel_axis_rationale: "{'quota_observability': ['no_claims'], 'framing': ['no_claims']}"
auto_subtask_parent: 2026-05-13-优化-agent-多模型-子-agent-调度的缓存命中率固定全局前缀分层上下文避免-prompt-工具序列漂移
auto_subtask_kind: non_convergence_narrowing
auto_subtask_axis: fallback_threshold
auto_subtask_trigger: auto_subtask_on_non_convergence:fallback_threshold
auto_subtask_issue_ids: []
auto_subtask_parent_artifact: /Users/charles/.hermes/tick-20260513-174951-208071-p56081-20f01d3b-fc84793b/discussion_result.json
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - proof:sha256:6e00959028680d7cd4dc59a7b093de5ef6aee3bf600c3efecb3ea99b9c0a467e
  - command:py_compile_taskpool PASS
  - proof:sha256:e94d9dd9dec36d4445b9a9efb88da2e5a3e8a0d22039f2a86cc7180dfc99a446
concepts: ["task", "auto-subtask", "non-convergence", "fallback-thresholds"]
multimodel_advisory_only: True
multimodel_certification_authority: False
multimodel_advisory_reasons: ["architecture_target", "evolution_lane"]
multimodel_certification_reasons: []
---

# Task - 为 2026-05-13-优化-agent-多模型-子-agent-调度的缓存命中率固定全局前缀分层上下文避免-prompt-工具序列漂移 细化 fallback threshold 收敛前置任务

## Objective

Auto-generated convergence slice for parent `2026-05-13-优化-agent-多模型-子-agent-调度的缓存命中率固定全局前缀分层上下文避免-prompt-工具序列漂移`. Do not change the parent objective. Define fallback thresholds, downgrade policy, and the minimum evidence required to justify noop vs change on budget exhaustion behavior.

## Acceptance Criteria

- [ ] Produce a narrowed brief covering trigger thresholds, allowed fallback actions, and explicit noop-vs-change decision criteria.

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Parent Link

- Parent task: 2026-05-13-优化-agent-多模型-子-agent-调度的缓存命中率固定全局前缀分层上下文避免-prompt-工具序列漂移
- Discussion artifact: /Users/charles/.hermes/tick-20260513-174951-208071-p56081-20f01d3b-fc84793b/discussion_result.json
- Trigger axis: fallback_threshold
- Issue IDs: none tagged

## Parent Objective Snapshot

基于用户提出的核心理念落地优化：Agent 能跑起来的关键不是模型多强，而是缓存命中率多高。按全局层/项目层/会话层/消息层分层，修复时间戳进 system prompt、工具序列化顺序漂移、子 agent 参数微调三大陷阱；实践信息更新走 message 不改 prompt，切模型用子 agent 独立运行，工具状态靠调用切换而非删减，压缩操作作为父对话延伸。

## Narrowed Scope

- Only resolve threshold semantics and noop-vs-change decision criteria.
- Do not redesign the full handoff workflow here.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-14T21:17:06+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-14T23:20:42+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260514-151133-976755-p31404-54c1dfc2-f7183421/discussion_result.json`. Failures: []. Recommended axes: ["quota_observability", "framing"]. Axis rationale: {"quota_observability": ["no_claims"], "framing": ["no_claims"]}

- 2026-05-14T23:37:59+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-autorun-step`. Reason: auto-claim-and-handoff

- 2026-05-14T23:37:59+08:00: Lifecycle transition `claimed` -> `running` by `hermes-autorun-step`.

- 2026-05-14T23:38:00+08:00: Lifecycle transition `running` -> `review` by `hermes-autorun-step`. Evidence: proof:sha256:6e00959028680d7cd4dc59a7b093de5ef6aee3bf600c3efecb3ea99b9c0a467e, command:py_compile_taskpool PASS

- 2026-05-14T23:38:00+08:00: Lifecycle transition `review` -> `done` by `hermes-autorun-review-close`. Reason: auto-close review after proof-gated evidence Evidence: proof:sha256:e94d9dd9dec36d4445b9a9efb88da2e5a3e8a0d22039f2a86cc7180dfc99a446, proof:sha256:6e00959028680d7cd4dc59a7b093de5ef6aee3bf600c3efecb3ea99b9c0a467e, command:py_compile_taskpool PASS
