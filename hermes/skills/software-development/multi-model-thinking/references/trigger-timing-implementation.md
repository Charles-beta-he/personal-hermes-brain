# Trigger Timing Implementation — Event-Driven Multi-Model Routing

> Landed 2026-05-12. Concrete implementation of event-driven, tiered trigger timing
> for Hermes local-brain taskpool multi-model intervention.

## Architecture

```
doctor --emit-signal
  → budget_signals.jsonl (local_brain_trigger_signal_v1)
  → orchestrator consumes signal → upgrades trigger tier
  → autopsy outputs recommended_tier + failure_class_counts
  → governance_ratchet detects noise/late-detection/repeats
  → economy_gate throttles/pauses by round count
  → dispatch tick outputs tier routing (advisory/certification)
  → intervention step routes by tier
  → advisory PASS blocked as PASS_ADVISORY_ONLY
  → write_multimodel_result writes advisory_only + certification_authority
```

## Files Changed

| File | What |
|------|------|
| `post-session-autopsy.py` | `classify_failure_group`, `recommend_autopsy_tier`, `failure_class_counts`, `recommended_tier` output |
| `brain_task_orchestrator.py` | `task_multimodel_advisory_reasons`, `task_multimodel_certification_reasons`, `write_multimodel_result` advisory fields, `build_multimodel_intervention_plan` economy gate, budget signal consumption, `PASS_ADVISORY_ONLY` blocking |
| `iteration_budget_doctor.py` | `--emit-signal` flag writes `budget_signals.jsonl` |
| `brain_task_dispatch_tick.py` | `multimodel_summary` outputs `advisory_reasons`, `certification_reasons`, `recommended_tier`, `advisory_only` |
| `governance_ratchet.py` | New script: reads signals + convergence, outputs `trigger_effectiveness_v1` with `recommended_adjustment` |

## Signal Schema

```json
{
  "schema": "local_brain_trigger_signal_v1",
  "ts": "ISO8601",
  "source": "iteration_budget_doctor|post_session_autopsy|orchestrator",
  "phase": "pre_action|mid_loop|post_failure|post_session|periodic_governance",
  "severity": "info|warn|high|critical",
  "signal_type": "iteration_budget_saturation|correction_repeat|tool_failure_repeat|...",
  "recommended_tier": "T0|T1_advisory|T2_advisory|T3_advisory|T3_certification",
  "advisory_only": true,
  "confidence": 0.0-1.0,
  "rationale": "short text"
}
```

## Tier Routing Rules

| Tier | When | Cost | Authority |
|------|------|------|-----------|
| T0 | deterministic/read-only/sanity | lowest | no model calls |
| T1_advisory | early intervention, low risk | cheap (1 model) | advisory only, cannot done |
| T2_advisory | repeat failures, mid risk | medium (2-3 models) | advisory only, cannot done |
| T3_advisory | high-risk pre-closeout | expensive (4 models) | advisory only, cannot done |
| T3_certification | final closeout | expensive (4 models) | full authority, can done |

## Threshold Defaults

- Mid-loop T1: corrections>=2, repeat_signature>=2, budget_used>=0.70
- Mid-loop T2: corrections>=3, repeat_signature>=3, budget_used>=0.85, verifier_failure>=1
- Post-failure T2: same failure class in 24h>=2
- Budget signal upgrade: doctor emits high/critical → orchestrator boosts weak trigger to T2

## Loop Economy Gate

Implemented in `task_multimodel_economy_gate()`:
- `rounds >= 3` and `last_status == "failed"` → throttle to T2_advisory (cert_reasons downgraded)
- `rounds >= 5` and `last_status == "failed"` → pause, intervention_required=False, needs human

## Advisory Done Blocking

In `write_multimodel_result_to_task`:
- If `advisory_only_plan=True` and gate returns PASS+LOOP_DONE → rewrite as `PASS_ADVISORY_ONLY` + `decision=continue_loop`
- This prevents advisory-only tasks from certifying

In `_run_single_task_pipeline` and `command_multimodel_intervention_step`:
- Same block applied before mutation step

## Governance Ratchet

Script: `~/.hermes/scripts/governance_ratchet.py`
Output: `~/.hermes/state/governance_ratchet.json` (trigger_effectiveness_v1)

Detects:
- noise_detected: trigger_count>20 but high_severity<3
- late_detection: post_session>0 but mid_loop==0
- repeated_types: same signal type >=3 times

Outputs recommended_adjustment per pattern.

## Pitfalls

1. `strong` set must be defined BEFORE budget signal block uses it (caused UnboundLocalError in 23 tests)
2. economy_gate returns a plan with `intervention_required=False` for paused tasks — dry-run consumers must check this
3. PASS_ADVISORY_ONLY is a new gate status; ratification_gate consumers must handle it as non-pass
4. governance_ratchet.py must be run separately (e.g., cron or manual) to populate `~/.hermes/state/governance_ratchet.json`
5. budget_signals.jsonl appends; old signals accumulate. Consider rotating or pruning in production.
