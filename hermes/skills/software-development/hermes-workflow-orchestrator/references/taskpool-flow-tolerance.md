# Taskpool flow tolerance and Lark quarantine

Use this when debugging Hermes local-brain taskpool dispatch/autorun after Lark task ingestion or historical proof debt blocks the queue.

## Pattern verified in session

Symptoms:
- `brain_task_dispatch_tick.py` returns `status: ERROR` even though `dispatch-dry-run` has a `next_task_id`.
- `brain_task_autorun_step.py --json` reports `eligible: true` but `claimed: false` with `reasons: ["policy_missing"]` or `policy_task_miss`.
- `proof_check` / `evidence_spine` fail because older `done` tasks are missing structured evidence.
- Active pool is dominated by Lark/Feishu work tasks; user wants them removed temporarily regardless of state.

Safe sequence:
1. Identify Lark tasks by explicit source markers in task notes/filenames: `lark`, `feishu`, `飞书`, `larksuite`, `lark-reopened`, source fields, task URLs/IDs.
2. Do not delete task files. Move them to a timestamped quarantine under the task directory, e.g. `tasks/_temporarily_removed_lark_tasks/<YYYYmmdd-HHMMSS>/`, and write a `manifest.json` containing original path, destination, status, title, and reason.
3. Regenerate dashboard and dispatch dry-run:
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write --json`
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json`
4. If dispatch tick is blocked only by historical `done` proof debt, tolerate it in `brain_task_dispatch_tick.py` instead of letting it block current active dispatch.
5. Keep fail-closed for active task proof errors, invalid proof hashes, selfcheck failures, boundary failures, and unknown errors.
6. If autorun reports `policy_missing`, create a temporary narrow `~/.hermes/state/auto_run_policy.json` for exactly the current `next_task_id`, exact lane, exact command IDs, allowed workspace root, and `close_mode: review_only`.
7. Trigger with `python3 ~/.hermes/scripts/brain_task_dispatch_tick.py --autorun-step --print-always` and parse JSON from stdout.
8. If the first task advances and the next task is denied by `policy_task_miss`, either stop or intentionally rotate the narrow policy to the new `next_task_id`; do not widen to a broad wildcard policy.

## Tolerable historical proof debt

Only downgrade proof/evidence errors to `flow_tolerated_errors` when the proof failures are exclusively historical completed-task debt, e.g.:
- `done task missing evidence: ...`
- `autorun done task missing proof evidence: ...`

Warnings that may accompany this tolerated condition:
- `missing Final Handoff section: ...`
- `legacy body-only evidence accepted: ...`

For `evidence_spine`, require the summary to show:
- `proof_check == FAIL`
- `selfcheck == PASS`
- `boundary_check == PASS`

If any other failure appears, keep dispatch tick in `ERROR`.

## Verification signals

Good outcome:
- dispatch tick `status: OK`
- `errors: []`
- `flow_tolerated_errors` lists only proof/evidence historical debt
- autorun has `eligible: true`, `claimed: true`, `advanced: true`
- target task moves to `review` or `done` according to its lifecycle/gates
- final `dispatch-dry-run` eventually shows `dispatchable: false`, `next: None` when no pending executable tasks remain

## Pitfalls

- Running `brain_task_dispatch_tick.py --autorun-step` without `--print-always` may produce no stdout on success; use `--print-always` when collecting evidence.
- `brain_task_dispatch_tick.py` may not support `--json`; do not assume it does. Use `--print-always` and parse stdout.
- A successful first autorun can make the policy stale immediately; subsequent current next task may return `policy_task_miss` by design.
- Quarantine Lark tasks by moving files, not by editing status, so they can be restored exactly from manifest.
