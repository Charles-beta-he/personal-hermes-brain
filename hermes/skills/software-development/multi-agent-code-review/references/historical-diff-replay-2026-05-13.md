# Historical Diff Replay — Multi-Agent Code Review Confidence Filtering

Date: 2026-05-13

## Replay Target

- Commit: `6ad7841 fix: sanitize model quota evidence`
- Diff file: `/tmp/multi_agent_code_review_historical_diff_6ad7841.patch`
- Reviewed files: `scripts/model_quota.py`, `scripts/test_model_quota.py`

## Raw Agent Findings

1. Security agent found a medium issue: sensitive dictionary key text could be persisted even when the value is redacted.
2. Logic agent found a medium issue: preserved higher-confidence snapshots did not force sanitized state back to disk, so old unsanitized state could survive.
3. Logic agent also found the dictionary-key leak as low severity.
4. Performance agent found no actionable issue.

## Aggregation Lesson

The default score formula is still useful:

```text
score = agreement_ratio * 0.6 + avg_confidence * 0.4
```

But this replay exposed a false-negative mode:

- Key-redaction cluster: 2/3 agents, avg_conf≈0.735, score≈0.694, just below medium threshold 0.7.
- Preserved-state cleanup: 1/3 agents, conf=0.86, score≈0.544, below medium threshold 0.7.

Both findings were real and were fixed with deterministic tests. Therefore confidence filtering must not be the final truth gate.

## Evidence Override Rule

For security/correctness findings:

- Cross-agent agreement reduces noise, but deterministic reproduction outranks agreement.
- A single-agent medium/high finding may be promoted when the reviewer supplies a specific repro/test or exact file-state proof.
- Final disposition should be one of:
  - `accepted`
  - `accepted_by_deterministic_override`
  - `suppressed_false_positive`
  - `accepted_risk`

## Fixes Landed From Replay

- Redact sensitive dict keys as `[REDACTED_KEY]` with deterministic dedupe.
- Persist sanitized state even when `record_snapshot()` preserves an existing higher-confidence snapshot.
- Apply `sanitize_usage()` to usage dicts discovered in already-persisted state.

Validation:

```bash
python3 /Users/charles/.hermes/scripts/test_model_quota.py
# 33 tests OK
python3 -m py_compile /Users/charles/.hermes/scripts/model_quota.py /Users/charles/.hermes/scripts/test_model_quota.py
# PASS
```
