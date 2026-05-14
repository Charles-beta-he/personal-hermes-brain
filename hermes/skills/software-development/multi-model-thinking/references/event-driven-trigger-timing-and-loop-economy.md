# Event-Driven Trigger Timing, Tiered Routing, and Loop Economy

Session: 2026-05-12
Topic: Shift from "post-session autopsy drives multi-model" to "event-driven, tiered trigger, closed-loop certification, self-converging loop"

## Problem Statement

Original system relied on post-session autopsy as the primary multi-model trigger, with keyword-based taskpool triggers as supplement. This caused:
- Late intervention (problems detected after session ended)
- Noisy over-triggering (keywords with >50% hit rates)
- No distinction between advisory review and closeout certification
- No cost control (T3 ran on every triggered task regardless of history)

## Architecture: Event-Driven 5-Phase Trigger

```
doctor --emit-signal → budget_signals.jsonl
  ↓ (consumed by orchestrator)
autopsy → recommended_tier + failure_class_counts
  ↓ (consumed by orchestrator)
governance_ratchet → trigger_effectiveness_v1 + recommended_adjustment
  ↓ (consumed by orchestrator)
economy_gate → throttle/pause based on round history
  ↓
dispatch tick → tier routing (advisory_reasons / certification_reasons / recommended_tier)
  ↓
intervention step → advisory/certification split → advisory_done_block
  ↓
write_multimodel_result → advisory_only + certification_authority fields
```

## 5 Trigger Phases

### 1. pre-action
- Trigger: blast_radius high, reversible low, closeout surface touch
- Output: T0/T1 advisory only

### 2. mid-loop (earliest self-correction point)
- Trigger: corrections >= 2, repeat_signature >= 2, iteration_budget_used >= 0.70
- Output: T1/T2 advisory
- Signal source: `iteration_budget_doctor.py --emit-signal` writes `budget_signals.jsonl`

### 3. post-failure
- Trigger: same failure class 24h >= 2, unknown high-severity failure
- Failure classes: tool_error, verifier_gap, requirement_mismatch, schema_mismatch, quota_or_timeout, router_skew, unknown
- Output: T1/T2/T3 by severity

### 4. post-session
- Downgraded from "primary trigger" to "evidence producer"
- Output: correction_count, tool_failures, iteration_budget_count, repeat_signature_count, failure_class_counts, recommended_tier

### 5. periodic governance (double-loop learning)
- Cadence: 50 events or 24h
- Metrics: trigger_rate, confirm_rate, post_session_only_detect_rate
- Auto-tuning: high trigger + low confirm → reduce noise; high post_session_only → improve early detection

## Tier Routing

| Tier | Models | Time/task | Use case |
|------|--------|-----------|----------|
| T0 | none | ~0 | deterministic sanity |
| T1_advisory | cheapest 1 | ~1min | early intervention, low risk |
| T2_advisory | 2 disagree-probe | ~3min | repeat failure, mid risk |
| T3_advisory | full panel | ~15min | high risk pre-closeout review |
| T3_certification | full 4/4 | ~15-20min | final closeout, requires gate PASS |

## Advisory vs Certification Hard Split

Advisory (T1/T2/T3_advisory):
- CAN suggest replan/retry/collect evidence
- CAN write to task frontmatter: multimodel_advisory_only=true
- CANNOT mark done, CANNOT closeout

Certification (T3_certification):
- CAN produce LOOP_DONE
- CAN write multimodel_status=certified
- REQUIRES 4/4 canonical participants + evidence binding + gate PASS
- Advisory PASS is blocked to PASS_ADVISORY_ONLY in intervention step

## Loop Economy Gate

Prevents burning T3 on tasks that won't converge:

```python
def task_multimodel_economy_gate(task):
    rounds = task_multimodel_round_count(task)  # count "Multimodel PUA-loop round" in body
    last_status = task.fm.get("multimodel_round_status")
    
    if rounds >= 5 and last_status == "failed":
        return {"action": "pause", "allowed_tier": "none"}  # requires human review
    if rounds >= 3 and last_status == "failed":
        return {"action": "throttle", "allowed_tier": "T2_advisory"}  # downgrade from T3
    return {"action": "allow", "allowed_tier": "any"}
```

