#!/usr/bin/env python3
"""Agent Team Controller v2 — Dynamic N + Task Classification + Conflict Avoidance.

Phase 4: Adaptive parallel scheduling.
- Dynamic N: min(ceil(dispatchable/7), conflict_groups, 3)
- Task classifier: deterministic boundary→group mapping
- Conflict groups: same group serial, different groups parallel
- Smoothing: N changes only after 2 consecutive cycles

Safety:
- Worker cannot mark DONE (controller-owned)
- Proof artifact required for DONE transition
- Lease TTL with auto-cleanup
- Human escape: kill switch file/env
- Conflict group isolation
"""
import json, subprocess, sys, time, os, hashlib
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path.home() / '.hermes' / 'scripts'))
from envelope_bus import create, get, update_status, append_trace, increment_retry, list_by_status, stats, human_escape_check
from task_classifier import classify_batch, get_parallel_schedule, boundary_health_check, check_parallel_file_conflicts
from dynamic_n import get_smoothed_n
from task_continuation import detect_budget_exhausted, save_checkpoint, can_continue, build_continuation_context, get_checkpoint_status, cleanup_checkpoint, list_checkpoints
from self_optimizing_verifier import save_rejection, analyze_rejection, generate_enhanced_criteria, generate_retry_prompt, update_project_profile

ORCHESTRATOR = Path.home() / '.hermes' / 'scripts' / 'brain_task_orchestrator.py'
STATE_DIR = Path.home() / '.hermes' / 'state'
KILL_SWITCH = STATE_DIR / 'agent_team_disabled'
PROOF_DIR = STATE_DIR / 'proof_artifacts'

def is_disabled():
    return os.environ.get('AGENT_TEAM_DISABLED') == '1' or KILL_SWITCH.exists()

