# Blocked multi-model task diagnostics

Use this when a user asks why taskpool/workflow items are `blocked`, whether they will auto-complete, or why an evolution task is not dispatching.

## Fast inspection path

1. Prefer the task orchestrator, not `brainctl list`:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py list --include-done --json > /tmp/tasklist.json
```

The JSON top-level shape is usually `{status, generated_at, task_count, rows}`; inspect `rows`, not `tasks`.

2. Match by exact `id` first, then by path/title fallback. Check these fields:

- `status`, `priority`, `lane`, `dispatchable`
- `retry_count`, `next_attempt_at`, `claimed_by`, `claim_expires_at`, `stale_claim`
- `mission_node_depends_on`, `mission_node_blockers`, `mission_node_ready`
- `multimodel_intervention_required`, `multimodel_intervention_reasons`
- `multimodel_status`, `multimodel_round_status`, `multimodel_last_gate_status`, `multimodel_last_decision`, `multimodel_last_failures`
- `completion_gate`, `path`, `lifecycle_next`

3. For exact failure details, read the task Markdown frontmatter and parse `multimodel_last_failures`. Common meanings:

- `missing_required_model_consulted:<model>` / `missing_required_model_vote:<model>`: certification quorum is incomplete; rerun/repair the missing model round before normal execution.
- `model_count_below_required` / `models_consulted_below_required`: not enough canonical participants.
- `agreement_below_threshold:<dimension>`: multi-model consensus did not converge on framing/approach/order.
- `best_within_constraints_missing:<model>`: that model did not provide the required constrained-best recommendation.
- `non_approve_vote:<model>:amend`: model requested amendment; fold the amendment into a revised proposal and revote.

## Automation/auto-completion check

1. Confirm scheduled automation exists/enabled in `~/.hermes/cron/jobs.json`; relevant jobs commonly include:

- `local-brain-taskpool-auto-completer` (`taskpool_dynamic_runner.py`)
- `local-brain-task-dispatch-safe-summary-tick`
- `local-brain-task-dispatch-autorun-summary-tick`

2. Understand the split:

- Normal dispatch only handles `dispatchable=true` work.
- Evolution tasks with `dispatchable=false` and `multimodel_status=not_certified` are blocked by the ratification gate, not by normal dependency ordering.
- `taskpool_dynamic_runner.py` can call `brain_task_dispatch_tick.py --summary --autorun-step --no-state` and, when intervention is required, start `multimodel_intervention_dynamic_step.py`.
- The dynamic multi-model step starts a detached worker; cron invocation is short and non-blocking.

3. To actively nudge a stuck certified/evolution queue, run:

```bash
python3 ~/.hermes/scripts/multimodel_intervention_dynamic_step.py --json
```

Then inspect:

- `intervention_required`
- `selected_task_id`
- `queued_count`
- `action` (`started_worker`, existing worker, cooldown, etc.)
- `pid`, `worker_log`

Useful state/log paths:

- `~/.hermes/state/multimodel_dynamic/state.json`
- `~/.hermes/state/multimodel_dynamic/worker.pid`
- `~/.hermes/logs/multimodel_intervention_dynamic_worker.log`
- `~/.hermes/logs/multimodel_intervention_dynamic_step.jsonl`

## Answering the user

Be precise: say whether the block is dependency-based, claim-based, retry/cooldown-based, or ratification-gate-based. For ratification-gate blocks, do not promise automatic `done`. Say: the system has an automatic retry/intervention path, but `done` requires the missing model votes, consensus thresholds, constrained-best fields, and evidence/selfcheck gates to pass. If `dispatchable=false`, normal autorun will not execute it until certification/review gates clear.