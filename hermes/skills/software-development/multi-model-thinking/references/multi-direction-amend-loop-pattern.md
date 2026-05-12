# Multi-Direction Amend Loop Pattern

Session: 2026-05-10 — 3-direction ratification (Agent Team + Kanban Watch + Missions Task Pool)
Result: Round 1 Dir1+Dir2 pass, Dir3 amend → Round 2 Dir3 pass → Round 3 consolidated confirm → FINAL_CERTIFIED

## Pattern

When ratifying multiple independent decisions in one pass, some directions may pass while others get `amend` votes. The correct workflow is NOT to re-run everything — it's to extract specific amend feedback, address it, and re-ratify only the amended direction.

### Step 1: Multi-Direction Ratification

Define `DIRECTIONS` list. Each direction gets its own vote field in the response schema:

```python
DIRECTIONS = ['direction_1_agent_team', 'direction_2_kanban_watch', 'direction_3_missions']

PROMPT = f"""...
Required JSON: {{
  "direction_1_agent_team": {{"vote":"approve|amend|reject", "best_within_constraints":true|false, "reasoning":"..."}},
  "direction_2_kanban_watch": {{"vote":"approve|amend|reject", "best_within_constraints":true|false, "reasoning":"..."}},
  "direction_3_missions": {{"vote":"approve|amend|reject", "best_within_constraints":true|false, "reasoning":"..."}},
  "overall": {{"vote":"approve|amend|reject", "reasoning":"..."}}
}}
"""
```

### Step 2: Per-Direction Breakdown

```python
for d in DIRECTIONS:
    dir_approvals = sum(1 for v in successful if v['parsed'][d]['vote'] == 'approve')
    print(f"{d}: {dir_approvals}/{len(successful)}")
```

### Step 3: Extract Amend Feedback

When a direction gets `amend`, read the specific reasoning from amend voters:

```python
amend_voters = [v for v in successful if v['parsed'][direction]['vote'] == 'amend']
for v in amend_voters:
    print(f"{v['model']}: {v['parsed'][direction]['reasoning']}")
```

Common amend requests:
- Missing numeric guardrails (timeouts, retry caps, thresholds)
- Missing state source specification
- References that should be downgraded
- Missing human-in-the-loop escape hatches

### Step 4: Amend and Re-Ratify (Single Direction Only)

Amend the decision with specific values addressing each feedback point. Re-ratify ONLY the amended direction — do not re-run already-approved directions:

```python
DECISION_AMENDED = {
    'appetite_timeout': '30min',        # Claude asked for numeric default
    'max_retry': 3,                      # GPT asked for retry cap
    'human_escape': '2 block or 3 crash', # Both asked for escape trigger
    'state_source': 'SQLite envelope bus', # GPT asked for single source
}
# Re-ratify only direction_3_amended, not all 3 directions
```

### Step 5: Consolidated Confirmation

After all directions pass individually, run one final confirmation round where models confirm the merged results:

```python
CONSOLIDATED = {
    'direction_1': {'status': 'certified_four_model', 'round': 1},
    'direction_2': {'status': 'certified_four_model', 'round': 1},
    'direction_3': {'status': 'certified_four_model', 'round': 2},
}
PROMPT = f"Confirm: all directions certified. JSON: {{\"confirm\": true|false, \"reasoning\": ...}}"
```

## Why Not Re-Run Everything

- Already-approved directions should not be re-voted (avoids regression/flapping)
- Amend feedback is direction-specific; addressing it for one direction doesn't affect others
- Final confirmation round proves all 4 models agree on the consolidated state
- Saves tokens: re-ratifying 1 direction costs ~1/3 of re-ratifying all 3

## Artifact Naming

```
mm-ratification-{topic}-v1.json          # Round 1 (may have partial certification)
mm-ratification-{topic}-amend-v1.json    # Round 2 (amended direction only)
mm-ratification-{topic}-final-v1.json    # Consolidated confirmation
```

## Pitfalls

- **Don't flatten per-direction votes into a single approve/reject.** A 3-direction ratification where Dir1+Dir2 approve but Dir3 amends is `not_certified` overall, even though 2/3 directions passed.
- **Amend feedback must be specific.** "Needs more detail" is not actionable. Extract exact parameters requested (timeout values, retry counts, thresholds).
- **Final confirmation is NOT a rubber stamp.** If a model disagrees with the consolidated result, it can still reject. The confirm round verifies awareness, not just counts.
