---
type: task
lane: evolution
layer: L3
status: pending
priority: P2
priority_layer: P2
dependency_order: ["1/4: Gate1 protocolization before runtime mechanisms"]
created: 2026-05-19T11:32:26+08:00
updated: 2026-05-19T11:32:26+08:00
expires_at: 2026-06-18T11:32:26+08:00
project: hermes
architecture_target: local-brain
capability_delta: "meta_synthesis_protocol_skill: workflow skill/reference can be loaded and used for multimodel/multibrain sessions"
anti_drift_check: Do not let 多模型同意 replace source/evidence; dissent ledger and handback remain mandatory
acceptance_evidence: skill exists; skill_view loads; protocol contains source_packet/dissent/handback/schema; one dry-run session record uses it
workflow_contract: [[08-模板/task-workflow-contract-template]]
requires_multimodel: true
multimodel_reason: core-methodology absorption affects multi-brain governance
expected_participants: ["gpt-5.5", "mimo-v2.5-pro", "deepseek-v4-pro"]
truth_gate: source evidence + protocol artifact + skill load verification
evidence_bundle: brain/03-理论与元认知/系统工程协议/综合集成研讨厅协议.md; brain/06-治理与评审/reviews/2026-05-19-qian-xuesen-multimodel-synthesis.md
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_triage_result: P2 evolution; evidence-first; existing Gate0 docs available; no immediate runtime side effect
claimed_by:
claim_expires_at:
run_id:
retry_count: 0
next_attempt_at:
workspace:
parallel_boundary: May run in parallel with observer bus design; must precede qual_to_quant automation
evidence: []
concepts: ["task"]
---

# Task - P1: 钱学森综合集成研讨厅协议沉淀为 Hermes workflow skill

## Objective

Turn Gate0 meta-synthesis protocol into reusable Hermes workflow skill/procedure

## Acceptance Criteria

- [ ] Gate1 protocol executable

## Plan / Workpad

- [ ] Reconcile current state, dependency order, and architecture boundaries before execution.
- [ ] Advance the long-term maintainable mainline plan with the next bounded step and staged evidence.
- [ ] Record proof, status, and any next dependency or handoff required.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-19T11:32:26+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:
