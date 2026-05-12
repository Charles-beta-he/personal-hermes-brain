# Task Flow Deadlock Detection and Fix

Session: 2026-05-11 PUA-loop + system audit
Symptom: 0 running tasks despite 16+ dispatchable, tasks stuck in "claimed" forever

## Deadlock Pattern

```
orchestrator.list → 23 tasks
  pending: 16 (dispatchable)
  claimed: 10 (NOT dispatchable, controller claimed but never delegated)
  review: 2
  
envelope_bus → 19 envelopes
  PENDING: 17 (no consumer)
  RUNNING: 4 (executor timed out, workers never started)
  DONE: 2
  
V(x) = 0.82 DEGRADED (before fix)
```

### Root Cause Chain

1. `agent_team_controller.run_dynamic_cycle()` calls `claim_task(task_id)` 
2. Creates envelope with status RUNNING
3. **STOPS** — never calls delegate/spawn worker
4. `envelope_executor.py` tries to consume but runs `hermes chat -q` which is too heavy (600s timeout)
5. Tasks stay in "claimed" state → NOT dispatchable → deadlock

### Detection Signals

- `stale_claim: true` on claimed tasks (TTL expired but not released)
- `dispatchable` count dropping without corresponding DONE/FAILED
- `claimed_by: agent-team-controller` with expired `claim_expires_at`
- PENDING envelopes accumulating (no consumer)
- RUNNING envelopes with old `started_at` (executor timeout)

## Fix Procedure

### Step 1: Release stale claims
```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py list --json | python3 -c "
import sys, json, subprocess
d = json.load(sys.stdin)
for r in d.get('rows', []):
    if r.get('stale_claim') or (r.get('status') == 'claimed' and r.get('claimed_by') == 'agent-team-controller'):
        subprocess.run(['python3', '...brain_task_orchestrator.py', 'release', r['id'], 
                        '--force', '--reason', 'deadlock_fix_release', '--json'], timeout=15)
"
```

### Step 2: Reset stuck envelopes
```python
from envelope_bus import list_by_status, update_status, append_trace
for e in list_by_status('RUNNING'):
    update_status(e['id'], 'PENDING')
    append_trace(e['id'], {'event': 'reset_from_deadlock'})
```

### Step 3: Fix controller to delegate after claim
Add `delegate_to_worker()` function to controller:
- Lightweight worker: `hermes chat -q` with `--max-turns 15`, MiMo model, 300s timeout
- Handle result: done→release, blocked→BLOCKED, timeout→retry
- Remove heavy `envelope_executor.py` as intermediary

### Step 4: Verify flow
```
pending → claim → delegate(MiMo worker) → proof → DONE → release
```

## Prevention

1. Controller must delegate in same cycle as claim (atomic claim+delegate)
2. Never claim without immediate delegation
3. Add stale claim auto-release to pipeline_tick
4. Monitor `dispatchable` count — if dropping without DONE, suspect deadlock
