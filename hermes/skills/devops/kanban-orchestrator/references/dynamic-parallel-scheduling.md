# Dynamic Parallel Scheduling — Conflict Group Classification + Adaptive N

Session: 2026-05-10 — Phase 4 agent team controller
Result: 4/4 multi-model approved, N=3 dynamic dispatch working

## Pattern

When orchestrating parallel task execution, dynamically adjust the number of concurrent workers based on workload and conflict groups.

### Dynamic N Formula

```python
import math

def calculate_n(dispatchable_count, conflict_group_count, max_cap=3):
    if dispatchable_count == 0:
        return 0
    n = math.ceil(dispatchable_count / 7)  # ~7 tasks per agent
    n = min(n, conflict_group_count, max_cap)
    return max(n, 1)
```

### Smoothing (Prevent Oscillation)

N should not flip every cycle. Require 2 consecutive cycles at the same candidate N before applying:

```python
SMOOTHING_CYCLES = 2

def get_smoothed_n(raw_n, state):
    if raw_n == state['current_n']:
        state['candidate_n'] = None
        state['candidate_count'] = 0
    elif raw_n == state.get('candidate_n'):
        state['candidate_count'] += 1
        if state['candidate_count'] >= SMOOTHING_CYCLES:
            state['current_n'] = raw_n
            state['candidate_n'] = None
            state['candidate_count'] = 0
    else:
        state['candidate_n'] = raw_n
        state['candidate_count'] = 1
    return state['current_n']
```

### Task Classification → Conflict Groups

Tasks that modify the same files/modules must be serial. Different groups can be parallel.

Deterministic classification (no LLM needed):
```python
BOUNDARY_TO_GROUP = {
    'workspace:~/.hermes': 'hermes-core',
    'workspace:~/work/uvisa-app': 'uvisa-frontend',
    'project:hermes-skill-tree': 'hermes-skills',
    # ...
}

def classify(task):
    boundary = task.get('parallel_boundary', '')
    if boundary in BOUNDARY_TO_GROUP:
        return BOUNDARY_TO_GROUP[boundary]
    return f'auto-{hashlib.sha256(boundary.encode()).hexdigest()[:6]}'
```

### Scheduling Algorithm

```python
def get_schedule(tasks, max_groups):
    groups = classify_batch(tasks)
    sorted_groups = sorted(groups.keys(), 
                          key=lambda g: sum(t['score'] for t in groups[g]), 
                          reverse=True)
    selected = sorted_groups[:max_groups]
    deferred = sorted_groups[max_groups:]
    
    schedule = []
    for group in selected:
        group_tasks = sorted(groups[group], key=lambda t: t['score'], reverse=True)
        schedule.append({'conflict_group': group, 'tasks': group_tasks})
    return schedule, deferred
```

## Pitfalls

- **Hash-based group fallback creates phantom groups.** Cap N at min(n, actual_conflict_groups).
- **Smoothing delays scaling DOWN.** Consider asymmetric: scale up fast (1 cycle), scale down slow (2 cycles).
- **Classification granularity matters.** Too coarse → no parallelism. Too fine → merge conflicts. Project-level is usually right.
- **deferred groups can starve.** Add priority decay: boost deferred group score by age.
- **Cycle timeout: `run_dynamic_cycle()` is synchronous and heavyweight.** The cycle doesn't just check status — it claims tasks, delegates workers, AND runs 4-model verification (Claude/GPT/DeepSeek/MiMo, each 90s timeout) all inline. With N=3, a single cycle can take **10+ minutes**. A 120s cron timeout WILL fail. Either increase cron timeout to 600s+ or refactor into claim-only + async verification passes. Diagnosed 2026-05-12 with 25 dispatchable tasks, 19 conflict groups, N=3.
- **Stale claims block release without --force.** When `agent-team-controller` owns a claim, `brain_task_orchestrator.py release` refuses without `--force`. Use the orchestrator list to check `stale_claim: true` before attempting cleanup.

## Diagnosing Cycle Timeouts

When `agent_team_controller_cycle.py` times out (cron or manual), run these independent diagnostics:

```python
# 1. Check orchestrator list (works even if cycle hangs)
python3 brain_task_orchestrator.py list --json

# 2. Envelope bus stats
from envelope_bus import stats
s = stats()  # shows total, by_status, timeouts, human_escape_triggered

# 3. Classify tasks and check N
from task_classifier import classify_batch, boundary_health_check
from dynamic_n import get_smoothed_n
groups = classify_batch(all_tasks)
n_result = get_smoothed_n(len(all_tasks), len(groups))
```

Key metrics to report:
- `dispatchable` count vs `total` tasks
- `conflict_groups` count (determines max parallelism)
- `applied_n` and whether `smoothing_active` changed N
- `stale_claim` tasks needing cleanup
- `human_escape_triggered` and `escape_info`
- `by_status` envelope distribution (PENDING/RUNNING/DONE/FAILED/timeout)
