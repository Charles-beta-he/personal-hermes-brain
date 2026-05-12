# Task Continuation — Budget Exhaustion Checkpoint/Resume

When a worker hits the iteration budget (max_turns=60), work is incomplete. Instead of restarting from scratch, checkpoint progress and resume.

## Detection Signals

```python
BUDGET_SIGNALS = [
    'Iteration budget reached',
    'iteration budget reached',
    'BUDGET_EXHAUSTED',
    'max_turns reached',
    '工具调用次数限制',
    '以下步骤还没做',
]
```

## Checkpoint Structure

```json
{
  "task_id": "...",
  "attempt": 1,
  "detected_at": "2026-05-10T...",
  "signal": "Iteration budget reached",
  "progress": {
    "completed_steps": ["✅ step 1", "✅ step 2"],
    "remaining_steps": ["- step 3", "- step 4"],
    "files_changed": ["file1.py"],
    "partial_output": "last 2000 chars..."
  },
  "continuation_count": 1
}
```

## Continuation Context Injection

When resuming, inject checkpoint into worker prompt:

```
=== CONTINUATION CONTEXT ===
This is a RESUMED task. Previous attempt hit iteration budget.
Attempt: 1/3

COMPLETED STEPS (do NOT repeat):
✅ step 1
✅ step 2

REMAINING STEPS (focus on these):
- step 3
- step 4

PARTIAL OUTPUT FROM PREVIOUS ATTEMPT:
...

=== ORIGINAL TASK CONTEXT ===
<original prompt>
```

## Limits

- `MAX_CONTINUATIONS = 3` (configurable via `MAX_CONTINUATIONS` env)
- Checkpoint cleaned up after successful completion
- Continuation count accumulates across attempts

## Integration with Envelope Executor

The executor checks for budget exhaustion after each worker run:
1. Detect signal in output
2. Save checkpoint
3. If continuation_count < max: re-queue as PENDING
4. If continuation_count >= max: mark FAILED

## Pitfalls

- **completed_steps detection is heuristic** — Looks for ✅, "已完成", "Done:" patterns. May miss some.
- **remaining_steps may include the budget signal itself** — Filter out detection signals from remaining steps.
- **Checkpoint accumulates across retries** — completed_steps from all attempts are merged, not replaced.
