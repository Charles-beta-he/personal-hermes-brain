---
type: task
lane: evolution
layer: L3
status: done
priority: P1
created: 2026-05-10T18:29:12+08:00
updated: 2026-05-13T16:06:16+08:00
expires_at: 2026-06-09T18:29:12+08:00
project: hermes-skill-learning
architecture_target: skill-graph
capability_delta: 评估可组合 skill 编排、brainstorming/TDD 原子能力拆分、与 Hermes 现有 pua/loop/tdd/plan 的互补关系。
anti_drift_check: 不直接导入外部 skill；先做来源核验、能力矩阵、最小复现实验与冲突/重复检查。
acceptance_evidence: "截图 OCR: 20多个可组合 Skill 覆盖开发全流程，brainstorming 和 TDD 最好用; linked state: /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/multi-model-state-linked-2026-05-10.json; multi-model artifact: /Users/charles/.hermes/tick-20260510-102539; truth gate grounded, fanout quorum met, consensus weak/advisory only."
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: advisory_completed
multimodel_last_checked_at: 2026-05-13T11:38:07+08:00
multimodel_round_status: advisory_passed
multimodel_last_gate_status: PASS_ADVISORY_ONLY
multimodel_last_decision: CONTINUE_LOOP
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260513-033510/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-10-skill学习路线superpowers-可组合开发流程与-tdd-brainstorming-适配评估-state.json
multimodel_last_failures: []
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: evolution:skill-learning:superpowers
evidence:
  - artifact:/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/superpowers-source-evidence-2026-05-13.json
  - artifact:/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/superpowers-composable-evaluation-2026-05-13.md
  - proof:superpowers evidence json repo=obra/superpowers license=MIT skill_count=14; decision=BORROW
concepts: ["skill-learning", "superpowers", "multi-model", "evidence-first"]
multimodel_advisory_only: True
multimodel_certification_authority: False
multimodel_advisory_reasons: ["architecture_target", "evolution_lane"]
multimodel_certification_reasons: []
---

# Task - Skill学习路线：Superpowers 可组合开发流程与 TDD/brainstorming 适配评估

## Objective

对截图候选 skill `superpowers` 走 evidence-first 分析学习路线：先核验来源/许可/能力，再评估 Hermes 适配，最后输出 adopt/borrow/reject 决策；本任务不安装、不导入、不宣称已采用。截图说明：20多个可组合 Skill 覆盖开发全流程，brainstorming 和 TDD 最好用。

## Acceptance Criteria

- [ ] 确认来源与许可；完成 Superpowers 能力矩阵；选 2 个 brainstorming/TDD 场景做可复现实验设计；给出 adopt/borrow/reject 决策与证据链接

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| Python stdlib GitHub API evidence collection | passed | `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/superpowers-source-evidence-2026-05-13.json` |
| deterministic report validation script | passed | repo=`obra/superpowers`, license=`MIT`, skill_count=14, matrix_rows=14, experiments A/B present, decision=BORROW, `ALL_VALIDATION_CHECKS_PASS` |
| read-back verification | passed | report and evidence JSON read via Hermes file tools; matrix grep returned 14 rows |

## Proof Log

- 2026-05-10T18:29:12+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-11T01:43:59+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T02:12:49+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: timeout_cleanup

- 2026-05-11T05:05:11+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T06:10:45+08:00: Reconcile action `stale_claim_released` by `hermes-reconcile`. Previous status `claimed`.

- 2026-05-11T06:15:33+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T07:19:15+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-11T13:51:01+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T15:01:02+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-12T02:54:25+08:00: Permission taxonomy defaults applied by `permission-migrate --apply`. Changes: {"required_authority": "budget-handoff", "max_authority": "autonomous-execution", "permission_tier": "budget-handoff", "write_surfaces": ["taskpool", "hermes-scripts", "brain"], "completion_gate": "ratification-or-selfcheck-review-done", "lane_semantics": "self-evolution: deterministic gates plus ratification/proof before review->done"}

- 2026-05-13T11:38:07+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-033510/discussion_result.json`. Failures: []

- 2026-05-13T15:45:53+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-gpt-5.5`. Reason: continue-loop-parallel-skill-learning

- 2026-05-13T15:45:53+08:00: Lifecycle transition `claimed` -> `running` by `hermes-gpt-5.5`. Reason: parallel-skill-learning-evidence-slice
- 2026-05-13T15:55:00+08:00: Deterministic evidence slice completed by subagent without lifecycle transition: source/license verified from GitHub API/raw via Python stdlib; report written to `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/superpowers-composable-evaluation-2026-05-13.md`; evidence cache written to `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/superpowers-source-evidence-2026-05-13.json`; validation script returned `ALL_VALIDATION_CHECKS_PASS`.

- 2026-05-13T16:06:16+08:00: Lifecycle transition `running` -> `review` by `hermes-gpt-5.5`. Reason: deterministic evidence slice verified; advisory-only provenance not used as closeout authority Evidence: artifact:/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/superpowers-composable-evaluation-2026-05-13.md

- 2026-05-13T16:06:16+08:00: Lifecycle transition `review` -> `done` by `hermes-gpt-5.5`. Reason: selfcheck-review-done: source/license, 14-skill matrix, two reproducible experiment designs verified Evidence: proof:superpowers evidence json repo=obra/superpowers license=MIT skill_count=14; decision=BORROW
