# Dynamic N Scheduler + Task Classifier

## Dynamic N Formula

```
N = min(ceil(dispatchable / 7), conflict_groups, MAX_CAP)
```

- `MAX_CAP` = 3 (configurable via `AGENT_TEAM_MAX_AGENTS` env)
- Floor = 1 (always at least 1 agent if tasks exist)
- Smoothing: N only changes after 2 consecutive cycles confirming the new value

## Smoothing State

```json
{
  "current_n": 1,
  "candidate_n": 3,
  "candidate_count": 1,
  "history": [{"ts": "...", "dispatchable": 20, "groups": 4, "raw_n": 3, "applied_n": 1}]
}
```

When `candidate_count >= SMOOTHING_CYCLES(2)`, `current_n` updates to `candidate_n`.

## Task Classifier

Deterministic boundary → conflict_group mapping:

```python
BOUNDARY_TO_GROUP = {
    'workspace:/Users/charles/.hermes': 'hermes-core',
    'workspace:.../uvisa-app-2.0': 'uvisa-frontend',
    'workspace:.../uvisa-backend': 'uvisa-backend',
    'project:hermes-skill-tree': 'hermes-skills',
    'project:local-brain-task-orchestration': 'brain-orchestration',
    'project:hermes-capability-router': 'hermes-router',
}

BOUNDARY_PREFIXES = [
    ('evolution:skill-learning:', 'evolution-skill-learning'),
    ('evolution:local-brain', 'evolution-local-brain'),
    ('evolution:', 'evolution-lane'),
    ('workspace:/tmp/', 'temp-workspace'),
    ('project:', 'project-other'),
]
```

**Matching order**: exact match → prefix match (longer first) → project → lane → hash fallback

## Conflict Group Scheduling

- Same group: serial execution (FIFO by priority score)
- Different groups: parallel execution (up to N groups simultaneously)
- Groups beyond N: deferred to next cycle

## Pitfalls

- **`brain_task_orchestrator list --json` returns `rows` not `tasks`** — Use `data.get('rows', [])`
- **Prefix matching order matters** — `evolution:skill-learning:` must match before `evolution:`. Define prefixes longest-first.
- **Smoothing prevents oscillation** — Without smoothing, N can bounce between 1→3→1→3 every cycle
- **Conflict group count limits N** — Even with 20 dispatchable tasks, if only 2 conflict groups exist, N=2 max
