#!/usr/bin/env python3
"""Brain → Kanban One-Way Bridge (Observability Only)

Mirrors selected brain tasks to Hermes Kanban for watch observability.
One-way: brain is source-of-truth, Kanban is mirror only.
Kill switch: set env KANBAN_BRIDGE_DISABLED=1 or touch ~/.hermes/state/kanban_bridge_disabled
"""
import json, os, sys, subprocess, hashlib, time
from pathlib import Path

STATE_DIR = Path.home() / '.hermes' / 'state'
BRIDGE_STATE = STATE_DIR / 'kanban_bridge_state.json'
KILL_SWITCH_FILE = STATE_DIR / 'kanban_bridge_disabled'
ORCHESTRATOR = Path.home() / '.hermes' / 'scripts' / 'brain_task_orchestrator.py'

def is_disabled():
    if os.environ.get('KANBAN_BRIDGE_DISABLED') == '1':
        return True
    if KILL_SWITCH_FILE.exists():
        return True
    return False

def load_state():
    if BRIDGE_STATE.exists():
        return json.loads(BRIDGE_STATE.read_text())
    return {'mirrored': {}, 'last_sync': None, 'errors': []}

def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state['last_sync'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    BRIDGE_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False))

def get_brain_tasks():
    """Get tasks from brain orchestrator."""
    r = subprocess.run(
        ['python3', str(ORCHESTRATOR), 'list', '--json'],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0:
        raise RuntimeError(f'orchestrator list failed: {r.stderr[:300]}')
    return json.loads(r.stdout)

def get_kanban_tasks():
    """Get existing Kanban tasks."""
    r = subprocess.run(
        ['hermes', 'kanban', 'stats', '--json'],
        capture_output=True, text=True, timeout=15
    )
    if r.returncode != 0:
        return {}
    return json.loads(r.stdout)

def task_hash(task):
    """Stable hash for dedup."""
    key = f"{task.get('title','')}{task.get('status','')}{task.get('priority','')}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]

def mirror_task(task, state):
    """Create or update a Kanban task mirroring brain task."""
    title = task.get('title', 'untitled')
    status = task.get('status', 'pending')
    priority = task.get('priority', 'medium')
    body = task.get('body', task.get('description', ''))[:500]
    
    th = task_hash(task)
    if th in state['mirrored']:
        return state['mirrored'][th]  # already mirrored
    
    # Map brain status to Kanban status
    status_map = {
        'pending': 'todo',
        'claimed': 'ready',
        'running': 'in_progress',
        'review': 'review',
        'done': 'done',
        'blocked': 'blocked',
    }
    kanban_status = status_map.get(status, 'todo')
    
    # Create Kanban task
    cmd = ['hermes', 'kanban', 'create', title, 
           '--assignee', 'brain-mirror',
           '--body', f'[brain-mirror] {body}\n\nSource: brain_task_orchestrator\nStatus: {status}\nPriority: {priority}']
    
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            # Extract task ID from output: "Created t_ac68d398  (ready, assignee=brain-mirror)"
            output = r.stdout.strip()
            task_id = 'unknown'
            import re as _re
            m = _re.search(r'Created\s+(t_[a-f0-9]+)', output)
            if m:
                task_id = m.group(1)
            state['mirrored'][th] = {
                'kanban_id': task_id,
                'brain_title': title,
                'brain_status': status,
                'mirrored_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            }
            return state['mirrored'][th]
        else:
            state['errors'].append(f'create failed for {title}: {r.stderr[:100]}')
    except Exception as e:
        state['errors'].append(f'create error for {title}: {str(e)[:100]}')
    
    return None

def run_bridge():
    """Main bridge logic."""
    if is_disabled():
        print('Bridge disabled (kill switch active)')
        return {'status': 'disabled'}
    
    state = load_state()
    
    try:
        tasks = get_brain_tasks()
    except Exception as e:
        state['errors'].append(f'brain list failed: {str(e)[:200]}')
        save_state(state)
        return {'status': 'error', 'error': str(e)[:200]}
    
    task_list = tasks if isinstance(tasks, list) else tasks.get('rows', tasks.get('tasks', []))
    
    # Filter to active tasks (not done)
    active = [t for t in task_list if t.get('status') not in ('done', 'cancelled')]
    
    mirrored_count = 0
    skipped_count = 0
    
    for task in active[:10]:  # Limit to 10 per sync
        th = task_hash(task)
        if th in state['mirrored']:
            skipped_count += 1
            continue
        result = mirror_task(task, state)
        if result:
            mirrored_count += 1
    
    # Cleanup old errors (keep last 10)
    state['errors'] = state['errors'][-10:]
    
    save_state(state)
    
    return {
        'status': 'ok',
        'active_tasks': len(active),
        'mirrored_new': mirrored_count,
        'skipped_existing': skipped_count,
        'total_mirrored': len(state['mirrored']),
        'errors': len(state['errors']),
    }

if __name__ == '__main__':
    result = run_bridge()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result.get('status') == 'error':
        sys.exit(1)
