# V(x) State Function and Auto-Trigger Chain Patterns

Session: 2026-05-10 Complex Giant Systems theory → Hermes optimization
Theory: 维纳控制论 + Lyapunov稳定性 + 钱学森开放复杂巨系统

## V(x) System State Function

Based on Complex Giant Systems theory (Qian Xuesen), implement a Lyapunov-inspired health function:

V(x) = Σ wᵢ · fᵢ(xᵢ) ∈ [0, 1]

### Components (7 weighted):

| Component | Weight | Function | Score Range |
|-----------|--------|----------|-------------|
| orchestrator | 0.20 | selfcheck PASS=1, FAIL=0 | 0 or 1 |
| dynamic_n | 0.10 | applied_n / max(1, raw_n) | 0-1 |
| classifier | 0.10 | unique_groups / sqrt(dispatchable) | 0-1 |
| continuation | 0.15 | 1 - (checkpoints / total_envelopes) | 0-1 |
| envelope | 0.15 | 1 - (failed+timeout / total) | 0-1 |
| cron | 0.15 | 1 - (recent_errors / total_crons) | 0-1 |
| kanban | 0.15 | mirrored / max(1, dispatchable) | 0-1 |

### Grade thresholds:
- V ≥ 0.7: HEALTHY
- 0.5 ≤ V < 0.7: DEGRADED
- V < 0.5: CRITICAL

### Bottleneck: use raw score minimum, NOT weighted score minimum.
Weighted scores can mislead (low-weight component with perfect score looks like bottleneck).

### Pitfalls:
1. Kanban stats `by_assignee` has nested dict: `{"brain-mirror": {"ready": 21}}` not `{"brain-mirror": 21}`
2. Cron `error:` in listing is historical — only count errors from last 48h by matching dates
3. `f_classifier` should use `groups / sqrt(dispatchable)` not `groups / dispatchable`

## Full Auto-Trigger Chain

The complete automated task execution pipeline:

```
orchestrator.list (brain_task_orchestrator.py)
    ↓ cron: pipeline-tick-hourly
pipeline_tick.py (create PENDING envelopes from dispatchable tasks)
    ↓ cron: envelope-executor-cycle (every 30m)
envelope_executor.py (PENDING → claim → delegate_task worker → DONE/BLOCKED/RETRY)
    ↓ cron: brain-kanban-bridge-sync (every 2h)
kanban_bridge.py (mirror to Kanban for observability)
    ↓ cron: v-state-hourly
v_state.py (V(x) health monitoring, ALERT if V < 0.7)
```

### Key components:
- **pipeline_tick.py**: reads brain tasks, creates envelope_bus entries, handles timeouts
- **envelope_executor.py**: the MISSING LINK — consumes PENDING envelopes, delegates to workers
- **task_continuation.py**: detects budget exhaustion, saves checkpoint, enables resume
- **task_classifier.py**: boundary → conflict_group mapping for parallel safety
- **dynamic_n.py**: N = min(ceil(dispatchable/7), conflict_groups, 3), with smoothing

### Coverage methodology:
- Count functional capabilities, not scripts
- "Embedded in component X" counts as covered
- "Replaced by newer component" counts as covered (upgrade, not gap)
- Deferred items must have explicit reason (avoid duplication, governance-only)

## PUA-Loop + Multi-Model Verification Pattern

Iterative improvement loop with multi-model verification at each round:

1. Multi-model assess what to fix (3+ models agree on direction)
2. Implement the fix
3. Multi-model verify the fix (must get 3/4 or 4/4 approval)
4. If not approved, address feedback and re-verify
5. Continue until all models approve

Key: each round must produce a VERIFIABLE deliverable (script, config, metric).
Never loop without a concrete output.
