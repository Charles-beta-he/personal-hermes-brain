# Trigger Timing Implementation Pattern

> Landed 2026-05-12. How to convert a "post-session review" multimodel system into event-driven tiered triggering.

## Architecture: Two-Layer Design

### Layer 1: Streaming (normal path)
Trigger: lifecycle events (claim, transition to running/review)
Action: `maybe_stream_multimodel_intervention(task)`
- Check if triggered
- Check economy gate (round count)
- Check cooldown (30 min since last check)
- Spawn background Popen worker
- Non-blocking to main flow

### Layer 2: Cron (fallback path)
Trigger: every 60 min
Action: `multimodel_intervention_dynamic_step`
- Scan all pending triggered tasks
- Clean up streaming layer misses
- Scale workers by queue depth (1/2/3)

## 5-Phase Trigger Table

| Phase | Trigger Point | Signals | Tier |
|-------|--------------|---------|------|
| pre_action | before risky tool call | blast_radius high, irreversible, closeout surface | T0/T1 |
| mid_loop | during execution | corrections>=2, repeat_sig>=2, budget>=0.70 | T1/T2 |
| post_failure | after failure | same class 24h>=2, unknown high-severity | T2/T3 |
| post_session | after session ends | autopsy recommended_tier | T0/T1/T2 |
| periodic_governance | 24h/50 events | noise/late detection patterns | threshold tuning |

## Advisory vs Certification Split

### Advisory (T1/T2)
- Can recommend retry/replan/evidence collection
- Cannot mark done
- Cannot authorize closeout
- Writes: multimodel_advisory_only=true, multimodel_certification_authority=false

### Certification (T3)
- Required for done/closeout
- Must have 4/4 canonical participants
- Must have evidence bound to task
- Must pass ratification gate

### Enforcement
When advisory_only=true and gate returns PASS/LOOP_DONE:
- Override to PASS_ADVISORY_ONLY
- Set decision to continue_loop
- Add advisory_block reason

## Loop Economy Gate

```
task_multimodel_economy_gate(task):
  rounds = count("Multimodel PUA-loop round" in body)
  if rounds >= 5 and last_status == "failed":
    return {action: "pause", allowed_tier: "none"}
  if rounds >= 3 and last_status == "failed":
    return {action: "throttle", allowed_tier: "T2_advisory"}
  return {action: "allow", allowed_tier: "any"}
```

## Budget Signal Consumption

Doctor `--emit-signal` writes to `budget_signals.jsonl` with schema `local_brain_trigger_signal_v1`.
Orchestrator reads last 20 lines; if high/critical severity + T2/T3 tier found, upgrades weak trigger to `iteration_budget_signal`.

## Governance Ratchet

`governance_ratchet.py` reads:
- budget_signals.jsonl
- improvement-signals.jsonl
- convergence stats

Outputs `trigger_effectiveness_v1`:
- health: healthy | healthy_quiet | suboptimal | degraded | needs_attention
- patterns: noise_detected, late_detection
- adjustments: reduce_noise, improve_early_detection, investigate_repeat

## Key Files (Hermes-local)
- `~/.hermes/scripts/governance_ratchet.py`
- `~/.hermes/scripts/iteration_budget_doctor.py --emit-signal`
- `~/.hermes/state/budget_signals.jsonl`
- `~/.hermes/state/governance_ratchet.json`
- `~/.hermes/docs/trigger_timing_policy_v1.md`
- `~/.hermes/logs/multimodel_streaming.jsonl`

## Pitfalls
- `strong` variable must be defined BEFORE budget signal check block, not after
- `completed_at` from Lark API is string `'0'` (truthy), not int `0` — filter by `status == 'todo'` instead
- Allowlist project names must exactly match task project field (case-sensitive)
- Dynamic step max_workers was hardcoded to 1-2; scale by queue depth
