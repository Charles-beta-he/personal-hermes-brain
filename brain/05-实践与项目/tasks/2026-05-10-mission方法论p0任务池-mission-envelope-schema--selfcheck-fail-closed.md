---
type: task
lane: evolution
layer: L3
status: done
priority: P0
created: 2026-05-10T18:23:40+08:00
updated: 2026-05-10T19:47:28+08:00
expires_at: 2026-06-09T18:23:40+08:00
project: Hermes-local-brain
architecture_target: taskpool
capability_delta: 为本地任务池引入 mission_id/objective/constraints/evidence_refs/acceptance_criteria/dag_nodes/checkpoints/permission_gates/proof_artifacts/frontmatter contract，形成可审计任务规划单元
anti_drift_check: selfcheck/proof-check/dispatch-dry-run 必须拒绝缺少 mission envelope 必填字段的 evolution 任务；不得执行 Markdown body；不得影响 work/product P0 调度优先级
acceptance_evidence: 新增 schema/validator/fixture；brain_task_orchestrator.py selfcheck --json PASS；proof-check --json PASS；dispatch-dry-run --json 可解析；至少 1 个旧任务迁移示例
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
mission_schema_version: v1
mission_id: mission-taskpool-envelope-selfcheck-fail-closed
mission_title: Mission方法论P0任务池Mission Envelope schema + selfcheck fail-closed
mission_objective: 将 Missions/OPORD 任务规划单元落成可校验 frontmatter contract，并复发防护 taskpool claimed->review / invalid-evidence closeout 事故
mission_constraints: ["no-markdown-body-execution", "fail-closed-before-dispatch", "work-lane-priority-preserved", "structured-evidence-only"]
red_lines: ["不执行 Markdown body 里的任意命令", "不让 evolution/self-improvement 抢占 work/product P0", "不用模型一致性替代证据/ratification artifact"]
non_goals: ["不在本切片实现广义自动 runner", "不放宽 lifecycle_gate 或 evidence_is_structured", "不把 task note 作为脚本执行"]
evidence_refs: ["file:/tmp/mission-incident-mm-evidence.json", "file:/tmp/mission-incident-mm-state.json", "file:/Users/charles/.hermes/tick-20260510-112420/plans/claude-opus-4-7.json", "file:/Users/charles/.hermes/tick-20260510-112420/merged_plan.json"]
acceptance_criteria: ["brain_task_orchestrator.py exposes mission_envelope fields in list/dispatch rows", "selfcheck --json fails closed on missing mission envelope fields", "proof-check --include-active --json fails closed on missing mission envelope fields", "lifecycle regression rejects claimed->review and accepts claimed->running->review->done with structured evidence", "dispatch-dry-run still selects work P0 before evolution Mission P0", "real vault selfcheck/proof-check/dispatch-dry-run PASS"]
dag_nodes: ["schema_constants", "mission_envelope_validator", "lifecycle_and_boundary_wiring", "regression_tests", "canonical_task_note_migration"]
checkpoint_states: ["mm_fanout_advisory_collected", "schema_added", "validator_wired", "tests_pass", "real_vault_pass"]
permission_gates: ["selfcheck_pass", "proof_check_include_active_pass", "dispatch_dry_run_parse", "scoped_git_diff_reviewed"]
handoff_artifacts: ["artifact:mission-envelope-validator", "artifact:taskpool-closeout-regression"]
proof_artifacts: ["artifact:test_brain_task_orchestrator_PASS", "artifact:selfcheck_PASS", "artifact:proof_check_include_active_PASS", "artifact:dispatch_dry_run_PASS"]
rollback_signal: revert scoped edits to ~/.hermes/scripts/brain_task_orchestrator.py and ~/.hermes/scripts/test_brain_task_orchestrator.py, then remove mission envelope frontmatter fields from this note
certification_status: advisory
ratification_artifact: file:/Users/charles/.hermes/tick-20260510-112420/merged_plan.json
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - file:/tmp/missions-taskpool-mm-state.json
  - file:/tmp/missions-task-planning-mm-state.json
  - file:/Users/charles/.hermes/tick-20260510-102004/merged_plan.json
  - file:/Users/charles/.hermes/tick-20260510-101903/merged_plan.json
  - "command: python3 ~/.hermes/scripts/test_brain_task_orchestrator.py PASS"
  - "command: selfcheck/proof-check/lifecycle/dispatch-dry-run PASS"
  - file:/Users/charles/.hermes/tick-20260510-112420/plans/claude-opus-4-7.json
  - artifact:mission-envelope-validator-and-closeout-regression
  - "command: python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --include-active --json PASS"
  - file:/Users/charles/Documents/brain/05-实践与项目/tasks/2026-05-10-mission方法论p0任务池-mission-envelope-schema--selfcheck-fail-closed.md
concepts: ["missions", "taskpool", "local-brain", "mission-envelope", "fail-closed", "proof-gate"]
---

# Task - Mission方法论P0：任务池 Mission Envelope schema + selfcheck fail-closed

## Objective

把 Missions 方法论的最小任务规划单元落成可校验 frontmatter/schema，而不是停留在文档口号。

