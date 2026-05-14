---
name: taskpool-ingest-triage
description: Use when adding external links, notes, repo analyses, or decomposed implementation tasks into the taskpool; enforces pre-ingest triage, priority stratification, dependency capture, and execution-order metadata at creation time.
---

# Taskpool Ingest Triage

## Blocked multi-model workflow diagnostics

When asked why taskpool/workflow items are `blocked` or whether they will automatically complete, use `references/blocked-multimodel-diagnostics.md`.
When asked why the pool has active work but no task is currently in progress, use `references/taskpool-autostart-and-gating.md`.

When users say there is "no task in progress" or ask why nothing is actively running, use `references/no-in-progress-diagnosis.md`. The durable pattern is that the pool may still contain active `pending`/`blocked` work while dispatch tick is failing governance gates (especially proof/evidence checks), so verify list/dashboard state, dynamic-runner logs, direct tick output, eligibility, and manual autorun handoff before concluding the pool is empty. Key rule: inspect `brain_task_orchestrator.py list --include-done --json` (`rows`), then distinguish ordinary dependency/claim blocks from multi-model ratification-gate blocks. For `dispatchable=false` + `multimodel_status=not_certified`, do not promise automatic `done`; verify dynamic worker/cron intervention and report the exact missing votes, consensus failures, or constrained-best gaps.

Use this when:
- The user sends repo/article links and wants them added to the taskpool
- A parent task is being decomposed into child tasks
- Work should enter the pool as a governed execution unit rather than a raw inbox item
- The user wants the taskpool to stay independent from later ad hoc re-triage
- The user asks why the pool has active tasks but nothing is in progress, or why no task auto-advanced to `claimed`/`running`

## Core rule

Do not treat task creation as raw capture.
Before or during `brain_task_orchestrator.py add`, convert the input into a governed task record with:
- P1/P2/P3 priority already decided
- dependency / sequencing intent already decided
- architecture target already decided
- multimodel triage rationale already decided for high-leverage items
- parallel boundary and acceptance boundary already stated when decomposition is involved

## Required ingest sequence

1. Classify the incoming work
   - External repo/article/reference to analyze
   - Parent task being split into child tasks
   - Direct implementation / audit task
   - Advisory / observation-only candidate

2. Run pre-ingest triage before formal add
   For external links and strategy-facing tasks, determine before creation:
   - Strategic leverage on Hermes/taskpool/control-plane
   - Near-term executability
   - Architectural landing zone
   - Overlap with existing tasks
   - Whether the item is true P1, normal P2, or reserve P3

3. Decide P1/P2/P3 at creation time
   Use a simple gate:
   - P1: directly changes core control-plane, taskpool, permission, context, prompt assembly, orchestration, recoverability, or another strong lever on overall completion/stability/cost
   - P2: clearly useful and actionable, but not first-batch leverage
   - P3: backlog/reserve/observation value; worth keeping but not immediate

4. Capture execution structure at creation time
   When creating decomposed tasks, decide and encode:
   - Which task must happen first
   - Which tasks can run in parallel
   - Which tasks are blocked by earlier outputs
   - Which task is packet/schema/protocol first and which is automation/state-machine later

5. Use workflow-contract fields intentionally
   At minimum review/populate these frontmatter fields when applicable:
   - `workflow_contract`
   - `required_authority`
   - `permission_tier`
   - `completion_gate`
   - `parallel_boundary`
   - `architecture_target`
   - concepts / capability_delta / anti_drift_check / acceptance_evidence

6. Add tasks only after the above decisions exist
   The pool should store governed tasks, not raw materials.

## Decomposition rule

When splitting one topic into multiple tasks, prefer this pattern:
- schema/packet definition first
- protocol/integration second
- automation/control-flow third

This avoids creating downstream tasks whose inputs are undefined.

Example from budget-handoff work:
1. Define continuation packet schema
2. Define `/new` + `prefill_messages` resume protocol
3. Define automatic handoff / fallback state machine

## Multimodel triage guidance

For external repo/article ingest or high-impact architecture work:
- Perform fixed multimodel triage before add, not after add
- Record the result in the task framing/rationale or supporting evidence
- Treat “triggered multimodel” and “passed/converged multimodel” as different states; do not mistake trigger statistics for completed analysis

### External repo ingest pattern

For GitHub repos, do a minimum evidence pass *before* `add`:
- fetch repo metadata (description, language, stars/forks/issues, topics)
- read README or equivalent project positioning text
- search the taskpool for existing mentions/duplicates
- produce three explicit judgments before creation:
  1. priority tier (P1/P2/P3) and why
  2. Hermes architectural landing zone (`local-brain` / `taskpool` / `control-plane` / other) and why
  3. anti-drift / acceptance / boundary constraints so the task does not turn into a generic industry survey

When the repo is a coding-agent / harness / orchestration project, prefer framing the created task around **what Hermes should absorb** (gap map, leverage points, smallest closure slice, execution order) instead of a broad repo summary.

### Add-command return-code pitfall

If `brain_task_orchestrator.py add` returns an event-hook nonzero such as `returncode=2`, do not assume the task failed to enter the pool. Verify the actual result payload and task note existence first. If the task file exists and the payload points at the created `next_task_id`, treat it as an ingest success with hook noise, not a missing task.

## References

- `references/multimodel-blocked-resolution.md` — repair pattern for tasks that remain `blocked` after multimodel certification passes because stale failed `evidence:` entries violate proof-gate shape.
- `references/non-convergence-auto-narrowing.md` — when a task is blocked by multimodel `loop_non_convergence`, preserve the parent objective and create a narrowed precondition child task instead of rewriting the parent into an easier but drifted target.

## Non-convergence blocked-task split rule

When a high-leverage task is `blocked` with multimodel signals like `multimodel_status=not_certified`, `multimodel_last_decision=CONTINUE_LOOP`, `agreement_below_threshold:*`, or `certification_intent=unresolved_noop_vs_change`, do **not** solve it by silently rewriting the parent task into an easier version.

Use this recovery pattern instead:
1. Keep the parent task as the canonical objective.
2. Extract the disagreement axis from the discussion artifact: typically `framing`, `approach`, `implementation_order`, or `noop_vs_change`.
3. Create one or more **precondition child tasks** whose sole purpose is to make the parent ratifiable again.
4. Record in the parent task's `Blockers / Confusions` that the block is `loop_non_convergence` and that the new child task(s) are front-loaded dependencies.
5. Add a `Proof Log` note in the parent that the unblock child task was created and should be executed before resuming the parent.
6. Narrow child tasks by axis, not by convenience: e.g. `quota observability`, `fallback threshold semantics`, `continuation packet / relay ordering`, or `patch normalization`.
7. Re-run ratification only after the child task produces a narrowed brief or evidence packet.

### Automation support

If the orchestrator has the `auto-split-non-convergence` command, prefer using it before hand-authoring child tasks.

Operational notes from the first implementation:
- Read the actual discussion artifact shape before classifying splits. In real `discussion_result.json` files, the decisive fields may live under `final_design.planner_patch_summary`, `final_design.merge_info`, and `final_design.quota_snapshot`, not only at the top level.
- Good split triggers include:
  - `agreement_matrix` dimensions below threshold
  - `final_design.merge_info.minority_patches` containing `quota`, `threshold`, or `relay` patches
  - `final_design.planner_patch_summary.certification_intent=unresolved_noop_vs_change`
  - low-confidence or `unknown`/`unobservable` entries inside `quota_snapshot`
  - unresolved `issue_ledger` IDs
- The automation must be **parent-preserving and idempotent**:
  - preserve the parent objective unchanged
  - write `auto_subtask_children` / `auto_subtask_kind` on the parent
  - update parent `Proof Log` and `Blockers / Confusions`
  - on rerun, create only missing subtasks instead of duplicating existing ones
- For budget-handoff style failures, the default three-way split is:
  1. quota observability
  2. fallback threshold semantics
  3. relay ordering

See `references/non-convergence-auto-narrowing.md` for the concrete artifact layout and command behavior.
See also `references/non-convergence-closure-loop.md` for the parent-reopen closure loop, taxonomy-driven axis selection, and blocked-resolve-step integration.

### Closure-loop escalation rule

When `loop_non_convergence` persists, treat it as a lifecycle problem, not just a split problem. The expected closure loop is:
1. `blocked-resolve-step` detects `loop_non_convergence` on a blocked parent and triggers `auto-split-non-convergence` when no narrowed children exist yet.
2. Child tasks must persist `auto_subtask_parent` and `auto_subtask_issue_ids` so the parent can be recovered without goal drift.
3. `reconcile` and `auto-subtask-sync --write` are the canonical parent-refresh paths; once all narrowed children are `done`, a blocked parent should automatically reopen to `pending`.
4. `blocked-resolve-step` should then report either `await_auto_subtasks` or `auto_subtask_parent_reopened` rather than leaving the parent in an ambiguous blocked state.

### Taxonomy-first narrowing rule

If the latest discussion artifact has weak or empty `issue_ledger`, do not fall back to a vague framing-only split. First derive a multimodel failure taxonomy from discussion failures and use it to recommend split axes. Durable mapping from this session:
- `agreement_low` -> `relay_ordering`
- `criteria_missing` and `loop_non_convergence` -> `fallback_threshold`
- `quota_unobservable` / `evidence_missing` / `no_claims` -> `quota_observability` (and sometimes `framing`)
- `final_design_missing` / provider parse problems -> `patch_normalization`
- `model_vote_missing` / `vote_reject` -> `framing`

Expected automation behavior:
- write parent-level `auto_subtask_taxonomy_axes`
- return `taxonomy_axes` and `axis_rationale` from `auto-split-non-convergence --json`
- write task-level `multimodel_recommended_axes` during PUA-loop result writeback so later split/reconcile passes reuse the same semantics

## Pitfalls

- Fixing convergence by changing the parent's goal instead of preserving it and splitting out a prerequisite child task.
- Creating a vague 'follow-up analysis' task that mixes multiple disagreement axes; split by one axis per child when possible.
- Treating `loop_non_convergence` as a scheduler failure; it is usually an evidence/framing failure.
- Re-running full multimodel discussion without first extracting the disagreement taxonomy from the last discussion artifact.

## Pitfalls

- Adding everything as P2 and promising to reorder later
- Creating child tasks without dependency/order semantics
- Treating taskpool as an inbox instead of a governed queue
- Leaving `parallel_boundary` blank on obviously serial vs parallelizable decompositions
- Deferring multimodel priority analysis until after the task is already in the pool
- Assuming a workflow contract exists means the ingest path already enforces it

## Verification

Before finishing, verify:
- Priority was decided before/at add time
- Child tasks have a clear recommended execution order
- Any P1 architecture task has a stated reason it is P1
- The created task text reflects dependency/parallel intent where relevant
- If the user challenged the ingest workflow, the fix was captured in the task formulation rather than only in chat

## Reference

See `references/taskpool-ingest-checklist.md` for a concise pre-add checklist and dependency-order heuristics.