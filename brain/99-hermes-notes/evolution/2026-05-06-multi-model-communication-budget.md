# Multi-model communication budget protocol

Date: 2026-05-06

## Problem

Full multi-model discussion was spending tokens by repeatedly broadcasting large `merged_plan`, full `evidence_bundle`, `truth_gate`, `fanout_certification`, and prior transcript payloads to every reviewer model each round.

## Landed change

`consult_models.py` now uses `multi_model_comm_packet_v1` for online discussion rounds.

Instead of full payload relay, each reviewer receives a compact `manifest_delta` packet:

- `artifact_manifest`: hash/char/token metadata for current_best, evidence_bundle, truth_gate, previous_transcript.
- `current_best_summary`: patch ids, target files, ops, risk, short rationale, source hash.
- `round_delta`: current unresolved issues and previous round vote summary only.
- `evidence_summary`: counts and grounding statuses, not full evidence bodies.
- `truth_gate`: bounded summary only, with source hash/source chars.
- `fanout_certification`: bounded summary only, with source hash/source chars.
- `token_budget`: raw-vs-packet char estimate, estimated char/token savings, compression ratio.

## Safety rule

Reviewer models must request omitted details via `evidence_requests`; they must not assert omitted facts from memory or agreement. The orchestrator owns tool execution and evidence hydration.

## Anti-waste communication rules

- Online discussion sends manifest/delta packets, not full raw artifacts.
- Offline discussion reports `mode=offline`, zero prompts, zero invented savings.
- If the packet has no char savings, telemetry reports zero token savings and marks `mode=manifest_delta_no_savings`.
- `packet_chars` is converged against the serialized packet so telemetry is honest.
- Invalid env integer config falls back safely instead of crashing import.

## Verification

- Added tests in `/Users/charles/.hermes/scripts/test_consult_models_integration.py`:
  - `test_discussion_packet_uses_manifest_and_delta_only_to_reduce_prompt_size`
  - `test_run_discussion_records_communication_telemetry_and_sends_compact_prompt`
  - `test_offline_discussion_communication_summary_does_not_report_manifest_savings`
  - `test_packet_reports_zero_token_savings_when_manifest_has_no_char_savings`
  - `test_env_int_falls_back_on_invalid_value`
  - `test_truth_gate_summary_handles_non_dict_inputs`
- Final relevant verification:
  - consult_models integration: 32 tests OK
  - brainctl: 10 tests OK
  - anti_drift_guard: 11 tests OK
  - py_compile OK
  - static diff scan: hardcoded-sensitive-value=0, shell_true=0, eval_exec=0, pickle=0
  - independent reviewer: passed=true, no security_concerns, no logic_errors

## Next evolution

- Add an evidence-request runner that executes read-only allowlisted requests and hydrates the next round.
- Persist per-run communication telemetry to the local brain dashboard.
- Add tier-specific token budgets so T0/T1 use cheaper/smaller packets than T3.
