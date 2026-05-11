# Multi-model communication budget protocol

Use this when multi-model discussion starts wasting tokens by rebroadcasting large artifacts to every reviewer on every round.

## Problem pattern

Token cost grows with:

- number of reviewer models
- discussion rounds
- full `current_best` / `merged_plan` size
- full `evidence_bundle` size
- full `truth_gate` and `fanout_certification` payload size
- prior transcript length

A naive loop sends the same large JSON bodies repeatedly. This is expensive and also encourages models to summarize each other instead of requesting primary evidence.

## Protocol: `multi_model_comm_packet_v1`

For online discussion rounds after seed planning, send a compact packet instead of full artifacts:

- `artifact_manifest`: hash, char count, estimated token count for omitted artifacts.
- `current_best_summary`: patch ids, target files, op, risk, short rationale, source hash.
- `round_delta`: current unresolved issue ledger plus previous-round vote/status summary.
- `evidence_summary`: counts, grounding status, evidence ids, not full evidence bodies.
- `truth_gate`: bounded summary only, with source hash/source chars.
- `fanout_certification`: bounded summary only, reason truncated, with source hash/source chars.
- `token_budget`: raw-vs-packet chars, estimated char/token savings, compression ratio, mode.

Reviewer models must request omitted detail with `evidence_requests`; the orchestrator executes read-only allowlisted tools and hydrates the next round.

## Honest telemetry rules

- Offline mode reports `mode=offline`, zero prompt chars, zero savings.
- If the manifest packet is not smaller than raw context, report zero char/token savings and mark `mode=manifest_delta_no_savings`.
- `packet_chars` should be computed from the actual serialized packet after telemetry insertion; do not use rough pre-insertion size.
- `estimated_tokens_saved` must be zero when `estimated_chars_saved` is zero.
- Invalid integer env vars controlling budgets should fall back safely instead of crashing import.

## Bounded summary rules

Do not inline unbounded free text in communication packets:

- truncate rationale/reason fields
- cap arrays such as unsupported/contradicted claim ids
- preserve `source_hash` and `source_chars` so omitted payloads can be requested and audited
- keep full evidence in artifacts/brain/index, not in every reviewer prompt

## Verification checklist

Add tests for:

- packet excludes large irrelevant blobs and full planner outputs
- online discussion sends compact prompt and records communication telemetry
- offline discussion does not invent savings
- no-savings packet reports zero token savings
- malformed truth gate / invalid env integers do not crash
- `packet_chars == len(json.dumps(packet, ensure_ascii=False))`

Run at minimum:

```bash
python3 ~/.hermes/scripts/test_consult_models_integration.py -v
python3 -m py_compile ~/.hermes/scripts/consult_models.py ~/.hermes/scripts/test_consult_models_integration.py
```

If changing Hermes local-brain integration too, also run brainctl and anti-drift tests.

## Commit hygiene

When the Hermes repo is dirty with unrelated runtime/session/cache files, stage only the intended pathspecs instead of `git add -A`.
