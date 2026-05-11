# Claims Injection for Taskpool Multimodel Intervention

When `consult_models.py state` is called without `--claim` flags, the truth gate returns `truth_status=no_claims` and the ratification gate always FAIL.

## The Problem

`build_multimodel_intervention_plan()` generates a `build_state_command` without `--claim` flags. The state has 0 claims. During discussion, models can't verify anything. The truth gate returns `no_claims`.

## The Fix

Add 3 explicit claims to the build_state_command, aligned with the gate's criteria_satisfied:

```python
"--claim 'C-001:Task decomposition is accurate — the identified task, lane, priority, and trigger reasons match the canonical task note' "
"--claim 'C-002:One-shot landing plan exists — a directly executable next slice with acceptance evidence and rollback boundary can be produced' "
"--claim 'C-003:Long-term goal alignment — the solution preserves lane/project/architecture_target and does not let evolution preempt work delivery' "
```

## Result

- Before: `truth_status=no_claims` (0 claims) → gate FAIL with 23 failures
- After: `truth_status=unsupported` (3 claims, 0 verified, coverage=0.0) → gate FAIL with 29 failures

The `unsupported` status is better than `no_claims` — claims exist but evidence linking hasn't happened yet. Evidence linking happens automatically during the discussion phase.

## Alignment

| Claim | Gate Criterion |
|-------|---------------|
| C-001 (decomposition accuracy) | accuracy |
| C-002 (one-shot landing) | one_shot_landing |
| C-003 (long-term alignment) | long_term_goal |

## When to Add More Claims

For specific tasks, add task-specific claims:
```bash
--claim 'C-004:The proposed fix addresses the root cause identified in the Lark task'
--claim 'C-005:Existing functionality is preserved (no regression)'
```
