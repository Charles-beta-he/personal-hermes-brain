---
type: task
lane: evolution
layer: L3
status: done
priority: P1
created: 2026-05-10T18:23:40+08:00
updated: 2026-05-13T01:09:26+08:00
expires_at: 2026-06-09T18:23:40+08:00
project: Hermes-local-brain
architecture_target: local-brain
capability_delta: 为每个 mission 生成 canonical Markdown mission note、evidence bundle、run/proof log 链接、live-note style objective update，并保持 SQLite/FTS/graph 为可重建派生缓存
anti_drift_check: canonical brain vault 仍是 ~/Documents/brain；不得把 runtime index 当源事实；evidence/ref/hash 必须可回放；sync/reindex/search/dashboard 都要验证
acceptance_evidence: 创建 mission artifact 模板与 sidecar hash；brainctl sync/reindex PASS；brainctl search 可检索 mission；dashboard/proof-check/selfcheck PASS；示例 mission note 指向本次 multi-model tick
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: advisory_completed
multimodel_last_checked_at: 2026-05-13T01:07:18+08:00
multimodel_round_status: advisory_passed
multimodel_last_gate_status: PASS_ADVISORY_ONLY
multimodel_last_decision: CONTINUE_LOOP
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260512-170247/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-10-mission方法论p1local-first-mission-artifacts-与知识图谱沉淀-state.json
multimodel_last_failures: []
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - artifact:/tmp/missions-taskpool-mm-state.json
  - artifact:/tmp/missions-task-planning-mm-state.json
  - artifact:/Users/charles/.hermes/tick-20260510-102004/merged_plan.json
  - artifact:/Users/charles/.hermes/tick-20260510-101903/merged_plan.json
  - file:~/Documents/brain/08-模板/mission-artifact-template.md
  - file:~/.hermes/scripts/evidence_manifest.py
  - file:~/Documents/brain/05-实践与项目/missions/2026-05-10-mission-local-first-artifacts-kg.md
  - artifact:/Users/charles/.hermes/tick-20260512-170247/discussion_result.json
  - proof:evidence_manifest verify 3/3; brainctl reindex indexed_blocks=3497; brainctl search mission-local-first-artifacts-kg hit mission note; proof-check PASS
  - proof:ratification-gate PASS; evidence_manifest verify 3/3; brainctl status/reindex/search PASS; proof-check PASS
concepts: ["missions", "local-first", "knowledge-graph", "markdown", "evidence-bundle", "rowboat-inspired"]
mission_artifact: ["[05-实践与项目/missions/2026-05-10-mission-local-first-artifacts-kg]"]
multimodel_advisory_only: True
multimodel_certification_authority: False
multimodel_advisory_reasons: ["architecture_target", "evolution_lane"]
multimodel_certification_reasons: []
---

# Task - Mission方法论P1：local-first Mission artifacts 与知识图谱沉淀

## Objective

吸收 Rowboat local-first KG 思路：Mission 的目标、证据、运行日志和决策沉淀为可编辑 Markdown，而非只在 transient session 里。

补充 OPORD 证据要求：Mission note 需要保留 Situation/Mission/Execution/Sustainment/Command-Control 与 evidence hash，SQLite/FTS/graph 只做可重建派生索引。

**Mission artifact**: → `[[05-实践与项目/missions/2026-05-10-mission-local-first-artifacts-kg]]`

## Acceptance Criteria

- [x] Mission note 模板可用 (`08-模板/mission-artifact-template.md`)
- [x] 证据路径/hash 可查 (`evidence_manifest.py`)
- [x] 索引可重建 (`brainctl reindex`)
- [x] 搜索能命中新 Mission (`brainctl search`)

## Plan / Workpad

- [x] Reconcile current state before execution.
- [x] Execute the smallest verifiable slice.
- [x] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| mission-artifact-template.md exists | PASS | `~/Documents/brain/08-模板/mission-artifact-template.md` |
| evidence_manifest.py --help | PASS | `python3 ~/.hermes/scripts/evidence_manifest.py` |
| mission note created | PASS | `~/Documents/brain/05-实践与项目/missions/2026-05-10-mission-local-first-artifacts-kg.md` |
| evidence_manifest.py create | PASS | sidecar .evidence.json created |
| evidence_manifest.py verify | PASS | all hashes verified |
| brainctl reindex | PASS | indexed mission note blocks |
| brainctl search "mission" | PASS | mission note found in results |

## Proof Log