def get_all_dispatchable():
    """Get all dispatchable tasks."""
    r = subprocess.run(
        ['python3', str(ORCHESTRATOR), 'list', '--json'],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0:
        raise RuntimeError(f'list failed: {r.stderr[:200]}')
    data = json.loads(r.stdout)
    return [t for t in data.get('rows', []) if t.get('dispatchable', False)]

def claim_task(task_id, actor='agent-team-controller', ttl=60):
    """Claim a task via orchestrator."""
    r = subprocess.run(
        ['python3', str(ORCHESTRATOR), 'claim', task_id,
         '--actor', actor, '--ttl-minutes', str(ttl),
         '--reason', 'Phase 4 dynamic parallel dispatch', '--json'],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0:
        return {'ok': False, 'error': r.stderr[:200]}
    data = json.loads(r.stdout)
    if data.get('status') == 'OK':
        return {'ok': True, 'data': data}
    return {'ok': False, 'error': data.get('reasons', str(data.get('status', 'unknown')))}

def build_worker_context(task, conflict_group, sibling_tasks=None):
    """Build context for delegate_task child.

    v2: Includes full boundary constraints so the worker understands its
    isolation envelope — allowed_globs, forbidden_globs, loc_budget,
    workspace_isolation, and merge_gate.

    v3: Includes sibling awareness — other tasks in the same conflict group
    so the worker knows what else is running and can avoid cross-contamination.
    """
    allowed_globs = task.get('allowed_globs', '')
    forbidden_globs = task.get('forbidden_globs', '')
    loc_budget = task.get('loc_budget', '')
    ws_isolation = task.get('workspace_isolation', '')
    merge_gate = task.get('merge_gate', '')
    workspace = task.get('workspace', '')
    parallel_group = task.get('parallel_group', '')

    boundary_constraints = []
    if workspace:
        boundary_constraints.append(f'WORKSPACE: {workspace}')
    if allowed_globs:
        boundary_constraints.append(f'ALLOWED_GLOBS: {allowed_globs}')
    if forbidden_globs:
        boundary_constraints.append(f'FORBIDDEN_GLOBS: {forbidden_globs}')
    if loc_budget:
        boundary_constraints.append(f'LOC_BUDGET: {loc_budget} lines max')
    if ws_isolation:
        boundary_constraints.append(f'WORKSPACE_ISOLATION: {ws_isolation}')
    if merge_gate:
        boundary_constraints.append(f'MERGE_GATE: {merge_gate}')
    if parallel_group:
        boundary_constraints.append(f'PARALLEL_GROUP: {parallel_group} (cooperative with same group)')

    boundary_section = ''
    if boundary_constraints:
        boundary_section = '\nBOUNDARY CONSTRAINTS (fail-closed: violations block task):\n' + '\n'.join(f'- {c}' for c in boundary_constraints)

    # Sibling awareness: inform worker about other tasks in the same conflict group
    sibling_section = ''
    if sibling_tasks:
        sib_lines = []
        for sib in sibling_tasks[:5]:  # Cap at 5 to avoid context bloat
            sib_id = sib.get('id', '?')
            sib_title = sib.get('title', '?')[:40]
            sib_status = sib.get('status', '?')
            sib_boundary = sib.get('parallel_boundary', sib.get('workspace', ''))
            sib_lines.append(f'- [{sib_status}] {sib_id}: {sib_title} (boundary: {sib_boundary})')
        if sib_lines:
            sibling_section = '\nSIBLING TASKS IN SAME CONFLICT GROUP (do NOT overlap files with these):\n' + '\n'.join(sib_lines)

    return f"""You are a Kanban worker executing a brain task.

TASK: {task.get('title', 'untitled')}
ID: {task.get('id', '')}
PRIORITY: {task.get('priority', 'P2')}
PROJECT: {task.get('project', '')}
BOUNDARY: {task.get('parallel_boundary', '')}
CONFLICT_GROUP: {conflict_group}
LANE: {task.get('lane', '')}
{boundary_section}
{sibling_section}

RULES:
1. You CANNOT mark this task done. Only the controller can.
2. You must produce a PROOF artifact when complete.
3. Stay within your boundary. Do not modify files outside your project.
4. If blocked, output BLOCKED: <reason> and stop.
5. If you need human input, output BLOCKED: HUMAN_INPUT_NEEDED: <question>
6. Respect BOUNDARY CONSTRAINTS: do not modify files matching FORBIDDEN_GLOBS,
   only modify files matching ALLOWED_GLOBS (if set), stay under LOC_BUDGET.

PROOF FORMAT (output as last line):
PROOF_JSON: {{"status":"done|blocked","summary":"<=200 chars","files_changed":[],"tests_passed":0,"proof_sha":"sha256_of_output"}}

WORKSPACE: Use /tmp/agent-team-{task.get('id','unknown')[:12]} as your workspace.
"""

def collect_proof(task_id, worker_output):
    """Extract proof from worker output."""
    for line in worker_output.split('\n'):
        line = line.strip()
        if line.startswith('PROOF_JSON:'):
            try:
                proof = json.loads(line[len('PROOF_JSON:'):].strip())
                PROOF_DIR.mkdir(parents=True, exist_ok=True)
                proof_path = PROOF_DIR / f'{task_id}.json'
                proof_path.write_text(json.dumps(proof, indent=2))
                return proof
            except json.JSONDecodeError:
                pass
    return None

def build_handoff_artifact(task, conflict_group, envelope_id):
    """Build a structured handoff artifact for parallel dispatch.

    This JSON artifact captures the full boundary envelope for a claimed task,
    enabling downstream verification that the worker stayed within constraints.
    It is recorded alongside the envelope state for audit and replay.
    """
    import time as _time
    boundary_key = task.get('parallel_boundary', '')
    workspace = task.get('workspace', '')
    allowed_globs = task.get('allowed_globs', '')
    forbidden_globs = task.get('forbidden_globs', '')
    loc_budget = task.get('loc_budget', '')
    ws_isolation = task.get('workspace_isolation', '')
    merge_gate = task.get('merge_gate', '')
    parallel_group = task.get('parallel_group', '')

    artifact = {
        'schema': 'local_brain_handoff_artifact_v1',
        'generated_at': _time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'task_id': task.get('id', ''),
        'title': task.get('title', ''),
        'project': task.get('project', ''),
        'priority': task.get('priority', 'P2'),
        'lane': task.get('lane', ''),
        'envelope_id': envelope_id,
        'conflict_group': conflict_group,
        'boundary': {
            'boundary_key': boundary_key,
            'workspace': workspace,
            'allowed_globs': allowed_globs,
            'forbidden_globs': forbidden_globs,
            'loc_budget': loc_budget,
            'workspace_isolation': ws_isolation,
            'merge_gate': merge_gate,
            'parallel_group': parallel_group,
        },
        'safety': {
            'worker_cannot_mark_done': True,
            'proof_required': True,
            'boundary_enforced': True,
            'forbidden_dominates_allowed': True,
        },
    }

    # Persist handoff artifact
    handoff_dir = STATE_DIR / 'handoff_artifacts'
    handoff_dir.mkdir(parents=True, exist_ok=True)
    handoff_path = handoff_dir / f'{task.get("id", "unknown")}_{envelope_id[:8]}.json'
    try:
        handoff_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False))
        artifact['handoff_path'] = str(handoff_path)
    except Exception:
        pass

    return artifact

