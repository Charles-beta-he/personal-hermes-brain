# Brain Task Orchestrator Integration Patterns

## Overview

`brain_task_orchestrator.py` is the canonical local-brain task orchestrator at `~/.hermes/scripts/brain_task_orchestrator.py`. It manages Markdown-based tasks in `~/Documents/brain/05-实践与项目/tasks/`.

## Key Commands

```bash
# List tasks (JSON output uses 'rows' key, NOT 'tasks')
python3 brain_task_orchestrator.py list --json
# Returns: {"status":"OK","task_count":23,"rows":[...]}

# Selfcheck
python3 brain_task_orchestrator.py selfcheck
# Returns: PASS/FAIL + task_count + boundary info

# Add task
python3 brain_task_orchestrator.py add --title "..." --lane work --priority P0

# Dry-run dispatch
python3 brain_task_orchestrator.py dispatch-dry-run --json

# Lifecycle check
python3 brain_task_orchestrator.py lifecycle --json
```

## Output Format Pitfall

The `list --json` output uses `rows` as the key for the task array, NOT `tasks`:

```python
# CORRECT
data = json.loads(r.stdout)
task_list = data.get('rows', [])

# WRONG — will return empty list
task_list = data.get('tasks', [])
```

## Task Object Shape

```json
{
  "id": "2026-05-10-修复-uvisa-...",
  "title": "Task - 修复 uvisa ...",
  "status": "review|pending|claimed|running|done|blocked",
  "priority": "P0|P1|P2|P3",
  "score": 445,
  "lane": "work|evolution|advisory",
  "project": "uvisa-app-2.0-work",
  "claimed_by": "hermes-taskpool-auto-review",
  "dispatchable": true|false,
  "parallel_boundary": "workspace:/path/to/dir",
  "stale_claim": true|false,
  "expired": true|false,
  "lifecycle_next": ["done", "retry", "blocked", "pending", "archived", "expired"]
}
```

## Selfcheck Output

```
PASS
task_count: 34
failures: []
warnings: []
boundary: {
  "status": "PASS",
  "dispatchable_count": 22,
  "dispatchable_by_lane": {"work": 5, "evolution": 17, "advisory": 0},
  "gates": {
    "work_lane_available": true,
    "autorun_enabled": false,
    "kill_switch_env_set": false,
    "evolution_preempted_by_work": true
  }
}
paths: {
  "dashboard": "/Users/charles/Documents/brain/07-仪表盘/待完成任务运行态.md",
  "sorted_pool": "/Users/charles/Documents/brain/05-实践与项目/tasks/任务池-排序.md"
}
```

## Kanban Create Output Parsing

`hermes kanban create` outputs:
```
Created t_ac68d398  (ready, assignee=brain-mirror)
```

Extract task ID with regex:
```python
m = re.search(r'Created\s+(t_[a-f0-9]+)', output)
task_id = m.group(1) if m else 'unknown'
```

## Cron Model Updates

`hermes cron edit` does NOT support `--model` or `--provider` flags. Use the `cronjob` tool:

```python
# Via cronjob tool (correct)
cronjob(action='update', job_id='xxx', model={'model': 'mimo-v2.5-pro', 'provider': 'xiaomi'})

# hermes cron edit only supports: --schedule, --prompt, --name, --deliver, --repeat, --skill, --script, --workdir
```

Note: after updating a cron job's model, the `last_error` field still shows the old error from the previous run. The model change takes effect on the NEXT run.

## One-Way Bridge Pattern (Brain → Kanban)

For observability, mirror brain tasks to Kanban:

1. Read from `brain_task_orchestrator.py list --json` (use `rows` key)
2. Filter to active tasks (not done/cancelled)
3. Create Kanban tasks with `hermes kanban create`
4. Track mirrored tasks in state file for dedup
5. Kill switch: `KANBAN_BRIDGE_DISABLED=1` env or state file

See `~/.hermes/scripts/kanban_bridge.py` for production implementation.
