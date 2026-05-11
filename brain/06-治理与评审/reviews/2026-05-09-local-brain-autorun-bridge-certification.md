---
type: review
title: Local Brain Task Pool Autorun Bridge Certification
created: 2026-05-09T10:48:50+08:00
status: certified
risk_level: high
tier: T2
models: [gpt-5.5, mimo-v2.5-pro, claude-opus-4-7, deepseek-v4-pro]
evidence:
  - artifact:/Users/charles/.hermes/tick-20260509-024207/discussion_result.json
  - artifact:/Users/charles/.hermes/tick-20260509-024207/merged_plan.json
  - artifact:/tmp/taskpool-autorun-impl-cert-state-v2.json
  - command:python3 ~/.hermes/scripts/test_brain_task_orchestrator.py
  - command:python3 ~/.hermes/scripts/test_brain_task_dispatch_tick.py
  - command:python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
  - command:python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
  - command:python3 ~/.hermes/scripts/brain_task_orchestrator.py auto-claim-and-handoff --json
concepts: [local-brain, task-pool, autorun, fail-closed, multi-model-certification]
---

# Local Brain Task Pool Autorun Bridge Certification

## Verdict

T2 quorum4 multi-model discussion **certified** the local-brain task-pool autorun bridge implementation.

## Evidence Boundary

Model agreement is provenance only. This certification note is bounded to the listed `discussion_result.json`, claim-linked state artifact, and deterministic command evidence below; it does not certify future autorun enablement, arbitrary Markdown execution, or any provider/runtime state outside those artifacts.

- Certification artifact: `/Users/charles/.hermes/tick-20260509-024207/discussion_result.json`
- Models: `gpt-5.5`, `mimo-v2.5-pro`, `claude-opus-4-7`, `deepseek-v4-pro`
- Rounds used: `1`
- Agreement matrix: framing `0.95`, approach `0.95`, implementation_order `0.95`
- Ratification votes: 4/4 approve, all `best_within_constraints=true`
- Truth gate: grounded, 6/6 claims verified, evidence coverage `1.0`
- Remaining risks: none recorded in the certification result

## Implemented Safety Boundary

This implementation is intentionally **not** an autonomous Markdown executor. It lands the safer control-plane bridge:

1. `eligibility-check --json`
   - Default denies when `HERMES_LOCAL_BRAIN_AUTORUN` is unset.
   - Empty/missing allowlist denies.
   - Selfcheck, proof-chain integrity, and dispatchability are gates.

2. `auto-claim-and-handoff --json`
   - Only claims a dispatchable allowlisted task after eligibility passes.
   - Writes a bounded handoff and append-only proof event.
   - Does **not** execute task Markdown.
   - Does **not** mark tasks done.

3. Autorun proof gate
   - Autorun-originated `done` requires `proof:<sha256:...>` evidence from the append-only proof JSONL.
   - Existing lifecycle invariant remains: `done` must pass through `review -> done` unless manually forced with audit reason.
   - `proof-check` now audits persisted autorun done notes for missing/invalid proof hash evidence.

4. Safe tick bridge
   - `brain_task_dispatch_tick.py` remains hint-only by default.
   - `--autorun` is an explicit opt-in bridge and only runs after safe tick gates pass.

## Deterministic Verification

All final gates passed after applying the prior multi-model amendments:

```bash
python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/brain_task_dispatch_tick.py ~/.hermes/scripts/test_brain_task_orchestrator.py ~/.hermes/scripts/test_brain_task_dispatch_tick.py
python3 ~/.hermes/scripts/test_brain_task_orchestrator.py
python3 ~/.hermes/scripts/test_brain_task_dispatch_tick.py
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py eligibility-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py auto-claim-and-handoff --json
python3 ~/.hermes/scripts/brain_task_dispatch_tick.py --print-always --no-state
```

Key production-safe disabled-mode observations:

- `eligibility-check`: `eligible=false`, reasons `allowlist_empty`, `autorun_disabled`.
- `auto-claim-and-handoff`: `claimed=false`, safety `fail-closed; no claim and no execution`.
- default safe tick: no `autorun` block, `dispatchable=true`, next task preserved as dispatch hint only.
- `proof-check`: PASS; one legacy body-only warning remains accepted for historical non-autorun evidence.

## Prior Round Amendments Resolved

The first implementation-certification round surfaced amend-only issues. They were resolved before final certification:

- Restored strict bare filesystem evidence: non-prefixed absolute paths must exist.
- Converted the missing historical tick directory evidence to explicit `artifact:` evidence.
- Added regression test rejecting nonexistent absolute path evidence.
- Added `proof-check` failure for persisted autorun done audit without `proof:sha256:` evidence.
- Added selfcheck warning for excessive autorun handoff directory growth.

## Files Changed

- `~/.hermes/scripts/brain_task_orchestrator.py`
- `~/.hermes/scripts/brain_task_dispatch_tick.py`
- `~/.hermes/scripts/test_brain_task_orchestrator.py`
- `~/.hermes/scripts/test_brain_task_dispatch_tick.py`
- `~/Documents/brain/05-实践与项目/tasks/2026-05-08-symphony-inspired-task-orchestrator-landing-log.md`

## Non-goals

- Production autorun was not enabled.
- External bounded runner was not implemented in this slice.
- No production task was claimed by the final disabled-mode verification.
