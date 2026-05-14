# Trigger Timing: Event-Driven Multi-Model Intervention Pattern

> Captured from 2026-05-12 session: 4 rounds of analysis + 2 rounds of implementation
> converting Hermes local-brain from "post-session autopsy driven" to "event-driven, tiered
> trigger, closed-loop certification, self-converging loop".

## Problem Statement

The original trigger mechanism was dominated by:
- `post-session-autopsy.py`: fires AFTER session ends
- `brain_task_orchestrator.py` intervention reasons: structural triggers at lifecycle transitions + keyword supplementation
- `iteration_budget_doctor.py`: read-only diagnostic, no trigger output

Result: intervention was either too late (post-session) or too noisy (keyword-based). pass_rate=0.179 with trigger_rate=0.5.

## 5-Phase Trigger Model

Instead of a single trigger point, use 5 temporal phases:

### Phase 1: pre-action
- **When**: Before high-risk tool calls / task transitions
- **Conditions**: blast_radius high, irreversible ops, closeout surface touches, high uncertainty
- **Output**: T0/T1 advisory only
- **Key insight**: Prevent damage before it happens, don't wait for failure

### Phase 2: mid-loop
- **When**: During active execution, before iteration budget exhaustion
- **Conditions**:
  - corrections >= 2 → T1
  - repeat_signature >= 2 → T1
  - iteration_budget_used >= 0.70 → T1
  - iteration_budget_used >= 0.85 → T2
  - verifier_failure >= 1 → T2
- **Output**: T1/T2 advisory
- **Key insight**: This is the BIGGEST gap in post-session-only systems. The earlier you intervene, the cheaper the fix.

### Phase 3: post-failure
- **When**: Immediately after a classified failure
- **Failure taxonomy**: tool_error, verifier_gap, requirement_mismatch, schema_mismatch, quota_or_timeout, router_skew, unknown
- **Conditions**:
  - First low-risk failure → T0/T1
  - Same failure class in 24h >= 2 → T2
  - Unknown/high-severity/closeout failure → T3 advisory or certification path
- **Key insight**: Classify failures structurally, don't just count them

### Phase 4: post-session
- **When**: After session ends (demoted from primary to evidence producer)
- **Output fields**: correction_count, tool_failures, iteration_budget_count, repeat_signatures, failure_class_counts, recommended_tier
- **Key insight**: Autopsy should produce consumable tier recommendations, not just reports

### Phase 5: periodic governance
- **When**: Every 50 task events or 24h
- **Governs**: trigger_rate vs confirm_rate, post_session_only_detect_rate, late_intervention_rate
- **Auto-tuning**:
  - High trigger rate + low confirm rate → reduce noise (raise weak signal thresholds)
  - High post_session_only_detect → lower mid-loop thresholds
  - Repeated unresolved T3 issues → switch to evidence-request loop
- **Key insight**: This is the double-loop learning layer — it tunes the trigger system itself

## Tier Routing Model

| Tier | Models | Time | Use Case |
|------|--------|------|----------|
| T0 | deterministic only | ~0 | Sanity checks, readonly |
| T1 advisory | cheapest available | ~1min | Early intervention, low risk |
| T2 advisory | 2-model disagree-probe | ~3-8min | Mid-risk, repeat patterns |
| T3 advisory | 4-model review | ~15-20min | High-risk pre-closeout |
| T3 certification | 4-model ratification | ~15-20min | Final closeout (fail-closed) |

## Advisory vs Certification Hard Split

THIS IS THE MOST IMPORTANT DESIGN DECISION:

### Advisory (T1/T2)
- CAN: recommend replan/retry/evidence collection
- CAN: write to task frontmatter as recommendation
- CANNOT: mark task done
- CANNOT: claim closeout authority
- CANNOT: suppress future intervention

### Certification (T3)
- CAN: write multimodel_status=certified
- CAN: write multimodel_ratification_artifact
- CAN: trigger LOOP_DONE
- REQUIRES: 4/4 canonical participant panel
- REQUIRES: evidence bound to exact task
- REQUIRES: unresolved severity>=3 = 0

### Implementation in write_multimodel_result_to_task
```python
advisory_reasons = task_multimodel_advisory_reasons(task)
cert_reasons = task_multimodel_certification_reasons(task)
is_advisory_only = not passed and not cert_reasons and bool(advisory_reasons)

updates["multimodel_advisory_only"] = is_advisory_only
updates["multimodel_certification_authority"] = bool(cert_reasons) or passed
updates["multimodel_advisory_reasons"] = advisory_reasons
updates["multimodel_certification_reasons"] = cert_reasons
```

## Signal Schema

```json
{
  "schema": "local_brain_trigger_signal_v1",
  "ts": "ISO8601",
  "source": "autopsy|doctor|orchestrator|validator|dispatch_tick",
  "phase": "pre_action|mid_loop|post_failure|post_session|periodic_governance",
  "severity": "info|warn|high|critical",
  "signal_type": "correction_repeat|tool_failure_repeat|iteration_budget_saturation|verifier_failure|unknown_failure|blast_radius_high|closeout_surface_touch|repeat_signature_hit|stale_evidence",
  "recommended_tier": "T0|T1_advisory|T2_advisory|T3_advisory|T3_certification",
  "advisory_only": true,
  "evidence_refs": [],
  "window": "5m|24h|3_sessions",
  "confidence": 0.0-1.0,
  "rationale": "short text"
}
```

## Loop Economy Rules

To prevent PUA-loop from burning expensive T3 calls unnecessarily:

1. **cheap pass**: Low risk + deterministic gates clear → T0/T1, skip T3
2. **mid audit**: Some disagreement → T2 advisory, collect evidence, then decide
3. **closeout gate**: Final done → T3 certification with 4/4 + evidence binding
4. **anti-burn**: Same task with unresolved severity>=3 for N rounds → pause T3, switch to targeted evidence-request loop
5. **quota-aware**: Low provider confidence → advisory uses cheap routing, T3 only when necessary

## Files Changed in This Session

| File | Change |
|------|--------|
| `post-session-autopsy.py` | +classify_failure_group, +recommend_autopsy_tier, +failure_class_counts, +recommended_tier |
| `brain_task_orchestrator.py` | +task_multimodel_advisory_reasons, +task_multimodel_certification_reasons, writeback advisory_only/certification_authority |
| `iteration_budget_doctor.py` | +--emit-signal, writes budget_signals.jsonl |
| `brain_task_dispatch_tick.py` | multimodel_summary surfaces advisory_reasons/certification_reasons/recommended_tier/advisory_only |
