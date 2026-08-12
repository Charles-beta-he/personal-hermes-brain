#!/usr/bin/env python3
"""Task Classifier — Classify tasks into conflict groups for parallel scheduling.

Two-phase classification:
1. Deterministic: task metadata, boundary, project, file patterns
2. Multi-model: ambiguous tasks only (optional, for precision)

Conflict group = tasks that modify same files/modules → must be serial.
Different conflict groups → can run in parallel.

v2: Boundary-aligned classification — derives conflict groups from the same
resolution order as brain_task_orchestrator.task_parallel_boundary_key(),
ensuring the classifier and the orchestrator agree on isolation boundaries.
"""
import json, subprocess, re, os, hashlib
from pathlib import Path
from collections import defaultdict

ORCHESTRATOR = Path.home() / '.hermes' / 'scripts' / 'brain_task_orchestrator.py'

# Deterministic classification rules (legacy fallback)
BOUNDARY_TO_GROUP = {
    'workspace:/Users/charles/.hermes': 'hermes-core',
    'workspace:/Users/charles/Desktop/folder/work/uvisa-app-2.0': 'uvisa-frontend',
    'workspace:/Users/charles/Desktop/folder/work/uvisa-backend': 'uvisa-backend',
    'project:hermes-skill-tree': 'hermes-skills',
    'project:local-brain-task-orchestration': 'brain-orchestration',
    'project:hermes-capability-router': 'hermes-router',
}

# Prefix-based boundary matching (order matters: longer prefix first)
BOUNDARY_PREFIXES = [
    ('evolution:skill-learning:', 'evolution-skill-learning'),
    ('evolution:local-brain', 'evolution-local-brain'),
    ('evolution:', 'evolution-lane'),
    ('workspace:/tmp/', 'temp-workspace'),
    ('project:', 'project-other'),
]

# File pattern → conflict group
FILE_PATTERNS = {
    'hermes-core': ['~/.hermes/scripts/*.py', '~/.hermes/config/*', '~/.hermes/memory/**'],
    'hermes-skills': ['~/.hermes/skills/**'],
    'uvisa-frontend': ['**/uvisa-app-2.0/**'],
    'uvisa-backend': ['**/uvisa-backend/**'],
    'brain-orchestration': ['**/brain/**', '**/brain_task_*.py'],
}

# Lane-based grouping (fallback)
LANE_GROUPS = {
    'work': 'work-lane',
    'evolution': 'evolution-lane',
    'advisory': 'advisory-lane',
}

# Valid workspace isolation modes (must match orchestrator)
VALID_WORKSPACE_ISOLATION = {'none', 'readonly', 'copy', 'worktree'}

# Title/content patterns → inferred conflict group (for tasks without explicit metadata)
# Order matters: first match wins. Longer/more-specific patterns checked first.
INFER_CONFLICT_PATTERNS = [
    # Hermes subsystem isolation
    (r'(?i)(skill|技能)', 'hermes-skills'),
    (r'(?i)(memory|记忆)', 'hermes-memory'),
    (r'(?i)(config|配置|设置)', 'hermes-config'),
    (r'(?i)(hook|钩子)', 'hermes-hooks'),
    (r'(?i)(plugin|插件)', 'hermes-plugins'),
    (r'(?i)(gateway|网关)', 'hermes-gateway'),
    (r'(?i)(cron|定时|调度)', 'hermes-cron'),
    (r'(?i)(agent.?team|multi.?agent|多agent)', 'hermes-agent-team'),
    (r'(?i)(task.?pool|任务池|task.?boundary|任务边界|dispatch|分派)', 'hermes-taskpool'),
    (r'(?i)(orchestrat|编排)', 'hermes-orchestrator'),
    (r'(?i)(brain.?sync|sync.?brain|同步)', 'hermes-brain-sync'),
    (r'(?i)(model.?router|provider|quota|配额)', 'hermes-model-router'),
    (r'(?i)(evolution|自进化|self.?improve)', 'hermes-evolution'),
    # External project isolation
    (r'(?i)(uvisa|u-visa)', 'uvisa-app'),
    (r'(?i)(rowboat)', 'rowboat'),
]

