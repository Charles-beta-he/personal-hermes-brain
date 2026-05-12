---
type: task
layer: L3
status: done
priority: P1
created: 2026-05-08T18:01:13+08:00
updated: 2026-05-08T19:04:57+08:00
expires_at: 2026-06-07T18:01:13+08:00
project: local-brain-governance
workflow_contract: repair-plan dry-run + review gate + explicit repair-apply + verification chain + structured proof
required_authority: autonomous-execution
max_authority: yolo-execution
permission_tier: autonomous-execution
write_surfaces: ["taskpool", "codebase"]
completion_gate: project-evidence-review-done
lane_semantics: "work/product delivery: project evidence, tests/build, scoped commit, report/push policy as required"
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
evidence:
  - command:local_brain_main_hierarchy_migration_selfcheck.py --json PASS
  - command:local_brain_exhaustive_audit.py --sample-limit 100 PASS stop_gate_pass=true broken_wikilinks=0 secret_hits=0
  - command:brainctl validate --write-dashboard PASS violations=0 l3_expiry_open=0
  - command:test_brainctl.py PASS 15 tests
  - command:brain_task_orchestrator selfcheck/proof-check PASS
  - file:/Users/charles/Documents/brain/06-治理与评审/历史快照/legacy-06-dashboard-20260508/repair-manifest.json
  - artifact:/tmp/local_brain_doc_func_after_archive_*
concepts: ["local-brain", "residue-cleanup", "repair-plan", "repair-apply", "dashboard-migration", "proof-gate"]
---

# Task - 本地大脑迁移残留闭环清理与 repair-plan/apply 验证

## Objective

基于 2026-05-08 本地大脑残留审计与多模型 advisory，闭环清理主层级迁移残留：06/07 仪表盘并存、broken JSON wikilink、brainctl validate violations、legacy evidence warning；禁止 dashboard->vault 自动修复，先产出 reviewed manifest，再显式 apply。

## Acceptance Criteria

- [ ] 1) repair-plan manifest 列出每个候选变更的 source/target/hash/references/rollback/verification；2) review gate 将每项分类为 safe_apply/needs_manual_decision/archive_only/false_positive/accepted_risk；3) 只执行 safe_apply；4) local_brain_main_hierarchy_migration_selfcheck PASS 或残留有 explicit accepted risk；5) local_brain_exhaustive_audit stop_gate_pass true；6) brainctl validate passed true 或剩余 violations 全部任务化/accepted risk；7) brain_task_orchestrator proof-check PASS；8) brainctl sync/reindex/search OK；9) task done 前写结构化 evidence。

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-08T18:01:13+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-08T19:04:57+08:00: Claimed by `hermes-doc-function-closure` until `2026-05-08T21:04:57+08:00`.

- 2026-05-08T19:04:57+08:00: Marked done by `hermes-doc-function-closure`. Evidence: command:local_brain_main_hierarchy_migration_selfcheck.py --json PASS, command:local_brain_exhaustive_audit.py --sample-limit 100 PASS stop_gate_pass=true broken_wikilinks=0 secret_hits=0, command:brainctl validate --write-dashboard PASS violations=0 l3_expiry_open=0, command:test_brainctl.py PASS 15 tests, command:brain_task_orchestrator selfcheck/proof-check PASS, file:/Users/charles/Documents/brain/06-治理与评审/历史快照/legacy-06-dashboard-20260508/repair-manifest.json, artifact:/tmp/local_brain_doc_func_after_archive_*.

- 2026-05-12T02:54:24+08:00: Permission taxonomy defaults applied by `permission-migrate --apply`. Changes: {"required_authority": "autonomous-execution", "max_authority": "yolo-execution", "permission_tier": "autonomous-execution", "write_surfaces": ["taskpool", "codebase"], "completion_gate": "project-evidence-review-done", "lane_semantics": "work/product delivery: project evidence, tests/build, scoped commit, report/push policy as required"}
