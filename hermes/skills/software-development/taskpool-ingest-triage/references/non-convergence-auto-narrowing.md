# Non-convergence auto-narrowing for blocked taskpool items

Use when a task is blocked after repeated multimodel rounds with signals such as:
- `multimodel_status: not_certified`
- `multimodel_last_decision: CONTINUE_LOOP`
- `agreement_below_threshold:framing|approach|implementation_order`
- `certification_intent: unresolved_noop_vs_change`
- repeated `review -> retry -> blocked` closeout loops

## Core rule

Do not rename or weaken the parent objective just to obtain convergence. Keep the parent as the canonical goal and create a precondition child task that narrows one disagreement axis.

## Recommended split axes

1. **Framing split**
   - Separate observability / diagnosis from orchestration / handoff.
   - Example: budget-exhaustion work usually mixes quota observability, fallback policy, and continuation relay into one oversized question.

2. **Approach split**
   - Resolve `noop_vs_change` before debating full implementation.
   - Ask a child task to prove whether a concrete patch is actually needed, with file evidence.

3. **Implementation-order split**
   - Force sequence: observability/state semantics first, thresholds/policy second, relay protocol third.

4. **Patch normalization split**
   - When one model proposes concrete patches and others stay at noop/advice level, create a child task that converts candidate patches into a normalized evidence packet with exact files, rationale, rollback, and verification.

## Parent-task writeback requirements

Update the blocked parent task with:
- `Blockers / Confusions`: state that the block is `loop_non_convergence`, not scheduler failure.
- dependency note: child task(s) must run before parent resumes.
- `Proof Log`: record the child-task creation timestamp and intent.

## Example taxonomy from a real blocked budget-handoff task

Observed disagreement pattern:
- `framing=0.65`: task mixed quota observability, fallback thresholds, and continuation relay.
- `approach=0.65`: one model proposed concrete patches; three models stayed noop/advisory.
- `implementation_order=0.65`: no agreement on whether to do quota probe, threshold semantics, or relay ordering first.
- final discussion showed `certification_intent=unresolved_noop_vs_change`.

Recommended child tasks:
- quota observability first
- fallback threshold semantics
- continuation packet / relay ordering
- patch normalization / evidence packet if concrete patches exist but were dropped from the merged plan

## Real artifact layout pitfall

Do not assume the actionable split signals are top-level fields.
In the real budget-handoff artifact, the useful fields were:
- top level: `agreement_matrix`, `issue_ledger`, `quota_snapshot`
- nested under `final_design`:
  - `final_design.planner_patch_summary`
  - `final_design.merge_info`
  - `final_design.quota_snapshot`

Important concrete clues:
- `final_design.planner_patch_summary.certification_intent = unresolved_noop_vs_change`
- `final_design.merge_info.minority_patches` contained `P-001-quota-probe`, `P-002-relay-ordering`, `P-003-fallback-thresholds`
- `final_design.quota_snapshot` contained per-model observability/confidence entries rather than one summary boolean
- unresolved issue IDs were recoverable from `issue_ledger` when `final_decision.unresolved_issue_ids` was absent

## Automation command behavior

A durable implementation pattern for the orchestrator command `auto-split-non-convergence`:
1. Load the parent task's `multimodel_last_discussion_artifact` JSON.
2. Derive split specs from the real artifact layout above.
3. Classify unresolved issues into explicit axes such as:
   - `quota_observability`
   - `fallback_threshold`
   - `relay_ordering`
   - `patch_normalization`
   - fallback `framing`
4. Create narrowed child tasks with parent-binding metadata, not just titles. Useful fields:
   - `auto_subtask_parent`
   - `auto_subtask_kind: non_convergence_narrowing`
   - `auto_subtask_axis`
   - `auto_subtask_trigger`
   - `auto_subtask_issue_ids`
   - `auto_subtask_parent_artifact`
5. Preserve the parent objective and append — not overwrite — parent `Proof Log` while updating `Blockers / Confusions`.
6. Make the command idempotent: if one child already exists, create only the missing children on rerun.

## Parent re-entry / closure loop

The split is only half the workflow. Also implement a parent-sync path (for example `auto-subtask-sync`, or integration into `reconcile`) that:
- reads `auto_subtask_children`
- computes `auto_subtask_open_children`
- writes `auto_subtask_ready_for_parent`
- updates `Blockers / Confusions` to say whether children remain open or all are done
- appends a progress line to `Proof Log`
- if the parent is still `blocked` and every child is terminal/done, re-open the parent to `pending` so ratification can re-run

This closes the `loop_non_convergence -> narrowed child -> child done -> parent re-entry` chain instead of leaving completed child tasks disconnected from the blocked parent.

## Anti-drift guard

A narrowed child task is valid only if it clearly states:
- which parent task it unblocks
- which disagreement axis it isolates
- what evidence artifact it must produce for the parent
- that the parent objective remains unchanged
