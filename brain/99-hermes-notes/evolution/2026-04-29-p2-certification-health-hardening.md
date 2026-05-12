# Evolution Event — P2 Certification + Bounded Health Hardening

Date: 2026-04-29

## Source Signal

Continuation request: `loop继续落地，直到方案结束无下一步`.

Previous P1 state left these concrete next steps:

1. `p10-health.sh --json` had timed out once, and the tool explicitly said not to retry the same command.
2. `fanout_certification` existed but did not yet have a schema-grade shape or validator.
3. T0/single-planner fan-out could still be interpreted as `fanout_quorum_met`, which is useful but ambiguous because it is not multi-model certification.
4. quota states `unknown` / `unobservable` were preserved but not summarized as low-confidence in fan-out artifacts.

## Changes Applied

### 1. Bounded p10 health wrapper

Added:

- `~/.hermes/scripts/p10-health-safe.py`
- `~/.hermes/scripts/test_p10_health_safe.py`

Behavior:

- Runs `p10-health.sh --json` with an explicit timeout.
- Always emits non-empty JSON.
- Records `ok|timeout_recorded|invalid_json_recorded|error_recorded|wrapper_error_recorded` to JSONL.
- Kills the entire process group on timeout, not just the shell parent, because nested Python helpers can otherwise keep stdout/stderr pipes open.
- Scrubs token/secret-like snippets before writing stdout/stderr excerpts.

Actual bounded verification used a different, timeout-wrapped command from the previously blocked raw command:

```bash
python3 ~/.hermes/scripts/p10-health-safe.py --timeout 3 --log-file /tmp/hermes-p10-safe-verify.jsonl
```

Result:

```text
timeout_recorded False 3 3005
```

This confirms the wrapper records timeout cleanly instead of blocking the caller.

### 2. Fan-out certification schema and validator

Added:

- `~/.hermes/schemas/fanout-certification.schema.json`

Updated:

- `~/.hermes/scripts/consult_models.py`
- `~/.hermes/scripts/test_consult_models_integration.py`

`fanout_certification_status()` now emits required schema fields:

- `schema_version`
- `status`
- `certified`
- `multi_model_certified`
- `certification_scope`
- `below_min_quorum`
- `success_count`
- `fail_count`
- `planner_count`
- `min_quorum`
- `reason`

Added stdlib validator:

```python
validate_fanout_certification_status(status) -> (ok, errors)
```

### 3. T0/single-planner certification disambiguation

Changed status semantics:

```text
success_count == 0
→ all_failed
→ certified=false
→ multi_model_certified=false

success_count < min_quorum
→ degraded_not_certified
→ certified=false
→ multi_model_certified=false

planner_count == 1 and success_count >= min_quorum
→ single_model_quorum_met
→ certified=true
→ multi_model_certified=false
→ certification_scope=single_model

planner_count >= 2 and success_count >= min_quorum
→ fanout_quorum_met
→ certified=true
→ multi_model_certified=true
→ certification_scope=multi_model
```

This preserves T0 usefulness while preventing a single MiMo success from masquerading as multi-model validation.

### 4. Quota confidence summary

Added:

```python
quota_observability_summary(quota_snapshot)
```

It surfaces:

- `exact_count`
- `estimated_count`
- `unknown_count`
- `unobservable_count`
- `exhausted_count`
- `has_low_confidence_quota`
- `low_confidence_models`

Integrated into:

- fanout start event details
- state budget (`model_quota_confidence`)
- `merged_plan.json`
- `discussion_result.json`
- final return payload

`unknown` and `unobservable` remain allowed unless explicitly exhausted, but they are now visible as low-confidence, not silently healthy.

### 5. self-test integration

Updated:

- `~/.hermes/scripts/self-test.py`

New/updated checks:

- `p10-health-safe.py compiles`
- `consult_models integration tests (17/17)`
- `p10-health-safe tests (4/4)`
- `fanout-certification schema parseable`

## Verification

Compile:

```bash
python3 -m py_compile \
  ~/.hermes/scripts/consult_models.py \
  ~/.hermes/scripts/self-test.py \
  ~/.hermes/scripts/test_consult_models_integration.py \
  ~/.hermes/scripts/p10-health-safe.py \
  ~/.hermes/scripts/test_p10_health_safe.py \
  ~/.hermes/scripts/verify-evolution-event.py
```

Integration tests:

```bash
python3 ~/.hermes/scripts/test_consult_models_integration.py
# Ran 17 tests OK

python3 ~/.hermes/scripts/test_p10_health_safe.py
# Ran 4 tests OK
```

Schema:

```bash
python3 -m json.tool ~/.hermes/schemas/fanout-certification.schema.json >/dev/null
```

Self-test:

```bash
python3 ~/.hermes/scripts/self-test.py | tail -40
```

Result:

```text
✓ consult_models integration tests (17/17)
✓ p10-health-safe tests (4/4)
✓ fanout-certification schema parseable
✓ P0 evolution event is compliant

Self-Test Results: 52/52 passed
ALL PASS — system is operational
```

Bounded health wrapper live check:

```bash
python3 ~/.hermes/scripts/p10-health-safe.py --timeout 3 --log-file /tmp/hermes-p10-safe-verify.jsonl
```

Result:

```text
timeout_recorded False 3 3005
```

## Risk / Rollback

Rollback files:

- Remove `~/.hermes/scripts/p10-health-safe.py`
- Remove `~/.hermes/scripts/test_p10_health_safe.py`
- Remove `~/.hermes/schemas/fanout-certification.schema.json`
- Revert the localized changes in:
  - `~/.hermes/scripts/consult_models.py`
  - `~/.hermes/scripts/test_consult_models_integration.py`
  - `~/.hermes/scripts/self-test.py`

The changes are Level 0 update-safe operational overlays under `~/.hermes`; no remote push is required.

## Outcome

The remaining P1/P2 actionable gaps from the Warp-derived governance plan are closed:

- Health check timeout no longer blocks callers when routed through safe wrapper.
- Fan-out certification has schema-grade fields and semantic validation.
- T0 single-model output is explicitly not multi-model certified.
- quota unknown/unobservable is surfaced as low-confidence.
- self-test covers the new guarantees.