# File path patterns → inferred conflict group (from allowed_globs or task context)
FILE_CONFLICT_PATTERNS = [
    ('~/.hermes/skills/', 'hermes-skills'),
    ('~/.hermes/config/', 'hermes-config'),
    ('~/.hermes/hooks/', 'hermes-hooks'),
    ('~/.hermes/plugins/', 'hermes-plugins'),
    ('~/.hermes/scripts/brain_task_', 'hermes-taskpool'),
    ('~/.hermes/scripts/agent_team_', 'hermes-agent-team'),
    ('~/.hermes/scripts/sync-brain', 'hermes-brain-sync'),
    ('~/.hermes/scripts/model_', 'hermes-model-router'),
    ('~/.hermes/cron/', 'hermes-cron'),
    ('~/.hermes/memory/', 'hermes-memory'),
]


def infer_conflict_group(task):
    """Infer a conflict group from task metadata when none is explicitly set.

    Uses title, concepts, project, and allowed_globs to derive a meaningful
    conflict group. This enables the boundary system to separate tasks that
    touch different subsystems even when they share a workspace.

    Returns the inferred group string, or '' if no inference can be made.
    """
    import re as _re

    # Already has explicit conflict_group — use it
    explicit = str(task.get('conflict_group') or '').strip()
    if explicit:
        return explicit

    # Try title + concepts + project
    title = str(task.get('title') or task.get('id') or '').strip()
    concepts = ' '.join(task.get('concepts', []) if isinstance(task.get('concepts'), list)
                        else str(task.get('concepts') or '').split(','))
    project = str(task.get('project') or '').strip()
    haystack = f'{title} {concepts} {project}'

    for pattern, group in INFER_CONFLICT_PATTERNS:
        if _re.search(pattern, haystack):
            return group

    # Try allowed_globs for file-level inference
    allowed_raw = str(task.get('allowed_globs') or '').strip()
    if allowed_raw:
        for path_pat, group in FILE_CONFLICT_PATTERNS:
            if path_pat in allowed_raw:
                return group

    return ''


def compute_boundary_key(task):
    """Compute the isolation boundary key matching orchestrator resolution order.

    This replicates brain_task_orchestrator.task_parallel_boundary_key()
    so that the classifier and the orchestrator produce identical boundary
    keys for the same task metadata.  Resolution order (most specific wins):
      1. explicit parallel_boundary field
      2. workspace_isolation = worktree/copy → per-task isolation
      3. conflict_group + workspace → fine-grained conflict isolation
      4. workspace → workspace-level isolation
      5. evolution lane + architecture_target
      6. project
      7. task id (self-isolating)
    """
    explicit = str(task.get('parallel_boundary') or '').strip()
    if explicit:
        return f'boundary:{explicit}'
    ws_isolation = str(task.get('workspace_isolation') or '').strip()
    if ws_isolation in ('worktree', 'copy'):
        return f'isolated:{task.get("id", "unknown")}'
    conflict = str(task.get('conflict_group') or '').strip()
    workspace = str(task.get('workspace') or '').strip()
    if conflict and workspace:
        return f'conflict:{workspace}:{conflict}'
    # v3: infer conflict_group from task metadata when workspace is shared
    # This separates tasks touching different subsystems within the same workspace
    if workspace and not conflict:
        inferred = infer_conflict_group(task)
        if inferred:
            return f'conflict:{workspace}:{inferred}'
    if workspace:
        return f'workspace:{workspace}'
    lane = str(task.get('lane') or '').strip().lower()
    arch_target = str(task.get('architecture_target') or '').strip()
    if lane == 'evolution' and arch_target:
        return f'evolution:{arch_target}'
    project = str(task.get('project') or '').strip()
    if project:
        return f'project:{project}'
    return f'task:{task.get("id", "unknown")}'