- 2026-05-10T18:23:40+08:00: Task created from local-brain control point.
- 2026-05-11T20:26:00+08:00: Created mission artifact template with OPORD structure (Situation/Mission/Execution/Sustainment/Command-Control).
- 2026-05-11T20:26:00+08:00: Created `evidence_manifest.py` for sidecar hash/evidence manifest.
- 2026-05-11T20:26:00+08:00: Created sample mission note at `05-实践与项目/missions/`.
- 2026-05-11T20:26:00+08:00: Linked task note to mission artifact via `mission_artifact` frontmatter field.

## Blockers / Confusions

- None.

## Final Handoff

- Status: implemented; template + sidecar + mission note + brainctl verification
- Evidence: mission-artifact-template.md, evidence_manifest.py, mission note
- Residual risk: Full vector embedding search deferred; TF-IDF keyword search sufficient for current scale

## Multi-model Missions synthesis

Status: truth-grounded advisory, not patch-level certification.

Artifacts:
- State: `/tmp/missions-taskpool-mm-state.json`
- Tick: `/Users/charles/.hermes/tick-20260510-102004/`
- Merged plan: `/Users/charles/.hermes/tick-20260510-102004/merged_plan.json`
- Source repo reference: `rowboatlabs/rowboat` cloned at `/tmp/rowboat-missions`, commit `10995ebed69f56db899619b8636c8c14b5f9b6cb`

Consensus summary:
- Truth gate grounded 4/4 claims: current Hermes taskpool has lifecycle primitives; Rowboat contributes local-first KG/run/permission/scheduled-agent patterns; safe Missions landing is envelope + DAG + proof/permission gates, not direct Markdown execution.
- Planner consensus was dissent/low score because planners named patches differently, but all useful concrete proposals converged on P0 envelope, P1 DAG/router/dashboard, P2 proof-gated autorun/handoff, plus local-first artifacts.
- Therefore this task is an executable taskpool landing slice, not a claim that implementation is already certified.

Mission rules to preserve:
- Mission notes are data/workpads, not scripts.
- Safe dispatch, claim/handoff, executor, and proof-gated completion remain separate stages.
- Evolution Missions must not starve work/product P0/P1 tasks.
- Canonical source is `~/Documents/brain`; SQLite/FTS/dashboard are derived caches.

## Implementation notes

Borrow from Rowboat selectively: local-first Markdown KG, inspectable/editable notes, persistent run logs, scheduled/live-note objective updates. Do not import Rowboat runtime.

Smallest safe slice:
1. Create a mission artifact template under the brain vault. ✅
2. Add sidecar hash/evidence manifest convention. ✅
3. Link task notes to mission artifacts and proof logs. ✅
4. Run `brainctl sync`, `brainctl reindex`, and a search smoke for the mission slug. (see validation)

- 2026-05-12T02:54:24+08:00: Permission taxonomy defaults applied by `permission-migrate --apply`. Changes: {"required_authority": "budget-handoff", "max_authority": "autonomous-execution", "permission_tier": "budget-handoff", "write_surfaces": ["taskpool", "hermes-scripts", "brain"], "completion_gate": "ratification-or-selfcheck-review-done", "lane_semantics": "self-evolution: deterministic gates plus ratification/proof before review->done"}

- 2026-05-13T01:02:47+08:00: Lifecycle transition `pending` -> `claimed` by `hermes`.

- 2026-05-13T01:07:18+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260512-170247/discussion_result.json`. Failures: []

- 2026-05-13T01:09:26+08:00: Lifecycle transition `claimed` -> `running` by `hermes`. Reason: verified local-first mission artifacts, sidecar evidence, reindex/search

- 2026-05-13T01:09:26+08:00: Lifecycle transition `running` -> `review` by `hermes`. Reason: ratification_gate_PASS plus brainctl/evidence_manifest/proof_check PASS Evidence: artifact:/Users/charles/.hermes/tick-20260512-170247/discussion_result.json, proof:evidence_manifest verify 3/3; brainctl reindex indexed_blocks=3497; brainctl search mission-local-first-artifacts-kg hit mission note; proof-check PASS

- 2026-05-13T01:09:26+08:00: Lifecycle transition `review` -> `done` by `hermes`. Reason: review closeout after target-bound ratification PASS and local-brain artifact verification PASS Evidence: artifact:/Users/charles/.hermes/tick-20260512-170247/discussion_result.json, proof:ratification-gate PASS; evidence_manifest verify 3/3; brainctl status/reindex/search PASS; proof-check PASS
