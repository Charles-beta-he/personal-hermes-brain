# Ratification Gate Pattern

Use this when a user asks for multi-model ratification/certification, especially after deterministic local checks already pass.

## Core lesson

Do not wrap an existing deterministic completion in a certification narrative. Treat deterministic output as evidence only. Certification is a lifecycle transition controlled by a target-bound ratification gate.

## Required artifact chain

1. Deterministic evidence gate
   - Run local selfcheck/test/audit commands.
   - Keep command, exit code, and output summary.
2. Claims/evidence bundle
   - Put every severity>=3 factual claim in `claims`.
   - Put every supporting observation in `evidence`.
   - Every high-severity claim must have explicit `supports: [claim_id]` links.
   - Failed commands can be evidence of failure states, but must not support success claims.
3. Issue ledger
   - Every blocker has `id`, `severity`, `status`, `resolution`, and `evidence_ids`.
   - `severity >= 3` must be `resolved` or `accepted_risk` before certification.
4. Scoped discussion artifact
   - A valid `discussion_result.json` (or equivalent) must be target-bound to the exact project/task.
   - Required binding fields should be explicit task identifiers/paths, e.g. top-level or nested `task_id`, `target_task_id`, `selected_task_id`, `source_task_id`, `canonical_task_id`, `task_path`, `target_task_path`, or `canonical_task_path`.
   - Treat implementation target file paths as insufficient binding: they prove touched code, not which task the certification belongs to.
   - Do not let a default gate pick up an unrelated latest `tick-*/discussion_result.json`.
5. Ratification gate
   - Fail closed on missing/unreadable/unscoped artifact, mixed/mismatched binding candidates, or stale artifacts from another task.
   - Check deterministic PASS, certified discussion status, exact participant identity, vote count, agreement matrix, truth gate, open issue ledger, and remaining risks.
   - For this user's task/Lark closeout policy, `certified` requires all 4 canonical models (`claude-opus-4-7`, `gpt-5.5`, `deepseek-v4-pro`, `mimo-v2.5-pro`). Do not lower requirements from self-attested `models_consulted`; `3/4` is `not_certified` for closeout even if quorum text says pass.
6. Status transition
   - Only the gate may promote final status to `FULLY_CERTIFIED` / `CERTIFIED`.

## Recommended status split

```json
{
  "matrix_status": "A_PLUS_MATRIX_COMPLETE",
  "deterministic_gate_status": "PASS|FAIL",
  "ratification_status": "NOT_STARTED|NOT_CERTIFIED_NO_ARTIFACT|NOT_CERTIFIED_TIMEOUT|CERTIFIED|CERTIFIED_WITH_MINOR_RISKS",
  "final_integration_status": "LOCAL_COMPLETE_UNRATIFIED|FULLY_CERTIFIED|CERTIFIED_WITH_MINOR_RISKS|BLOCKED"
}
```

## Gate checks — dual-shape support

The gate must accept two canonical output shapes from `consult_models.py`:

### Shape A: Explicit criteria (legacy/structured)

When the discussion result has top-level `criteria_satisfied` and a `final_design` with explicit next-slice fields:

- `discussion_result.json` exists and is scoped to the target.
- `status in {certified, certified_with_minor_risks}`.
- `agreement_matrix.framing/approach/implementation_order >= 0.85`.
- approval votes are at least `N-1`, reject votes are zero.
- every vote has `best_within_constraints: true` unless explicitly accepted as a minor risk.
- `truth_assessment.can_certify_truth == true`.
- no `unsupported_high_severity_claim_ids`.
- no unresolved severity>=3 issue in `issue_ledger`.
- no severity>=3 item in `remaining_risks`.
- `criteria_satisfied.accuracy == true`.
- `criteria_satisfied.long_term_goal == true`.
- `criteria_satisfied.one_shot_landing == true`.
- `final_design.next_slice` is non-empty.
- `final_design.acceptance_evidence` is a non-empty list.
- `final_design.rollback_boundary` is non-empty.
- `final_design.long_term_goal_alignment == true`.