def classify_deterministic(task):
    """Phase 1: deterministic classification from task metadata.

    v2: First tries boundary-aligned classification via compute_boundary_key()
    which matches the orchestrator's resolution order. Falls back to legacy
    static mapping for backward compatibility.
    v3: Uses infer_conflict_group() to auto-derive groups from metadata.
    """
    # --- v2: boundary-aligned primary classification ---
    boundary_key = compute_boundary_key(task)

    # conflict_group: tasks with the same explicit conflict_group in the same
    # workspace are already isolated by compute_boundary_key (→ conflict:...).
    # Tasks with DIFFERENT conflict_groups get different keys and CAN run parallel.
    # This is the correct semantic for the classifier.

    # parallel_group: tasks sharing a parallel_group are explicitly cooperative
    # and may co-dispatch. Use parallel_group as the group label when present.
    parallel_group = str(task.get('parallel_group') or '').strip()
    if parallel_group:
        return f'pg:{parallel_group}'

    # For non-cooperative tasks, derive the group from the boundary key.
    # This ensures the classifier and orchestrator agree on isolation.
    return boundary_key


def classify_deterministic_legacy(task):
    """Legacy classification (pre-v2) preserved for backward compat."""
    boundary = task.get('parallel_boundary', '')
    project = task.get('project', '')
    lane = task.get('lane', '')

    # Try exact boundary mapping first
    if boundary in BOUNDARY_TO_GROUP:
        return BOUNDARY_TO_GROUP[boundary]

    # Try prefix-based boundary matching (longer prefixes first)
    for prefix, group in BOUNDARY_PREFIXES:
        if boundary.startswith(prefix):
            return group

    # Try project mapping
    if project:
        for pattern, group in FILE_PATTERNS.items():
            if project in pattern or pattern in project:
                return group

    # Fallback to lane
    if lane in LANE_GROUPS:
        return LANE_GROUPS[lane]

    # Last resort: hash-based
    return f'auto-{hashlib.sha256(boundary.encode()).hexdigest()[:6]}'

def classify_batch(tasks):
    """Classify a batch of tasks into conflict groups."""
    groups = defaultdict(list)
    for task in tasks:
        group = classify_deterministic(task)
        task['_conflict_group'] = group
        groups[group].append(task)

    return dict(groups)


def validate_boundary_consistency(tasks):
    """Cross-validate classifier groups against orchestrator boundary keys.

    Returns a dict with:
      - consistent: bool — True if all tasks' classifier groups match boundary keys
      - mismatches: list of tasks where group != boundary_key
      - stats: summary counts
    """
    mismatches = []
    for task in tasks:
        group = classify_deterministic(task)
        boundary_key = compute_boundary_key(task)
        # For parallel_group tasks, the group is 'pg:<name>' while boundary_key
        # reflects the underlying isolation. This is intentional — parallel_group
        # overrides boundary isolation. Only flag non-pg mismatches.
        is_cooperative = bool(str(task.get('parallel_group') or '').strip())
        if not is_cooperative and group != boundary_key:
            mismatches.append({
                'id': task.get('id', ''),
                'classifier_group': group,
                'boundary_key': boundary_key,
                'parallel_boundary': task.get('parallel_boundary', ''),
                'workspace': task.get('workspace', ''),
                'conflict_group': task.get('conflict_group', ''),
                'project': task.get('project', ''),
            })
    return {
        'consistent': len(mismatches) == 0,
        'mismatch_count': len(mismatches),
        'total_checked': len(tasks),
        'mismatches': mismatches,
    }


