#!/usr/bin/env python3
"""Task Continuation Manager — Handle iteration budget exhaustion with resume.

Detects "Iteration budget reached" in worker output, saves checkpoint,
and enables resume from last checkpoint instead of restart from scratch.

Max continuations: 3 (configurable via MAX_CONTINUATIONS env)
"""
import json, subprocess, time, hashlib, os
from pathlib import Path

STATE_DIR = Path.home() / '.hermes' / 'state'
CHECKPOINT_DIR = STATE_DIR / 'task_checkpoints'
MAX_CONTINUATIONS = int(os.environ.get('MAX_CONTINUATIONS', '3'))

BUDGET_SIGNALS = [
    'Iteration budget reached',
    'iteration budget reached',
    'BUDGET_EXHAUSTED',
    'max_turns reached',
    '工具调用次数限制',
    '以下步骤还没做',
]

def detect_budget_exhausted(worker_output):
    """Detect if worker hit iteration budget."""
    if not worker_output:
        return False, ''
    for signal in BUDGET_SIGNALS:
        if signal in worker_output:
            return True, signal
    return False, ''

def extract_progress(worker_output):
    """Extract completed work and remaining tasks from worker output."""
    progress = {
        'completed_steps': [],
        'remaining_steps': [],
        'files_changed': [],
        'partial_output': '',
        'error_context': '',
    }
    
    lines = worker_output.split('\n')
    collecting_remaining = False
    
    for line in lines:
        line_stripped = line.strip()
        
        # Look for "已完成" or "done" sections
        if any(kw in line_stripped for kw in ['已完成', 'Done:', 'Completed:', '✅', '✓']):
            progress['completed_steps'].append(line_stripped[:200])
        
        # Look for "未完成" or "remaining" sections
        if any(kw in line_stripped for kw in ['未完成', 'Remaining:', '还没做', 'TODO:', '⚠']):
            collecting_remaining = True
            progress['remaining_steps'].append(line_stripped[:200])
        elif collecting_remaining and line_stripped:
            if line_stripped.startswith(('- ', '* ', '1.', '2.', '3.', '4.', '5.')):
                progress['remaining_steps'].append(line_stripped[:200])
            else:
                collecting_remaining = False
        
        # Look for file changes
        if any(kw in line_stripped for kw in ['Changed:', 'Modified:', 'Created:', '文件']):
            progress['files_changed'].append(line_stripped[:200])
    
    # Get last 2000 chars as partial output context
    progress['partial_output'] = worker_output[-2000:] if len(worker_output) > 2000 else worker_output
    
    return progress

def save_checkpoint(task_id, worker_output, attempt=1):
    """Save continuation checkpoint."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    
    exhausted, signal = detect_budget_exhausted(worker_output)
    if not exhausted:
        return None
    
    progress = extract_progress(worker_output)
    
    checkpoint = {
        'task_id': task_id,
        'attempt': attempt,
        'detected_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'signal': signal,
        'progress': progress,
        'continuation_count': 0,
    }
    
    # Load existing checkpoint if any
    cp_path = CHECKPOINT_DIR / f'{hashlib.sha256(task_id.encode()).hexdigest()[:16]}.json'
    if cp_path.exists():
        existing = json.loads(cp_path.read_text())
        checkpoint['continuation_count'] = existing.get('continuation_count', 0)
        # Accumulate completed steps
        checkpoint['progress']['completed_steps'] = (
            existing.get('progress', {}).get('completed_steps', []) + 
            progress['completed_steps']
        )
        checkpoint['progress']['files_changed'] = list(set(
            existing.get('progress', {}).get('files_changed', []) + 
            progress['files_changed']
        ))
    
    checkpoint['continuation_count'] += 1
    cp_path.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False))
    
    return checkpoint

def can_continue(task_id):
    """Check if task can be continued."""
    cp_path = CHECKPOINT_DIR / f'{hashlib.sha256(task_id.encode()).hexdigest()[:16]}.json'
    if not cp_path.exists():
        return True, 0  # No checkpoint = first attempt
    cp = json.loads(cp_path.read_text())
    count = cp.get('continuation_count', 0)
    return count < MAX_CONTINUATIONS, count

def build_continuation_context(task_id, original_context):
    """Build context for continuation worker."""
    cp_path = CHECKPOINT_DIR / f'{hashlib.sha256(task_id.encode()).hexdigest()[:16]}.json'
    if not cp_path.exists():
        return original_context
    
    cp = json.loads(cp_path.read_text())
    progress = cp.get('progress', {})
    
    continuation = f"""=== CONTINUATION CONTEXT ===
