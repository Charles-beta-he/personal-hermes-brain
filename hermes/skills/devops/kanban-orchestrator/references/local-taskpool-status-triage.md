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
5. Guardian result: stale claims, stuck envelopes, `V`, grade, bottleneck.
6. Envelope result: status counts, timeouts, `human_escape_triggered`, and concrete failed envelope IDs/titles/errors when escape is true.
7. Cron jobs relevant to taskpool: auto-completer, occasional report, guardian, pipeline tick, agent-team controller, envelope executor.
8. Actionable blockers in priority order.

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

## Do not do during a status check

- Do not mark tasks done, release claims, or delete failed envelopes unless the user asked for repair, not just status.
- Running `task_pool_guardian.py run` is acceptable as a safe health/cleanup check because it only releases stale claims/timeouts through existing guardrails; still report if it changed anything.
- Do not treat `hermes kanban stats` as canonical for the local brain taskpool; it may only show mirrored observability rows.