def detect_glob_overlap(globs_a, globs_b):
    """Detect whether two sets of glob patterns could match the same files.

    Conservative (fail-closed): returns True if any pattern in globs_a is a
    prefix/suffix of or contains a pattern in globs_b, or vice versa.
    Uses simple prefix/suffix containment rather than full glob evaluation
    to avoid false negatives.

    Args:
        globs_a: comma-separated glob string or list
        globs_b: comma-separated glob string or list

    Returns:
        dict with 'overlap' bool, 'reasons' list, 'patterns_a', 'patterns_b'
    """
    def _parse(g):
        if isinstance(g, list):
            return [p.strip() for p in g if p.strip()]
        return [p.strip() for p in str(g).split(',') if p.strip()]

    pa = _parse(globs_a)
    pb = _parse(globs_b)

    if not pa or not pb:
        return {'overlap': False, 'reasons': [], 'patterns_a': pa, 'patterns_b': pb}

    reasons = []
    for a in pa:
        for b in pb:
            # Exact match
            if a == b:
                reasons.append(f'exact_match:{a}')
                continue
            # One is a prefix of the other (e.g., "*.py" matches "**/*.py")
            a_base = a.replace('**', '').replace('*', '').rstrip('/')
            b_base = b.replace('**', '').replace('*', '').rstrip('/')
            if a_base and b_base:
                # Containment check: if the stripped forms overlap
                if a_base.startswith(b_base) or b_base.startswith(a_base):
                    reasons.append(f'prefix_overlap:{a}~{b}')
            # Wildcard overlap: *.py overlaps with test_*.py
            a_ext = a.split('.')[-1] if '.' in a else ''
            b_ext = b.split('.')[-1] if '.' in b else ''
            if a_ext and b_ext and a_ext == b_ext and ('*' in a or '*' in b):
                reasons.append(f'ext_overlap:{a}~{b}')

    return {
        'overlap': len(reasons) > 0,
        'reasons': reasons,
        'patterns_a': pa,
        'patterns_b': pb,
    }


def check_parallel_file_conflicts(tasks):
    """Check for file-level conflicts among tasks scheduled for parallel dispatch.

    Even when tasks have different boundary keys, their allowed_globs could
    match overlapping files. This function detects such cases.

    Args:
        tasks: list of task dicts (must have _conflict_group set via classify_batch)

    Returns:
        dict with 'conflicts' list and 'safe_pairs' count
    """
    conflicts = []
    safe_pairs = 0

    # Group tasks by boundary key (tasks in same group are already serial)
    by_group = defaultdict(list)
    for t in tasks:
        group = t.get('_conflict_group', classify_deterministic(t))
        by_group[group].append(t)

    groups = list(by_group.keys())
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            ga, gb = groups[i], groups[j]
            tasks_a = by_group[ga]
            tasks_b = by_group[gb]

            # Check glob overlap between the two groups
            globs_a = ','.join(str(t.get('allowed_globs', '') or '') for t in tasks_a)
            globs_b = ','.join(str(t.get('allowed_globs', '') or '') for t in tasks_b)

            overlap = detect_glob_overlap(globs_a, globs_b)
            if overlap['overlap']:
                conflicts.append({
                    'group_a': ga,
                    'group_b': gb,
                    'tasks_a': [t.get('id', '') for t in tasks_a],
                    'tasks_b': [t.get('id', '') for t in tasks_b],
                    'reasons': overlap['reasons'],
                })
            else:
                safe_pairs += 1

    return {
        'total_group_pairs': len(groups) * (len(groups) - 1) // 2,
        'conflicts': conflicts,
        'conflict_count': len(conflicts),
        'safe_pairs': safe_pairs,
    }


def boundary_health_check(tasks):
    """Audit boundary system health across all tasks.

    Checks for:
    1. Tasks without any boundary key derivation possible
    2. Boundary key consistency between classifier and orchestrator
    3. File-level conflicts among parallel-schedulable tasks
    4. Tasks with stale/conflicting metadata

    Args:
        tasks: list of task dicts

    Returns:
        dict with health status and issues
    """
    issues = []
    boundary_keys = defaultdict(list)

    for task in tasks:
        tid = task.get('id', 'unknown')
        key = compute_boundary_key(task)
        boundary_keys[key].append(tid)

        # Check for tasks with no useful metadata for boundary derivation
        has_explicit = bool(str(task.get('parallel_boundary', '')).strip())
        has_ws = bool(str(task.get('workspace', '')).strip())
        has_project = bool(str(task.get('project', '')).strip())
        has_isolation = str(task.get('workspace_isolation', '')).strip() in ('worktree', 'copy')

        if not any([has_explicit, has_ws, has_project, has_isolation]):
            issues.append({
                'type': 'no_boundary_metadata',
                'task_id': tid,
                'key': key,
                'severity': 'warning',
            })

        # Check for conflicting isolation metadata
        if str(task.get('workspace_isolation', '')).strip() == 'worktree' and \
           str(task.get('parallel_group', '')).strip():
            issues.append({
                'type': 'isolation_vs_cooperative_conflict',
                'task_id': tid,
                'reason': 'workspace_isolation=worktree conflicts with parallel_group',
                'severity': 'error',
            })

    # Check consistency
    consistency = validate_boundary_consistency(tasks)

    # Check file conflicts
    classify_batch(tasks)  # Sets _conflict_group
    file_conflicts = check_parallel_file_conflicts(tasks)

    return {
        'total_tasks': len(tasks),
        'unique_boundaries': len(boundary_keys),
        'boundary_distribution': {k: len(v) for k, v in boundary_keys.items()},
        'consistency': consistency,
        'file_conflicts': file_conflicts,
        'issues': issues,
        'healthy': len(issues) == 0 and consistency['consistent'] and file_conflicts['conflict_count'] == 0,
    }