This is a RESUMED task. Previous attempt hit iteration budget.
Attempt: {cp.get('continuation_count', 0)}/{MAX_CONTINUATIONS}

COMPLETED STEPS (do NOT repeat):
{chr(10).join(progress.get('completed_steps', ['(none detected)']))}

FILES ALREADY CHANGED:
{chr(10).join(progress.get('files_changed', ['(none detected)']))}

REMAINING STEPS (focus on these):
{chr(10).join(progress.get('remaining_steps', ['(no remaining steps detected — verify manually)']))}

PARTIAL OUTPUT FROM PREVIOUS ATTEMPT:
{progress.get('partial_output', '')[:1500]}

=== ORIGINAL TASK CONTEXT ===
{original_context}

IMPORTANT:
1. Do NOT repeat completed steps
2. Focus on remaining steps only
3. Verify existing changes before continuing
4. Output PROOF_JSON when ALL steps are complete
"""
    return continuation

def get_checkpoint_status(task_id):
    """Get checkpoint status for a task."""
    cp_path = CHECKPOINT_DIR / f'{hashlib.sha256(task_id.encode()).hexdigest()[:16]}.json'
    if not cp_path.exists():
        return {'has_checkpoint': False, 'continuation_count': 0}
    cp = json.loads(cp_path.read_text())
    return {
        'has_checkpoint': True,
        'continuation_count': cp.get('continuation_count', 0),
        'max_continuations': MAX_CONTINUATIONS,
        'can_continue': cp.get('continuation_count', 0) < MAX_CONTINUATIONS,
        'last_signal': cp.get('signal', ''),
        'completed_steps': len(cp.get('progress', {}).get('completed_steps', [])),
        'remaining_steps': len(cp.get('progress', {}).get('remaining_steps', [])),
    }

def cleanup_checkpoint(task_id):
    """Clean up checkpoint after successful completion."""
    cp_path = CHECKPOINT_DIR / f'{hashlib.sha256(task_id.encode()).hexdigest()[:16]}.json'
    if cp_path.exists():
        cp_path.unlink()

def list_checkpoints():
    """List all active checkpoints."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoints = []
    for f in CHECKPOINT_DIR.glob('*.json'):
        try:
            cp = json.loads(f.read_text())
            checkpoints.append({
                'task_id': cp.get('task_id', 'unknown')[:50],
                'continuation_count': cp.get('continuation_count', 0),
                'max': MAX_CONTINUATIONS,
                'remaining': len(cp.get('progress', {}).get('remaining_steps', [])),
                'detected_at': cp.get('detected_at', ''),
            })
        except:
            pass
    return checkpoints

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'detect':
            # Test detection
            test = "⚠ Iteration budget reached (60/60) — response may be incomplete"
            print(f'Detect: {detect_budget_exhausted(test)}')
        elif cmd == 'list':
            cps = list_checkpoints()
            print(json.dumps(cps, indent=2, ensure_ascii=False))
        elif cmd == 'status':
            if len(sys.argv) > 2:
                print(json.dumps(get_checkpoint_status(sys.argv[2]), indent=2))
            else:
                print('Usage: task_continuation.py status <task_id>')
        elif cmd == 'test':
            # Test with sample output
            sample = """已完成:
✅ 分析了 Agent-S 代码结构
✅ 识别了 3 个关键改进点

⚠ Iteration budget reached (60/60) — response may be incomplete

由于工具调用次数限制，以下步骤还没做:
- 实现改进点 1
- 编写测试
- 更新文档"""
            exhausted, signal = detect_budget_exhausted(sample)
            print(f'Exhausted: {exhausted}, Signal: {signal}')
            progress = extract_progress(sample)
            cs = progress["completed_steps"]
            rs = progress["remaining_steps"]
            print(f'Completed: {cs}')
            print(f'Remaining: {rs}')
        else:
            print('Usage: task_continuation.py [detect|list|status <id>|test]')
    else:
        print('Usage: task_continuation.py [detect|list|status <id>|test]')
