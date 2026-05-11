---
type: governance-artifact
status: active
created: 2026-05-07T00:54:32+08:00
concepts: [agent-cos, ratification-first, evidence-bundle, issue-ledger]
---

# Agent COS Ratification Gate

## Current lifecycle status

- matrix_status: `A_PLUS_MATRIX_COMPLETE`
- deterministic_gate_status: `PASS`
- ratification_status: `CERTIFIED`
- final_integration_status: `FULLY_CERTIFIED`
- certified_discussion_result: `05-实践与项目/projects/agent-cognitive-operating-system/ratification-discussion-result-2026-05-07.json`

## Canonical artifacts

- Evidence bundle JSON: `05-实践与项目/projects/agent-cognitive-operating-system/ratification-evidence-bundle.json`
- Issue ledger JSON: `05-实践与项目/projects/agent-cognitive-operating-system/ratification-issue-ledger.json`
- Gate script: `/Users/charles/.hermes/scripts/ratification_gate.py`
- Deterministic evidence script: `/Users/charles/.hermes/scripts/agent_cos_selfcheck.py`

## Anti-shell rule

Deterministic PASS is an evidence layer, not a certification shell. The only valid status transition into `FULLY_CERTIFIED` is:

claims/evidence bundle -> issue ledger -> scoped multi-model `discussion_result.json` -> `ratification_gate.py` PASS -> dashboard status update.

## Current decision

The scoped Agent-COS discussion artifact passed `ratification_gate.py`: 3/3 available models approved, agreement matrix >= 0.95, no remaining risks, truth assessment grounded, and no open severity>=3 blockers. Final integration status is `FULLY_CERTIFIED`.

## Search Aliases

Agent COS ratification gate evidence bundle issue ledger deterministic PASS is evidence only LOCAL_COMPLETE_UNRATIFIED