def get_parallel_schedule(tasks, max_groups=3):
    """Get a parallel schedule: N groups running in parallel, each group serial.

    v2: Uses boundary-aligned classification so that the schedule respects the
    same isolation semantics as the orchestrator's select_parallel_dispatch().
    """
    groups = classify_batch(tasks)

    # Sort groups by total priority score (highest first)
    group_scores = {}
    for group, group_tasks in groups.items():
        score = sum(int(t.get('score', 0)) for t in group_tasks)
        group_scores[group] = score

    sorted_groups = sorted(group_scores.keys(), key=lambda g: group_scores[g], reverse=True)

    # Select top N groups for parallel execution
    selected_groups = sorted_groups[:max_groups]

    schedule = []
    for group in selected_groups:
        group_tasks = groups[group]
        # Sort within group by priority
        group_tasks.sort(key=lambda t: int(t.get('score', 0)), reverse=True)
        schedule.append({
            'conflict_group': group,
            'task_count': len(group_tasks),
            'tasks': [{'id': t['id'][:40], 'title': t.get('title', '')[:50], 'score': t.get('score', 0)} for t in group_tasks],
            'execution': 'serial',  # within group
        })

    # Remaining groups (deferred)
    deferred = []
    for group in sorted_groups[max_groups:]:
        deferred.append({
            'conflict_group': group,
            'task_count': len(groups[group]),
            'reason': 'max_groups_cap',
        })

    return {
        'total_tasks': len(tasks),
        'total_groups': len(groups),
        'selected_groups': len(selected_groups),
        'deferred_groups': len(deferred),
        'schedule': schedule,
        'deferred': deferred,
    }


def show_classification():
    """Show classification of all dispatchable tasks."""
    r = subprocess.run(
        ['python3', str(ORCHESTRATOR), 'list', '--json'],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0:
        return {'error': r.stderr[:200]}

    data = json.loads(r.stdout)
    tasks = [t for t in data.get('rows', []) if t.get('dispatchable', False)]

    groups = classify_batch(tasks)
    schedule = get_parallel_schedule(tasks)
    consistency = validate_boundary_consistency(tasks)

    return {
        'dispatchable': len(tasks),
        'groups': {g: len(ts) for g, ts in groups.items()},
        'schedule': schedule,
        'boundary_consistency': consistency,
    }


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'show':
        print(json.dumps(show_classification(), indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == 'schedule':
        r = subprocess.run(['python3', str(ORCHESTRATOR), 'list', '--json'], capture_output=True, text=True, timeout=30)
        tasks = [t for t in json.loads(r.stdout).get('rows', []) if t.get('dispatchable', False)]
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        print(json.dumps(get_parallel_schedule(tasks, n), indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == 'consistency':
        r = subprocess.run(['python3', str(ORCHESTRATOR), 'list', '--json'], capture_output=True, text=True, timeout=30)
        tasks = [t for t in json.loads(r.stdout).get('rows', []) if t.get('dispatchable', False)]
        print(json.dumps(validate_boundary_consistency(tasks), indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == 'boundary-key':
        # Debug: compute boundary key for a task dict passed as JSON
        task = json.loads(sys.argv[2])
        print(json.dumps({'boundary_key': compute_boundary_key(task), 'group': classify_deterministic(task)}, indent=2))
    else:
        print('Usage: task_classifier.py [show|schedule [N]|consistency|boundary-key <json>]')
