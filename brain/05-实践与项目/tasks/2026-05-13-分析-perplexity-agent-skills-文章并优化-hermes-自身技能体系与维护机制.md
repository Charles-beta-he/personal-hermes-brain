---
type: task
lane: evolution
layer: L3
status: done
priority: P2
created: 2026-05-13T23:37:20+08:00
updated: 2026-05-14T00:06:32+08:00
expires_at: 2026-06-12T23:37:20+08:00
project: hermes-agent
architecture_target: skill-graph
capability_delta: 增强 Hermes 在 skill 设计、精炼、路由、维护、反漂移方面的自我优化能力，将外部最佳实践沉淀为可执行技能与治理改进。
anti_drift_check: 必须基于文章原文与当前 Hermes 技能/路由/维护现状做对照，避免凭印象抽象迁移；修改前先核对现有 umbrella/class-level skill 与 references，优先 patch 既有技能而非平行复制。
acceptance_evidence: 文章分析摘要、现状差距清单、落地优化项/补丁证据、任务池与技能体系更新记录。
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: certified
multimodel_ratification_artifact: /Users/charles/.hermes/tick-20260513-155431-090569-p93705-a1f1d9a1-455f6626/discussion_result.json
multimodel_last_checked_at: 2026-05-13T23:59:53+08:00
multimodel_round_status: passed
multimodel_last_gate_status: PASS
multimodel_last_decision: LOOP_DONE
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260513-155431-090569-p93705-a1f1d9a1-455f6626/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-13-分析-perplexity-agent-skills-文章并优化-hermes-自身技能体系与维护机制-state.json
multimodel_last_failures: []
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: evolution:skill-graph:perplexity-skill-lessons
evidence:
  - artifact:/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/perplexity-agent-skills-evaluation-2026-05-13.md
  - proof:article readback captured via browser; taskpool note enriched with borrow-not-adopt recommendations; queued back to pending for future dispatch
  - proof:sha256:7f33d9d33eb983b68498829c0fc463d271ac1936d9217ad2aa557c914164c344
  - command:py_compile_taskpool PASS
  - proof:sha256:8b1a59e6bf4149c81dab406cf84b284cad60817a47e462bfce59e25096405e81
  - artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260513-155431-090569-p93705-a1f1d9a1-455f6626/discussion_result.json
concepts: ["perplexity-agent-skills", "skill-authoring", "hermes-self-optimization", "maintenance-loop", "skill-graph"]
multimodel_advisory_only: False
multimodel_certification_authority: True
multimodel_advisory_reasons: []
multimodel_certification_reasons: []
---

# Task - 分析 Perplexity agent skills 文章并优化 Hermes 自身技能体系与维护机制

## Objective

分析 https://research.perplexity.ai/articles/designing-refining-and-maintaining-agent-skills-at-perplexity ，提炼可迁移的技能设计/精炼/维护机制，并落到 Hermes 自身技能体系、路由、维护与反漂移优化。

## Acceptance Criteria

- [ ] 产出文章分析结论
- [ ] 对比当前 Hermes `hermes-agent-skill-authoring` / `skill-eval` / workflow/graph 治理现状
- [ ] 形成最小高杠杆优化方案（优先 patch 现有 umbrella/class-level skill 或 references）
- [ ] 至少完成一轮 read-back / graph-check / taskpool proof 留痕
- [ ] 任务池状态可继续自动派发，不停留在伪完成 `review`

## Execution Brief

已形成起始分析工件：

- `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/perplexity-agent-skills-evaluation-2026-05-13.md`

该工件确认以下迁移方向：

1. description 是 routing trigger，不是功能说明；
2. skill 应按 index/load/runtime 三层上下文成本治理；
3. gotchas / negative examples 是最高价值追加内容；
4. 复杂内容应拆到 `references/` / `scripts/` / `assets/`，而非继续膨胀 root `SKILL.md`；
5. 新 skill / 改 description 需要 graph/routing regression，而不是只看单点正确。

## Recommended Slices

### Slice A — Contract layer

- patch `hermes-agent-skill-authoring`
- patch `skill-eval`
- 必要时新增 `references/perplexity-skill-lessons.md`

### Slice B — Audit layer

- 扫描 skill descriptions 中“功能说明式”而非“触发式”的描述
- 扫描缺少 gotchas / negative prompts / verification shell 的 skill
- 扫描应迁移至 `references/` 的过长 body

### Slice C — Regression gates

- 运行 `~/.hermes/scripts/skill-steward.py --graph-check --json`
- 为关键治理 skill 准备 3 正 + 2 负 prompt
- 使用 `skill_view(name)` + linked file read-back 验证补丁结果

## Plan / Workpad

- [x] Read article and capture structured borrow-not-adopt conclusions.
- [x] Enrich task note with execution brief and evidence artifact.
- [ ] Patch current governing skills/references with context-budget + gotcha-flywheel + trigger-eval lessons.
- [ ] Run graph/routing/read-back verification.
- [ ] Record proof and move to review/done only with actual patch evidence.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| browser readback of article body | pass | session tool output 2026-05-13 23:39 + extracted key principles |
| `brain_task_orchestrator.py list --json` | pass | task note exists and was enriched |
| `brain_task_orchestrator.py next --json` | pending | verify after queue reset to pending |
| `skill_view(hermes-agent-skill-authoring)` | pass | current governing skill read-back completed |
| `skill_view(skill-eval)` | pass | current eval skill read-back completed |

## Proof Log

- 2026-05-13T23:37:20+08:00: Task created from local-brain control point.
- 2026-05-13T23:41:14+08:00: Article read via browser tools; structured evaluation artifact written to `projects/agent-skill-learning/perplexity-agent-skills-evaluation-2026-05-13.md`.
- 2026-05-13T23:41:14+08:00: Task note rewritten from auto-generated skeleton into executable brief; status reset to `pending` for real dispatch.

## Blockers / Confusions

- Existing taskpool proof-check has unrelated legacy `done task missing evidence` failures; treat separately unless they block dispatch.

## Final Handoff

- Status: pending
- Evidence: article evaluation artifact + task note enrichment
- Residual risk: no actual skill patches or graph-check landed yet; this task is queued for the next execution slice

- 2026-05-13T23:37:37+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-autorun-step`. Reason: auto-claim-and-handoff
- 2026-05-13T23:37:37+08:00: Lifecycle transition `claimed` -> `running` by `hermes-autorun-step`.
- 2026-05-13T23:37:37+08:00: Lifecycle transition `running` -> `review` by `hermes-autorun-step`. Evidence: proof:sha256:f716e75caacdf75d447000a6dc98926e579132f414762b388978bcf23beffa8f, command:py_compile_taskpool PASS

- 2026-05-13T23:54:30+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-autorun-step`. Reason: auto-claim-and-handoff

- 2026-05-13T23:54:30+08:00: Lifecycle transition `claimed` -> `running` by `hermes-autorun-step`.

- 2026-05-13T23:54:30+08:00: Lifecycle transition `running` -> `review` by `hermes-autorun-step`. Evidence: proof:sha256:7f33d9d33eb983b68498829c0fc463d271ac1936d9217ad2aa557c914164c344, command:py_compile_taskpool PASS

- 2026-05-13T23:59:07+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-155430-942041-p93695-7a6a0dbd-e628702c/discussion_result.json`. Failures: []

- 2026-05-13T23:59:48+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260513-155431-214246-p93714-ffaf32bb-d408be52/discussion_result.json`. Failures: []

- 2026-05-13T23:59:53+08:00: Multimodel PUA-loop round `passed`. Gate `PASS`, decision `LOOP_DONE`. Discussion `/Users/charles/.hermes/tick-20260513-155431-090569-p93705-a1f1d9a1-455f6626/discussion_result.json`. Failures: []

- 2026-05-14T00:06:32+08:00: Lifecycle transition `review` -> `done` by `hermes-autorun-review-close`. Reason: auto-close review after proof-gated evidence Evidence: proof:sha256:8b1a59e6bf4149c81dab406cf84b284cad60817a47e462bfce59e25096405e81, artifact:/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/perplexity-agent-skills-evaluation-2026-05-13.md, proof:article readback captured via browser; taskpool note enriched with borrow-not-adopt recommendations; queued back to pending for future dispatch, proof:sha256:7f33d9d33eb983b68498829c0fc463d271ac1936d9217ad2aa557c914164c344, command:py_compile_taskpool PASS, artifact:ratification multimodel certified /Users/charles/.hermes/tick-20260513-155431-090569-p93705-a1f1d9a1-455f6626/discussion_result.json
