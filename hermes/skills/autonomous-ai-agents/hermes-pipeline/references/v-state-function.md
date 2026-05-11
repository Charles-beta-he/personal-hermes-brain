# V(x) System State Function

Complex Giant Systems health monitor based on Wiener's cybernetics + Lyapunov stability theory.

## Formula

```
V(x) = Σ wᵢ · fᵢ(xᵢ) ∈ [0, 1]
```

## Components

| Component | Weight | Function | Data Source |
|-----------|--------|----------|-------------|
| orchestrator | 0.20 | selfcheck PASS=1, else 0 | brain_task_orchestrator.py selfcheck |
| dynamic_n | 0.10 | applied_n / max(1, raw_n) | dynamic_n_state.json |
| classifier | 0.10 | groups / sqrt(dispatchable) | task_classifier.py show |
| continuation | 0.15 | 1 - (checkpoints / total_envelopes) | task_checkpoints/ + envelope_bus |
| envelope | 0.15 | 1 - (failed+timeout / total) | envelope_bus.py stats |
| cron | 0.15 | 1 - (recent_errors / total_crons) | hermes cron list (48h window) |
| kanban | 0.10 | mirrored / dispatchable | kanban stats + orchestrator list |

## Grade Thresholds

| V(x) | Grade | Action |
|-------|-------|--------|
| ≥ 0.7 | HEALTHY | Normal operation |
| 0.5–0.7 | DEGRADED | Reduce parallelism, investigate bottleneck |
| < 0.5 | CRITICAL | Stop all non-essential work, fix bottleneck |

## Bottleneck Detection

Bottleneck = component with lowest raw score (not weighted). This identifies which single component needs the most improvement.

## Cron Integration

Run hourly. Alert only when V < 0.7:
```
v_state.py --json → if V < 0.7, report bottleneck
```

## Pitfalls

- **Cron error counting** — Only count errors from last 48h, not historical. Old errors persist in `last_error` field after model fix.
- **Kanban assignee parsing** — `by_assignee.brain-mirror` is a dict `{"ready": N}`, not an int. Parse: `mirror_data.get('ready', 0)`.
- **classifier coverage** — Use `groups / sqrt(dispatchable)`, not `groups / dispatchable`. The sqrt prevents inflated scores when few tasks exist.
