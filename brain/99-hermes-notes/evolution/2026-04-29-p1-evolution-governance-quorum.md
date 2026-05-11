# Evolution Event: P1 Evolution Governance + T1 Quorum Hardening

**Date:** 2026-04-29
**Type:** governance-hardening
**Status:** completed
**Scope:** Level 0 update-safe scripts/config + multi-model governance hardening

## Source Signal

Continuation from P0 Warp → Hermes multi-model governance work.

P0 discovered two immediate P1 gaps:

1. Evolution events need to be part of the health/self-test loop, not just manually documented.
2. T1 multi-model tier had `min_quorum: 1`, which allowed a single successful planner to masquerade as multi-model certification.

## Changes

### 1. self-test integrates evolution compliance

Updated:

- `~/.hermes/scripts/self-test.py`

Added checks:

- `verify-evolution-event.py compiles`
- `P0 evolution event is compliant`

Result:

```text
Self-Test Results: 49/49 passed
ALL PASS — system is operational
```

### 2. consult_models fan-out certification status

Updated:

- `~/.hermes/scripts/consult_models.py`
- `~/.hermes/scripts/test_consult_models_integration.py`

Added:

```python
def fanout_certification_status(success_count, planner_count, min_quorum, fail_count=0) -> dict
```

Semantics:

- `success_count == 0` → `all_failed`, `certified=false`
- `success_count < min_quorum` → `degraded_not_certified`, `certified=false`
- `success_count >= min_quorum` → `fanout_quorum_met`, `certified=true`

Integrated into:

- `merged_plan.json` via `fanout_certification`
- `merged_plan.json` via `certification_status=degraded_not_certified` when below min quorum
- `discussion_result.json` via `fanout_certification`
- final `fanout_end` event verdict: only `pass` when fanout quorum is actually certified
- return object: `fanout_certification`

### 3. T1 min_quorum hardened

Updated:

- `~/.hermes/config/quorum.yaml`

Change:

```yaml
T1:
  quorum: 3
  min_quorum: 2  # P1: T1 must not certify from a single planner
```

Backup:

```text
~/.hermes/backups/quorum.pre-p1-minquorum-20260429-223736.yaml
```

### 4. Tests added

Updated:

- `~/.hermes/scripts/test_consult_models_integration.py`

New tests:

- `test_quorum_t1_min_quorum_requires_two_models`
- `test_fanout_below_min_quorum_is_degraded_not_certified`

Result:

```text
Ran 13 tests in 0.012s
OK
```

## Verification

### RED/GREEN evidence

RED 1:

```text
RED: self-test does not include evolution verifier yet
```

GREEN 1:

```text
✓ verify-evolution-event.py compiles
✓ P0 evolution event is compliant
Self-Test Results: 49/49 passed
```

RED 2:

```text
AssertionError: 1 not greater than or equal to 2 : T1 min_quorum=1, need >= 2
```

GREEN 2:

```text
Ran 13 tests in 0.012s
OK
```

### Final verification commands

```bash
python3 -m py_compile \
  ~/.hermes/scripts/consult_models.py \
  ~/.hermes/scripts/self-test.py \
  ~/.hermes/scripts/test_consult_models_integration.py \
  ~/.hermes/scripts/verify-evolution-event.py

python3 ~/.hermes/scripts/consult_models.py status --quota
python3 ~/.hermes/scripts/test_consult_models_integration.py
python3 ~/.hermes/scripts/self-test.py
```

Final observed results:

```text
compile_ok
T1: quorum=3 min=2 planners=['gpt-5.5', 'mimo-v2.5-pro', 'deepseek-v4-pro']
consult_models integration tests: 13/13 OK
self-test: 49/49 passed
```

### p10-health note

Attempted:

```bash
bash ~/.hermes/scripts/p10-health.sh --json | python3 -m json.tool
```

Result: command timed out in tool harness. The tool explicitly required not retrying that exact command. Current confidence therefore comes from compile + targeted integration tests + full `self-test.py`.

## Upgrade Survival

All changes are Level 0 update-safe:

- `~/.hermes/scripts/consult_models.py`
- `~/.hermes/scripts/self-test.py`
- `~/.hermes/scripts/test_consult_models_integration.py`
- `~/.hermes/config/quorum.yaml`
- `~/.hermes/notes/evolution/...`

These are outside the upstream hermes-agent git repo. No remote push needed.

## Remaining P1/P2 Candidates

- Add a bounded wrapper around p10-health if timeout persists.
- Add explicit T0 fallback/degraded status test if MiMo is unavailable.
- Add a daily cron job or existing health job integration for `verify-evolution-event.py` output summary.
- Consider promoting fanout certification into a JSON schema for `merged_plan.json`.
