# Hermes Taskpool Closeout Recovery Pattern

Use when a session is resumed with “继续 / 检查任务池进度” and prior context may be compacted or tool budget is tight.

## Fast recovery sequence

1. Refresh/read the taskpool state before acting:
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write --json`
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py next --reconcile --json`
2. If the next task already has a target-bound `multimodel_ratification_artifact` or `multimodel_last_discussion_artifact`, run the gate explicitly before closeout:
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py ratification-gate --task <task_id> --discussion-result <artifact> --json`
3. Only close tasks through lifecycle transitions, never by editing markdown status directly:
   - `claim` if needed
   - `transition <task> --to running`
   - `transition <task> --to review --evidence ...`
   - `done <task> --evidence ...`
4. After every closeout batch, run and fix deterministic gates:
   - `proof-check --json`
   - `selfcheck --json`
   - `dashboard --write --json`

## Evidence hygiene

`proof-check` treats bare file paths in frontmatter `evidence:` as unstructured evidence. Use typed prefixes:

```yaml
evidence:
  - artifact:/absolute/path/to/discussion_result.json
  - proof:ratification-gate PASS; selfcheck PASS; proof-check PASS
```

If proof-check fails on an existing task because older evidence rows are bare paths, patch those rows to `artifact:/...`, then rerun `proof-check` and `selfcheck` before continuing. Subagents may add bare evidence paths while producing reports; the controller must normalize those rows before final proof/selfcheck/dashboard gates.

After `done`, some list-style taskpool commands may omit completed tasks from `rows`. Do not interpret a missing row or `status=None` from `list --json` as failed closeout. Verify completed targets by reading the canonical task Markdown frontmatter directly and checking `status: done` plus typed `artifact:` / `proof:` evidence.

## Advisory-only multimodel results

If the task says:

```yaml
multimodel_last_gate_status: PASS_ADVISORY_ONLY
multimodel_last_decision: CONTINUE_LOOP
multimodel_certification_authority: False
```

then the result is provenance only. Do not transition to `done` from advisory evidence alone. Continue deterministic implementation/verification and obtain a target-bound closeout gate before done.

Advisory-only taskpool interventions should route as advisory, not closeout certification:

- `build_multimodel_intervention_plan(task)` should set `advisory_only: true` when advisory reasons exist and `certification_reasons` is empty.
- The generated `run_discussion_command` should use the recommended advisory tier (`--tier T1` or `--tier T2`) and must not force `--tier T3 --quorum 4` for advisory-only work.
- The loop mode should be explicit, e.g. `advisory_until_signal_consumed`: a passing advisory round records/consumes the weak trigger (`PASS_ADVISORY_ONLY`) but never authorizes `LOOP_DONE` or `done`.
- Reserve target-bound `T3 --quorum 4` ratification for strong certification triggers and actual closeout authority.

## Economy-pause targeted evidence closeout

When `claim` / `transition` reports `multimodel_streaming.reason: economy_pause` after repeated failed T3 rounds, do not keep re-running T3 or fabricate certification. Treat the pause as a directive to land a targeted deterministic evidence fix:

1. Inspect the latest `multimodel_last_discussion_artifact` and issue ledger to find the concrete blocker (for example, `unresolved_noop_vs_change`, missing participant, or low agreement).
2. Resolve the blocker with local evidence: reproduce on a historical diff, add/adjust tests, write a concise brain artifact, or update the governing skill/reference.
3. Close only through lifecycle commands: `claim` → `transition --to running` → `transition --to review --evidence ...` → `done --evidence ...`.
4. Preserve multimodel provenance in frontmatter if it remains `not_certified` / advisory-only; do not rewrite it to certified unless a target-bound ratification gate actually passes.
5. Verification before reporting: task-specific tests, `self-test.py` when Hermes scripts changed, `proof-check --include-active`, `selfcheck`, `dashboard --write`, and `multimodel-intervention-dry-run` to confirm the paused queue is drained.

Closeout authority in this pattern is `selfcheck-review-done` plus typed deterministic evidence, not the stale failed T3 artifact.

## Noop-vs-change disagreement handling

When multi-model output shows one model proposing concrete patches (often MiMo) while the other models vote noop/no-change, do not collapse this into `implementation_required` and do not claim the merge layer "dropped" patches just because `current_best.patches` is empty. Treat it as an explicit unresolved disagreement:

```json
{
  "certification_intent": "unresolved_noop_vs_change",
  "concrete_model_count": 1,
  "noop_only_model_count": 3,
  "models_with_concrete_patches": ["mimo-v2.5-pro"]
}
```

The next loop action is to resolve the issue ledger: either corroborate and accept the concrete patches, or downgrade them to advisory/noop with evidence. This avoids a false blocker where models debate an `implementation_required`/empty-patches contradiction instead of the real noop-vs-change split.

## Tool/context budget closeout

If max tool calls or context compaction interrupts the loop, final response must be a recovery handoff, not a completion claim. Include:

- current claimed task id and status
- latest discussion/tick artifact
- gates already run and their result
- gates not yet run
- exact next commands or validation class
- explicit warning when advisory-only evidence cannot authorize done
