---
name: multi-model-certification-round
description: "Evaluate a multi-model certification packet (Round N) and produce structured vote output."
triggers:
  - "multi_model_comm_packet_v1 with mode manifest_delta"
  - "certification round vote request"
---

# Multi-Model Certification Round Protocol

When receiving a `multi_model_comm_packet_v1` with `mode: manifest_delta`:

## Decision Framework

1. **Check round_delta.unresolved_issues** -- if non-empty, these MUST be addressed before approving
2. **Check truth_gate** -- `can_certify_truth` must be true; all claims must be `verified_by_evidence`
3. **Check certification_intent** from planner_patch_summary:
   - `no_action_certification` + `concrete_patch_count == 0` → empty patches list is NOT a blocker (planners explicitly signed off with noop)
   - `unresolved_noop_vs_change` → do NOT claim patches were dropped; resolve the ledger first
4. **Check evidence coverage** -- `evidence_coverage` should be 1.0
5. **Identify novel severity >= 3 blockers** -- only discuss these, not resolved/repeated issues

## Vote Logic

- **approve**: truth gate permits, no unresolved issues, no novel blockers, `best_within_constraints: true`
- **amend**: specific corrections needed (cite evidence IDs)
- **reject**: fundamental blocker that cannot be amended

## Output Format

```
critiques: [{target_model, severity (1-5), claim, evidence ref, correction, novel: bool}]
evidence_requests: [{claim_id, tool_needed, command, why}] (only if omitted detail needed)
vote: approve|amend|reject
best_within_constraints: true|false
reasoning: <=600 chars, cite issue/evidence IDs
```

## Key Pitfalls

- NEVER assume omitted payload bodies; use evidence_requests if detail needed
- NEVER claim patches were dropped when certification_intent explains why patches list is empty
- Empty unresolved_issues means no blockers from prior rounds to carry forward
- Previous round "amend" votes may have been resolved; re-evaluate independently
