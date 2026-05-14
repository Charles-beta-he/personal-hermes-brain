---
type: task
lane: evolution
layer: L3
status: done
priority: P1
created: 2026-05-14T21:17:06+08:00
updated: 2026-05-15T00:50:25+08:00
expires_at: 2026-06-12T21:36:05+08:00
project: hermes-agent-cache-optimization
architecture_target: provider-quota
capability_delta: quota observability narrowed brief
anti_drift_check: keep parent objective unchanged while proving quota_state semantics
acceptance_evidence: proof log cites source evidence for quota_state confidence and unknown handling
workflow_contract: "['[08-模板/task-workflow-contract-template]']"
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: not_certified
multimodel_last_checked_at: 2026-05-15T01:02:51+08:00
multimodel_round_status: failed
multimodel_last_gate_status: FAIL
multimodel_last_decision: CONTINUE_LOOP
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260514-165025-559741-p71625-e949886b-9992f36d/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-14-为-2026-05-13-优化-agent-多模型-子-agent-调度的缓存命中率固定全局前缀分层上下文避免-prompt-工具序列漂移-细化-quota-o-state.json
multimodel_last_failures: ["agreement_below_threshold:approach:0.65", "agreement_below_threshold:framing:0.65", "agreement_below_threshold:implementation_order:0.65", "best_within_constraints_missing:claude-opus-4-7", "best_within_constraints_missing:gpt-5.5", "best_within_constraints_missing:mimo-v2.5-pro", "non_approve_vote:claude-opus-4-7:amend", "non_approve_vote:deepseek-v4-pro:amend"]
multimodel_failure_taxonomy: ["agreement_low", "criteria_missing", "vote_reject"]
multimodel_recommended_axes: ["fallback_threshold", "relay_ordering", "framing"]
multimodel_axis_rationale: "{'fallback_threshold': ['criteria_missing'], 'relay_ordering': ['agreement_low'], 'framing': ['vote_reject']}"
auto_subtask_parent: 2026-05-13-优化-agent-多模型-子-agent-调度的缓存命中率固定全局前缀分层上下文避免-prompt-工具序列漂移
auto_subtask_kind: non_convergence_narrowing
auto_subtask_axis: quota_observability
auto_subtask_trigger: auto_subtask_on_non_convergence:quota_observability
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
  - proof:sha256:a67d5461664d61c4d04a675b28292bb51faf0285752534d6ed0ecd34cfc083a5
  - command:py_compile_taskpool PASS
  - proof:sha256:c24c8d47bc320c51f1f0571a7f771e0e708cb6dc627575c9f8f3032c65948328
concepts: ["task", "auto-subtask", "non-convergence", "quota-observability"]
multimodel_advisory_only: False
multimodel_certification_authority: False
multimodel_advisory_reasons: []
multimodel_certification_reasons: []
---

# Task - 为 2026-05-13-优化-agent-多模型-子-agent-调度的缓存命中率固定全局前缀分层上下文避免-prompt-工具序列漂移 细化 quota observability 收敛前置任务

## Objective

Auto-generated convergence slice for parent `2026-05-13-优化-agent-多模型-子-agent-调度的缓存命中率固定全局前缀分层上下文避免-prompt-工具序列漂移`. Do not change the parent objective. Define quota_state source, confidence, staleness, and fail-closed semantics so future ratification can decide whether quota-aware change is required.

## Acceptance Criteria

- [ ] Produce a narrowed brief covering quota_state source, confidence, unknown/unobservable handling, and file-backed evidence locations.

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Parent Link

- Parent task: 2026-05-13-优化-agent-多模型-子-agent-调度的缓存命中率固定全局前缀分层上下文避免-prompt-工具序列漂移
- Discussion artifact: /Users/charles/.hermes/tick-20260513-174951-208071-p56081-20f01d3b-fc84793b/discussion_result.json
- Trigger axis: quota_observability
- Issue IDs: none tagged

## Parent Objective Snapshot

基于用户提出的核心理念落地优化：Agent 能跑起来的关键不是模型多强，而是缓存命中率多高。按全局层/项目层/会话层/消息层分层，修复时间戳进 system prompt、工具序列化顺序漂移、子 agent 参数微调三大陷阱；实践信息更新走 message 不改 prompt，切模型用子 agent 独立运行，工具状态靠调用切换而非删减，压缩操作作为父对话延伸。

## Narrowed Scope

- Only resolve quota observability and evidence gaps.
- Do not decide relay ordering or broader fallback policy here.

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

- 2026-05-14T21:56:56+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260514-134605-684532-p72328-2e53327e-18a9d07e/discussion_result.json`. Failures: []. Recommended axes: ["quota_observability", "framing"]. Axis rationale: {"quota_observability": ["no_claims"], "framing": ["no_claims"]}

- 2026-05-15T00:50:25+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-autorun-step`. Reason: auto-claim-and-handoff

- 2026-05-15T00:50:25+08:00: Lifecycle transition `claimed` -> `running` by `hermes-autorun-step`.

- 2026-05-15T00:50:25+08:00: Lifecycle transition `running` -> `review` by `hermes-autorun-step`. Evidence: proof:sha256:a67d5461664d61c4d04a675b28292bb51faf0285752534d6ed0ecd34cfc083a5, command:py_compile_taskpool PASS

- 2026-05-15T00:50:25+08:00: Lifecycle transition `review` -> `done` by `hermes-autorun-review-close`. Reason: auto-close review after proof-gated evidence Evidence: proof:sha256:c24c8d47bc320c51f1f0571a7f771e0e708cb6dc627575c9f8f3032c65948328, proof:sha256:a67d5461664d61c4d04a675b28292bb51faf0285752534d6ed0ecd34cfc083a5, command:py_compile_taskpool PASS

- 2026-05-15T00:55:30+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260514-165025-685987-p71634-0086d035-82b49087/discussion_result.json`. Failures: []. Recommended axes: ["quota_observability", "framing"]. Axis rationale: {"quota_observability": ["no_claims"], "framing": ["no_claims"]}

- 2026-05-15T01:02:51+08:00: Multimodel PUA-loop round `failed`. Gate `FAIL`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260514-165025-559741-p71625-e949886b-9992f36d/discussion_result.json`. Failures: ["agreement_below_threshold:approach:0.65", "agreement_below_threshold:framing:0.65", "agreement_below_threshold:implementation_order:0.65", "best_within_constraints_missing:claude-opus-4-7", "best_within_constraints_missing:gpt-5.5", "best_within_constraints_missing:mimo-v2.5-pro", "non_approve_vote:claude-opus-4-7:amend", "non_approve_vote:deepseek-v4-pro:amend"]. Recommended axes: ["fallback_threshold", "relay_ordering", "framing"]. Axis rationale: {"fallback_threshold": ["criteria_missing"], "relay_ordering": ["agreement_low"], "framing": ["vote_reject"]}
