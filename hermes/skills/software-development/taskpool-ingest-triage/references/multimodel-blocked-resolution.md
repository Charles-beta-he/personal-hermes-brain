# Multimodel blocked-resolution pattern

Use this when taskpool items are `status: blocked` even though multimodel analysis appears to have succeeded.

## Symptoms

- Task rows show `multimodel_status: certified`, `multimodel_last_gate_status: PASS`, `multimodel_last_decision: LOOP_DONE`, but `status` remains `blocked`.
- `blocked-resolve-step --force --json` returns `keep_blocked_gate_failed`.
- Failure text mentions invalid evidence shape, commonly stale entries such as:
  - `multimodel_gate:FAIL`
  - `multimodel_decision:CONTINUE_LOOP`
  - `multimodel_status:not_certified`
  - `multimodel_auto_outcome:certification_failed`

## Repair sequence

1. Refresh task state:
   ```bash
   python3 ~/.hermes/scripts/brain_task_orchestrator.py list --include-done --json > /tmp/tasklist.json
   ```
2. Confirm current multimodel fields in task frontmatter or list output:
   - `multimodel_status: certified`
   - `multimodel_last_gate_status: PASS`
   - `multimodel_last_decision: LOOP_DONE`
   - `multimodel_last_failures: []`
   - `multimodel_ratification_artifact` points at an existing artifact.
3. If evidence still contains stale failed multimodel markers, replace them with legal evidence prefixes that reflect current state:
   ```yaml
   - command:multimodel_gate PASS
   - command:multimodel_decision LOOP_DONE
   - command:multimodel_status certified
   - command:multimodel_auto_outcome certification_passed
   ```
   Do not leave bare `multimodel_*:...` evidence entries; proof gate requires prefixes such as `command:`, `file:`, `artifact:`, `proof:`, etc.
4. Re-run blocked resolver for each affected task:
   ```bash
   python3 ~/.hermes/scripts/brain_task_orchestrator.py blocked-resolve-step --task '<task-id>' --actor hermes --authority autonomous-execution --force --json
   ```
5. If tasks enter `review`, run review closer:
   ```bash
   python3 ~/.hermes/scripts/brain_task_orchestrator.py auto-close-review --json
   ```
6. Verify final state:
   ```bash
   python3 ~/.hermes/scripts/brain_task_orchestrator.py list --include-done --json
   ```

## Pitfall

Do not assume a successful multimodel certification automatically clears `blocked`. The resolver also validates the `evidence:` list. Stale failed evidence can keep tasks blocked after certification has passed.