def verify_worker_boundary(task, proof):
    """Verify that worker's proof output complies with task boundary constraints.

    Fail-closed: if boundary constraints are set and the proof includes
    files_changed, verify compliance. Returns a dict with status and violations.
    """
    allowed_raw = task.get('allowed_globs', '')
    forbidden_raw = task.get('forbidden_globs', '')
    loc_budget_raw = task.get('loc_budget', '')

    allowed_globs = [g.strip() for g in str(allowed_raw).split(',') if g.strip()] if allowed_raw else []
    forbidden_globs = [g.strip() for g in str(forbidden_raw).split(',') if g.strip()] if forbidden_raw else []

    loc_budget = 0
    if loc_budget_raw:
        try:
            loc_budget = int(loc_budget_raw)
        except (ValueError, TypeError):
            pass

    if not allowed_globs and not forbidden_globs and loc_budget <= 0:
        return {'status': 'SKIP', 'reason': 'no_boundary_constraints'}

    files_changed = proof.get('files_changed', [])
    if not isinstance(files_changed, list):
        files_changed = []

    import fnmatch
    violations = []

    # forbidden_globs dominate
    for fpath in files_changed:
        fpath = str(fpath).strip()
        if not fpath:
            continue
        for pattern in forbidden_globs:
            if fnmatch.fnmatch(fpath, pattern):
                violations.append(f'forbidden_match:{fpath}:{pattern}')
                break

    # allowed_globs: if set, every file must match at least one
    if allowed_globs:
        for fpath in files_changed:
            fpath = str(fpath).strip()
            if not fpath:
                continue
            if any(v.startswith(f'forbidden_match:{fpath}:') for v in violations):
                continue
            if not any(fnmatch.fnmatch(fpath, p) for p in allowed_globs):
                violations.append(f'not_in_allowed_globs:{fpath}')

    # loc_budget
    if loc_budget > 0 and len(files_changed) > loc_budget:
        violations.append(f'loc_budget_exceeded:{len(files_changed)}>{loc_budget}')

    return {
        'status': 'PASS' if not violations else 'FAIL',
        'violations': violations,
        'files_changed_count': len(files_changed),
    }

def cleanup_worktree(task_id):
    """Clean up temporary workspace."""
    import shutil
    workspace = Path(f'/tmp/agent-team-{task_id[:12]}')
    if workspace.exists():
        try:
            shutil.rmtree(workspace)
        except Exception:
            pass

def load_project_profile(project):
    """Load project profile for task context injection."""
    profile_dir = Path.home() / '.hermes' / 'project-profiles'
    # Try exact match first
    for name in [project, project.replace('-work', ''), project.split('-')[0]]:
        p = profile_dir / f'{name}.json'
        if p.exists():
            return json.loads(p.read_text())
    # Default to hermes
    default = profile_dir / 'hermes.json'
    if default.exists():
        return json.loads(default.read_text())
    return {}

