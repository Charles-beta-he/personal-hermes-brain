---
type: task
lane: evolution
layer: L3
status: done
priority: P1
created: 2026-05-10T18:29:13+08:00
updated: 2026-05-13T16:38:54+08:00
expires_at: 2026-06-09T18:29:13+08:00
project: hermes-skill-learning
architecture_target: taskpool
capability_delta: 评估 hook/stop-condition/继续执行机制如何强化 Hermes loop、PUA、任务池 proof gate 与长时自运行。
anti_drift_check: 不能无限循环或绕过用户停止；必须有预算、kill switch、证据门和 handoff 边界。
acceptance_evidence: "截图 OCR: Claude 想提前收工? Hook 拦截塞回去直到做完; linked state: /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/multi-model-state-linked-2026-05-10.json; multi-model artifact: /Users/charles/.hermes/tick-20260510-102539; truth gate grounded, fanout quorum met, consensus weak/advisory only."
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: advisory_completed
multimodel_last_checked_at: 2026-05-13T11:50:13+08:00
multimodel_round_status: advisory_passed
multimodel_last_gate_status: PASS_ADVISORY_ONLY
multimodel_last_decision: CONTINUE_LOOP
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260513-034712/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-10-skill学习路线ralph-loop-hook-防提前收工与-hermes-pua-loop-边界评估-state.json
multimodel_last_failures: []
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: evolution:skill-learning:ralph-loop
evidence:
  - artifact:/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/ralph-loop-hook-evaluation-2026-05-13.md
  - proof:ralph-loop report acceptance PASS; decision REJECT original / ADOPT PUA Loop / BORROW anti-premature-closeout gates
concepts: ["skill-learning", "ralph-loop", "multi-model", "evidence-first"]
multimodel_advisory_only: True
multimodel_certification_authority: False
multimodel_advisory_reasons: ["architecture_target", "evolution_lane"]
multimodel_certification_reasons: []
---

# Task - Skill学习路线：Ralph Loop Hook 防提前收工与 Hermes PUA/Loop 边界评估

## Objective

对截图候选 skill `ralph-loop` 走 evidence-first 分析学习路线：先核验来源/许可/能力，再评估 Hermes 适配，最后输出 adopt/borrow/reject 决策；本任务不安装、不导入、不宣称已采用。截图说明：Claude 想提前收工? Hook 拦截塞回去直到做完。

## Acceptance Criteria

- [x] 确认来源与许可；拆解 hook 触发条件；映射到 Hermes loop/PUA/iteration-budget；设计有界继续执行策略与停止条件测试

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |
| evidence-first report | DONE | /Users/charles/.hermes/artifacts/ralph-loop-hook-evaluation/report.md (7 sections) |
| learning path summary | DONE | §7 appended: PUA/Loop/Taskpool boundary matrix |

## Proof Log

- 2026-05-10T18:29:13+08:00: Task created from local-brain control point.
- 2026-05-12T08:40:00+08:00: Evidence-first evaluation completed. Report: /Users/charles/.hermes/artifacts/ralph-loop-hook-evaluation/report.md. Decisions: Ralph Loop=REJECT (Claude Code专用), PUA Loop=ADOPT (已集成), 防提前收工=BORROW (提取完成条件到pre_task_done gate). Learning path summary appended (§7).

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-11T01:58:54+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T02:12:49+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: timeout_cleanup

- 2026-05-12T02:54:25+08:00: Permission taxonomy defaults applied by `permission-migrate --apply`. Changes: {"required_authority": "budget-handoff", "max_authority": "autonomous-execution", "permission_tier": "budget-handoff", "write_surfaces": ["taskpool", "hermes-scripts", "brain"], "completion_gate": "ratification-or-selfcheck-review-done", "lane_semantics": "self-evolution: deterministic gates plus ratification/proof before review->done"}

- 2026-05-13T11:50:13+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-034712/discussion_result.json`. Failures: []

- 2026-05-13T16:21:25+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-gpt-5.5`. Reason: continue-loop-parallel-skill-learning

- 2026-05-13T16:21:25+08:00: Lifecycle transition `claimed` -> `running` by `hermes-gpt-5.5`. Reason: parallel-skill-learning-evidence-slice

- 2026-05-13T16:38:54+08:00: Lifecycle transition `running` -> `review` by `hermes-gpt-5.5`. Reason: deterministic evidence slice verified; advisory-only provenance not used as closeout authority Evidence: artifact:/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/ralph-loop-hook-evaluation-2026-05-13.md

- 2026-05-13T16:38:54+08:00: Lifecycle transition `review` -> `done` by `hermes-gpt-5.5`. Reason: selfcheck-review-done: source/license, hook triggers, bounded strategy and stop tests verified Evidence: proof:ralph-loop report acceptance PASS; decision REJECT original / ADOPT PUA Loop / BORROW anti-premature-closeout gates
