#!/usr/bin/env python3
"""V(x) System State Function — Complex Giant Systems health monitor.

V(x) = Σ wᵢ · fᵢ(xᵢ) ∈ [0, 1]

Components:
- orchestrator_health: selfcheck PASS=1, else 0
- dynamic_n_efficiency: applied_n / max(1, raw_n) 
- classifier_coverage: known_groups / total_dispatchable
- continuation_pressure: 1 - (active_checkpoints / max(1, total_tasks))
- envelope_health: 1 - (failed+timeout / max(1, total))
- cron_health: 1 - (error_crons / max(1, total_crons))
- kanban_sync: mirrored / max(1, dispatchable)

V(x) < 0.5 → DEGRADED mode
V(x) < 0.3 → CRITICAL mode
"""
import json, subprocess, sys, time, math
from pathlib import Path

HOME = Path.home()
SCRIPTS = HOME / '.hermes' / 'scripts'
STATE = HOME / '.hermes' / 'state'

def safe_run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else ''
    except:
        return ''

def f_orchestrator():
    """Selfcheck PASS=1, FAIL=0."""
    out = safe_run(['python3', str(SCRIPTS / 'brain_task_orchestrator.py'), 'selfcheck'])
    return 1.0 if 'PASS' in out else 0.0

def f_dynamic_n():
    """applied_n / max(1, raw_n). Smooth transition bonus."""
    try:
        state = json.loads((STATE / 'dynamic_n_state.json').read_text())
        applied = state.get('current_n', 1)
        # Get raw from last history entry
        history = state.get('history', [])
        raw = history[-1].get('raw_n', 1) if history else 1
        if raw == 0:
            return 1.0  # No tasks = healthy
        return min(applied / max(1, raw), 1.0)
    except:
        return 0.5

def f_classifier():
    """Coverage: unique groups / sqrt(dispatchable). Capped at 1."""
    try:
        r = safe_run(['python3', str(SCRIPTS / 'task_classifier.py'), 'show'])
        data = json.loads(r)
        groups = len(data.get('groups', {}))
        dispatchable = data.get('dispatchable', 1)
        if dispatchable == 0:
            return 1.0
        return min(groups / max(1, math.sqrt(dispatchable)), 1.0)
    except:
        return 0.5

def f_continuation():
    """1 - (active_checkpoints / max(1, total_envelopes))."""
    try:
        cps = list((STATE / 'task_checkpoints').glob('*.json'))
        active = len(cps)
        # Total envelopes
        r = safe_run(['python3', str(SCRIPTS / 'envelope_bus.py'), 'stats'])
        data = json.loads(r)
        total = data.get('total', 1)
        return max(0, 1 - active / max(1, total))
    except:
        return 0.8

def f_envelope():
    """1 - (failed + timeout) / max(1, total)."""
    try:
        r = safe_run(['python3', str(SCRIPTS / 'envelope_bus.py'), 'stats'])
        data = json.loads(r)
        total = data.get('total', 1)
        by_status = data.get('by_status', {})
        bad = by_status.get('FAILED', 0) + by_status.get('BLOCKED', 0)
        timeouts = data.get('timeouts', 0)
        return max(0, 1 - (bad + timeouts) / max(1, total))
    except:
        return 0.8

def f_cron():
    """1 - recent_error_crons / max(1, total_crons). Only count errors from last 48h."""
    try:
        out = safe_run(['hermes', 'cron', 'list'])
        total = out.count('[active]')
        if total == 0:
            return 1.0
        # Count only recent errors (from today/yesterday)
        import re
        today = time.strftime('%Y-%m-%d')
        yesterday = time.strftime('%Y-%m-%d', time.localtime(time.time() - 86400))
        recent_errors = 0
        lines = out.split('\n')
        for i, line in enumerate(lines):
            if 'error:' in line.lower():
                # Check if the error is from recent runs
                if today in line or yesterday in line:
                    recent_errors += 1
        return max(0, 1 - recent_errors / total)
    except:
        return 0.8

def f_kanban():
    """mirrored / max(1, dispatchable). Capped at 1."""
    try:
        r = safe_run(['hermes', 'kanban', 'stats', '--json'])
        data = json.loads(r)
        by_assignee = data.get('by_assignee', {})
        mirror_data = by_assignee.get('brain-mirror', {})
        if isinstance(mirror_data, dict):
            mirrored = mirror_data.get('ready', 0) + mirror_data.get('in_progress', 0)
        else:
            mirrored = int(mirror_data) if mirror_data else 0
        # Get dispatchable count
        r2 = safe_run(['python3', str(SCRIPTS / 'brain_task_orchestrator.py'), 'list', '--json'])
        data2 = json.loads(r2)
        dispatchable = sum(1 for t in data2.get('rows', []) if t.get('dispatchable'))
        if dispatchable == 0:
            return 1.0
        return min(mirrored / dispatchable, 1.0)
    except:
        return 0.5

# Weights
WEIGHTS = {
    'orchestrator': 0.20,
    'dynamic_n': 0.10,
    'classifier': 0.10,
    'continuation': 0.15,
    'envelope': 0.15,
    'cron': 0.15,
    'kanban': 0.15,
}

FUNCTIONS = {
    'orchestrator': f_orchestrator,
    'dynamic_n': f_dynamic_n,
    'classifier': f_classifier,
    'continuation': f_continuation,
    'envelope': f_envelope,
    'cron': f_cron,
    'kanban': f_kanban,
}

def compute_v():
    components = {}
    for name, fn in FUNCTIONS.items():
        try:
            score = fn()
        except:
            score = 0.0
        components[name] = round(score, 3)
    
    v = sum(WEIGHTS[name] * components[name] for name in WEIGHTS)
    v = round(v, 3)
    
    if v >= 0.7:
        grade = 'HEALTHY'
    elif v >= 0.5:
        grade = 'DEGRADED'
    else:
        grade = 'CRITICAL'
    
    # Find bottleneck (lowest raw score, not weighted)
    bottleneck = min(components, key=components.get)
    
    weighted = {name: round(WEIGHTS[name] * components[name], 3) for name in WEIGHTS}
    
    return {
        'V': v,
        'grade': grade,
        'components': components,
        'weights': WEIGHTS,
        'weighted_scores': weighted,
        'bottleneck': bottleneck,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }

def main():
    result = compute_v()
    
    if '--json' in sys.argv:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"V(x) = {result['V']} [{result['grade']}]")
        print(f"Bottleneck: {result['bottleneck']}")
        for name in sorted(result['components']):
            w = result['weights'][name]
            s = result['components'][name]
            ws = result['weighted_scores'][name]
            bar = '█' * int(s * 10) + '░' * (10 - int(s * 10))
            print(f"  {name:15} {bar} {s:.2f} × {w:.2f} = {ws:.3f}")

if __name__ == '__main__':
    main()