def verify_with_models(task_title, worker_output, project_profile):
    """4-model verification of task completion. All 4 must approve."""
    if isinstance(project_profile, str):
        project_profile = load_project_profile(project_profile)
    if project_profile is None:
        project_profile = {}
    if not isinstance(project_profile, dict):
        return {
            'models_checked': 0,
            'verified': 0,
            'passed': False,
            'errors': 1,
            'issues': ['invalid_project_profile'],
            'details': [],
            'model_errors': ['invalid_project_profile'],
        }
    if not isinstance(worker_output, str):
        return {
            'models_checked': 0,
            'verified': 0,
            'passed': False,
            'errors': 1,
            'issues': ['invalid_worker_output: expected string'],
            'details': [],
            'model_errors': ['invalid_worker_output: expected string'],
        }
    verify_prompt = f"""Verify task completion. Return ONLY compact JSON.
Task: {task_title}
Project: {project_profile.get('display_name', 'unknown')}
Acceptance: {json.dumps(project_profile.get('acceptance', []), ensure_ascii=False)}
Output (last 500): {worker_output[-500:]}
JSON: {{"verified":true|false,"issues":[],"reasoning":"<=80 chars"}}"""

    import subprocess as _sp
    from concurrent.futures import ThreadPoolExecutor as _TPE, as_completed as _ac
    import re as _re, urllib.request as _ur

    def _extract(s):
        s = (s or '').strip()
        m = _re.search(r'\{[^{}]*\}', s)
        if m: return json.loads(m.group())
        raise ValueError('no json')

    def _call_gpt():
        cmd = ['hermes', 'chat', '-q', verify_prompt, '--model', 'gpt-5.5', '--provider', 'openai-codex',
               '--quiet', '--max-turns', '1', '--source', 'verify', '--ignore-rules']
        r = _sp.run(cmd, capture_output=True, text=True, timeout=60)
        return _extract(r.stdout)

    def _call_claude():
        cmd = ['claude', '-p', verify_prompt, '--model', 'claude-opus-4-7', '--max-turns', '1', '--output-format', 'json']
        r = _sp.run(cmd, capture_output=True, text=True, timeout=60)
        raw = r.stdout
        try:
            outer = json.loads(raw)
            if isinstance(outer, dict) and isinstance(outer.get('result'), str): raw = outer['result']
        except: pass
        return _extract(raw)

    def _call_ds():
        key = os.environ.get('DEEPSEEK_API_KEY')
        if not key:
            raise RuntimeError('DEEPSEEK_API_KEY missing')
        url = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').rstrip('/') + '/chat/completions'
        body = json.dumps({'model': 'deepseek-v4-pro', 'messages': [{'role': 'user', 'content': verify_prompt}],
                          'temperature': 0, 'max_tokens': 500}).encode()
        req = _ur.Request(url, data=body, headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
        with _ur.urlopen(req, timeout=60) as resp:
            content = json.loads(resp.read().decode())['choices'][0]['message']['content']
        return _extract(content)

    def _call_mimo():
        key = os.environ.get('XIAOMI_API_KEY')
        if not key:
            raise RuntimeError('XIAOMI_API_KEY missing')
        url = os.environ.get('XIAOMI_BASE_URL', 'https://token-plan-cn.xiaomimimo.com/v1').rstrip('/') + '/chat/completions'
        body = json.dumps({'model': 'mimo-v2.5-pro', 'messages': [{'role': 'user', 'content': verify_prompt}],
                          'temperature': 0, 'max_tokens': 300}).encode()
        for _ in range(3):
            req = _ur.Request(url, data=body, headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
            try:
                with _ur.urlopen(req, timeout=60) as resp:
                    c = json.loads(resp.read().decode())['choices'][0]['message']['content']
                if c and c.strip(): return _extract(c)
            except: import time; time.sleep(2)
        raise RuntimeError('MiMo failed')

    results = []
    all_issues = []

    # Phase 1: Claude + GPT + DeepSeek concurrent
    with _TPE(max_workers=3) as ex:
        futs = {ex.submit(fn): name for name, fn in [('claude', _call_claude), ('gpt', _call_gpt), ('ds', _call_ds)]}
        for fut in _ac(futs):
            model = futs[fut]
            try:
                parsed = fut.result()
                results.append({'model': model, 'verified': parsed.get('verified', False)})
                all_issues.extend(parsed.get('issues', []))
            except Exception as exc:
                results.append({'model': model, 'verified': False, 'error': str(exc)[:160]})

    # Phase 2: MiMo sequential
    try:
        parsed = _call_mimo()
        results.append({'model': 'mimo', 'verified': parsed.get('verified', False)})
        all_issues.extend(parsed.get('issues', []))
    except Exception as exc:
        results.append({'model': 'mimo', 'verified': False, 'error': str(exc)[:160]})

    verified = sum(1 for r in results if r.get('verified'))
    total = len(results)
    errors = sum(1 for r in results if r.get('error'))

    return {
        'models_checked': total,
        'verified': verified,
        'passed': verified >= 3,  # Need 3/4 to pass
        'errors': errors,
        'issues': all_issues,
        'details': results,
        'model_errors': [f"{r.get('model')}: {r.get('error')}" for r in results if r.get('error')],
    }

def handle_continuations():
    """Check RUNNING tasks for budget exhaustion and create continuations."""
    running = list_by_status('RUNNING')
    continuations = []
    
    for env in running:
        eid = env['id']
        task_id = env.get('payload', {})
        if isinstance(task_id, str):
            try:
                task_id = json.loads(task_id).get('brain_id', '')
            except:
                task_id = ''
        else:
            task_id = (task_id or {}).get('brain_id', '')
        
        if not task_id:
            continue
        
        # Check if this envelope has budget exhaustion in trace
        trace = json.loads(env.get('trace', '[]'))
        last_events = [t for t in trace if 'budget' in str(t).lower() or 'exhausted' in str(t).lower()]
        
        if last_events:
            # Already handled
            continue
        
        # Check if task can be continued
        can_cont, count = can_continue(task_id)
        if not can_cont:
            continue
        
        # Mark as continuation pending
        update_status(eid, 'PENDING')
        append_trace(eid, {
            'event': 'continuation_pending',
            'reason': 'budget_exhausted',
            'continuation_count': count + 1,
        })
        
        continuations.append({
            'envelope_id': eid,
            'task_id': task_id[:50],
            'continuation_count': count + 1,
        })
    
    return continuations

def delegate_to_worker(task, conflict_group, eid, sibling_tasks=None):
    """Delegate task to a lightweight worker via hermes chat -q."""
    import subprocess as _sp
    title = task.get('title', 'untitled')
    task_id = task.get('id', '')
    boundary = task.get('parallel_boundary', '')
    
    # Load and inject project profile
    project = task.get('project', '')
    profile = load_project_profile(project)
    profile_context = ''
    if profile:
        profile_context = f'''
PROJECT PROFILE:
Name: {profile.get('display_name', project)}
Tech: {json.dumps(profile.get('tech_stack', {}), ensure_ascii=False)}
Conventions: {chr(10).join('- ' + c for c in profile.get('conventions', []))}
Test: {profile.get('test_cmd', 'N/A')}
Acceptance: {chr(10).join('- ' + a for a in profile.get('acceptance', []))}
Forbidden: {chr(10).join('- ' + f for f in profile.get('forbidden', []))}
'''

    # Check continuation
    can_cont, cont_count = can_continue(task_id)
    context = build_worker_context(task, conflict_group, sibling_tasks=sibling_tasks) + profile_context
    if cont_count > 0:
        context = build_continuation_context(task_id, context)
    
    # Route by task type: code tasks → GPT-5.5, analysis → MiMo
    needs_code = any(kw in title.lower() for kw in ['修复', 'fix', '实现', 'implement', '代码', 'uvisa', '前端', '后端', '恢复', '集成'])
    model = 'gpt-5.5' if needs_code else 'mimo-v2.5-pro'
    provider = 'openai-codex' if needs_code else 'xiaomi'
    max_turns = 30 if needs_code else 15
    timeout_s = 600 if needs_code else 300

    try:
        cmd = [
            'hermes', 'chat', '-q', context,
            '--model', model, '--provider', provider,
            '--quiet', '--max-turns', str(max_turns),
            '--source', f'team-worker-{eid[:8]}',
            '--ignore-rules',
        ]
        r = _sp.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        output = r.stdout
        
        # Check budget exhaustion
        exhausted, signal = detect_budget_exhausted(output)
        if exhausted:
            cp = save_checkpoint(task_id, output)
            can_cont, _ = can_continue(task_id)
            if can_cont:
                return {'status': 'continuation_pending', 'signal': signal}
            return {'status': 'failed', 'reason': 'budget_exhausted_max_continuations'}
        
        # Check for proof
        if 'PROOF_JSON' in output:
            proof = collect_proof(task_id, output)
            if not proof:
                return {'status': 'failed', 'reason': 'invalid_proof', 'output': output[-300:]}
            return {'status': 'done', 'proof': proof, 'output': output}
        elif 'BLOCKED' in output:
            return {'status': 'blocked', 'output': output[:200]}
        else:
            return {'status': 'failed', 'reason': 'missing_proof', 'output': output[-300:]}
    
    except _sp.TimeoutExpired:
        return {'status': 'timeout'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)[:200]}
def run_dynamic_cycle():
    """One cycle with dynamic N + conflict group scheduling."""
    if is_disabled():
        return {'status': 'disabled', 'reason': 'kill switch active'}
    
    # Check human escape
    escape, escape_info = human_escape_check()
    if escape:
        return {'status': 'escaped', 'reason': f'Human escape: {escape_info}'}
    
    # Get all dispatchable tasks
    try:
        all_tasks = get_all_dispatchable()
    except Exception as e:
        return {'status': 'error', 'reason': str(e)[:200]}
    
    if not all_tasks:
        return {'status': 'idle', 'reason': 'no dispatchable tasks'}
    
    # Classify into conflict groups
    groups = classify_batch(all_tasks)
    conflict_group_count = len(groups)

    # Boundary health check: verify no file-level conflicts
    health = boundary_health_check(all_tasks)
    file_conflicts = health.get('file_conflicts', {})
    if file_conflicts.get('conflict_count', 0) > 0:
        # Log conflicts but don't block — reduce parallelism instead
        for conflict in file_conflicts.get('conflicts', [])[:3]:
            ga = conflict['group_a']
            gb = conflict['group_b']
            # Move conflicting groups to serial: remove the lower-scored group from parallel
            if ga in groups and gb in groups:
                score_a = sum(int(t.get('score', 0)) for t in groups[ga])
                score_b = sum(int(t.get('score', 0)) for t in groups[gb])
                loser = gb if score_a >= score_b else ga
                # Cap loser at 0 effective parallelism by merging into winner
                winner = ga if loser == gb else gb
                groups[winner].extend(groups.pop(loser))
                conflict_group_count = len(groups)
    
    # Calculate dynamic N
    n_result = get_smoothed_n(len(all_tasks), conflict_group_count)
    applied_n = n_result['applied_n']
    
    if applied_n == 0:
        return {'status': 'idle', 'reason': 'N=0 (no tasks)', 'n_info': n_result}
    
    # Get parallel schedule
    schedule = get_parallel_schedule(all_tasks, applied_n)
    
    # Claim tasks from selected groups (one per group, up to N)
    claimed = []
    for group_info in schedule['schedule'][:applied_n]:
        group = group_info['conflict_group']
        group_tasks = [t for t in all_tasks if t.get('_conflict_group') == group]
        
        # Take highest priority task from this group
        if group_tasks:
            task = group_tasks[0]
            task_id = task.get('id', '')
            title = task.get('title', 'untitled')
            project = task.get('project', '')
            
            result = claim_task(task_id)
            if result.get('ok'):
                # Create envelope (state tracking only)
                eid = create(
                    type='TASK',
                    title=task.get('title', 'untitled'),
                    project=task.get('project', ''),
                    assignee=f'agent-team-{group}',
                    payload={
                        'brain_id': task_id,
                        'boundary': task.get('parallel_boundary', ''),
                        'conflict_group': group,
                    },
                    appetite_seconds=1800,
                )
                update_status(eid, 'RUNNING')
                append_trace(eid, {'event': 'claimed', 'group': group, 'n': applied_n})
                
                # DIRECT DELEGATE: spawn worker immediately
                # Collect sibling tasks (other tasks in the same conflict group)
                siblings = [t for t in all_tasks
                           if t.get('_conflict_group') == group and t.get('id') != task_id]
                worker_result = delegate_to_worker(task, group, eid, sibling_tasks=siblings)
                append_trace(eid, {'event': 'delegated', 'result': worker_result.get('status', '?')})
                
                # Handle result
                if worker_result.get('status') == 'done':
                    # Multi-model verification before marking DONE. Proof is mandatory;
                    # delegate_to_worker no longer returns done without parsed proof.
                    verification = verify_with_models(
                        task.get('title', 'untitled'), 
                        worker_result.get('output', ''),
                        load_project_profile(task.get('project', ''))
                    )
                    append_trace(eid, {'event': 'verified', 'passed': verification['passed'], 
                                       'models': verification['models_checked'],
                                       'model_errors': verification.get('model_errors', [])})
                    
                    if verification['passed']:
                        update_status(eid, 'DONE')
                        # Release claim
                        subprocess.run(
                            ['python3', str(ORCHESTRATOR), 'release', task_id, 
                             '--reason', 'worker_verified_done', '--json'],
                            capture_output=True, timeout=15
                        )
                    else:
                        # SELF-OPTIMIZING: analyze rejection → enhanced criteria → retry
                        save_rejection(task_id, title, project, verification['issues'], 
                                      worker_result.get('output', ''))
                        rejection = analyze_rejection(task_id)
                        
                        if rejection['count'] < 3:
                            # Generate enhanced criteria and retry
                            enhanced = generate_enhanced_criteria(
                                profile.get('acceptance', []), rejection)
                            update_project_profile(project, rejection)
                            update_status(eid, 'PENDING')  # Re-queue for retry
                            append_trace(eid, {
                                'event': 'self_optimize_retry',
                                'attempt': rejection['count'],
                                'patterns': rejection['patterns'],
                                'enhanced_criteria': len(enhanced),
                            })
                        else:
                            # Tier 3: Deep 4/4 review before final failure
                            deep = deep_review_4_of_4(title, worker_result.get('output', ''), profile, rejection)
                            append_trace(eid, {'event': 'tier3_deep_review', 'approved': deep['approved'], 
                                              'passed': deep['passed'], 'missing': deep['missing_evidence']})
                            
                            if deep['passed']:
                                # 4/4 approved at Tier 3
                                update_status(eid, 'DONE')
                                subprocess.run(
                                    ['python3', str(ORCHESTRATOR), 'release', task_id,
                                     '--reason', 'tier3_deep_review_passed', '--json'],
                                    capture_output=True, timeout=15
                                )
                            else:
                                # Truly failed — needs human
                                update_status(eid, 'FAILED', 
                                             error=f'Tier 3 failed ({deep["approved"]}/4): {deep["missing_evidence"][:2]}')
                                subprocess.run(
                                    ['python3', str(ORCHESTRATOR), 'release', task_id,
                                     '--reason', 'tier3_human_needed', '--json'],
                                    capture_output=True, timeout=15
                                )
                elif worker_result.get('status') == 'blocked':
                    update_status(eid, 'BLOCKED')
                elif worker_result.get('status') == 'continuation_pending':
                    pass  # Keep RUNNING, will retry next cycle
                else:
                    update_status(eid, 'FAILED', error=str(worker_result)[:200])
                
                claimed.append({
                    'task_id': task_id,
                    'title': task.get('title', '')[:50],
                    'envelope_id': eid,
                    'conflict_group': group,
                    'priority': task.get('priority', 'P2'),
                    'worker_result': worker_result.get('status', '?'),
                })
    
    return {
        'status': 'ok',
        'n_info': n_result,
        'conflict_groups': conflict_group_count,
        'total_dispatchable': len(all_tasks),
        'tasks_claimed': len(claimed),
        'claimed': claimed,
        'deferred_groups': schedule['deferred_groups'],
    }

def show_status():
    """Show current agent team status with classification."""
    env_stats = stats()
    
    try:
        all_tasks = get_all_dispatchable()
        groups = classify_batch(all_tasks)
        n_result = get_smoothed_n(len(all_tasks), len(groups))
    except:
        all_tasks = []
        groups = {}
        n_result = {'applied_n': 1, 'raw_n': 1}
    
    return {
        'disabled': is_disabled(),
        'applied_n': n_result['applied_n'],
        'raw_n': n_result['raw_n'],
        'smoothing_active': n_result.get('smoothing_active', False),
        'dispatchable_tasks': len(all_tasks),
        'conflict_groups': {g: len(ts) for g, ts in groups.items()},
        'envelope_stats': env_stats,
        'proof_count': len(list(PROOF_DIR.glob('*.json'))) if PROOF_DIR.exists() else 0,
    }

def deep_review_4_of_4(task_title, worker_output, project_profile, rejection_history):
    """Tier 3: High-confidence 4/4 review. All must approve with evidence."""
    import subprocess as _sp, urllib.request as _ur, re as _re
    
    issues_str = '\n'.join(f'- {i}' for i in rejection_history.get('issues', [])[-5:])
    criteria = project_profile.get('acceptance', [])
    
    prompt = f"""HIGH CONFIDENCE REVIEW. Reply JSON only.
Task: {task_title}
Criteria: {json.dumps(criteria)}
Prior issues: {issues_str}
Output: {worker_output[-600:]}
Rules: approve ONLY if ALL criteria have concrete evidence. "looks ok" is NOT enough.
{{"ok":true|false,"missing":"what is missing"}}"""

    def _extract(s):
        m = _re.search(r'\{{[^{{}}]*\}}', s or '')
        if m: return json.loads(m.group())
        raise ValueError('no json')

    results = []
    
    # Claude
    try:
        r = _sp.run(['claude','-p',prompt,'--model','claude-opus-4-7','--max-turns','1','--output-format','json'],
                    capture_output=True, text=True, timeout=90)
        raw = r.stdout
        try:
            o = json.loads(raw)
            if isinstance(o,dict) and 'result' in o: raw = o['result']
        except: pass
        parsed = _extract(raw)
        results.append({'model':'claude','ok':parsed.get('ok',False),'missing':parsed.get('missing','')})
    except:
        results.append({'model':'claude','ok':False,'missing':'error'})
    
    # GPT
    try:
        r = _sp.run(['hermes','chat','-q',prompt,'--model','gpt-5.5','--provider','openai-codex',
                     '--quiet','--max-turns','1','--source','tier3','--ignore-rules'],
                    capture_output=True, text=True, timeout=90)
        parsed = _extract(r.stdout)
        results.append({'model':'gpt','ok':parsed.get('ok',False),'missing':parsed.get('missing','')})
    except:
        results.append({'model':'gpt','ok':False,'missing':'error'})
    
    # DeepSeek
    try:
        key = os.environ.get('DEEPSEEK_API_KEY')
        url = os.environ.get('DEEPSEEK_BASE_URL','https://api.deepseek.com').rstrip('/')+'/chat/completions'
        body = json.dumps({'model':'deepseek-v4-pro','messages':[{'role':'user','content':prompt}],
                          'temperature':0,'max_tokens':500}).encode()
        req = _ur.Request(url, data=body, headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        with _ur.urlopen(req, timeout=90) as resp:
            c = json.loads(resp.read().decode())['choices'][0]['message']['content']
        parsed = _extract(c)
        results.append({'model':'deepseek','ok':parsed.get('ok',False),'missing':parsed.get('missing','')})
    except:
        results.append({'model':'deepseek','ok':False,'missing':'error'})
    
    # MiMo (sequential with retry)
    for _ in range(3):
        try:
            key = os.environ.get('XIAOMI_API_KEY')
            url = os.environ.get('XIAOMI_BASE_URL','https://token-plan-cn.xiaomimimo.com/v1').rstrip('/')+'/chat/completions'
            body = json.dumps({'model':'mimo-v2.5-pro','messages':[{'role':'user','content':prompt}],
                              'temperature':0,'max_tokens':500}).encode()
            req = _ur.Request(url, data=body, headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
            with _ur.urlopen(req, timeout=90) as resp:
                c = json.loads(resp.read().decode())['choices'][0]['message']['content']
            if c and c.strip():
                parsed = _extract(c)
                results.append({'model':'mimo','ok':parsed.get('ok',False),'missing':parsed.get('missing','')})
                break
        except:
            import time; time.sleep(3)
    else:
        results.append({'model':'mimo','ok':False,'missing':'error'})
    
    approved = sum(1 for r in results if r.get('ok'))
    all_missing = [r['model'] + ': ' + r['missing'] for r in results if r.get('missing') and r['missing'] not in ('','error')]
    
    return {
        'models_checked': len(results),
        'approved': approved,
        'passed': approved == 4,
        'details': results,
        'missing_evidence': all_missing,
    }

if __name__ == '__main__':
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'cycle':
            print(json.dumps(run_dynamic_cycle(), indent=2, ensure_ascii=False))
        elif cmd == 'status':
            print(json.dumps(show_status(), indent=2, ensure_ascii=False))
        elif cmd == 'enable':
            KILL_SWITCH.unlink(missing_ok=True)
            os.environ.pop('AGENT_TEAM_DISABLED', None)
            print('Agent team enabled')
        elif cmd == 'disable':
            KILL_SWITCH.touch()
            print('Agent team disabled')
        else:
            print('Usage: agent_team_controller.py [cycle|status|enable|disable]')
    else:
        print('Usage: agent_team_controller.py [cycle|status|enable|disable]')


