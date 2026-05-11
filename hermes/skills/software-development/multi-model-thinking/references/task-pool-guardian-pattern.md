# Task Pool Guardian Pattern

When running an autonomous task pool with claim/delegate/complete lifecycle, a dedicated guardian daemon is essential to prevent deadlock and flow stagnation.

## Problem

Without a guardian:
- Controller claims tasks but never delegates → stale claims block dispatch
- Worker times out → envelope stuck in RUNNING forever
- No automatic recovery → manual intervention required repeatedly
- Task flow deadlock: 5 claimed + 0 running + 0 stale = stuck

## Solution: Guardian Daemon

A lightweight cron job (every 10 minutes) that:

1. **Detects stale claims**: `stale_claim=True` in orchestrator list → `release --force --reason guardian_cleanup`
2. **Resets stuck envelopes**: RUNNING envelopes exceeding appetite timeout → reset to PENDING (or FAILED if max_retries exceeded)
3. **Reports health**: V(x) score, task counts, envelope status

## Implementation

```python
# task_pool_guardian.py
def run_guardian():
    results = {}
    results['stale_claims'] = check_stale_claims()  # release expired claims
    results['stuck_envelopes'] = check_stuck_envelopes()  # reset timed-out RUNNING
    results['health'] = check_flow_health()  # V(x) + task/envelope stats
    return {
        'issues_found': results['stale_claims']['found'] + results['stuck_envelopes']['found'],
        'issues_fixed': results['stale_claims']['released'] + results['stuck_envelopes']['reset'],
        'v_score': results['health']['v_state']['V'],
    }

def check_stale_claims():
    """Release stale claims via orchestrator."""
    r = subprocess.run(['python3', str(ORCHESTRATOR), 'list', '--json'], ...)
    d = json.loads(r.stdout)
    stale = [t for t in d.get('rows', []) if t.get('stale_claim')]
    released = 0
    for t in stale:
        r2 = subprocess.run(
            ['python3', str(ORCHESTRATOR), 'release', t['id'],
             '--force', '--reason', 'guardian_stale_claim_cleanup', '--json'],
            capture_output=True, text=True, timeout=15)
        if r2.returncode == 0: released += 1
    return {'found': len(stale), 'released': released}

def check_stuck_envelopes():
    """Reset envelopes stuck in RUNNING beyond appetite."""
    from envelope_bus import list_by_status, update_status, append_trace, check_timeout
    timed_out = check_timeout()
    reset = 0
    for env in timed_out:
        eid = env['id']
        retry = env.get('retry_count', 0)
        max_r = env.get('max_retries', 3)
        if retry >= max_r:
            update_status(eid, 'FAILED', error='guardian: max retries exceeded')
        else:
            update_status(eid, 'PENDING')
            append_trace(eid, {'event': 'guardian_reset', 'retry': retry + 1})
        reset += 1
    return {'found': len(timed_out), 'reset': reset}

def check_flow_health():
    """Check overall flow health."""
    # Orchestrator stats
    r = subprocess.run(['python3', str(ORCHESTRATOR), 'list', '--json'], ...)
    d = json.loads(r.stdout)
    rows = d.get('rows', [])
    # Envelope stats
    from envelope_bus import stats as env_stats
    es = env_stats()
    # V(x)
    r2 = subprocess.run(['python3', str(HOME/'.hermes/scripts/v_state.py'), '--json'], ...)
    v = json.loads(r2.stdout)
    return {
        'tasks': {'total': len(rows), 'pending': sum(1 for t in rows if t.get('status')=='pending'), ...},
        'envelopes': es,
        'v_state': {'V': v['V'], 'grade': v['grade'], 'bottleneck': v['bottleneck']},
    }
```

## Cron Setup

```
every 10m: task_pool_guardian.py run
  - If issues_found=0, silent (no output)
  - If issues_fixed>0, report count
  - If V<0.7, ALERT
```

## Key Pitfalls

- Guardian must use `--force --reason` for release (orchestrator requires audit trail)
- Stuck envelopes should be reset to PENDING (not FAILED) unless max_retries exceeded
- Guardian should NOT execute tasks itself — only fix flow state
- Run guardian BEFORE controller cycle (fix stale claims before new claims)
- Guardian found 4 issues on first run (1 stale + 3 stuck) — proves it's essential
- brain_task_orchestrator list output uses `rows` not `tasks` key

## Real-World Impact

On 2026-05-11, guardian detected and fixed:
- 1 stale claim (agent-team-controller claimed but never delegated)
- 3 stuck envelopes (RUNNING beyond appetite timeout)
- V(x) improved from 0.947 to 1.0 after guardian cleanup
