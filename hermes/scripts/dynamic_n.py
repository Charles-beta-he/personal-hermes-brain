#!/usr/bin/env python3
"""Dynamic N Calculator — Determine optimal parallel agent count.

Formula: N = min(ceil(dispatchable/7), conflict_groups, MAX_CAP)
Floor: 1, Max cap: 3 (configurable)

Smoothing: N only changes if sustained for 2 consecutive cycles.
"""
import json, time, os
from pathlib import Path

STATE_FILE = Path.home() / '.hermes' / 'state' / 'dynamic_n_state.json'
MAX_CAP = int(os.environ.get('AGENT_TEAM_MAX_AGENTS', '3'))
SMOOTHING_CYCLES = 2  # N must be consistent for this many cycles before change

def calculate_raw_n(dispatchable_count, conflict_group_count):
    """Raw N calculation."""
    import math
    if dispatchable_count == 0:
        return 0
    n = math.ceil(dispatchable_count / 7)
    n = min(n, conflict_group_count, MAX_CAP)
    return max(n, 1)

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {'current_n': 1, 'candidate_n': None, 'candidate_count': 0, 'history': []}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))

def get_smoothed_n(dispatchable_count, conflict_group_count):
    """Get N with smoothing to prevent oscillation."""
    raw_n = calculate_raw_n(dispatchable_count, conflict_group_count)
    state = load_state()
    
    if raw_n == state['current_n']:
        # Same as current, reset candidate
        state['candidate_n'] = None
        state['candidate_count'] = 0
    elif raw_n == state.get('candidate_n'):
        # Same candidate, increment count
        state['candidate_count'] = state.get('candidate_count', 0) + 1
        if state['candidate_count'] >= SMOOTHING_CYCLES:
            # Sustained, apply change
            state['current_n'] = raw_n
            state['candidate_n'] = None
            state['candidate_count'] = 0
    else:
        # New candidate
        state['candidate_n'] = raw_n
        state['candidate_count'] = 1
    
    # Record history (last 20)
    state['history'] = state.get('history', [])[-19:] + [{
        'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'dispatchable': dispatchable_count,
        'groups': conflict_group_count,
        'raw_n': raw_n,
        'applied_n': state['current_n'],
    }]
    
    save_state(state)
    
    return {
        'applied_n': state['current_n'],
        'raw_n': raw_n,
        'candidate_n': state.get('candidate_n'),
        'candidate_count': state.get('candidate_count', 0),
        'smoothing_active': state.get('candidate_n') is not None and state.get('candidate_count', 0) < SMOOTHING_CYCLES,
        'formula': f'min(ceil({dispatchable_count}/7), {conflict_group_count}, {MAX_CAP})',
    }

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # Test with various inputs
        for d, g in [(0, 0), (3, 2), (7, 3), (15, 4), (30, 5)]:
            result = get_smoothed_n(d, g)
            print(f"  dispatchable={d}, groups={g} → raw={result['raw_n']}, applied={result['applied_n']}")
    elif len(sys.argv) > 1 and sys.argv[1] == 'state':
        print(json.dumps(load_state(), indent=2))
    else:
        print('Usage: dynamic_n.py [test|state]')
