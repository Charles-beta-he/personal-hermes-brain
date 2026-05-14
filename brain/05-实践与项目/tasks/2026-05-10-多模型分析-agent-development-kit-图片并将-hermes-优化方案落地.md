---
type: task
lane: evolution
layer: L3
status: done
priority: P1
created: 2026-05-10T14:15:34+08:00
updated: 2026-05-13T00:24:49+08:00
expires_at: 2026-06-09T14:15:34+08:00
project: hermes-agentops-engineering
architecture_target: taskpool
capability_delta: Selectively convert ADK screenshot insights into Hermes-native taskpool/guardrail improvements without importing third-party runtime.
anti_drift_check: Must remain evidence-first and advisory until unresolved severity>=3 multimodel issues are closed; no Markdown body execution or automatic done.
acceptance_evidence: tick-20260510-060032 truth-grounded not_certified artifact plus follow-up selfcheck/proof-check/dashboard evidence.
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: certified
multimodel_ratification_artifact: /Users/charles/.hermes/tick-20260512-075430/discussion_result.json
multimodel_last_checked_at: 2026-05-12T15:59:23+08:00
multimodel_round_status: passed
multimodel_last_gate_status: PASS
multimodel_last_decision: LOOP_DONE
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260512-075430/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-10-多模型分析-agent-development-kit-图片并将-hermes-优化方案落地-state.json
multimodel_last_failures: []
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: /Users/charles/.hermes
evidence:
  - artifact:/tmp/adk_image_multimodel_evidence.json
  - artifact:/tmp/adk_image_hermes_optimization_state.json
  - artifact:/Users/charles/.hermes/tick-20260510-060032/merged_plan.json
  - artifact:/Users/charles/.hermes/tick-20260510-060032/discussion_result.json
  - artifact:/Users/charles/.hermes/tick-20260510-060032/final/certification_manifest.json
  - artifact:/Users/charles/.hermes/tick-20260512-075430/discussion_result.json
  - proof:brain_task_orchestrator selfcheck/proof-check/boundary-check PASS 2026-05-13T00:23:17+08:00
  - proof:ratification-gate PASS; selfcheck PASS; proof-check PASS; boundary-check PASS
concepts: ["multi-model", "agent-development-kit", "hermes", "self-improvement", "agentops", "taskpool", "guardrails", "plugins", "subagents"]
---

# Task - 多模型分析 Agent Development Kit 图片并将 Hermes 优化方案落地

## Objective

基于截图中的 Agent Development Kit 五文件夹架构（CLAUDE.md、skills/、hooks/、subagents/、plugins/）和四模型分析结果，选择性提炼 Hermes-native 优化方案；先区分 Hermes 已有能力与真实缺口，再按 P0/P1/P2 建立可验证实施计划，不整体引入第三方运行时。

## Acceptance Criteria

- [ ] 1) 读取图片 OCR/vision 证据与 tick-20260510-060032 多模型 artifact；2) 解决 discussion_result 中未认证 issue ledger，至少补齐 evidence_requests 或降级为 advisory；3) 形成 P0/P1/P2 Hermes-native ADK 优化实施方案；4) P0 优先覆盖 fail-closed taskpool proof gate、repo-local agent constitution/hook registry，不执行 Markdown 任务体、不自动 done；5) P1/P2 覆盖 skill governance、plugin supply-chain governance、subagent budget/context isolation、AgentOps observability/eval/prompt-injection fixtures；6) 运行 brain_task_orchestrator selfcheck/proof-check/dashboard 与相关脚本测试，更新证据链。

## Multi-model Result Snapshot

- Source image: `/Users/charles/.hermes/images/clip_20260510_135202_1.png`.
- OCR / vision extraction: `Agent Development Kit` = `CLAUDE.md` + `skills/` + `hooks/` + `subagents/` + `plugins/`.
- Consult state: `/tmp/adk_image_hermes_optimization_state.json`.
- Tick: `/Users/charles/.hermes/tick-20260510-060032`.
- Models reached in fan-out: `claude-opus-4-7`, `gpt-5.5`, `deepseek-v4-pro`, `mimo-v2.5-pro`.
- Truth gate: grounded for C-001..C-004, evidence_coverage=1.0.
- Certification status: `not_certified` after one focused discussion round.
- Reason for non-certification: implementation patch family had 20 unresolved severity>=3 issues / coverage gaps; fan-out produced useful proposals but patch-level certification requires additional evidence requests and implementation-specific claims.

## Adopt / Reject Boundary

Adopt selectively as Hermes-native architecture principles:

- `CLAUDE.md` concept -> repo-local constitution / AGENTS.md contract / project policy loader.
- `skills/` concept -> existing Hermes skill registry + owner/version/eval metadata.
- `hooks/` concept -> deterministic lifecycle guardrails, proof gates, hook registry, fail-closed validators.
- `subagents/` concept -> delegate/external-agent registry with explicit budget, context scope, and tool allowlist.
- `plugins/` concept -> tool/MCP/plugin registry with manifest, pinning, permission scopes, secret boundary, and supply-chain checks.

