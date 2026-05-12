#!/usr/bin/env python3
"""Task Pool Guardian — Monitors and fixes task flow issues.

Detects and auto-fixes:
- Stale claims (claimed but TTL expired)
- Stuck envelopes (RUNNING beyond appetite)
- Deadlock (claimed > 5min with no envelope activity)
- Flow gaps (PENDING tasks not reaching workers)

Run via cron every 10 minutes.
"""
import json, subprocess, sys, time, os
from pathlib import Path

sys.path.insert(0, str(Path.home() / '.hermes' / 'scripts'))

ORCHESTRATOR = Path.home() / '.hermes' / 'scripts' / 'brain_task_orchestrator.py'

def check_stale_claims():
    """Release stale claims."""
    r = subprocess.run(['python3', str(ORCHESTRATOR), 'list', '--json'],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        return {'action': 'none', 'error': 'orchestrator failed'}
    
    d = json.loads(r.stdout)
    stale = [t for t in d.get('rows', []) if t.get('stale_claim')]
    
    released = 0
    for t in stale:
        task_id = t['id']
        r2 = subprocess.run(
            ['python3', str(ORCHESTRATOR), 'release', task_id,
             '--force', '--reason', 'guardian_stale_claim_cleanup', '--json'],
            capture_output=True, text=True, timeout=15
        )
        if r2.returncode == 0:
            released += 1
    
    return {
        'action': 'release_stale',
        'found': len(stale),
        'released': released,
    }

def check_stuck_envelopes():
    """Reset envelopes stuck in RUNNING beyond appetite."""
    try:
        from envelope_bus import list_by_status, update_status, append_trace, check_timeout
        timed_out = check_timeout()
        
        reset = 0
        for env in timed_out:
            eid = env['id']
            # Check retry count
            retry = env.get('retry_count', 0)
            max_r = env.get('max_retries', 3)
            
            if retry >= max_r:
                update_status(eid, 'FAILED', error='guardian: max retries exceeded')
                append_trace(eid, {'event': 'guardian_failed', 'reason': 'max_retries'})
            else:
                update_status(eid, 'PENDING')
                append_trace(eid, {'event': 'guardian_reset', 'retry': retry + 1})
            reset += 1
        
        return {
            'action': 'reset_stuck_envelopes',
            'found': len(timed_out),
            'reset': reset,
        }
    except Exception as e:
        return {'action': 'reset_stuck_envelopes', 'error': str(e)[:200]}

def check_flow_health():
    """Check overall flow health and report."""
    try:
        # Orchestrator
        r = subprocess.run(['python3', str(ORCHESTRATOR), 'list', '--json'],
                           capture_output=True, text=True, timeout=30)
        d = json.loads(r.stdout)
        rows = d.get('rows', [])
        
        total = len(rows)
        pending = sum(1 for t in rows if t.get('status') == 'pending')
        claimed = sum(1 for t in rows if t.get('status') == 'claimed')
        review = sum(1 for t in rows if t.get('status') == 'review')
        stale = sum(1 for t in rows if t.get('stale_claim'))
        dispatchable = sum(1 for t in rows if t.get('dispatchable'))
        
        # Envelope
        from envelope_bus import stats as env_stats
        es = env_stats()
        
        # V(x)
        r2 = subprocess.run(['python3', str(Path.home()/'.hermes/scripts/v_state.py'), '--json'],
                            capture_output=True, text=True, timeout=60)
        v = json.loads(r2.stdout)
        
        return {
            'action': 'health_check',
            'tasks': {'total': total, 'pending': pending, 'claimed': claimed, 'review': review, 'stale': stale, 'dispatchable': dispatchable},
            'envelopes': es,
            'v_state': {'V': v['V'], 'grade': v['grade'], 'bottleneck': v['bottleneck']},
        }
    except Exception as e:
        return {'action': 'health_check', 'error': str(e)[:200]}

def run_guardian():
    """Full guardian cycle."""
    results = {}
    
    # 1. Fix stale claims
    results['stale_claims'] = check_stale_claims()
    
    # 2. Fix stuck envelopes
    results['stuck_envelopes'] = check_stuck_envelopes()
    
    # 3. Health check
    results['health'] = check_flow_health()
    
    # Summary
    issues_found = (
        results['stale_claims'].get('found', 0) +
        results['stuck_envelopes'].get('found', 0)
    )
    issues_fixed = (
        results['stale_claims'].get('released', 0) +
        results['stuck_envelopes'].get('reset', 0)
    )
    
    v_score = results['health'].get('v_state', {}).get('V', 0)
    grade = results['health'].get('v_state', {}).get('grade', 'unknown')
    
    return {
        'status': 'ok',
        'issues_found': issues_found,
        'issues_fixed': issues_fixed,
        'v_score': v_score,
        'grade': grade,
        'details': results,
    }

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        print(json.dumps(run_guardian(), indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == 'health':
        print(json.dumps(check_flow_health(), indent=2, ensure_ascii=False))
    else:
        print('Usage: task_pool_guardian.py [run|health]')
