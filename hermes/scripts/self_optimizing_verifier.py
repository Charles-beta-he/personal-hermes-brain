#!/usr/bin/env python3
"""Self-Optimizing Verifier — Rejection-driven task improvement loop.

When verify_with_models rejects a task:
1. Analyze rejection issues
2. Generate improved task description with specific evidence requirements
3. Re-dispatch with enhanced acceptance criteria
4. Track rejection patterns for project profile learning

Safety: max_retries=3, no scope expansion, intent preservation.
"""
import json, subprocess, sys, time, os, hashlib
from pathlib import Path

sys.path.insert(0, str(Path.home() / '.hermes' / 'scripts'))

HISTORY_DIR = Path.home() / '.hermes' / 'state' / 'verification_history'
PROFILE_DIR = Path.home() / '.hermes' / 'project-profiles'

def save_rejection(task_id, task_title, project, issues, worker_output):
    """Save rejection for analysis and learning."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        'task_id': task_id,
        'title': task_title,
        'project': project,
        'issues': issues,
        'output_snippet': worker_output[-300:],
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    fpath = HISTORY_DIR / f'{hashlib.sha256(task_id.encode()).hexdigest()[:16]}.json'
    # Append to existing
    existing = []
    if fpath.exists():
        existing = json.loads(fpath.read_text())
    existing.append(entry)
    fpath.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    return entry

def analyze_rejection(task_id):
    """Analyze rejection history to find patterns."""
    fpath = HISTORY_DIR / f'{hashlib.sha256(task_id.encode()).hexdigest()[:16]}.json'
    if not fpath.exists():
        return {'count': 0, 'patterns': []}
    
    entries = json.loads(fpath.read_text())
    all_issues = []
    for e in entries:
        all_issues.extend(e.get('issues', []))
    
    # Categorize issues
    patterns = {
        'missing_build': any('build' in i.lower() for i in all_issues),
        'missing_test': any('test' in i.lower() for i in all_issues),
        'missing_screenshot': any('screenshot' in i.lower() or '截图' in i.lower() for i in all_issues),
        'missing_evidence': any('evidence' in i.lower() or '验证' in i.lower() for i in all_issues),
        'vague_output': any('vague' in i.lower() or '模糊' in i.lower() for i in all_issues),
        'scope_drift': any('scope' in i.lower() or '范围' in i.lower() for i in all_issues),
    }
    
    return {
        'count': len(entries),
        'patterns': [k for k, v in patterns.items() if v],
        'issues': all_issues,
    }

def generate_enhanced_criteria(original_criteria, rejection_analysis):
    """Generate enhanced acceptance criteria based on rejection patterns."""
    enhanced = list(original_criteria)  # Copy
    
    patterns = rejection_analysis.get('patterns', [])
    
    if 'missing_build' in patterns:
        enhanced.append('必须提供 build 命令输出 (exit code 0)')
    if 'missing_test' in patterns:
        enhanced.append('必须提供 test 命令输出 (exit code 0)')
    if 'missing_screenshot' in patterns:
        enhanced.append('必须提供浏览器截图或 UI 验证证据')
    if 'missing_evidence' in patterns:
        enhanced.append('必须提供具体证据: 命令输出、文件 diff、测试结果')
    if 'vague_output' in patterns:
        enhanced.append('输出必须具体: 文件名+行号+改动内容')
    if 'scope_drift' in patterns:
        enhanced.append('改动范围必须与任务描述一致')
    
    return enhanced

def generate_retry_prompt(original_title, original_context, rejection_analysis, enhanced_criteria):
    """Generate improved prompt for retry attempt."""
    issues_str = '\n'.join(f'- {i}' for i in rejection_analysis.get('issues', [])[-5:])
    
    return f"""=== RETRY TASK (attempt {rejection_analysis['count'] + 1}/3) ===

Previous attempt failed verification. Issues found:
{issues_str}

ENHANCED ACCEPTANCE CRITERIA (must satisfy ALL):
{chr(10).join(f'- {c}' for c in enhanced_criteria)}

IMPORTANT: Provide CONCRETE EVIDENCE for each criterion:
- Build: include actual command + exit code
- Test: include actual test output
- Screenshot: describe UI state or include verification
- Files: list exact files changed with line numbers

=== ORIGINAL TASK ===
{original_title}

{original_context}
"""

def update_project_profile(project, rejection_analysis):
    """Learn from rejections to improve project profile."""
    profile_path = PROFILE_DIR / f'{project}.json'
    if not profile_path.exists():
        return
    
    profile = json.loads(profile_path.read_text())
    patterns = rejection_analysis.get('patterns', [])
    
    if not patterns:
        return
    
    # Add learned rules to profile
    if 'learned_rules' not in profile:
        profile['learned_rules'] = []
    
    for pattern in patterns:
        rule = f'auto-learned: {pattern} detected in rejections'
        if rule not in profile['learned_rules']:
            profile['learned_rules'].append(rule)
    
    # Update acceptance criteria if missing
    acceptance = profile.get('acceptance', [])
    if 'missing_build' in patterns and 'build exit 0' not in str(acceptance).lower():
        acceptance.append('build 成功 (exit 0)')
    if 'missing_test' in patterns and 'test exit 0' not in str(acceptance).lower():
        acceptance.append('测试通过 (exit 0)')
    
    profile['acceptance'] = acceptance
    profile_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False))

def get_rejection_stats():
    """Get overall rejection statistics."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    total_rejections = 0
    total_tasks = 0
    pattern_counts = {}
    
    for f in HISTORY_DIR.glob('*.json'):
        entries = json.loads(f.read_text())
        total_tasks += 1
        for e in entries:
            total_rejections += 1
            for issue in e.get('issues', []):
                for pattern_name in ['build', 'test', 'screenshot', 'evidence', 'vague', 'scope']:
                    if pattern_name in issue.lower():
                        pattern_counts[pattern_name] = pattern_counts.get(pattern_name, 0) + 1
    
    return {
        'total_tasks_with_rejections': total_tasks,
        'total_rejections': total_rejections,
        'top_patterns': sorted(pattern_counts.items(), key=lambda x: -x[1])[:5],
    }

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'stats':
        print(json.dumps(get_rejection_stats(), indent=2, ensure_ascii=False))
    else:
        print('Usage: self_optimizing_verifier.py stats')
