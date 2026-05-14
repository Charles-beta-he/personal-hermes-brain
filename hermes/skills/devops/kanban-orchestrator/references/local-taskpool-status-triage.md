# Local Brain Taskpool Status Triage

Use this when the user asks to check local task-pool/taskpool/任务池 status. The canonical source is the local-brain Markdown taskpool, not Kanban watch alone.

## Source of truth commands

```bash
# Current active task rows and state
python3 ~/.hermes/scripts/brain_task_orchestrator.py list --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py next --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json

# Guardian health and safe cleanup cycle
python3 ~/.hermes/scripts/task_pool_guardian.py health
python3 ~/.hermes/scripts/task_pool_guardian.py run

# Envelope subsystem
python3 ~/.hermes/scripts/envelope_bus.py stats
python3 ~/.hermes/scripts/pipeline_tick.py tick
python3 ~/.hermes/scripts/agent_team_controller.py cycle
python3 ~/.hermes/scripts/envelope_executor.py run 1

# Cron schedule/source evidence
hermes cron list
```

## Summarize in this order

1. Timestamp (`date`) and live-read status.
2. Canonical taskpool counts by status/lane/priority.
3. Current `review` / `running` / `blocked` / `retry` / `expired` tasks.
4. `next` dispatchable task and whether it requires multi-model gates.
5. Project-profile readiness when the question is about execution/validation readiness, not just lifecycle status.
6. Guardian result: stale claims, stuck envelopes, `V`, grade, bottleneck.
7. Envelope result: status counts, timeouts, `human_escape_triggered`, and concrete failed envelope IDs/titles/errors when escape is true.
8. Cron jobs relevant to taskpool: auto-completer, occasional report, guardian, pipeline tick, agent-team controller, envelope executor.
9. Actionable blockers in priority order.

## Project profile resolution boundary

Local-brain task notes normally store a routing key, not a full project profile snapshot. `brain_task_orchestrator.py add` writes fields such as `project`, `workspace`, `parallel_boundary`, `lane`, and acceptance/proof metadata into Markdown frontmatter. Plain status checks (`list`, `next`, `proof-check`, `selfcheck`) should read lifecycle/proof state from the Markdown taskpool and do not need to query project profiles.

When the user asks whether a task can proceed, how it will be executed, or whether validation is project-correct, check project-profile resolution separately. `agent_team_controller.py` loads `~/.hermes/project-profiles/{project}.json` at execution/verification time via `load_project_profile(project)` and injects the resulting `PROJECT PROFILE` into worker and reviewer prompts. Report whether profile resolution is exact, missing, or default-fallback.

Treat fallback-to-default profiles as a risk boundary: for `lane=work` or product/Lark tasks, a missing project profile should be reported as `project_profile_missing`/`default_profile_fallback`, not silently accepted as correct project context. For Hermes/local-brain self-evolution tasks, default Hermes profile fallback may be acceptable if stated.

## Human escape interpretation

`human_escape_triggered=true` from `envelope_bus.stats()` means envelope/agent-team automation is intentionally stopped by a protection gate. Do not report the local-brain taskpool itself as broken if `brain_task_orchestrator.py proof-check` and `selfcheck` pass. Report the split explicitly:

- canonical taskpool: healthy / unhealthy
- envelope/agent-team chain: escaped / not escaped
- failed envelope evidence: `id`, `project`, `assignee`, `title`, `error`, `retry_count`, `updated_at`

A useful SQLite query for failed envelopes:

```bash
python3 - <<'PY'
import json, sqlite3
from pathlib import Path
p = Path.home()/'.hermes/state/envelope_bus.db'
conn = sqlite3.connect(p); conn.row_factory = sqlite3.Row
rows = conn.execute("""
SELECT id,status,type,project,assignee,title,error,retry_count,max_retries,created_at,updated_at,completed_at
FROM envelopes
WHERE status IN ('FAILED','BLOCKED','RUNNING')
ORDER BY updated_at DESC LIMIT 20
""").fetchall()
print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))
PY
```

## Cron/script pitfall

Some Hermes cron jobs store `script` as a single string with arguments, e.g. `pipeline_tick.py tick` or `envelope_executor.py run 1`. The scheduler may log `Script not found: /Users/.../pipeline_tick.py tick` because it treats the whole string as a filename. This is a cron configuration/wrapper issue, not proof that the underlying script file is absent.

Verify both layers:

```bash
ls ~/.hermes/scripts/pipeline_tick.py ~/.hermes/scripts/envelope_executor.py ~/.hermes/scripts/agent_team_controller.py
python3 ~/.hermes/scripts/pipeline_tick.py tick
python3 ~/.hermes/scripts/envelope_executor.py run 1
python3 ~/.hermes/scripts/agent_team_controller.py cycle
```

When reporting, distinguish:

- scheduler script-path parsing failure
- actual script return status, e.g. `escaped` due to failed envelopes

## Delivery/report pitfall

`local-brain-taskpool-occasional-report` may show `last_delivery_error: no delivery target resolved for deliver=origin`. This is a delivery binding issue, not a taskpool state issue. Suggest changing the delivery target to an explicit Telegram target only after checking the current cron configuration and user intent.

## Auto-completer / non-work task interpretation

When the user asks whether non-`work` tasks will finish automatically, answer from live taskpool/cron evidence and keep these semantics explicit:

- `local-brain-taskpool-auto-completer` is not a proof-free closer despite its name. Its dynamic runner drives safe ticks and bounded steps; it is not allowed to mark arbitrary Markdown tasks `done`.
- `brain_task_dispatch_tick.py` is control-plane only: ingest/reconcile/dashboard/proof/evidence-spine/multimodel dry-run/dispatch hint. It never executes task Markdown and never marks a task done.
- `brain_task_autorun_step.py` runs only static command IDs allowed by policy, never parses task bodies for commands, and stops successful execution at `review` (`review_only`).
- `multimodel_intervention_dynamic_step.py` can start detached multi-model intervention workers; successful gates persist `multimodel_status` / ratification artifacts, but do not perform lifecycle `review -> done`.
- Final closeout still requires the lane-specific completion gate: `work` needs project evidence, `evolution` needs ratification/selfcheck/proof evidence, and `advisory` needs deposited advisory/report evidence. `--yolo` authorizes execution, not completion.

## JSON output pitfall

If `python3 ~/.hermes/scripts/brain_task_orchestrator.py list --json` prints rows but `json.loads` fails because a task title/body introduced an unescaped control character or delimiter, do not abandon the canonical source or fall back to stale derived files. Import the script module and call its internal row builder directly:

```python
import importlib.util, sys
from pathlib import Path
script = Path.home() / '.hermes/scripts/brain_task_orchestrator.py'
spec = importlib.util.spec_from_file_location('bto', script)
bto = importlib.util.module_from_spec(spec)
sys.modules['bto'] = bto  # required for dataclasses during dynamic import
spec.loader.exec_module(bto)
rows = [t.row() for t in bto.iter_tasks() if t.status not in bto.TERMINAL_STATUSES]
```

This preserves the same canonical Markdown taskpool semantics as the CLI while bypassing serialization bugs. Use it only for read-only inspection unless the user explicitly requested repair.

## Do not do during a status check

- Do not mark tasks done, release claims, or delete failed envelopes unless the user asked for repair, not just status.
- Running `task_pool_guardian.py run` is acceptable as a safe health/cleanup check because it only releases stale claims/timeouts through existing guardrails; still report if it changed anything.
- Do not treat `hermes kanban stats` as canonical for the local brain taskpool; it may only show mirrored observability rows.
