# Cycle Timeout Diagnostics — Bypass a Hung Controller

When `agent_team_controller.py cycle` hangs or times out, you can diagnose the system state
without waiting for the cycle to complete. The cycle blocks on `delegate_to_worker()` (which
calls `hermes chat -q` synchronously), but the underlying data is accessible directly.

## Quick Diagnosis Commands

```bash
# 1. Check running processes — identify what's blocking
ps aux | grep -E "agent_team_controller|brain_task_orchestrator|claude -p" | grep -v grep

# 2. Query envelope bus stats directly (instant, no subprocess blocking)
cd ~/.hermes/scripts && python3 -c "
from envelope_bus import stats, list_by_status, human_escape_check
import json
s = stats()
print(json.dumps(s, indent=2, ensure_ascii=False))
esc = human_escape_check()
print('Escape:', esc[0])
"

# 3. List RUNNING tasks with details
cd ~/.hermes/scripts && python3 -c "
from envelope_bus import list_by_status
import json
for t in list_by_status('RUNNING'):
    print(json.dumps(t, indent=2, ensure_ascii=False))
    print('---')
"

# 4. Check dynamic N state (last successful cycle)
cat ~/.hermes/state/dynamic_n_state.json

# 5. Test orchestrator list independently (should return in <5s)
cd ~/.hermes/scripts && timeout 15 python3 brain_task_orchestrator.py list --json | head -50

# 6. Check for blocking multimodel intervention processes
cat ~/.hermes/state/brain_task_dispatch_tick_state.json
```

## Common Blocking Scenarios

### Scenario A: Worker delegation timeout
- `delegate_to_worker()` calls `hermes chat -q` which spawns a full agent session
- Each worker: 300-600s + verification 300-400s = 600-1000s per task
- With N=3 sequential: 1800-3000s total cycle time
- **Diagnosis:** `ps aux | grep claude` shows active worker processes
- **Bypass:** Wait for workers to finish, or kill stale ones

### Scenario B: multimodel-intervention-step blocking
- `brain_task_orchestrator.py multimodel-intervention-step` spawns `claude -p` subprocess
- This doesn't block `list --json` but indicates system is under load
- **Diagnosis:** `ps aux | grep "multimodel-intervention-step"`
- **Note:** The intervention step and the cycle use separate subprocesses, so they can
  coexist. But if both are trying to claim/release tasks, there may be contention.

### Scenario C: Orchestrator lock contention
- Multiple processes calling orchestrator commands simultaneously
- `list --json` works fine (no lock), but `claim`/`release` may contend
- **Diagnosis:** `list --json` returns quickly but cycle still hangs → contention in claim phase

## Envelope Bus Direct Access

The envelope_bus SQLite database is at `~/.hermes/state/envelope_bus.db`.
You can query it directly when the Python API is also slow:

```bash
sqlite3 ~/.hermes/state/envelope_bus.db "SELECT id, status, title, started_at FROM envelopes WHERE status='RUNNING';"
sqlite3 ~/.hermes/state/envelope_bus.db "SELECT status, COUNT(*) FROM envelopes GROUP BY status;"
```

## Appetite Timeout Check

To check if RUNNING tasks have exceeded their appetite:

```python
from datetime import datetime, timezone
# Tasks have appetite_seconds (default 1800 = 30min)
# started_at is in the envelope record
now = datetime.now(timezone.utc)
# Compare (now - started_at).total_seconds() > appetite_seconds
```

## Recovery Actions

1. **Stale RUNNING tasks (>30min):** Release via orchestrator:
   ```bash
   python3 brain_task_orchestrator.py release TASK_ID --reason appetite_expired --json
   ```

2. **Kill stuck worker processes:**
   ```bash
   kill PID  # for claude/hermes subprocess
   # The envelope bus will detect timeout on next cycle
   ```

3. **Force reset envelope to PENDING:**
   ```python
  from envelope_bus import update_status
  update_status('ENVELOPE_ID', 'PENDING')
  ```