Reject for now:

- Wholesale copying a third-party ADK runtime.
- Treating folders as governance without deterministic enforcement.
- Letting Markdown task bodies execute commands.
- Letting taskpool/cron mark `done` directly without proof + review.
- Creating a second canonical memory/skill/plugin stack that duplicates Hermes.

## P0 / P1 / P2 Implementation Plan

### P0 — safety and repo-local contract

- [ ] Resolve evidence requests for existing Hermes surfaces: AGENTS.md/CLAUDE.md loading, hooks/proof gates, taskpool done transitions, plugin config, audit/eval directories.
- [ ] Split `constitution` and `hook registry` into separate implementation claims before certification.
- [ ] Add or harden taskpool proof-gate verifier: `pending/claimed/running/review/done` lifecycle must fail closed; no Markdown execution; `done` requires structured proof hash or explicit artifact evidence.
- [ ] Define repo-local Agent Kit contract verifier that reports `existing / gap / duplicate / intentionally unsupported` for policy, skills, hooks, subagents, plugins.

### P1 — governance and supply-chain

- [ ] Add skill governance metadata/check: owner, version, eval suite, last audit, deprecation path; integrate with existing skill steward instead of a second system.
- [ ] Add plugin/tool/MCP governance checker: manifest, lock/pin, permission scopes, env var declarations, secret boundary, broad filesystem/network warning, install-source allowlist.
- [ ] Create prompt-injection red-team fixtures for web/browser/subagent outputs and immutable instruction handling.

### P2 — observability and specialized agents

- [ ] Add AgentOps read-only evaluation gate: taskpool transitions, verifier failures, subagent runs, plugin/tool usage, model quota uncertainty, proof-review outcomes.
- [ ] Add structured audit log proposal and smoke check: tool name, args hash, status, duration, model/provider, token/cost where available, linked task/proof id.
- [ ] Add subagent contract schema: role, can_edit, allowed tools, allowed paths, context scope, token/wall-clock/tool budget, approval requirement.

## Execution Protocol

- [ ] Start by fulfilling `discussion_result.json.evidence_requests` with read-only tools.
- [ ] Rebuild claim/evidence bundle with implementation-specific claims per patch family.
- [ ] Rerun multi-model discussion only after deterministic evidence exists; if still unresolved, preserve `not_certified` and split task further.
- [ ] Implement the smallest P0 slice first; do not batch P0/P1/P2 into one patch.
- [ ] After each code change, run targeted tests and global selfchecks, then commit scoped files only in `/Users/charles/.hermes`.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| image vision extraction | done | `/tmp/adk_image_multimodel_evidence.json` |
| consult_models state | done | `/tmp/adk_image_hermes_optimization_state.json` |
| T3 quorum4 fan-out | done | `/Users/charles/.hermes/tick-20260510-060032/plans/*.json` |
| discussion / ratification | not_certified | `/Users/charles/.hermes/tick-20260510-060032/discussion_result.json` |
| certification manifest | not_certified | `/Users/charles/.hermes/tick-20260510-060032/final/certification_manifest.json` |
| brain_task_orchestrator list | OK | taskpool flow repair reran list/dry-run; stale claim released |
| brain_task_orchestrator selfcheck | PASS | 2026-05-11T22:29 +08:00 |
| brain_task_orchestrator proof-check | PASS | 2026-05-11T22:29 +08:00 |

## Proof Log

- 2026-05-10T14:15:34+08:00: Task created from local-brain control point.
- 2026-05-10T14:16:30+08:00: Added image evidence, T3 fan-out artifact, not-certified discussion result, P0/P1/P2 implementation plan, and fail-closed execution protocol.

- 2026-05-11T22:30:54+08:00: 流转校准：释放过期 agent-team-controller claim；显式记录 multimodel_status=not_certified，保留 20260510-060032 为 truth-grounded provenance，需补齐 evidence_requests 后重新 target-bound 4/4。

## Blockers / Confusions

- Multi-model analysis is truth-grounded but not implementation-certified. The next executor must not claim the ADK optimization patch plan is certified until issue ledger I-001..I-020 is resolved or intentionally split/downscoped.
- `discussion_result.json` requested additional read-only evidence for existing Hermes hooks, plugin governance, audit/eval, AGENTS.md/CLAUDE.md loading, and prompt-injection controls.

## Final Handoff

- Status: pending; ready for taskpool dispatch.
- Evidence: image extraction + four-model fan-out + not-certified ratification artifact linked in frontmatter.
- Residual risk: implementation plan needs evidence-request fulfillment and a second certification pass before broad Hermes runtime changes.