### Shape B: Derived from consult_models discussion output

When `criteria_satisfied` is missing, derive from the actual `consult_models.py run --discussion` output structure:

- `status: certified` (top-level) ✅
- `ratification_votes`: 4 canonical models all approve with `best_within_constraints: true` ✅
- `agreement_matrix`: all axes >= 0.85 ✅
- `issue_ledger`: empty or all severity>=3 resolved ✅
- **truth gate**: check nested locations — `discussion.truth_status`, `discussion.truth_assessment.truth_status`, or `discussion.final_design.truth_assessment.truth_status`. Reject `not_certified/unsupported/contradicted/no_claims`.
- **accuracy**: `final_design.evidence_bundle.grounding` — all claims must have `truth_status: verified_by_evidence`.
- **long_term_goal**: `final_design.fanout_certification.multi_model_certified == true`, OR fall back to `status in MULTIMODEL_PASS_STATUSES`.
- **one_shot_landing**: `final_design.verification.guard_metrics` is a non-empty list.
- **final_design structure**: must have EITHER (Shape A: next_slice + acceptance_evidence + rollback_boundary) OR (Shape B: diagnosis + verification + rollback_signal with `auto_rollback_if`).

### Important pitfalls

- Do NOT require `criteria_satisfied` to exist — Shape B is the more common output from `consult_models.py`.
- `truth_status` is often nested, not top-level. Check 3 levels deep.
- `final_design` from consult_models has `diagnosis/verification/rollback_signal`, NOT `next_slice/acceptance_evidence/rollback_boundary`. Accept both shapes.
- `rollback_signal.auto_rollback_if` is advisory (warning if missing); `verification.guard_metrics` is required (failure if missing).
- Degraded fanout/quorum/timeouts remain provenance only; they cannot certify.

## Target-binding and model-count regression tests

When hardening a local ratification gate, add RED tests before implementation for these cases:

- good artifact for the expected task should PASS;
- artifact with a different top-level `task_id` or nested `context.task_id` must FAIL;
- artifact that contains both a matching and a mismatching explicit task binding must FAIL (mixed bindings are contamination, not success);
- artifact with only implementation files but no explicit task id/path must FAIL when an expected task is supplied;
- closeout artifact with only 3 of the 4 canonical models must FAIL for this user's certification policy, including both `models_consulted` and `ratification_votes` mismatches;
- CLI commands such as `brain_task_orchestrator.py ratification-gate --task TASK --discussion-result ARTIFACT --json` must pass the resolved expected task into the verifier, not call the verifier without target context.

A useful failure taxonomy includes `target_task_binding_missing`, `target_task_mismatch:<id-or-stem>`, `model_count_below_required:N/4`, `missing_required_model_vote:<model>`, and `missing_required_model_consulted:<model>`.

## Handling model/provider degradation

If a T3/four-model run degrades because one provider is unavailable or planners time out:

- Preserve the degraded artifact as provenance.
- Do not call it certification.
- If user wants “no follow-up suggestions” and the missing provider is an availability issue rather than an epistemic dissent, rerun an available-model tier (for example T1 with 3 providers) with the same evidence bundle.
- Certification may use the available-model artifact only if it is explicitly scoped, quorum succeeds, the gate passes, and the final writeup states which higher-tier attempt degraded.

## TDD pattern for local gates

Before implementing the gate, add tests that fail for:

- selfcheck not exposing status split;
- missing discussion artifact;
- unrelated latest tick artifact;
- certified artifact with unresolved severity>=3 issue;
- certified artifact with insufficient votes or low agreement;
- clean certified artifact that should pass.

Then implement the smallest gate that makes these pass.

## Local brain landing checklist

For local-brain tasks, write or update:

- canonical dashboard/contract;
- evidence bundle JSON;
- issue ledger JSON;
- ratification decision note;
- proof/task log;
- review log;
- evolution log;
- scoped local git commit after sync/reindex/search/audit.

Keep the canonical brain artifact stable; runtime tick directories are provenance, not the source of truth.