补充 OPORD/mission-command 映射：`mission_contract` 至少覆盖 `commander_intent`、`situation`、`mission_statement`、`task/purpose/end_state`、`control_measures/constraints`、`sustainment/dependencies`、`command_control/escalation`、`proof_gates`。新增证据 `/tmp/missions-task-planning-mm-state.json` 与 `tick-20260510-101903` 明确指出现有模板缺少这些字段，且应作为 schema/selfcheck 层落地。

## Acceptance Criteria

- [x] Mission envelope 字段可被 list/next/dispatch/dashboard 读取；缺字段 fail-closed；现有任务兼容或有迁移提示；所有验证命令记录到 proof。

## Plan / Workpad

- [x] Reconcile current state before execution.
- [x] Execute the smallest verifiable slice.
- [x] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| Claude Code planner participation | PASS | `/Users/charles/.hermes/tick-20260510-112420/plans/claude-opus-4-7.json` shows `adapter: claude-code`, `latency_ms: 66629`, non-empty patch plan |
| T3 fanout advisory | PARTIAL | `merged_plan.json` exists; `discussion_result.json` missing due outer timeout, so advisory not full ratification |
| test_brain_task_orchestrator.py | PASS | `python3 ~/.hermes/scripts/test_brain_task_orchestrator.py` |
| py_compile | PASS | `python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/test_brain_task_orchestrator.py` |
| selfcheck real vault | PASS | `python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json` |
| proof-check include-active real vault | PASS | `python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --include-active --json` |
| lifecycle real vault | PASS | `python3 ~/.hermes/scripts/brain_task_orchestrator.py lifecycle --json` |
| dispatch-dry-run real vault | PASS | `python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json` |
| dashboard write | PASS | `python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write --json` |

## Proof Log

- 2026-05-10T18:23:40+08:00: Task created from local-brain control point.
- 2026-05-10T19:46:08+08:00: Added Mission Envelope frontmatter schema fields, structured evidence_refs/proof_artifacts/permission_gates, and real-vault proof commands.
- 2026-05-10T19:46:27+08:00: Real-vault selfcheck/lifecycle/dispatch/dashboard and script tests PASS; proof-check include-active PASS with only legacy body-evidence warnings on unrelated archived tasks.

## Blockers / Confusions

- None.

## Final Handoff

- Status: implemented; deterministic gates PASS; task transition to review/done will carry structured evidence.
- Evidence: Mission envelope validator/list fields/tests in `~/.hermes/scripts/brain_task_orchestrator.py` and `~/.hermes/scripts/test_brain_task_orchestrator.py`; advisory multi-model artifacts in `/tmp/mission-incident-mm-state.json` and `/Users/charles/.hermes/tick-20260510-112420/`.
- Residual risk: T3 discussion timed out before `discussion_result.json`; treat multi-model output as fanout advisory, not full certification. MiMo adapter failed with provider parameter error in this tick; Claude Code/Codex/DeepSeek produced usable plans.

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

Required fields for the first envelope draft:
- `mission_id`, `mission_title`, `mission_objective`
- `mission_constraints`, `red_lines`, `non_goals`
- `evidence_refs` with path/hash/source type
- `acceptance_criteria` and `acceptance_evidence`
- `dag_nodes` / `checkpoint_states` / `permission_gates`
- `handoff_artifacts` / `proof_artifacts` / `rollback_signal`

Smallest safe slice:
1. Add parser/normalizer support without changing dispatch behavior.
2. Add selfcheck fixtures for valid/invalid mission envelope.
3. Run canonical vault selfcheck, proof-check, dispatch-dry-run.
4. Only then consider enabling router behavior in the P1 task.


- 2026-05-10T19:20:25+08:00: Lifecycle transition `pending` -> `claimed` by `hermes`.

- 2026-05-10T19:22:50+08:00: Lifecycle transition `claimed` -> `running` by `hermes`.

- 2026-05-10T19:47:21+08:00: Lifecycle transition `running` -> `review` by `hermes`. Evidence: command: python3 ~/.hermes/scripts/test_brain_task_orchestrator.py PASS, command: selfcheck/proof-check/lifecycle/dispatch-dry-run PASS, file:/Users/charles/.hermes/tick-20260510-112420/plans/claude-opus-4-7.json

- 2026-05-10T19:47:28+08:00: Lifecycle transition `review` -> `done` by `hermes`. Evidence: artifact:mission-envelope-validator-and-closeout-regression, command: python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --include-active --json PASS, file:/Users/charles/Documents/brain/05-实践与项目/tasks/2026-05-10-mission方法论p0任务池-mission-envelope-schema--selfcheck-fail-closed.md

- 2026-05-12T02:54:24+08:00: Permission taxonomy defaults applied by `permission-migrate --apply`. Changes: {"required_authority": "budget-handoff", "max_authority": "autonomous-execution", "permission_tier": "budget-handoff", "write_surfaces": ["taskpool", "hermes-scripts", "brain"], "completion_gate": "ratification-or-selfcheck-review-done", "lane_semantics": "self-evolution: deterministic gates plus ratification/proof before review->done"}
