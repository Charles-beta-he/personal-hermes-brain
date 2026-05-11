# Brain → Kanban One-Way Bridge

Session: 2026-05-10 — Phase 1 observability bridge
Result: 21 tasks mirrored, cron every 2h, kill switch working

## Purpose

Mirror selected brain_task_orchestrator tasks to Hermes Kanban for `hermes kanban watch` observability. One-way only: brain is source-of-truth, Kanban is read-only mirror.

## Architecture

```
brain_task_orchestrator.py list --json
    ↓ filter: not done, not cancelled
    ↓ dedup: hash(title+status+priority)
kanban_bridge.py
    ↓ hermes kanban create <title> --assignee brain-mirror --body ...
kanban DB (mirror)
    ↓ hermes kanban watch (human observability)
```

## Key Implementation Details

### Task ID Parsing

`hermes kanban create` outputs: `Created t_ac68d398  (ready, assignee=brain-mirror)`

```python
import re
m = re.search(r'Created\s+(t_[a-f0-9]+)', output)
task_id = m.group(1) if m else 'unknown'
```

### Dedup via Content Hash

```python
def task_hash(task):
    key = f"{task.get('title','')}{task.get('status','')}{task.get('priority','')}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]
```

### Kill Switch

Two mechanisms:
1. Environment variable: `KANBAN_BRIDGE_DISABLED=1`
2. File: `~/.hermes/state/kanban_bridge_disabled`

Check both before running.

### Cron Setup

```python
# hermes cron create --script kanban_bridge.py --schedule "every 2h"
# Silent when no new tasks (don't spam output)
```

## Pitfalls

- **Orchestrator list format: `rows` not `tasks`.** `brain_task_orchestrator.py list --json` returns `{"rows": [...]}`, not `{"tasks": [...]}`.
- **Old Kanban tasks accumulate.** No purge command exists. Use `hermes kanban gc` or archive individually.
- **Bridge state file grows.** `~/.hermes/state/kanban_bridge_state.json` accumulates all mirrored hashes. Periodically clean entries older than 30 days.
- **Status mapping is lossy.** Brain has `pending/claimed/running/review/done/blocked`. Kanban has `todo/ready/in_progress/review/done/blocked`. Map `claimed→ready`, `running→in_progress`.
