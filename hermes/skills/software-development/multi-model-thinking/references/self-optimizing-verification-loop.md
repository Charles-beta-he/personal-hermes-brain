# Self-Optimizing Verification Loop

When multi-model verification rejects a task completion, the system enters a self-improving loop instead of simply marking FAILED.

## Flow

```
verify_with_models() rejects
    ↓ save_rejection(task_id, title, project, issues, output)
rejection history accumulated
    ↓ analyze_rejection(task_id)
patterns detected: missing_build, missing_test, missing_screenshot, missing_evidence
    ↓ generate_enhanced_criteria(original_acceptance, patterns)
acceptance criteria expanded: 4→8 (added build/test/screenshot/evidence requirements)
    ↓ update_project_profile(project, patterns)
project profile auto-learns: learned_rules + acceptance扩充
    ↓ retry with enhanced criteria (max 3 attempts)
再次 4 模型验证
    ↓ 通过 → DONE | 3次失败 → FAILED + release
```

## Implementation

```python
def save_rejection(task_id, task_title, project, issues, worker_output):
    """Save rejection for analysis and learning."""
    HISTORY_DIR = Path.home() / '.hermes' / 'state' / 'verification_history'
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        'task_id': task_id, 'title': task_title, 'project': project,
        'issues': issues, 'output_snippet': worker_output[-300:],
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }
    fpath = HISTORY_DIR / f'{hashlib.sha256(task_id.encode()).hexdigest()[:16]}.json'
    existing = json.loads(fpath.read_text()) if fpath.exists() else []
    existing.append(entry)
    fpath.write_text(json.dumps(existing, indent=2, ensure_ascii=False))

def analyze_rejection(task_id):
    """Analyze rejection history to find patterns."""
    fpath = HISTORY_DIR / f'{hashlib.sha256(task_id.encode()).hexdigest()[:16]}.json'
    entries = json.loads(fpath.read_text()) if fpath.exists() else []
    all_issues = [i for e in entries for i in e.get('issues', [])]
    patterns = {
        'missing_build': any('build' in i.lower() for i in all_issues),
        'missing_test': any('test' in i.lower() for i in all_issues),
        'missing_screenshot': any('screenshot' in i.lower() or '截图' in i.lower() for i in all_issues),
        'missing_evidence': any('evidence' in i.lower() or '验证' in i.lower() for i in all_issues),
    }
    return {'count': len(entries), 'patterns': [k for k, v in patterns.items() if v], 'issues': all_issues}

def generate_enhanced_criteria(original_criteria, rejection_analysis):
    """Generate enhanced acceptance criteria based on rejection patterns."""
    enhanced = list(original_criteria)
    patterns = rejection_analysis.get('patterns', [])
    if 'missing_build' in patterns: enhanced.append('必须提供 build 命令输出 (exit code 0)')
    if 'missing_test' in patterns: enhanced.append('必须提供 test 命令输出 (exit code 0)')
    if 'missing_screenshot' in patterns: enhanced.append('必须提供浏览器截图或 UI 验证证据')
    if 'missing_evidence' in patterns: enhanced.append('必须提供具体证据: 命令输出、文件 diff、测试结果')
    return enhanced

def update_project_profile(project, rejection_analysis):
    """Learn from rejections to improve project profile."""
    profile_path = PROFILE_DIR / f'{project}.json'
    if not profile_path.exists(): return
    profile = json.loads(profile_path.read_text())
    if 'learned_rules' not in profile: profile['learned_rules'] = []
    for pattern in rejection_analysis.get('patterns', []):
        rule = f'auto-learned: {pattern} detected in rejections'
        if rule not in profile['learned_rules']:
            profile['learned_rules'].append(rule)
    # Also expand acceptance criteria
    acceptance = profile.get('acceptance', [])
    if 'missing_build' in patterns and 'build exit 0' not in str(acceptance).lower():
        acceptance.append('build 成功 (exit 0)')
    profile['acceptance'] = acceptance
    profile_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False))
```

## Integration into Controller

In `delegate_to_worker`, after `verify_with_models` rejects:

```python
if not verification['passed']:
    save_rejection(task_id, title, project, verification['issues'], worker_output)
    rejection = analyze_rejection(task_id)
    if rejection['count'] < 3:
        enhanced = generate_enhanced_criteria(profile.get('acceptance', []), rejection)
        update_project_profile(project, rejection)
        update_status(eid, 'PENDING')  # Re-queue for retry
        append_trace(eid, {'event': 'self_optimize_retry', 'attempt': rejection['count']})
    else:
        update_status(eid, 'FAILED', error=f'Max retries: {rejection["issues"][-3:]}')
```

## Safety

- **max_retries=3**: prevents infinite retry loops
- **No scope expansion**: only enhances evidence requirements, never changes task scope
- **Intent preservation**: enhanced criteria must relate to original acceptance
- **Human escalation**: 3 failures → FAILED + release, requires human review
- **Audit trail**: all rejections saved in verification_history/ with timestamps

## Learning Output

Project profiles accumulate `learned_rules` over time:
```json
{
  "learned_rules": [
    "auto-learned: missing_build detected in rejections",
    "auto-learned: missing_test detected in rejections"
  ],
  "acceptance": [
    "build 成功 (npm run build exit 0)",
    "测试通过 (npm run test exit 0)",
    "浏览器截图验证 UI 无破损",
    "build 成功 (exit 0)"  // auto-added by learning
  ]
}
```

## Key Pitfalls

- Don't retry forever — max 3 attempts then human介入
- Enhanced criteria must be machine-checkable where possible
- Learned rules should be deduplicated (check before adding)
- Project profile updates are idempotent — safe to call multiple times
- Rejection history is per-task (by hash), not per-project