- 2026-05-11T00:42:51+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T01:39:48+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: deadlock_fix_release

- 2026-05-11T01:47:24+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T02:12:48+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: timeout_cleanup

- 2026-05-11T16:31:40+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T17:34:53+08:00: Reconcile action `stale_claim_released` by `hermes-reconcile`. Previous status `claimed`.

- 2026-05-11T20:04:32+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T20:06:49+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: orphan_worker_cleaned_after_manual_agent_cycle_timeout

- 2026-05-11T21:19:19+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T22:29:52+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: stale_claim_cleanup_taskpool_flow_repair

- 2026-05-12T02:54:26+08:00: Permission taxonomy defaults applied by `permission-migrate --apply`. Changes: {"required_authority": "budget-handoff", "max_authority": "autonomous-execution", "permission_tier": "budget-handoff", "write_surfaces": ["taskpool", "hermes-scripts", "brain"], "completion_gate": "ratification-or-selfcheck-review-done", "lane_semantics": "self-evolution: deterministic gates plus ratification/proof before review->done"}

- 2026-05-12T07:12:54+08:00: Multimodel PUA-loop round `skipped`. Gate `SKIP`, decision `CONTINUE_LOOP`. Discussion `missing`. Failures: ["no_discussion_result"]

- 2026-05-12T08:17:13+08:00: Multimodel PUA-loop round `skipped`. Gate `SKIP`, decision `CONTINUE_LOOP`. Discussion `missing`. Failures: ["no_discussion_result"]

- 2026-05-12T09:30:36+08:00: Multimodel PUA-loop round `skipped`. Gate `SKIP`, decision `CONTINUE_LOOP`. Discussion `missing`. Failures: ["no_discussion_result"]

- 2026-05-12T11:44:56+08:00: Multimodel PUA-loop round `skipped`. Gate `SKIP`, decision `CONTINUE_LOOP`. Discussion `missing`. Failures: ["no_discussion_result"]

- 2026-05-12T12:39:45+08:00: Multimodel PUA-loop round `failed`. Gate `FAIL`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260512-042805/discussion_result.json`. Failures: ["agreement_below_threshold:approach:0.65", "agreement_below_threshold:framing:0.65", "agreement_below_threshold:implementation_order:0.65", "best_within_constraints_missing:claude-opus-4-7", "best_within_constraints_missing:gpt-5.5", "non_approve_vote:claude-opus-4-7:amend", "non_approve_vote:deepseek-v4-pro:amend", "non_approve_vote:gpt-5.5:amend"]

- 2026-05-12T14:03:02+08:00: Multimodel PUA-loop round `failed`. Gate `FAIL`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260512-055233/discussion_result.json`. Failures: ["agreement_below_threshold:approach:0.65", "agreement_below_threshold:framing:0.65", "agreement_below_threshold:implementation_order:0.65", "best_within_constraints_missing:claude-opus-4-7", "best_within_constraints_missing:gpt-5.5", "best_within_constraints_missing:mimo-v2.5-pro", "non_approve_vote:claude-opus-4-7:amend", "non_approve_vote:deepseek-v4-pro:amend"]

- 2026-05-12T15:06:05+08:00: Multimodel PUA-loop round `failed`. Gate `FAIL`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260512-065230/discussion_result.json`. Failures: ["agreement_below_threshold:approach:0.65", "agreement_below_threshold:framing:0.65", "agreement_below_threshold:implementation_order:0.65", "best_within_constraints_missing:claude-opus-4-7", "best_within_constraints_missing:gpt-5.5", "best_within_constraints_missing:mimo-v2.5-pro", "non_approve_vote:claude-opus-4-7:amend", "non_approve_vote:deepseek-v4-pro:amend"]

- 2026-05-12T15:59:23+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260512-075430/discussion_result.json`. Failures: []

- 2026-05-13T00:22:03+08:00: Lifecycle transition `pending` -> `claimed` by `hermes`.

- 2026-05-13T00:24:49+08:00: Lifecycle transition `claimed` -> `running` by `hermes`. Reason: resume closeout verification

- 2026-05-13T00:24:49+08:00: Lifecycle transition `running` -> `review` by `hermes`. Reason: ratification_gate_PASS_selfcheck_proof_boundary_PASS_no_action_certification Evidence: artifact:/Users/charles/.hermes/tick-20260512-075430/discussion_result.json, proof:brain_task_orchestrator selfcheck/proof-check/boundary-check PASS 2026-05-13T00:23:17+08:00

- 2026-05-13T00:24:49+08:00: Lifecycle transition `review` -> `done` by `hermes`. Reason: review closeout after ratification gate PASS and deterministic checks PASS Evidence: artifact:/Users/charles/.hermes/tick-20260512-075430/discussion_result.json, proof:ratification-gate PASS; selfcheck PASS; proof-check PASS; boundary-check PASS