In build_multimodel_intervention_plan:
- economy_gate=pause → return intervention_required=False immediately
- economy_gate=throttle → move cert_reasons into advisory_reasons, cap at T2

## Signal Schema: local_brain_trigger_signal_v1

```json
{
  "schema": "local_brain_trigger_signal_v1",
  "ts": "ISO8601",
  "source": "iteration_budget_doctor|autopsy|orchestrator|dispatch_tick",
  "phase": "pre_action|mid_loop|post_failure|post_session|periodic_governance",
  "severity": "info|warn|high|critical",
  "signal_type": "correction_repeat|tool_failure_repeat|iteration_budget_saturation|...",
  "recommended_tier": "T0|T1_advisory|T2_advisory|T3_advisory|T3_certification",
  "advisory_only": true,
  "confidence": 0.0-1.0,
  "rationale": "short text"
}
```

## Governance Ratchet

Script: `~/.hermes/scripts/governance_ratchet.py`
Output: `trigger_effectiveness_v1` with health assessment and recommended adjustments

Detection patterns:
- noise_detected: trigger_count > 20 but high_severity_count < 3
- late_detection: post_session signals present but mid_loop signals absent
- repeated_types: same signal type appearing >= 3 times

Health states: healthy_quiet, healthy, suboptimal, degraded, needs_attention

## Streaming Architecture (Event-Driven, Not Cron-Driven)

**Key insight from user**: "定时应该只是作为保底维护，正常应该流式执行任务"

### Two-layer architecture:

1. **Streaming layer (normal path)**
   - Trigger: command_claim / command_transition(running/review)
   - Action: `maybe_stream_multimodel_intervention(task)` spawns background Popen
   - 30-minute dedup window prevents re-processing
   - Economy gate prevents wasted work

2. **Cron layer (fallback/maintenance)**
   - Trigger: every 60 minutes
   - Action: `multimodel_intervention_dynamic_step` sweeps for missed tasks
   - Scales workers by queue depth: 1/2/3

### Implementation:
```python
# In command_claim and command_transition:
streaming = maybe_stream_multimodel_intervention(t)
return {..., "multimodel_streaming": streaming}

def maybe_stream_multimodel_intervention(task):
    if not task_multimodel_intervention_required(task): return skip
    if economy_gate == "pause": return skip
    if recently_checked(< 30min): return skip
    # spawn background worker
    proc = Popen([python3, orchestrator.py, "multimodel-intervention-step", "--task", task.id])
    return {"action": "spawned", "pid": proc.pid}
```

## Files Changed (2026-05-12)

| File | Lines | Change |
|------|-------|--------|
| post-session-autopsy.py | +56 | classify_failure_group, recommend_autopsy_tier, recommended_tier |
| brain_task_orchestrator.py | +123 | advisory/cert split, economy gate, budget signal consumption, streaming hook, advisory done block |
| iteration_budget_doctor.py | +35 | --emit-signal → budget_signals.jsonl |
| brain_task_dispatch_tick.py | +14 | tier routing in multimodel_summary |
| governance_ratchet.py | +170 | new: trigger effectiveness metrics |
| multimodel_intervention_dynamic_step.py | +5 | scalable workers 1/2/3 |
| trigger_timing_policy_v1.md | full doc | implementation spec |

## Pitfalls

1. **Python UnboundLocalError from variable ordering**: When adding new code blocks that reference variables defined later in the same function, define the variable BEFORE the new block. Common when inserting signal consumption before existing `strong = {...}` set definition.

2. **Advisory-only tasks must NOT authorize done**: The intervention step checks `advisory_only_plan` and blocks PASS→LOOP_DONE, converting to PASS_ADVISORY_ONLY with continue_loop decision.

3. **Streaming dedup**: 30-minute window prevents same task from spawning multiple workers. Check `multimodel_last_checked_at` before spawning.

4. **Cron is fallback, not primary**: Streaming handles real-time; cron catches edge cases (tasks that slipped through, tasks added directly to filesystem without going through orchestrator).

5. **Budget signals must be structured JSONL**: Each line is a complete `local_brain_trigger_signal_v1` object. Doctor must write to `~/.hermes/state/budget_signals.jsonl`.
