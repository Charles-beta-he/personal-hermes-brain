# Taskpool review closeout evidence-shape normalization

Use this when a task is `status: review` or was recently `blocked`, multimodel fields now show `certified / PASS / LOOP_DONE`, but `auto-close-review` still skips it with `invalid evidence shape` or similar proof-gate failures.

## Symptoms

- `auto-close-review --json` returns `skip` with failures containing `invalid evidence shape`.
- The task frontmatter already shows current multimodel state such as:
  - `multimodel_status: certified`
  - `multimodel_last_gate_status: PASS`
  - `multimodel_last_decision: LOOP_DONE`
- `evidence:` still contains legacy bare entries like:
  - `multimodel_gate:FAIL`
  - `multimodel_status:not_certified`
  - `multimodel_decision:CONTINUE_LOOP`
  - `multimodel_auto_outcome:certification_failed`

## Repair sequence

1. Read the task note and confirm the **current** multimodel fields, not just historical evidence.
2. If the current state is certified/PASS/LOOP_DONE, remove or normalize stale failed evidence entries.
3. Keep the latest ratification artifact and proof items; do not preserve obsolete FAIL markers just because they are historical.
4. Prefer structured evidence only:
   - `proof:sha256:...`
   - `command:...`
   - `artifact:...`
5. Re-run:
   ```bash
   python3 ~/.hermes/scripts/brain_task_orchestrator.py auto-close-review --task '<task-id>' --actor hermes --authority autonomous-execution --json
   ```
6. Verify with:
   ```bash
   python3 ~/.hermes/scripts/brain_task_orchestrator.py list --include-done --json
   ```

## Prevention at the source

If the orchestrator itself writes multimodel diagnostic evidence during retries/closeout, emit structured entries from the start:

- `command:multimodel_gate FAIL`
- `command:multimodel_decision CONTINUE_LOOP`
- `command:multimodel_status not_certified`
- `command:multimodel_auto_outcome certification_failed`

Do **not** write bare `multimodel_*:...` lines into `evidence:`. They can poison later `review -> done` closeout even after certification eventually passes.

## Key rule

For closeout, frontmatter fields describe **current authority state**; `evidence:` must also be syntactically valid for proof-gated lifecycle transitions. Historical failed markers are useful only if they remain in a legal evidence shape or are moved into proof log/body text instead of the active `evidence:` list.
