# Non-convergence closure loop

Use this when a task is blocked by multimodel `loop_non_convergence` and you need the full parent->child->parent lifecycle, not just one-off child creation.

## Durable pattern

### 1. Split without drifting the parent
- Parent objective stays canonical.
- Child tasks are narrowing prerequisites only.
- Child frontmatter should include:
  - `auto_subtask_parent`
  - `auto_subtask_issue_ids`
  - `auto_subtask_axis`
  - optional `auto_subtask_trigger`

### 2. Prefer taxonomy-assisted axis selection
When `issue_ledger` is sparse, derive axes from multimodel failure taxonomy before splitting.

Practical mapping proven in session:
- `agreement_low` -> `relay_ordering`
- `criteria_missing` or `loop_non_convergence` -> `fallback_threshold`
- `quota_unobservable`, `evidence_missing`, `no_claims` -> `quota_observability`
- `final_design_missing` or provider parse failures -> `patch_normalization`
- `model_vote_missing`, `vote_reject` -> `framing`

Recommended machine-readable outputs:
- `taxonomy_axes`
- `axis_rationale`
- parent frontmatter `auto_subtask_taxonomy_axes`
- task writeback `multimodel_recommended_axes`

### 3. Close the lifecycle explicitly
The split is incomplete until the parent can be revived automatically.

Expected control-plane behavior:
- `blocked-resolve-step` on a blocked loop-non-convergence parent:
  - if no children exist yet -> `auto_split_non_convergence`
  - if children exist and are unfinished -> `await_auto_subtasks`
  - if all children are `done` and parent still blocked -> `auto_subtask_parent_reopened`
- `reconcile --write` and `auto-subtask-sync --write` should refresh parent status and blockers.
- Reopened parents move from `blocked` to `pending`, preserving the original objective for the next ratification pass.

## Verification checklist
- Parent objective unchanged after split.
- No duplicate children on rerun.
- Parent `Proof Log` preserved and appended, not overwritten.
- Parent `Blockers / Confusions` mentions narrowed convergence subtasks.
- All-child-done path reopens blocked parent to `pending`.
- JSON output includes axis hints so upper layers do not re-infer semantics.
