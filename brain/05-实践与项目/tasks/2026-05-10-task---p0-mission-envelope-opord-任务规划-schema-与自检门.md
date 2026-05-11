---
type: task
lane: evolution
layer: L3
status: archived
priority: P1
created: 2026-05-10T18:25:11+08:00
updated: 2026-05-10T18:25:11+08:00
expires_at: 2026-06-09T18:25:11+08:00
project: hermes-self-improvement
architecture_target: taskpool
capability_delta: Add mission-command/OPORD mission envelope fields to local-brain task notes and workflow contracts, with deterministic selfcheck/proof-check validation before dispatch.
anti_drift_check: Layer mission metadata over existing Markdown taskpool; no external source of truth; no autonomous write execution; work P0/P1 priority remains first.
acceptance_evidence: Templates and orchestrator selfcheck validate mission_contract required fields; legacy serial tasks stay compatible; dispatch-dry-run/proof-check/dashboard/reindex/search PASS.
workflow_contract: [[08-模板/task-workflow-contract-template]]
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - /tmp/missions-task-planning-mm-state.json
  - /Users/charles/.hermes/tick-20260510-101903/merged_plan.json
  - /Users/charles/.hermes/tick-20260510-102004/merged_plan.json
  - /tmp/current_taskpool_summary.json
concepts: ["missions", "mission-command", "opord", "taskpool", "evolution", "proof-gate"]
---

# Task - Task - P0 Mission Envelope/OPORD 任务规划 schema 与自检门

## Objective

Define and validate a Hermes-native mission_contract / OPORD packet: commander_intent, situation, mission/task-purpose-end_state, control_measures/constraints, sustainment/dependencies, command_control/escalation, proof gates.

## Acceptance Criteria

- [ ] Mission fields exist in task template/workflow contract and are machine-validated; missing fields create warnings or fail-closed only for missionized/evolution tasks per compatibility rule.

## Multi-model Advisory Result

Status: `truth_grounded_advisory / weak_consensus`, not full certification. T2 four-planner fanout produced plans from GPT-5.5, Claude, DeepSeek, and a failed MiMo adapter; no final `discussion_result.json` was produced before timeout, so this task is seeded as an evolution task, not as an implementation-certified patch.

Evidence:
- State: `/tmp/missions-task-planning-mm-state.json`
- Primary tick: `/Users/charles/.hermes/tick-20260510-101903/merged_plan.json` (`weak_consensus`, arbitration needed)
- Related mission-envelope tick: `/Users/charles/.hermes/tick-20260510-102004/merged_plan.json` (`dissent`, useful P0/P1/P2 split)
- Current taskpool summary: `/tmp/current_taskpool_summary.json` (12 tasks: 6 work / 6 evolution; 11 dispatchable)

Shared conclusion: current taskpool already has lifecycle/proof primitives, but task notes and workflow contracts do not yet encode Mission/OPORD intent. Add mission metadata as a deterministic schema layer over existing Markdown tasks; do not replace lifecycle or enable autonomous writes.

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Extend `08-模板/local-brain-task-note-template.md` with a `mission_contract` block.
- [ ] Extend `08-模板/task-workflow-contract-template.md` with mission validation expectations.
- [ ] Add/extend `brain_task_orchestrator.py selfcheck` and/or a dedicated mission schema check.
- [ ] Preserve backward compatibility: legacy serial tasks warn; missionized/evolution tasks can fail closed when required mission fields are absent.
- [ ] Run dashboard/reindex/search proof before closeout.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-10T18:25:11+08:00: Task created from local-brain control point.
- 2026-05-10T18:29:00+08:00: Archived as duplicate; absorbed into `2026-05-10-mission方法论p0任务池-mission-envelope-schema--selfcheck-fail-closed`.

## Blockers / Confusions

- Exact external “Missions” source was not user-provided; interpreted conservatively as mission-command / OPORD. If a specific Missions framework is later supplied, rebase schema names without changing fail-closed safety gates.
- Full T2/T3 certification is still blocked by missing `discussion_result.json` and MiMo adapter failure; treat planner output as advisory until reratified.

## Final Handoff

- Status:
- Evidence:
- Residual risk:
