# Advisory-only multimodel PASS consumption

Use this when taskpool multimodel intervention produces an advisory-only PASS for weak triggers (for example `P0_priority`, `closeout_ratification`, `architecture_target`, `accuracy_keyword`) but the task has no certification authority reasons.

## Durable lesson

Advisory rounds are not closeout authority, but a successful advisory-only round should still consume the weak trigger. Otherwise the scheduler repeatedly queues the same already-reviewed advisory task, wasting model budget and obscuring genuinely new certification work.

## Correct state model

When an advisory-only plan receives a normal `PASS + LOOP_DONE` from the ratification gate:

1. Rewrite/persist it as `PASS_ADVISORY_ONLY` with `decision: continue_loop`.
2. Write task frontmatter:
   - `multimodel_status: advisory_completed`
   - `multimodel_round_status: advisory_passed`
   - `multimodel_advisory_only: true`
   - `multimodel_certification_authority: false`
   - `multimodel_last_discussion_artifact: <discussion_result.json>`
3. Do not write `multimodel_ratification_artifact`, and do not make `task_multimodel_passed()` return true.
4. Suppress future weak advisory triggers once this state exists.
5. Do not suppress strong certification triggers. `stale_claim`, `p0_evolution_blast_radius`, and `loop_non_convergence` must still re-trigger intervention.

## Regression shape

Add a taskpool regression test that:

- Creates a P1 evolution task with weak advisory triggers only.
- Asserts intervention is required before writeback.
- Calls `write_multimodel_result_to_task()` with `{"status": "PASS_ADVISORY_ONLY", "decision": "continue_loop"}`.
- Asserts the task is not certified, advisory is completed, and future weak triggers are consumed.
- Mutates `retry_count >= 2` and asserts `loop_non_convergence` still triggers.

## Verification commands

```bash
cd ~/.hermes
python3 -m py_compile scripts/brain_task_orchestrator.py scripts/test_brain_task_orchestrator.py
python3 scripts/test_brain_task_orchestrator.py
python3 scripts/self-test.py
python3 scripts/brain_task_orchestrator.py multimodel-intervention-dry-run --task <task-id> --json
```

## Pitfalls

- Do not mark advisory-only work as `certified`; that turns model agreement into unauthorized closeout authority.
- Do not leave advisory-only PASS as ordinary `not_certified failed`; that creates repeat queue churn.
- Do not suppress strong triggers just because an advisory result exists.
- Avoid piping huge JSON CLI output into a downstream parser that exits early; it can produce a `BrokenPipeError` in the producer. Capture output first or parse via a small Python wrapper that reads the full stream.
