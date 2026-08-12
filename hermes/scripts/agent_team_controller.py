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
import argparse
import json, subprocess, sys, time, os, hashlib
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path.home() / '.hermes' / 'scripts'))
from envelope_bus import create, get, update_status, append_trace, increment_retry, list_by_status, stats, human_escape_check
from task_classifier import classify_batch, get_parallel_schedule, boundary_health_check, check_parallel_file_conflicts
from dynamic_n import get_smoothed_n
from task_continuation import detect_budget_exhausted, save_checkpoint, can_continue, build_continuation_context, get_checkpoint_status, cleanup_checkpoint, list_checkpoints
from self_optimizing_verifier import save_rejection, analyze_rejection, generate_enhanced_criteria, generate_retry_prompt, update_project_profile
from uvisa_lark_work_contract import generate_acceptance_atoms, extract_lark_guid

HERMES_HOME = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes'))).expanduser()
ORCHESTRATOR = HERMES_HOME / 'scripts' / 'brain_task_orchestrator.py'
STATE_DIR = HERMES_HOME / 'state'
LOG_DIR = HERMES_HOME / 'logs'
KILL_SWITCH = STATE_DIR / 'agent_team_disabled'
PROOF_DIR = STATE_DIR / 'proof_artifacts'
WORKER_JOB_DIR = STATE_DIR / 'taskpool-workers' / 'jobs'
WORKER_LOG_DIR = LOG_DIR / 'taskpool-workers'
UVISA_CONTRACT_DIRNAME = 'uvisa_lark_contracts'

def utc_ts():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def worker_job_task_ids(claimed_items):
    ids = []
    for item in claimed_items or []:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get('task_id') or item.get('id') or '').strip()
        if task_id:
            ids.append(task_id)
    return ids


def worker_job_safe_token(value, max_len=96):
    text = str(value or '').strip() or 'batch'
    safe = ''.join(ch if ch.isalnum() or ch in '._-' else '-' for ch in text).strip('-._')
    return (safe or 'batch')[:max_len]


def worker_job_signature(claimed_items, batch_id=''):
    payload = {
        'batch_id': str(batch_id or ''),
        'task_ids': sorted(worker_job_task_ids(claimed_items)),
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def process_alive(pid, expected_cmd=None):
    try:
        pid = int(pid or 0)
    except Exception:
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return False if expected_cmd else True
    except Exception:
        return False
    if expected_cmd:
        try:
            proc = subprocess.run(
                ['ps', '-p', str(pid), '-o', 'command='],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            command = proc.stdout.strip()
        except Exception:
            return False
        if not command:
            return False
        expected_parts = [str(part) for part in expected_cmd if part]
        if not all(part in command for part in ('agent_team_controller.py', 'consume-claimed')):
            return False
        batch_id = ''
        if '--batch-id' in expected_parts:
            try:
                batch_id = expected_parts[expected_parts.index('--batch-id') + 1]
            except Exception:
                batch_id = ''
        if batch_id and batch_id not in command:
            return False
    return True


def load_worker_job(path):
    try:
        job = json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(job, dict):
            return None
        job['job_file'] = str(path)
        job['alive'] = process_alive(job.get('pid'), job.get('cmd') or [])
        return job
    except Exception:
        return None


def list_worker_jobs():
    WORKER_JOB_DIR.mkdir(parents=True, exist_ok=True)
    jobs = []
    for path in sorted(WORKER_JOB_DIR.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
        job = load_worker_job(path)
        if job:
            jobs.append(job)
    return jobs


def find_alive_worker_job_for(claimed_items, batch_id=''):
    sig = worker_job_signature(claimed_items, batch_id=batch_id)
    requested_ids = set(worker_job_task_ids(claimed_items))
    for job in list_worker_jobs():
        if not job.get('alive'):
            continue
        if job.get('signature') == sig:
            return job
        job_ids = set(job.get('task_ids') or [])
        if requested_ids and requested_ids.intersection(job_ids):
            return job
    return None


def command_worker_jobs():
    jobs = list_worker_jobs()
    return {
        'status': 'OK',
        'schema': 'taskpool_worker_async_jobs_v1',
        'generated_at': utc_ts(),
        'job_count': len(jobs),
        'alive_count': sum(1 for job in jobs if job.get('alive')),
        'jobs': jobs,
        'safety': 'status only; worker child remains the sole owner of task mutation',
    }


def start_consume_claimed_background(claimed_items, max_agents=3, batch_id=''):
    if not claimed_items:
        return {'status': 'SKIP', 'event_driven': True, 'reason': 'no claimed tasks', 'consumed_count': 0}
    if is_disabled():
        return {'status': 'SKIP', 'event_driven': True, 'reason': 'kill switch active', 'consumed_count': 0}
    escape, escape_info = human_escape_check()
    if escape:
        released = release_claimed_batch_for_escape(claimed_items, escape_info)
        return {
            'status': 'SKIP',
            'event_driven': True,
            'async_worker': False,
            'reason': f'Human escape: {escape_info}',
            'consumed_count': 0,
            'released_count': sum(1 for item in released.get('released', []) if (item.get('retry_transition') or {}).get('ok')),
            'released': released.get('released', []),
            'skipped': released.get('skipped', []),
            'safety': 'background worker not spawned; claimed handoffs released to retry to avoid claimed-without-progress wedge',
        }
    try:
        max_agents = max(1, int(max_agents or 3))
    except Exception:
        max_agents = 3
    existing = find_alive_worker_job_for(claimed_items, batch_id=batch_id)
    if existing:
        return {
            'status': 'OK',
            'event_driven': True,
            'async_worker': True,
            'already_running': True,
            'job': existing,
            'job_id': existing.get('job_id'),
            'pid': existing.get('pid'),
            'task_ids': worker_job_task_ids(claimed_items),
            'safety': 'dedupe: an alive taskpool worker job already owns this batch/task set',
        }
    WORKER_JOB_DIR.mkdir(parents=True, exist_ok=True)
    WORKER_LOG_DIR.mkdir(parents=True, exist_ok=True)
    task_ids = worker_job_task_ids(claimed_items)
    token = worker_job_safe_token(batch_id or '-'.join(task_ids[:2]) or 'batch')
    job_id = f"{time.strftime('%Y%m%dT%H%M%S', time.gmtime())}-{token}-{os.getpid()}"
    job_path = WORKER_JOB_DIR / f'{job_id}.json'
    log_path = WORKER_LOG_DIR / f'{job_id}.jsonl'
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        'consume-claimed',
        '--claimed-json',
        json.dumps(claimed_items, ensure_ascii=False),
        '--max-agents',
        str(max_agents),
        '--batch-id',
        str(batch_id or ''),
    ]
    logf = log_path.open('a', encoding='utf-8')
    proc = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT, text=True, start_new_session=True, env=os.environ.copy())
    job = {
        'schema': 'taskpool_worker_async_job_v1',
        'job_id': job_id,
        'batch_id': str(batch_id or ''),
        'task_ids': task_ids,
        'signature': worker_job_signature(claimed_items, batch_id=batch_id),
        'pid': proc.pid,
        'cmd': cmd,
        'started_at': utc_ts(),
        'job_file': str(job_path),
        'log_path': str(log_path),
        'max_agents': max_agents,
        'safety': 'background process owns claimed->running->review/retry/blocked; parent tick returns immediately; worker cannot mark done',
    }
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    job['alive'] = True
    return {
        'status': 'OK',
        'event_driven': True,
        'async_worker': True,
        'started': True,
        'job': job,
        'job_id': job_id,
        'pid': proc.pid,
        'task_ids': task_ids,
        'requested_count': len(claimed_items),
        'launched_count': 0,
        'consumed_count': 0,
        'running_count': 0,
        'reviewed_count': 0,
        'done_count': 0,
        'next_tick_requested': False,
        'safety': 'taskpool worker spawned as durable async job; parent tick does not wait for hermes chat workers',
    }


def create_worker_proof_stub(task, envelope_id='', run_id=''):
    """Create a durable pre-flight proof checkpoint before long worker execution.

    This preserves the original per-task proof gate: the stub is not completion
    proof; it only prevents timeout_without_proof from erasing execution context.
    """
    task_id = str((task or {}).get('id') or (task or {}).get('task_id') or '').strip() or 'unknown-task'
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = PROOF_DIR / 'checkpoints'
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    proof_path = checkpoint_dir / f'{worker_job_safe_token(task_id)}-{worker_job_safe_token(envelope_id or run_id or str(int(time.time())))}.json'
    payload = {
        'schema': 'taskpool_worker_proof_checkpoint_v1',
        'task_id': task_id,
        'title': str((task or {}).get('title') or ''),
        'project': str((task or {}).get('project') or ''),
        'envelope_id': str(envelope_id or ''),
        'run_id': str(run_id or ''),
        'status': 'started',
        'created_at': utc_ts(),
        'updated_at': utc_ts(),
        'checkpoints_required': ['stub', 'structure_map', 'concept_cards', 'practice_tasks', 'final_notes'],
        'completed_checkpoints': ['stub'],
        'acceptance_preserved': True,
        'safety': 'checkpoint only; not sufficient for review/done; final PROOF_JSON remains required',
    }
    proof_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return {'status': 'OK', 'proof_stub_path': str(proof_path), 'task_id': task_id, 'checkpoint': payload}


def record_worker_heartbeat(task, *, envelope_id='', proof_stub_path='', checkpoint='worker_started', note=''):
    path = Path(proof_stub_path) if proof_stub_path else None
    if not path or not path.exists():
        stub = create_worker_proof_stub(task, envelope_id=envelope_id)
        path = Path(stub['proof_stub_path'])
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        payload = {}
    payload.setdefault('schema', 'taskpool_worker_proof_checkpoint_v1')
    payload['status'] = 'running'
    payload['updated_at'] = utc_ts()
    payload['last_heartbeat_at'] = utc_ts()
    payload['last_checkpoint'] = str(checkpoint or 'worker_started')
    if note:
        payload.setdefault('heartbeat_notes', []).append(str(note)[:500])
    payload['acceptance_preserved'] = True
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return {'status': 'OK', 'proof_stub_path': str(path), 'checkpoint': payload.get('last_checkpoint')}


def record_worker_timeout_checkpoint(task, *, envelope_id='', proof_stub_path='', reason='timeout'):
    path = Path(proof_stub_path) if proof_stub_path else None
    if not path or not path.exists():
        stub = create_worker_proof_stub(task, envelope_id=envelope_id)
        path = Path(stub['proof_stub_path'])
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        payload = {}
    payload.setdefault('schema', 'taskpool_worker_proof_checkpoint_v1')
    payload['status'] = 'timeout'
    payload['updated_at'] = utc_ts()
    payload['timeout_reason'] = str(reason or 'timeout')
    payload['partial_proof_available'] = True
    payload['acceptance_preserved'] = True
    payload['safety'] = 'timeout checkpoint only; task must retry/resume and still produce final PROOF_JSON before review/done'
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return {'status': 'timeout_with_proof_stub', 'proof_stub_path': str(path), 'task_id': payload.get('task_id') or str((task or {}).get('id') or '')}


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
        capture_output=True, text=True, timeout=90
    )
    if r.returncode != 0:
        return {'ok': False, 'error': r.stderr[:200]}
    data = json.loads(r.stdout)
    if data.get('status') == 'OK':
        return {'ok': True, 'data': data}
    return {'ok': False, 'error': data.get('reasons', str(data.get('status', 'unknown')))}


def transition_task(task_id, to_status, actor, reason, evidence=None, ttl=60, force=False):
    """Transition a brain task through the lifecycle gate."""
    cmd = [
        'python3', str(ORCHESTRATOR), 'transition', task_id,
        '--to', to_status,
        '--actor', actor,
        '--ttl-minutes', str(ttl),
        '--reason', reason,
        '--json',
    ]
    for item in evidence or []:
        cmd.extend(['--evidence', str(item)])
    if force:
        cmd.append('--force')
    try:
        transition_env = os.environ.copy()
        # Agent-team workers already own the event-driven follow-through loop.
        # Letting each lifecycle transition run the taskpool event hook recursively
        # can serialize/timeout a parallel batch before all claimed items reach
        # `running`, leaving the pool with one running task and one claimed task.
        # Disable nested hooks only for these worker-owned transitions; cron and
        # top-level operator transitions keep their normal hook behavior.
        transition_env.setdefault('HERMES_TASKPOOL_EVENT_HOOK_DISABLED', '1')
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=transition_env)
    except subprocess.TimeoutExpired as exc:
        return {
            'ok': False,
            'error': f'transition_timeout:{to_status}:{exc.timeout}s',
            'timeout': exc.timeout,
            'stdout': (exc.stdout or '')[:500] if isinstance(exc.stdout, str) else '',
            'stderr': (exc.stderr or '')[:500] if isinstance(exc.stderr, str) else '',
        }
    if r.returncode != 0:
        return {'ok': False, 'error': (r.stderr or r.stdout)[:500], 'returncode': r.returncode}
    try:
        data = json.loads(r.stdout)
    except Exception:
        data = {'raw': r.stdout[:500]}
    return {'ok': data.get('status') == 'OK', 'data': data}


def _transition_error_text(result):
    if not isinstance(result, dict):
        return str(result)
    parts = []
    for key in ('error', 'stderr', 'stdout'):
        if result.get(key):
            parts.append(str(result.get(key)))
    data = result.get('data')
    if isinstance(data, dict):
        for key in ('error', 'reason', 'reasons', 'status'):
            if data.get(key):
                parts.append(str(data.get(key)))
    if not parts:
        parts.append(str(result))
    return ' '.join(parts)


def _is_stale_claim_transition_error(result):
    text = _transition_error_text(result).lower()
    return (
        'claim-bound status requires claimed_by' in text
        or 'task claim is stale' in text
        or 'valid non-expired claim_expires_at' in text
    )


def _release_stale_claim_after_running_failure(task_id, actor, eid, running, *, source):
    """Release stale claim envelopes without counting them as worker failures.

    A stale claim is a lease cleanup condition, not an agent-quality failure. If
    we mark the envelope FAILED here, three stale leases trip human_escape and
    freeze unrelated dispatchable work. Force-release the brain task to retry and
    mark the envelope SKIPPED so the next tick can reclaim it under a fresh lease.
    """
    release = transition_task(
        task_id,
        'retry',
        actor,
        f'{source} detected stale claim before running; force-release for fresh claim',
        evidence=[f'command:agent_team_controller {source} stale_claim_release'],
        force=True,
    )
    update_status(eid, 'SKIPPED', error='stale_claim_running_transition_skipped')
    return {
        'task_id': task_id,
        'envelope_id': eid,
        'reason': 'stale_claim_running_transition_released',
        'detail': running,
        'release_transition': release,
        'envelope_status': 'SKIPPED',
        'to_status': 'retry' if release.get('ok') else 'claimed',
    }


def list_task_rows(include_done=False):
    cmd = ['python3', str(ORCHESTRATOR), 'list']
    if include_done:
        cmd.append('--include-done')
    cmd.append('--json')
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise RuntimeError(f'list failed: {(r.stderr or r.stdout)[:300]}')
    return json.loads(r.stdout).get('rows', [])


def rows_by_id(ids):
    wanted = set(ids)
    return {row.get('id'): row for row in list_task_rows(include_done=True) if row.get('id') in wanted}


def page_batch_siblings_for(row, rows=None, limit=8):
    """Return same-boundary work/Lark UI siblings for page-level batching context.

    The controller still claims/closes only the current task. Siblings are context
    so a worker can make one coherent page-level code change and report which
    acceptance atoms were covered.
    """
    boundary = str(row.get('parallel_boundary') or '').strip()
    project = str(row.get('project') or '').strip()
    task_id = str(row.get('id') or '').strip()
    if not boundary or not project:
        return []
    rows = rows if rows is not None else list_task_rows(include_done=False)
    out = []
    for other in rows:
        if str(other.get('id') or '') == task_id:
            continue
        if str(other.get('project') or '').strip() != project:
            continue
        if str(other.get('parallel_boundary') or '').strip() != boundary:
            continue
        status = str(other.get('status') or '').strip()
        if status not in {'pending', 'retry', 'claimed', 'running', 'review'}:
            continue
        title_blob = f"{other.get('id','')} {other.get('title','')}".lower()
        row_blob = f"{row.get('id','')} {row.get('title','')}".lower()
        if not (('lark' in title_blob or 'lark' in row_blob or project.startswith('uvisa')) and (row.get('lane') == 'work' or other.get('lane') == 'work')):
            continue
        out.append(other)
        if len(out) >= limit:
            break
    return out

def _looks_like_uvisa_lark_task(task):
    text = ' '.join(str(task.get(k, '') or '') for k in ('id', 'title', 'project', 'source', 'body', 'description')).lower()
    return ('lark' in text or '飞书' in text) and ('uvisa' in text or 'uvisa-admin' in text or '管理端' in text)

def ensure_uvisa_lark_contract(task):
    """Create/read the fail-closed UVISA Lark contract for a task.

    The task dict is mutated with uvisa_contract_path so downstream context,
    envelope payloads, and closeout gates all point at the same artifact.
    """
    if not _looks_like_uvisa_lark_task(task):
        return None
    existing = task.get('uvisa_contract_path')
    if existing and Path(existing).expanduser().exists():
        try:
            return json.loads(Path(existing).expanduser().read_text())
        except Exception:
            pass
    task_id = str(task.get('id', '') or '').strip()
    title = str(task.get('title', '') or task_id)
    body = str(task.get('body', '') or task.get('description', '') or '')
    lark_guid = str(task.get('lark_task_guid', '') or '')
    if not lark_guid:
        lark_guid = extract_lark_guid(task_id, title, body)
    contract = generate_acceptance_atoms(task_id=task_id, title=title, body=body, lark_task_guid=lark_guid)
    contract_data = dict(contract.__dict__)
    out_dir = STATE_DIR / UVISA_CONTRACT_DIRNAME
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = ''.join(ch if ch.isalnum() or ch in '._-' else '-' for ch in (lark_guid or task_id or 'uvisa-lark-task')).strip('-._')[:80] or 'uvisa-lark-task'
    path = out_dir / f'{safe}.contract.json'
    path.write_text(json.dumps(contract_data, ensure_ascii=False, indent=2, sort_keys=True))
    task['uvisa_contract_path'] = str(path)
    task['uvisa_contract_task_type'] = contract.task_type
    return contract_data

def re_search_lark_guid(text):
    import re as _re
    m = _re.search(r'lark[-_\s:]*([0-9a-f]{6,12})', str(text), flags=_re.I)
    return m.group(1) if m else ''

def format_uvisa_contract_context(contract, path):
    if not contract:
        return ''
    atoms = contract.get('acceptance_atoms') or []
    atom_lines = []
    for atom in atoms:
        atom_lines.append(f"- {atom.get('id')}: {atom.get('proof_type')} :: {atom.get('requirement')}")
    return f'''
UVISA LARK WORK CONTRACT (fail-closed)
CONTRACT_PATH: {path}
TASK_TYPE: {contract.get('task_type')}
REPOS: {', '.join(contract.get('repos') or [])}
BRANCH_NAMESPACE: {contract.get('branch_namespace')}
VIEWPORT: 1512x982 / 14-inch-admin
TARGET_SURFACE: {contract.get('target_surface')}
ACCEPTANCE_ATOMS:
{chr(10).join(atom_lines)}
CLOSEOUT_RULES:
- Worker cannot mark done; controller owns done transition.
- PR merge, online UI regression evidence, Lark close response, and TG evidence-directory notification are mandatory.
- Data correctness tasks require source_to_sink_equality assertion JSON.
'''

def build_execution_rules_digest(hermes_home=None, max_source_chars=1800):
    """Build compact invariant rules for execution workers using --ignore-rules.

    `--ignore-rules` intentionally skips chat context files and memory, but
    task-execution workers still need non-negotiable safety/evidence rules.
    Keep this digest compact and deterministic; do not dump full memory.
    """
    home = Path(hermes_home) if hermes_home is not None else (Path.home() / '.hermes')
    source_paths = [home / 'AGENTS.md']
    source_chunks = []
    for path in source_paths:
        try:
            if path.exists() and path.is_file():
                text = path.read_text(encoding='utf-8', errors='replace').strip()
                if text:
                    source_chunks.append(f'SOURCE {path}:\n{text[:max_source_chars]}')
        except Exception as exc:
            source_chunks.append(f'SOURCE {path}: unreadable ({exc})')

    invariants = [
        '--ignore-rules only skips chat context/memory/persona; it never bypasses tool, permission, proof, lifecycle, or task boundary gates.',
        'Preserve user/project red lines. Do not remove functionality, weaken validation, fake evidence, or mark tasks done from a worker.',
        'Use real project state and deterministic verification. If verification or required context is missing, return BLOCKED with the specific missing evidence.',
        'Stay inside declared workspace, allowed_globs, forbidden_globs, loc_budget, and merge gates. Boundary violations block closeout.',
        'Produce structured PROOF_JSON only for work actually completed and verified; advisory/model opinions are not delivery proof.',
    ]
    body = '\n'.join(f'- {item}' for item in invariants)
    sources = '\n\n'.join(source_chunks) if source_chunks else 'SOURCE: no local AGENTS.md found; invariants above still apply.'
    return f"""CANONICAL EXECUTION RULES DIGEST
{body}

{sources}
""".strip()


def _compact_task_text(value, max_chars=1200):
    """Render task-local requirements compactly for worker prompts."""
    if value is None or value == '':
        return ''
    if isinstance(value, (list, tuple)):
        lines = []
        for item in value[:12]:
            rendered = _compact_task_text(item, max_chars=300)
            if rendered:
                lines.append(f'- {rendered}')
        text = '\n'.join(lines)
    elif isinstance(value, dict):
        try:
            text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except TypeError:
            text = str(value)
    else:
        text = str(value)
    text = '\n'.join(line.rstrip() for line in text.strip().splitlines() if line.strip())
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + '… [truncated]'
    return text


def build_task_spec_section(task, max_body_chars=1800, max_field_chars=900):
    """Build a compact task-level requirements snapshot for execution workers.

    `--ignore-rules` should isolate workers from chat history/persona, not from
    the concrete requirement that was already captured into the task record.
    This section is the chat→taskpool SSOT bridge: say it once in chat, persist
    it on the task, and let workers read this deterministic snapshot.
    """
    body = _compact_task_text(task.get('body') or task.get('description'), max_body_chars)
    field_map = [
        ('OBJECTIVE', 'objective'),
        ('MISSION_OBJECTIVE', 'mission_objective'),
        ('ACCEPTANCE_CRITERIA', 'acceptance_criteria'),
        ('ACCEPTANCE_EVIDENCE', 'acceptance_evidence'),
        ('RED_LINES', 'red_lines'),
        ('NON_GOALS', 'non_goals'),
        ('EVIDENCE_REFS', 'evidence_refs'),
        ('WORKFLOW_CONTRACT', 'workflow_contract'),
    ]
    sections = []
    if body:
        sections.append(f'BODY_OR_DESCRIPTION:\n{body}')
    for label, key in field_map:
        rendered = _compact_task_text(task.get(key), max_field_chars)
        if rendered:
            sections.append(f'{label}:\n{rendered}')
    if not sections:
        return ''
    return '''
TASK-SPEC REQUIREMENTS SNAPSHOT (chat-to-task SSOT; do not ask user to repeat):
{sections}
TASK-SPEC RULES:
- Treat this snapshot as the task-level source of truth for user requirements already captured before dispatch.
- If it conflicts with global/project red lines, fail closed and return BLOCKED with the conflict.
- Do not import unrelated chat history or memory; preserve isolation while honoring these explicit requirements.
'''.format(sections='\n\n'.join(sections)).strip()


def _coerce_name_list(value):
    """Normalize comma/JSON/list skill or tool declarations into stable names."""
    if value is None or value == '':
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith('['):
            try:
                value = json.loads(text)
            except Exception:
                value = text
        if isinstance(value, str):
            return [item.strip() for item in value.split(',') if item.strip()]
    if isinstance(value, dict):
        return [str(k).strip() for k, enabled in value.items() if enabled and str(k).strip()]
    if isinstance(value, (list, tuple, set)):
        names = []
        for item in value:
            names.extend(_coerce_name_list(item))
        deduped = []
        seen = set()
        for name in names:
            if name not in seen:
                seen.add(name)
                deduped.append(name)
        return deduped
    return [str(value).strip()] if str(value).strip() else []


def _merge_name_lists(*values):
    names = []
    seen = set()
    for value in values:
        for name in _coerce_name_list(value):
            if name not in seen:
                seen.add(name)
                names.append(name)
    return names


def collect_worker_required_skills(task, profile=None):
    """Collect explicitly required worker skills from task and profile metadata."""
    profile = profile or {}
    return _merge_name_lists(
        task.get('required_skills'),
        task.get('skills'),
        profile.get('required_skills'),
        profile.get('skills'),
    )


def _configured_mcp_servers(config_path=None):
    """Best-effort list of configured MCP server names without exposing secrets."""
    path = Path(config_path) if config_path is not None else (Path.home() / '.hermes' / 'config.yaml')
    if not path.exists():
        return []
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(path.read_text(encoding='utf-8', errors='replace')) or {}
        servers = data.get('mcp_servers') if isinstance(data, dict) else None
        if isinstance(servers, dict):
            return sorted(str(name) for name in servers.keys())
    except Exception:
        pass
    # Tiny fallback parser for tests / minimal environments.
    servers = []
    in_mcp = False
    mcp_indent = None
    child_indent = None
    for raw in path.read_text(encoding='utf-8', errors='replace').splitlines():
        if raw.strip().startswith('#') or not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(' '))
        stripped = raw.strip()
        if stripped == 'mcp_servers:':
            in_mcp = True
            mcp_indent = indent
            child_indent = None
            continue
        if in_mcp:
            if mcp_indent is not None and indent <= mcp_indent:
                break
            if child_indent is None:
                child_indent = indent
            if indent != child_indent:
                continue
            if stripped.endswith(':') and ':' not in stripped[:-1]:
                servers.append(stripped[:-1])
    return sorted(name for name in servers if name)


def build_agent_card_context_pack(task, profile=None):
    """Build Agent Card context for workers.

    Default is enabled now that specialist routing is default-on. Disable with
    HERMES_ENABLE_AGENT_CARD_CONTEXT=0/off/false/no if prompt regression or
    budget pressure appears. Agent Cards remain guidance, not authority.
    """
    raw = os.environ.get('HERMES_ENABLE_AGENT_CARD_CONTEXT')
    if str(raw).strip().lower() in {'0', 'false', 'off', 'no', 'disabled'}:
        return ''
    try:
        from agent_cards_runtime import render_agent_card_context
        profile_name = None
        if isinstance(profile, dict):
            profile_name = profile.get('agent_card_profile') or profile.get('name')
        profile_name = profile_name or task.get('agent_card_profile') or task.get('recommended_profile')
        return render_agent_card_context(task, profile=profile_name, enabled=True)
    except Exception as exc:
        return f'''AGENT CARD CONTEXT UNAVAILABLE (non-blocking):
- reason: {exc}
- boundary: Agent Cards are optional guidance only; do not expand permissions.'''


def build_environment_capability_pack(task, profile=None, config_path=None, max_field_chars=900):
    """Build a compact skills/MCP/local-brain capability snapshot for workers.

    This is intentionally a capability/discovery pack, not a full chat context
    clone. MCP tools remain tool-layer capabilities; explicit skills are passed
    via CLI flags; local-brain context is limited to task/profile metadata that
    was already curated into the task handoff.
    """
    profile = profile or {}
    skills = collect_worker_required_skills(task, profile)
    mcp_tools = _merge_name_lists(
        task.get('required_mcp_tools'), task.get('mcp_tools'), task.get('required_mcp'),
        profile.get('required_mcp_tools'), profile.get('mcp_tools'), profile.get('required_mcp'),
    )
    mcp_servers = _configured_mcp_servers(config_path)
    brain_fields = []
    for label, source, key in [
        ('TASK_BRAIN', task, 'brain'),
        ('TASK_BRAIN_PROFILE', task, 'brain_profile'),
        ('TASK_ARCHITECTURE_TARGET', task, 'architecture_target'),
        ('TASK_BRAIN_CONTRACT', task, 'brain_contract'),
        ('TASK_BRAIN_CONTEXT', task, 'brain_context'),
        ('TASK_LOCAL_BRAIN_REFS', task, 'local_brain_refs'),
        ('PROFILE_BRAIN', profile, 'brain'),
        ('PROFILE_BRAIN_PROFILE', profile, 'brain_profile'),
        ('PROFILE_BRAIN_CONTRACT', profile, 'brain_contract'),
        ('PROFILE_BRAIN_CONTEXT', profile, 'brain_context'),
        ('PROFILE_LOCAL_BRAIN_REFS', profile, 'local_brain_refs'),
    ]:
        rendered = _compact_task_text(source.get(key), max_field_chars) if isinstance(source, dict) else ''
        if rendered:
            brain_fields.append(f'{label}:\n{rendered}')

    sections = []
    if skills:
        sections.append('REQUIRED_SKILLS (passed via --skills despite --ignore-rules):\n' + '\n'.join(f'- {s}' for s in skills))
    if mcp_tools:
        sections.append('REQUIRED_MCP_TOOLS (tool layer; do not fake calls):\n' + '\n'.join(f'- {t}' for t in mcp_tools))
    if mcp_servers and mcp_tools:
        sections.append('CONFIGURED_MCP_SERVERS (names only; credentials omitted):\n' + '\n'.join(f'- {s}' for s in mcp_servers[:20]))
    if brain_fields:
        sections.append('LOCAL_BRAIN_CONTEXT_PACK (curated snapshot only, not full memory):\n' + '\n\n'.join(brain_fields))
    if not sections:
        return ''
    return '''
ENVIRONMENT CAPABILITY PACK (skills/MCP/local-brain bridge; preserve isolation):
{sections}
CAPABILITY RULES:
- Explicit skills are allowed because they are scoped handoff requirements, not global preloaded skills.
- MCP availability is inherited from Hermes config/tool discovery; never fabricate MCP results without calling tools.
- Local-brain context here is a bounded curated snapshot. Do not import raw chat history or full memory dumps.
'''.format(sections='\n\n'.join(sections)).strip()


def build_worker_context(task, conflict_group, sibling_tasks=None, profile=None):
    """Build context for delegate_task child.

    v2: Includes full boundary constraints so the worker understands its
    isolation envelope — allowed_globs, forbidden_globs, loc_budget,
    workspace_isolation, and merge_gate.

    v3: Includes sibling awareness — other tasks in the same conflict group
    so the worker knows what else is running and can avoid cross-contamination.

    v4: For Lark/work UI bursts, same-boundary sibling tasks are page-batch
    acceptance atoms. The worker may implement them in the same page-level
    code slice when safe, but lifecycle closeout remains per original task.
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

    # Sibling awareness: inform worker about other tasks in the same conflict group.
    # For Lark/work UI bursts, same-boundary siblings are page-batch candidates:
    # implement together only when safe, but keep proof/closeout mapped per task.
    sibling_section = ''
    if sibling_tasks:
        sib_lines = []
        for sib in sibling_tasks[:5]:  # Cap at 5 to avoid context bloat
            sib_id = sib.get('id', '?')
            sib_title = sib.get('title', '?')[:80]
            sib_status = sib.get('status', '?')
            sib_boundary = sib.get('parallel_boundary', sib.get('workspace', ''))
            sib_lines.append(f'- [{sib_status}] {sib_id}: {sib_title} (boundary: {sib_boundary})')
        if sib_lines:
            sibling_section = '''
SIBLING TASKS IN SAME CONFLICT GROUP:
{lines}
PAGE-BATCH RULES:
- If these siblings target the same repo + route/page/module and can be verified in one browser pass, include their code changes in the same page-level slice.
- Keep each original task/GUID as an acceptance atom; do not mark sibling tasks done from this worker.
- PROOF_JSON should include page_batch_covered_task_ids when sibling acceptance atoms are covered.
- Do not batch siblings that cross repos, need BE/schema changes, have unrelated modules, or are blocked by a different release gate.
'''.format(lines='\n'.join(sib_lines))

    uvisa_contract = ensure_uvisa_lark_contract(task)
    uvisa_contract_section = format_uvisa_contract_context(uvisa_contract, task.get('uvisa_contract_path', ''))
    execution_rules_digest = build_execution_rules_digest()
    task_spec_section = build_task_spec_section(task)
    environment_capability_pack = build_environment_capability_pack(task, profile=profile)
    agent_card_context_pack = build_agent_card_context_pack(task, profile=profile)

    return f"""You are a Kanban worker executing a brain task.

{execution_rules_digest}

{task_spec_section}

{environment_capability_pack}

{agent_card_context_pack}

TASK: {task.get('title', 'untitled')}
ID: {task.get('id', '')}
PRIORITY: {task.get('priority', 'P2')}
PROJECT: {task.get('project', '')}
BOUNDARY: {task.get('parallel_boundary', '')}
CONFLICT_GROUP: {conflict_group}
LANE: {task.get('lane', '')}
{boundary_section}
{sibling_section}
{uvisa_contract_section}

RULES:
1. You CANNOT mark this task done. Only the controller can.
2. You must produce a PROOF artifact when complete.
3. Stay within your boundary. Do not modify files outside your project.
4. If blocked, output BLOCKED: <reason> and stop.
5. If you need human input, output BLOCKED: HUMAN_INPUT_NEEDED: <question>
6. Respect BOUNDARY CONSTRAINTS: do not modify files matching FORBIDDEN_GLOBS,
   only modify files matching ALLOWED_GLOBS (if set), stay under LOC_BUDGET.

PROOF FORMAT (output as last line):
PROOF_JSON: {{"status":"done|blocked","summary":"<=200 chars","files_changed":[],"tests_passed":0,"proof_sha":"sha256_of_output","acceptance_criteria_covered":[{{"criterion":"...","status":"covered|blocked","evidence":["command:...|file:...|artifact:..."],"blocker":""}}],"red_lines_status":{{"red line":"safe|violated|blocked"}},"no_red_line_violations":true,"blockers":[],"evidence":[]}}
PROOF CLOSEOUT RULES:
- For done proof, every task acceptance criterion or acceptance_evidence fallback must appear in acceptance_criteria_covered with deterministic evidence.
- For done proof, red_lines_status must be safe and no_red_line_violations must be true; otherwise output BLOCKED instead of done.
- If evidence is missing, status must be blocked with blockers explaining the missing proof.

WORKSPACE: Use {_workspace_path(task.get('id','unknown'))} as your workspace.
"""

def _extract_json_object(text):
    """Return the first balanced JSON object from text, tolerating markdown fences."""
    if not text:
        return None
    cleaned = str(text).strip()
    if cleaned.startswith('```'):
        cleaned = '\n'.join(line for line in cleaned.splitlines() if not line.strip().startswith('```')).strip()
    start = cleaned.find('{')
    if start < 0:
        return None
    in_string = False
    escape = False
    depth = 0
    for idx in range(start, len(cleaned)):
        ch = cleaned[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return cleaned[start:idx + 1]
    return None


def collect_proof(task_id, worker_output):
    """Extract proof from worker output.

    Some providers wrap or pretty-print the final proof across multiple lines.
    The proof contract says "PROOF_JSON:" must appear as the final marker, but
    not every provider keeps the JSON object on the same physical line.  Parse a
    balanced object after the marker before declaring invalid_proof.
    """
    marker = 'PROOF_JSON:'
    text = worker_output or ''
    marker_pos = text.rfind(marker)
    candidates = []
    if marker_pos >= 0:
        candidates.append(text[marker_pos + len(marker):])
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith(marker):
            candidates.append(line[len(marker):].strip())
    for candidate in candidates:
        json_text = _extract_json_object(candidate)
        if not json_text:
            continue
        try:
            proof = json.loads(json_text)
            PROOF_DIR.mkdir(parents=True, exist_ok=True)
            proof_path = PROOF_DIR / f'{task_id}.json'
            proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2))
            return proof
        except json.JSONDecodeError:
            continue
    return None


def _task_spec_items(value):
    """Return a compact list of task-level spec atoms from list/string/dict values."""
    if value is None or value == '':
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith('['):
            try:
                return _task_spec_items(json.loads(text))
            except Exception:
                pass
        return [line.strip(' -\t') for line in text.splitlines() if line.strip(' -\t')]
    if isinstance(value, dict):
        return [f'{k}: {v}' for k, v in value.items() if str(k).strip() or str(v).strip()]
    if isinstance(value, (list, tuple, set)):
        out = []
        for item in value:
            out.extend(_task_spec_items(item))
        return [item for item in out if item]
    return [str(value).strip()] if str(value).strip() else []


def _required_acceptance_items(task):
    items = _task_spec_items(task.get('acceptance_criteria'))
    if items:
        return items
    # Legacy task records often carry the acceptance atom in the older
    # acceptance_evidence field or only in the body. Use the explicit legacy
    # field as a machine-readable fallback; the full body remains prompt context
    # but is too noisy to gate mechanically.
    return _task_spec_items(task.get('acceptance_evidence'))


def _proof_acceptance_entries(value):
    if isinstance(value, dict):
        entries = []
        for criterion, detail in value.items():
            if isinstance(detail, dict):
                entry = {'criterion': str(criterion), **detail}
            else:
                entry = {'criterion': str(criterion), 'status': detail}
            entries.append(entry)
        return entries
    if isinstance(value, list):
        entries = []
        for item in value:
            if isinstance(item, dict):
                entries.append(item)
            else:
                entries.append({'criterion': str(item), 'status': 'covered'})
        return entries
    if value:
        return [{'criterion': str(value), 'status': 'covered'}]
    return []


def _entry_has_evidence(entry):
    evidence = entry.get('evidence') or entry.get('proof') or entry.get('proof_refs')
    return bool(_task_spec_items(evidence))


def _entry_is_covered(entry):
    status = str(entry.get('status') or entry.get('state') or '').strip().lower()
    return status in {'covered', 'pass', 'passed', 'done', 'verified', 'ok', 'safe'} and _entry_has_evidence(entry)


def _norm_spec_text(value):
    return ' '.join(str(value or '').lower().split())


def _entry_matches_required(entry, required_item):
    criterion = _norm_spec_text(entry.get('criterion') or entry.get('acceptance') or entry.get('requirement'))
    required = _norm_spec_text(required_item)
    if not required:
        return True
    if not criterion:
        return False
    return criterion == required or criterion in required or required in criterion


def _covered_acceptance_required_items(required_items, entries):
    remaining = list(entries)
    missing = []
    for required in required_items:
        match_index = None
        for idx, entry in enumerate(remaining):
            if _entry_matches_required(entry, required) and _entry_is_covered(entry):
                match_index = idx
                break
        if match_index is None:
            missing.append(required)
        else:
            remaining.pop(match_index)
    return missing


def _red_line_status_is_safe(red_lines_status):
    safe_values = {'safe', 'ok', 'pass', 'passed', 'no_violation', 'no_violations', 'none'}
    if isinstance(red_lines_status, dict):
        if not red_lines_status:
            return False
        return all(str(v).strip().lower() in safe_values for v in red_lines_status.values())
    if isinstance(red_lines_status, list):
        if not red_lines_status:
            return False
        for item in red_lines_status:
            if isinstance(item, dict):
                value = item.get('status') or item.get('state') or item.get('result')
            else:
                value = item
            if str(value).strip().lower() not in safe_values:
                return False
        return True
    return str(red_lines_status or '').strip().lower() in safe_values


def validate_worker_proof_against_task(task, proof):
    """Fail closed when DONE proof does not map task SSOT requirements.

    Workers may report BLOCKED with missing evidence. Only DONE proof is held to
    acceptance/red-line coverage, because accepting it lets the controller move
    toward lifecycle closeout.
    """
    proof_status = str(proof.get('status') or '').strip().lower()
    if str(proof.get('schema') or '') == 'taskpool_worker_proof_checkpoint_v1':
        return {'status': 'FAIL', 'proof_status': proof_status or 'checkpoint', 'violations': ['checkpoint_stub_is_not_completion_proof']}
    if proof_status in {'blocked', 'block'}:
        return {'status': 'PASS', 'proof_status': 'blocked', 'violations': []}

    violations = []
    acceptance_items = _required_acceptance_items(task)
    if acceptance_items:
        entries = _proof_acceptance_entries(proof.get('acceptance_criteria_covered'))
        if not entries:
            violations.append('acceptance_criteria_covered_missing')
        elif len(entries) < len(acceptance_items):
            violations.append(f'acceptance_criteria_covered_incomplete:{len(entries)}<{len(acceptance_items)}')
        if entries:
            missing_acceptance = _covered_acceptance_required_items(acceptance_items, entries)
            for missing in missing_acceptance:
                violations.append(f'acceptance_criterion_not_evidence_covered:{missing[:80]}')

    red_lines = _task_spec_items(task.get('red_lines'))
    if red_lines:
        if proof.get('no_red_line_violations') is not True:
            violations.append('red_line_no_violation_boolean_missing_or_false')
        if not _red_line_status_is_safe(proof.get('red_lines_status')):
            violations.append('red_lines_status_not_safe')

    return {
        'status': 'PASS' if not violations else 'FAIL',
        'proof_status': proof_status or 'unknown',
        'violations': violations,
        'acceptance_required_count': len(acceptance_items),
        'red_lines_required_count': len(red_lines),
    }


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
    uvisa_contract = ensure_uvisa_lark_contract(task)

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
            'uvisa_closeout_contract_required': bool(uvisa_contract),
        },
    }
    if uvisa_contract:
        artifact['uvisa_lark_contract'] = {
            'contract_path': task.get('uvisa_contract_path', ''),
            'schema': uvisa_contract.get('schema'),
            'task_type': uvisa_contract.get('task_type'),
            'acceptance_atom_ids': [a.get('id') for a in (uvisa_contract.get('acceptance_atoms') or []) if isinstance(a, dict)],
            'closeout_blockers': uvisa_contract.get('closeout_blockers') or [],
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

def _workspace_path(task_id):
    """Return a collision-resistant worker workspace path for a task id.

    Many task ids share the same date/CJK prefix (for example
    `2026-06-02-评...`).  Using only `task_id[:12]` made parallel workers share
    `/tmp/agent-team-2026-06-02-评`; one worker's cleanup could delete another
    worker's workspace between mkdir and the readiness write, producing false
    `workspace_not_ready` failures and retriggering human_escape.
    """
    raw = str(task_id or 'unknown').strip() or 'unknown'
    safe_prefix = ''.join(ch if ch.isascii() and (ch.isalnum() or ch in {'-', '_'}) else '-' for ch in raw[:24]).strip('-') or 'task'
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]
    return Path(f'/tmp/agent-team-{safe_prefix[:32]}-{digest}')


def cleanup_worktree(task_id):
    """Clean up temporary workspace."""
    import shutil
    workspace = _workspace_path(task_id)
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
        claude_model = os.environ.get('HERMES_TASKPOOL_CLAUDE_VERIFY_MODEL', 'claude-opus-4-8')
        cmd = ['claude', '-p', verify_prompt, '--model', claude_model, '--max-turns', '1', '--output-format', 'json']
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

def _timeout_text(value):
    if value is None:
        return ''
    if isinstance(value, bytes):
        return value.decode(errors='replace')
    return str(value)


def _timeout_exc_output(exc):
    """Return stdout/stderr text carried by subprocess.TimeoutExpired."""
    stdout = _timeout_text(getattr(exc, 'stdout', None) or getattr(exc, 'output', None))
    stderr = _timeout_text(getattr(exc, 'stderr', None))
    return stdout, stderr


def _is_no_output_timeout(output, stderr):
    return not _timeout_text(output).strip() and not _timeout_text(stderr).strip()


def _detect_infra_failure(output, stderr=''):
    """Detect infrastructure-level failures that justify immediate model fallback.

    Returns (is_infra, category) where category is a short label for tracing.
    These are NOT task-level failures (bad code, missing proof) — they are
    platform/SDK/network failures that waste the full timeout budget.
    """
    combined = (output or '') + '\n' + (stderr or '')
    combined_l = combined.lower()
    # Codex SDK null-response crash (150 occurrences in one session 2026-05-28)
    if 'SDK parse_response crashed on null response' in combined:
        return True, 'codex_sdk_null_response'
    # MCP server connection failures (repeated retry loops burning 7+ seconds)
    if combined.count('MCP server') > 3 and 'failed' in combined:
        return True, 'mcp_server_connection_loop'
    # OpenAI client closed / recreation
    if 'Detected closed shared OpenAI client' in combined and 'recreating' in combined:
        return True, 'openai_client_closed'
    # Codex-specific auth/quota errors
    if 'openai-codex' in combined and ('401' in combined or '429' in combined or '503' in combined):
        return True, 'codex_auth_or_quota'
    # Provider-generic auth/quota/rate-limit errors. These are infrastructure
    # failures even when the active provider is not openai-codex (for example
    # xiaomi/MiMo returning "HTTP 429: Too many requests"). Without this, the
    # controller misclassifies quota exhaustion as a task-level missing-proof
    # failure, leaves the brain task running, and trips human_escape.
    if (
        'http 429' in combined_l
        or 'too many requests' in combined_l
        or 'ratelimiterror' in combined_l
        or 'rate limit' in combined_l
        or 'quota exceeded' in combined_l
        or 'insufficient quota' in combined_l
        or "you're out of extra usage" in combined_l
        or 'out of extra usage' in combined_l
    ):
        return True, 'provider_rate_limit_or_quota'
    if (
        'http 401' in combined_l
        or 'error code: 401' in combined_l
        or 'unauthorized' in combined_l
        or 'missing api key' in combined_l
        or 'not configured' in combined_l
        or 'no credentials' in combined_l
    ):
        return True, 'provider_auth_or_config'
    return False, ''


def _verify_workspace_ready(task_id):
    """Verify workspace directory exists and is accessible before spawning worker.

    Returns (ok, workspace_path, error_msg).
    """
    ws = _workspace_path(task_id)
    if not ws.exists():
        try:
            ws.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, str(ws), f'mkdir failed: {e}'
    # Check writability
    test_file = ws / '.worker_ready_test'
    try:
        test_file.write_text('ok')
        test_file.unlink()
    except Exception as e:
        return False, str(ws), f'workspace not writable: {e}'
    return True, str(ws), ''


def _is_advisory_analysis_task(task, title_l='', project_l=''):
    """Return True for reference-review / evaluation tasks that should not start on codegen models.

    External-framework evaluations often mention "Hermes", "worker", or "control-plane"
    because they map ideas back to Hermes.  Treating those words as code markers routes the
    task to expensive codegen workers, which repeatedly timed out without final proof.
    """
    title_l = title_l or str(task.get('title') or '').lower()
    project_l = project_l or str(task.get('project') or '').lower()
    body_l = str(task.get('body') or task.get('description') or '').lower()
    combined = '\n'.join([title_l, project_l, body_l])
    advisory_markers = [
        '评估', '参考价值', 'reference review', 'framework evaluation', 'external framework',
        'advisory', 'analysis', 'analyze', '调研', '研究', 'gap analysis', 'mapping', '对 hermes',
    ]
    implementation_markers = [
        '实现', '修复', '修改代码', '落地实现', 'code change', 'patch', 'edit file',
        'write code', 'implement', 'fix bug', '变更源码', '提交代码',
    ]
    return any(marker in combined for marker in advisory_markers) and not any(marker in combined for marker in implementation_markers)


def _worker_needs_codegen(task, title_l='', project_l=''):
    """Classify whether a worker should start with codegen providers."""
    title_l = title_l or str(task.get('title') or '').lower()
    project_l = project_l or str(task.get('project') or '').lower()
    if _is_advisory_analysis_task(task, title_l=title_l, project_l=project_l):
        return False
    code_markers = [
        '修复', 'fix', '实现', 'implement', '代码', 'uvisa', '前端', '后端', '恢复', '集成',
        'lark', 'admin', '管理后台', '用户端', '页面', 'ui', '下拉', '弹窗', '抽屉', '复刻',
        '回测', '接口', 'api', 'backend', 'frontend', 'taskpool', 'hermes', 'telemetry',
        'control-plane', '控制面', 'gate', 'worker', 'cron',
    ]
    return ('uvisa' in project_l) or ('hermes-agent' in project_l) or any(kw in title_l for kw in code_markers)


def multimodel_conductor_mode(default='apply'):
    """Return multimodel conductor mode: off, shadow, or apply.

    apply is default: worker proofs get a multi-model advisory certification
    packet before the controller moves the task to review. The packet never
    grants lifecycle/write authority; review->done remains separately gated.
    """
    raw = os.environ.get('HERMES_MULTIMODEL_CONDUCTOR_MODE') or os.environ.get('HERMES_MULTIMODEL_CONDUCTOR') or default
    mode = str(raw or '').strip().lower()
    if mode in {'0', 'false', 'off', 'no', 'disabled'}:
        return 'off'
    if mode in {'1', 'true', 'yes', 'on'}:
        return 'apply'
    if mode not in {'off', 'shadow', 'apply'}:
        return 'apply'
    return mode


def run_multimodel_conductor(task, worker_output, project_profile, worker_profile_name='', mode=None):
    """Run default-on advisory multi-model certification for worker proof.

    This is not a done/write authority. It returns a packet attached to the
    worker proof and trace. If providers fail, the packet records degraded
    certification instead of fabricating approval.
    """
    mode = multimodel_conductor_mode() if mode is None else str(mode or 'apply').lower()
    packet: dict = {
        'schema': 'hermes_multimodel_conductor_v1',
        'mode': mode,
        'status': 'skipped' if mode == 'off' else 'pending',
        'profile': worker_profile_name or '',
        'authority': 'advisory_only_no_lifecycle_or_write_authority',
    }
    if mode == 'off':
        packet['reason'] = 'disabled_by_env'
        return packet
    try:
        verdict = verify_with_models(str(task.get('title') or 'untitled'), worker_output, project_profile or {})
        packet.update({
            'status': 'certified' if verdict.get('passed') else 'not_certified',
            'passed': bool(verdict.get('passed')),
            'verified': verdict.get('verified', 0),
            'models_checked': verdict.get('models_checked', 0),
            'errors': verdict.get('errors', 0),
            'issues': verdict.get('issues', []),
            'details': verdict.get('details', []),
            'model_errors': verdict.get('model_errors', []),
        })
    except Exception as exc:
        packet.update({
            'status': 'degraded',
            'passed': False,
            'errors': 1,
            'model_errors': [str(exc)[:200]],
        })
    return packet


def conductor_done_closeout_mode(default='apply'):
    """Return conductor-authorized closeout mode: off, shadow, or apply.

    apply is default after explicit operator authorization. It is narrow:
    only review -> done for a task that already produced a valid proof and a
    certified multimodel conductor packet.
    """
    raw = os.environ.get('HERMES_CONDUCTOR_DONE_CLOSEOUT_MODE') or os.environ.get('HERMES_CONDUCTOR_DONE_CLOSEOUT') or default
    mode = str(raw or '').strip().lower()
    if mode in {'0', 'false', 'off', 'no', 'disabled'}:
        return 'off'
    if mode in {'1', 'true', 'yes', 'on'}:
        return 'apply'
    if mode not in {'off', 'shadow', 'apply'}:
        return 'apply'
    return mode


def _canonical_digest(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def build_conductor_done_authorization(task_id, proof, proof_path, ttl_seconds=900, mode=None):
    """Build a digest-bound authorization packet for narrow review->done closeout."""
    mode = conductor_done_closeout_mode() if mode is None else str(mode or 'apply').lower()
    conductor = proof.get('multimodel_conductor') if isinstance(proof, dict) else None
    packet: dict = {
        'schema': 'hermes_conductor_done_authorization_v1',
        'mode': mode,
        'task_id': task_id,
        'previous_status': 'review',
        'target_status': 'done',
        'authority': 'narrow_review_to_done_only_no_external_side_effects',
        'artifact': f'artifact:{proof_path}',
        'issued_at': utc_ts(),
        'ttl_seconds': ttl_seconds,
        'authorized': False,
        'reasons': [],
    }
    if mode == 'off':
        packet['reasons'].append('disabled_by_env')
        return packet
    if not isinstance(proof, dict) or not proof:
        packet['reasons'].append('missing_proof')
        return packet
    if not isinstance(conductor, dict):
        packet['reasons'].append('missing_multimodel_conductor')
        return packet
    if conductor.get('status') != 'certified' or not conductor.get('passed'):
        packet['reasons'].append('conductor_not_certified')
        return packet
    if int(conductor.get('verified') or 0) < 3:
        packet['reasons'].append('conductor_verified_below_3')
        return packet
    packet['proof_digest'] = _canonical_digest(proof)
    packet['conductor_digest'] = _canonical_digest(conductor)
    auth_basis = {
        'task_id': task_id,
        'previous_status': 'review',
        'target_status': 'done',
        'proof_digest': packet['proof_digest'],
        'conductor_digest': packet['conductor_digest'],
        'artifact': str(proof_path),
    }
    packet['authorization_id'] = _canonical_digest(auth_basis)
    packet['authorized'] = True
    packet['reasons'].append('certified_conductor_bound_to_proof_digest')
    return packet


def apply_conductor_done_closeout(task_id, actor, eid, proof, proof_path, *, mode=None, source='agent_team_controller'):
    """Apply digest-bound conductor closeout for exactly one review->done transition."""
    auth = build_conductor_done_authorization(task_id, proof, proof_path, mode=mode)
    result = {
        'schema': 'hermes_conductor_done_closeout_v1',
        'mode': auth.get('mode'),
        'task_id': task_id,
        'authorization': auth,
        'write_executed': False,
        'readback_verified': False,
        'status': 'skipped',
    }
    append_trace(eid, {'event': 'conductor_done_authorization', 'authorization': auth})
    if not auth.get('authorized'):
        result['reason'] = ','.join(auth.get('reasons') or ['not_authorized'])
        return result
    if auth.get('mode') == 'shadow':
        result['status'] = 'shadow_authorized_not_executed'
        return result
    current = rows_by_id([task_id]).get(task_id) or {}
    current_status = str(current.get('status') or '').strip()
    if current_status == 'done':
        result.update({'status': 'already_done', 'write_executed': False, 'readback_verified': True})
        return result
    if current_status != 'review':
        result.update({'status': 'skipped_current_status_not_review', 'current_status': current_status})
        return result
    transition = transition_task(
        task_id,
        'done',
        actor,
        f'{source} conductor-certified proof authorized review->done closeout',
        evidence=[
            f'artifact:{proof_path}',
            f'proof:sha256:{auth.get("proof_digest")}',
            f'conductor:sha256:{auth.get("conductor_digest")}',
            f'authorization:{auth.get("authorization_id")}',
        ],
    )
    result['transition'] = transition
    if not transition.get('ok'):
        result.update({'status': 'transition_failed', 'reason': str(transition)[:300]})
        return result
    readback = rows_by_id([task_id]).get(task_id) or {}
    result['readback_status'] = readback.get('status')
    result['write_executed'] = True
    result['readback_verified'] = readback.get('status') == 'done'
    result['status'] = 'done_write_verified' if result['readback_verified'] else 'readback_mismatch'
    append_trace(eid, {'event': 'conductor_done_closeout_result', 'result': result})
    return result


_PROFILE_PROVIDER_STATUS_CACHE = {}


def _profile_provider_status(profile_name):
    """Best-effort provider auth readiness for a Hermes named profile.

    Uses `hermes -p <profile> doctor` because provider auth can live in profile
    homes and OAuth stores. Cached per controller process; failure is fail-open
    for providers without an explicit auth signal, but fail-closed for Gemini to
    avoid known routed-profile OAuth misses.
    """
    profile_name = str(profile_name or '').strip()
    if not profile_name:
        return {}
    if profile_name in _PROFILE_PROVIDER_STATUS_CACHE:
        return _PROFILE_PROVIDER_STATUS_CACHE[profile_name]
    status = {'profile': profile_name, 'doctor_ok': False, 'openai_codex': None, 'google_gemini': None}
    try:
        r = subprocess.run(
            ['hermes', '-p', profile_name, 'doctor'],
            capture_output=True,
            text=True,
            timeout=25,
        )
        output = (r.stdout or '') + '\n' + (r.stderr or '')
        status['doctor_ok'] = r.returncode == 0
        status['openai_codex'] = '✓ OpenAI Codex auth' in output
        status['google_gemini'] = '✓ Google Gemini OAuth' in output
    except Exception as exc:
        status['error'] = str(exc)
    _PROFILE_PROVIDER_STATUS_CACHE[profile_name] = status
    return status


def _provider_available_for_worker_profile(profile_name, provider):
    """Return whether provider is ready under the routed worker profile."""
    provider = str(provider or '').strip()
    profile_name = str(profile_name or '').strip()
    if not profile_name:
        return True
    status = _profile_provider_status(profile_name)
    if provider == 'google-gemini-cli':
        return status.get('google_gemini') is True
    if provider == 'openai-codex':
        # Codex is the primary routed-profile provider; require positive auth
        # when a profile is explicitly used so routing does not create an auth
        # regression hidden behind fallbacks.
        return status.get('openai_codex') is True
    return True


def _filter_model_chain_for_worker_profile(model_chain, profile_name):
    """Drop providers known unavailable in the routed worker profile."""
    profile_name = str(profile_name or '').strip()
    if not profile_name:
        return model_chain, []
    filtered = []
    dropped = []
    for entry in model_chain:
        model, provider, *_ = entry
        if _provider_available_for_worker_profile(profile_name, provider):
            filtered.append(entry)
        else:
            dropped.append({'model': model, 'provider': provider, 'reason': 'profile_provider_not_ready'})
    return (filtered or model_chain), dropped


def delegate_to_worker(task, conflict_group, eid, sibling_tasks=None):
    """Delegate task to a lightweight worker via hermes chat -q."""
    import subprocess as _sp
    title = task.get('title', 'untitled')
    task_id = task.get('id', '')
    boundary = task.get('parallel_boundary', '')
    
    # Load and inject project profile
    project = task.get('project', '')
    profile = load_project_profile(project)
    agent_card_routing = {'mode': 'unavailable', 'applies': False, 'chosen_profile': ''}
    worker_profile_name = ''
    try:
        from agent_cards_runtime import routing_decision
        current_profile = str(task.get('assignee') or task.get('claimed_by') or '')
        agent_card_routing = routing_decision(task, current_profile=current_profile)
        worker_profile_name = str(agent_card_routing.get('chosen_profile') or '')
        task['agent_card_routing'] = agent_card_routing
        if worker_profile_name:
            task['agent_card_profile'] = worker_profile_name
        append_trace(eid, {'event': 'agent_card_routing_decision', **agent_card_routing})
    except Exception as exc:
        agent_card_routing = {'mode': 'error', 'applies': False, 'chosen_profile': '', 'error': str(exc)}
        append_trace(eid, {'event': 'agent_card_routing_error', 'error': str(exc)})
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
    profile_for_context = dict(profile or {})
    if worker_profile_name:
        profile_for_context['agent_card_profile'] = worker_profile_name
    required_skills = collect_worker_required_skills(task, profile_for_context)
    context = build_worker_context(task, conflict_group, sibling_tasks=sibling_tasks, profile=profile_for_context) + profile_context
    if cont_count > 0:
        context = build_continuation_context(task_id, context)
    
    # Route by task type: code/product tasks prefer stronger code models; advisory
    # analysis prefers cheaper/reliable analysis models first.  Never rely on a
    # single provider: one-provider chains caused retry storms when MiMo returned
    # HTTP 429 / timeout under parallel load.  Claude Code is intentionally not
    # in the default chain while local smoke checks report "out of extra usage".
    project_l = str(task.get('project') or '').lower()
    title_l = title.lower()
    needs_code = _worker_needs_codegen(task, title_l=title_l, project_l=project_l)
    # Fallback chain: each entry is (model, provider, max_turns, timeout_s).
    # Keep timeouts bounded; infra failures fall through to the next provider.
    if needs_code:
        model_chain = [
            ('gpt-5.5', 'openai-codex', 25, 500),
            ('gemini-3-flash-preview', 'google-gemini-cli', 18, 360),
            ('deepseek-v4-flash', 'deepseek', 18, 360),
            ('mimo-v2.5-pro', 'xiaomi', 12, 240),
        ]
    else:
        model_chain = [
            ('gemini-3-flash-preview', 'google-gemini-cli', 15, 300),
            ('deepseek-v4-flash', 'deepseek', 15, 300),
            ('gpt-5.5', 'openai-codex', 15, 360),
            ('mimo-v2.5-pro', 'xiaomi', 10, 220),
        ]
    if agent_card_routing.get('applies') and worker_profile_name:
        model_chain, dropped_providers = _filter_model_chain_for_worker_profile(model_chain, worker_profile_name)
        if dropped_providers:
            append_trace(eid, {
                'event': 'agent_card_profile_provider_filter',
                'profile': worker_profile_name,
                'dropped': dropped_providers,
                'remaining_providers': [provider for _, provider, *_ in model_chain],
            })

    # Cron/no-agent wrappers must return within the scheduler budget.  Keep the
    # default interactive worker chain unchanged, but allow wrappers to cap each
    # provider timeout and the number of providers attempted in one tick.
    try:
        timeout_ceiling = int(os.environ.get('HERMES_AGENT_TEAM_WORKER_TIMEOUT_CEILING', '0') or 0)
    except Exception:
        timeout_ceiling = 0
    if timeout_ceiling > 0:
        model_chain = [
            (model, provider, max_turns, min(timeout_s, max(1, timeout_ceiling)))
            for model, provider, max_turns, timeout_s in model_chain
        ]
        append_trace(eid, {'event': 'worker_timeout_ceiling_applied', 'timeout_ceiling_s': timeout_ceiling})
    try:
        chain_limit = int(os.environ.get('HERMES_AGENT_TEAM_MODEL_CHAIN_LIMIT', '0') or 0)
    except Exception:
        chain_limit = 0
    if chain_limit > 0:
        model_chain = model_chain[:max(1, chain_limit)]
        append_trace(eid, {'event': 'worker_model_chain_limited', 'chain_limit': chain_limit, 'remaining_providers': [provider for _, provider, *_ in model_chain]})

    chain_idx = 0
    model, provider, max_turns, timeout_s = model_chain[chain_idx]

    # Workspace sync barrier: ensure directory exists before worker spawns
    ws_ok, ws_path, ws_err = _verify_workspace_ready(task_id)
    if not ws_ok:
        append_trace(eid, {'event': 'workspace_not_ready', 'path': ws_path, 'error': ws_err})
        return {'status': 'failed', 'reason': f'workspace_not_ready: {ws_err}'}

    proof_stub = create_worker_proof_stub(task, envelope_id=eid, run_id=f'worker-{eid[:8]}')
    append_trace(eid, {'event': 'proof_stub_created', 'path': proof_stub.get('proof_stub_path'), 'task_id': task_id})
    record_worker_heartbeat(task, envelope_id=eid, proof_stub_path=proof_stub.get('proof_stub_path', ''), checkpoint='before_hermes_chat')

    # Model fallback loop: try each model in chain until success or all exhausted.
    # Infrastructure failures (SDK crashes, MCP loops) trigger immediate fallback.
    # Task-level failures (missing proof, blocked) stop the loop.
    last_output = ''
    last_stderr = ''
    for chain_idx, (model, provider, max_turns, timeout_s) in enumerate(model_chain):
        try:
            cmd = ['hermes']
            if agent_card_routing.get('applies') and worker_profile_name:
                cmd.extend(['-p', worker_profile_name])
            cmd.extend([
                'chat', '-q', context,
                '--model', model, '--provider', provider,
                '--quiet', '--max-turns', str(max_turns),
                '--source', f'team-worker-{eid[:8]}',
            ])
            for skill_name in required_skills:
                cmd.extend(['--skills', skill_name])
            cmd.append('--ignore-rules')
            worker_env = os.environ.copy()
            if agent_card_routing.get('applies') and worker_profile_name:
                worker_env['HERMES_PROFILE'] = worker_profile_name
                worker_env['HERMES_PROFILE_NAME'] = worker_profile_name
            append_trace(eid, {'event': 'worker_attempt', 'chain_idx': chain_idx, 'model': model, 'provider': provider, 'agent_card_profile': worker_profile_name if agent_card_routing.get('applies') else '', 'agent_card_routing_mode': agent_card_routing.get('mode')})
            r = _sp.run(cmd, capture_output=True, text=True, timeout=timeout_s, env=worker_env)
            record_worker_heartbeat(task, envelope_id=eid, proof_stub_path=proof_stub.get('proof_stub_path', ''), checkpoint='hermes_chat_returned', note=f'model={model} returncode={r.returncode}')
            output = r.stdout
            last_output = output
            last_stderr = r.stderr or ''

            # Check for infrastructure failures → fallback to next model
            is_infra, infra_cat = _detect_infra_failure(output, r.stderr)
            if is_infra:
                append_trace(eid, {
                    'event': 'infra_failure_fallback',
                    'chain_idx': chain_idx, 'model': model,
                    'infra_category': infra_cat,
                    'output_tail': output[-300:],
                })
                # If not the last model in chain, try next
                if chain_idx < len(model_chain) - 1:
                    continue
                # Last model also failed with infra error
                return {'status': 'timeout', 'reason': f'all_models_infra_failed:{infra_cat}', 'output': output[-300:]}

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
                    append_trace(eid, {
                        'event': 'proof_contract_fallback',
                        'chain_idx': chain_idx,
                        'model': model,
                        'provider': provider,
                        'proof_reason': 'invalid_proof',
                        'output_tail': output[-300:],
                    })
                    if chain_idx < len(model_chain) - 1:
                        continue
                    return {'status': 'failed', 'reason': 'invalid_proof', 'output': output[-300:], 'model_used': model}
                proof_check = validate_worker_proof_against_task(task, proof)
                if proof_check.get('proof_status') == 'blocked':
                    return {'status': 'blocked', 'proof': proof, 'proof_check': proof_check, 'output': output[:500]}
                if proof_check.get('status') != 'PASS':
                    return {'status': 'blocked', 'reason': 'proof_consistency_failed', 'proof': proof, 'proof_check': proof_check, 'output': output[-500:]}
                conductor = run_multimodel_conductor(
                    task,
                    output,
                    profile or {},
                    worker_profile_name=worker_profile_name,
                )
                proof['multimodel_conductor'] = conductor
                append_trace(eid, {'event': 'multimodel_conductor_verdict', 'verdict': conductor})
                return {'status': 'done', 'proof': proof, 'proof_check': proof_check, 'multimodel_conductor': conductor, 'output': output, 'model_used': model}
            elif 'BLOCKED' in output:
                return {'status': 'blocked', 'output': output[:200], 'model_used': model}
            else:
                append_trace(eid, {
                    'event': 'proof_contract_fallback',
                    'chain_idx': chain_idx,
                    'model': model,
                    'provider': provider,
                    'proof_reason': 'missing_proof',
                    'output_tail': output[-300:],
                })
                if chain_idx < len(model_chain) - 1:
                    continue
                return {'status': 'failed', 'reason': 'missing_proof', 'output': output[-300:], 'model_used': model}

        except _sp.TimeoutExpired as exc:
            # Timeout could be infra (model hanging) or task (too complex).
            # Prefer the current TimeoutExpired stdout/stderr over stale output
            # from a prior provider attempt; an empty timeout is a provider
            # no-output hang and must not be requeued as task-level proof debt.
            timeout_output, timeout_stderr = _timeout_exc_output(exc)
            current_output = timeout_output or ''
            current_stderr = timeout_stderr or ''
            if _is_no_output_timeout(current_output, current_stderr):
                append_trace(eid, {
                    'event': 'provider_no_output_timeout',
                    'chain_idx': chain_idx,
                    'model': model,
                    'provider': provider,
                    'timeout_s': timeout_s,
                    'category': 'provider_no_output_timeout',
                })
                if chain_idx < len(model_chain) - 1:
                    continue
                return {
                    'status': 'blocked',
                    'reason': 'provider_no_output_circuit_open',
                    'infra_category': 'all_models_provider_no_output_timeout',
                    'model_used': model,
                }

            is_infra, infra_cat = _detect_infra_failure(current_output, current_stderr)
            if is_infra and chain_idx < len(model_chain) - 1:
                append_trace(eid, {
                    'event': 'timeout_infra_fallback',
                    'chain_idx': chain_idx, 'model': model,
                    'infra_category': infra_cat,
                })
                continue
            timeout_checkpoint = record_worker_timeout_checkpoint(task, envelope_id=eid, proof_stub_path=proof_stub.get('proof_stub_path', ''), reason=f'subprocess_timeout_{model}')
            append_trace(eid, {'event': 'worker_timeout_checkpoint', 'path': timeout_checkpoint.get('proof_stub_path'), 'reason': f'subprocess_timeout_{model}', 'chain_idx': chain_idx})
            return {'status': 'timeout', 'reason': 'timeout_with_proof_stub', 'proof_stub_path': timeout_checkpoint.get('proof_stub_path'), 'model_used': model}
        except Exception as e:
            append_trace(eid, {'event': 'worker_exception', 'model': model, 'error': str(e)[:200]})
            if chain_idx < len(model_chain) - 1:
                continue
            return {'status': 'error', 'error': str(e)[:200], 'model_used': model}

    # Should not reach here, but safety fallback
    return {'status': 'failed', 'reason': 'model_chain_exhausted', 'output': last_output[-300:]}


def create_claim_envelope(task, conflict_group, actor='agent-team-controller', *, source='claim-cycle', handoff=''):
    """Create a PENDING envelope for a claimed brain task.

    Claiming and execution are intentionally decoupled: claim paths enqueue work,
    execute paths consume envelopes later under an explicit worker budget.
    """
    eid = create(
        type='TASK',
        title=task.get('title', 'untitled'),
        project=task.get('project', ''),
        assignee=f'agent-team-{conflict_group}',
        payload={
            'brain_id': task.get('id', ''),
            'boundary': task.get('parallel_boundary', ''),
            'parallel_boundary': task.get('parallel_boundary', ''),
            'conflict_group': conflict_group,
            'project': task.get('project', ''),
            'claimed_by': actor,
            'claim_source': source,
            'handoff': handoff,
        },
        appetite_seconds=1800,
    )
    append_trace(eid, {'event': 'enqueued', 'group': conflict_group, 'source': source, 'actor': actor})
    return eid


def prepare_claim_batch(max_claims=3):
    """Select a safe batch to claim without executing workers."""
    if is_disabled():
        return {'status': 'disabled', 'reason': 'kill switch active'}

    escape, escape_info = human_escape_check()
    if escape:
        return {'status': 'escaped', 'reason': f'Human escape: {escape_info}'}

    try:
        all_tasks = get_all_dispatchable()
    except Exception as e:
        return {'status': 'error', 'reason': str(e)[:200]}

    if not all_tasks:
        return {'status': 'idle', 'reason': 'no dispatchable tasks'}

    groups = classify_batch(all_tasks)
    conflict_group_count = len(groups)

    health = boundary_health_check(all_tasks)
    file_conflicts = health.get('file_conflicts', {})
    if file_conflicts.get('conflict_count', 0) > 0:
        for conflict in file_conflicts.get('conflicts', [])[:3]:
            ga = conflict['group_a']
            gb = conflict['group_b']
            if ga in groups and gb in groups:
                score_a = sum(int(t.get('score', 0)) for t in groups[ga])
                score_b = sum(int(t.get('score', 0)) for t in groups[gb])
                loser = gb if score_a >= score_b else ga
                winner = ga if loser == gb else gb
                groups[winner].extend(groups.pop(loser))
                conflict_group_count = len(groups)

    n_result = get_smoothed_n(len(all_tasks), conflict_group_count)
    applied_n = n_result['applied_n']
    try:
        batch_cap = max(1, int(max_claims or applied_n or 1))
    except Exception:
        batch_cap = max(1, applied_n or 1)
    selected_n = min(applied_n, batch_cap)

    if selected_n == 0:
        return {'status': 'idle', 'reason': 'N=0 (no tasks)', 'n_info': n_result}

    schedule = get_parallel_schedule(all_tasks, selected_n)
    return {
        'status': 'ok',
        'all_tasks': all_tasks,
        'groups': groups,
        'schedule': schedule,
        'n_info': n_result,
        'applied_n': applied_n,
        'selected_n': selected_n,
        'conflict_group_count': conflict_group_count,
        'health': health,
    }


def claim_cycle(max_claims=3, wall_budget_seconds=20):
    """Claim + enqueue only. Never calls hermes chat/delegate."""
    prepared = prepare_claim_batch(max_claims=max_claims)
    if prepared.get('status') != 'ok':
        return prepared

    started = time.monotonic()
    claimed = []
    claim_errors = []
    all_tasks = list(prepared.get('all_tasks') or [])
    schedule = prepared.get('schedule') or {}
    schedule_items = schedule.get('schedule', []) if isinstance(schedule, dict) else []
    selected_n = int(prepared.get('selected_n') or 0)

    for group_info in schedule_items[:selected_n]:
        if time.monotonic() - started >= max(1, int(wall_budget_seconds or 20)):
            break
        group = group_info['conflict_group']
        group_tasks = [t for t in all_tasks if t.get('_conflict_group') == group]
        if not group_tasks:
            continue
        task = group_tasks[0]
        task_id = task.get('id', '')
        result = claim_task(task_id)
        if not result.get('ok'):
            claim_errors.append({'task_id': task_id, 'group': group, 'error': result.get('error', 'claim_failed')})
            continue
        eid = create_claim_envelope(task, group, actor='agent-team-controller', source='claim-cycle')
        claimed.append({
            'task_id': task_id,
            'title': task.get('title', '')[:50],
            'envelope_id': eid,
            'conflict_group': group,
            'priority': task.get('priority', 'P2'),
            'worker_result': 'enqueued',
        })

    return {
        'status': 'ok',
        'mode': 'claim-only',
        'n_info': prepared['n_info'],
        'conflict_groups': prepared['conflict_group_count'],
        'total_dispatchable': len(all_tasks),
        'tasks_claimed': len(claimed),
        'claimed': claimed,
        'claim_errors': claim_errors,
        'deferred_groups': schedule.get('deferred_groups', []) if isinstance(schedule, dict) else [],
        'safety': 'claim-cycle only claims and enqueues; execution is delegated to execute-cycle',
    }


def _process_worker_result(row, actor, eid, worker_result):
    record = {'task_id': row.get('id', ''), 'envelope_id': eid, 'worker_result': worker_result.get('status', '?')}
    task_id = row.get('id', '')

    def _requeue(reason, evidence, *, envelope_status='FAILED', envelope_error=None):
        retry = transition_task(task_id, 'retry', actor, reason, evidence=evidence)
        record['retry_transition'] = retry
        if retry.get('ok'):
            update_status(eid, envelope_status, error=envelope_error or reason[:200])
            record['envelope_status'] = envelope_status
            record['to_status'] = 'retry'
        else:
            update_status(eid, 'FAILED', error=str(retry)[:200])
            record['envelope_status'] = 'FAILED'
            record['to_status'] = 'running'
        return record

    if worker_result.get('status') == 'done':
        proof = worker_result.get('proof') or {}
        PROOF_DIR.mkdir(parents=True, exist_ok=True)
        proof_path = PROOF_DIR / f"{task_id}.json"
        if not proof_path.exists():
            proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2))
        review = transition_task(
            task_id,
            'review',
            actor,
            'worker produced proof; controller stops at review for proof-gated closeout',
            evidence=[f'artifact:{proof_path}'],
        )
        record['review_transition'] = review
        if review.get('ok'):
            closeout = apply_conductor_done_closeout(task_id, actor, eid, proof, proof_path, source='execute-cycle')
            record['conductor_done_closeout'] = closeout
            if closeout.get('readback_verified'):
                update_status(eid, 'DONE')
                record['to_status'] = 'done'
            else:
                update_status(eid, 'DONE')
                record['to_status'] = 'review'
        else:
            _requeue(
                'worker proof produced but review transition failed; requeue to avoid false running',
                ['command:agent_team_controller execute-cycle review_transition_failed'],
                envelope_status='FAILED',
                envelope_error=str(review)[:200],
            )
        return record
    if worker_result.get('status') == 'blocked':
        blocked = transition_task(
            task_id,
            'blocked',
            actor,
            'worker reported blocked; release running task to blocked state',
            evidence=['command:agent_team_controller execute-cycle worker blocked'],
        )
        record['blocked_transition'] = blocked
        if blocked.get('ok'):
            # A worker-reported blocker is now represented on the canonical brain task.
            # The envelope successfully performed its handoff/release duty, so do not
            # count this as a global envelope-bus BLOCKED incident that can freeze
            # unrelated tasks via human_escape. Missing/invalid proof paths remain
            # FAILED and still trip the safety breaker.
            update_status(eid, 'SKIPPED', error='task_blocked_released')
            record['envelope_status'] = 'SKIPPED'
            record['to_status'] = 'blocked'
        else:
            update_status(eid, 'FAILED', error=str(blocked)[:200])
            record['to_status'] = 'running'
        return record
    if worker_result.get('status') == 'continuation_pending':
        return _requeue(
            'worker requested continuation; requeue checkpointed task for next continuation pass',
            ['command:agent_team_controller execute-cycle continuation_pending'],
            envelope_status='SKIPPED',
            envelope_error='continuation_pending_requeued',
        )
    if worker_result.get('status') == 'timeout':
        return _requeue(
            'worker timed out without proof; requeue for proof-gated retry',
            ['command:agent_team_controller execute-cycle worker timeout'],
            envelope_status='SKIPPED',
            envelope_error='worker_timeout_requeued',
        )
    return _requeue(
        f"worker failed without completion proof; requeue to avoid false running: {worker_result.get('reason') or worker_result.get('status') or 'unknown'}",
        ['command:agent_team_controller execute-cycle worker failed'],
        envelope_status='FAILED',
        envelope_error=str(worker_result)[:200],
    )


def execute_cycle(max_workers=3, wall_budget_seconds=600):
    """Consume PENDING claim envelopes under an explicit worker budget."""
    if is_disabled():
        return {'status': 'disabled', 'reason': 'kill switch active'}

    escape, escape_info = human_escape_check()
    if escape:
        return {'status': 'escaped', 'reason': f'Human escape: {escape_info}'}

    try:
        max_workers = max(1, int(max_workers or 3))
    except Exception:
        max_workers = 3
    budget_s = max(1, int(wall_budget_seconds or 600))
    started = time.monotonic()

    pending = [env for env in list_by_status('PENDING') if str(env.get('assignee', '')).startswith('agent-team-')]
    if not pending:
        return {'status': 'idle', 'mode': 'execute-only', 'pending': 0, 'processed': 0}

    results = []
    skipped = []
    processed = 0
    for envelope in pending:
        if processed >= max_workers or time.monotonic() - started >= budget_s:
            break
        eid = envelope['id']
        payload = json.loads(envelope.get('payload') or '{}') if isinstance(envelope.get('payload'), str) else (envelope.get('payload') or {})
        task_id = str(payload.get('brain_id') or '').strip()
        if not task_id:
            # Stale/malformed queued envelopes are audit noise, not worker failures.
            # Mark them SKIPPED so a recovery cycle does not trip human_escape while
            # draining old PENDING agent-team envelopes.
            update_status(eid, 'SKIPPED', error='missing_brain_id_skipped')
            skipped.append({'envelope_id': eid, 'reason': 'missing_brain_id'})
            continue
        row = rows_by_id([task_id]).get(task_id)
        if not row:
            update_status(eid, 'SKIPPED', error='task_not_found_skipped')
            skipped.append({'envelope_id': eid, 'task_id': task_id, 'reason': 'task_not_found'})
            continue
        if row.get('status') != 'claimed':
            update_status(eid, 'SKIPPED', error=f"not_claimed_skipped:{row.get('status')}")
            skipped.append({'envelope_id': eid, 'task_id': task_id, 'reason': f"not_claimed:{row.get('status')}"})
            continue
        payload_actor = str(payload.get('claimed_by') or '').strip()
        row_actor = str(row.get('claimed_by') or '').strip()
        if payload_actor and row_actor and payload_actor != row_actor:
            update_status(eid, 'SKIPPED', error=f"claimed_by_mismatch_skipped:payload={payload_actor}:row={row_actor}")
            skipped.append({'envelope_id': eid, 'task_id': task_id, 'reason': 'claimed_by_mismatch', 'payload_actor': payload_actor, 'row_actor': row_actor})
            continue
        actor = row_actor or payload_actor or 'agent-team-controller'
        if str(os.environ.get('HERMES_AGENT_TEAM_EXECUTE_ASYNC') or '').strip().lower() in {'1', 'true', 'yes', 'on'}:
            async_result = start_consume_claimed_background(
                [{'task_id': task_id, 'handoff': payload.get('handoff', '')}],
                max_agents=1,
                batch_id=f'execute-cycle-{eid}',
            )
            results.append({
                'task_id': task_id,
                'envelope_id': eid,
                'worker_result': 'async_spawned' if async_result.get('status') == 'OK' else 'async_spawn_failed',
                'async_worker': async_result,
                'to_status': row.get('status'),
            })
            processed += 1
            if async_result.get('status') == 'OK':
                update_status(eid, 'SKIPPED', error='async_worker_spawned')
            else:
                update_status(eid, 'FAILED', error=str(async_result)[:200])
            continue
        running = transition_task(task_id, 'running', actor, 'execute-cycle worker trigger after queued claim')
        if not running.get('ok'):
            if _is_stale_claim_transition_error(running):
                skipped.append(_release_stale_claim_after_running_failure(
                    task_id,
                    actor,
                    eid,
                    running,
                    source='execute-cycle',
                ))
            else:
                update_status(eid, 'FAILED', error=str(running)[:200])
                skipped.append({'envelope_id': eid, 'task_id': task_id, 'reason': 'running_transition_failed', 'detail': running})
            continue
        update_status(eid, 'RUNNING')
        group = payload.get('conflict_group') or row.get('parallel_group') or row.get('conflict_group') or row.get('parallel_boundary') or row.get('project') or 'default'
        siblings = page_batch_siblings_for(row)
        worker_result = delegate_to_worker(row, str(group), eid, sibling_tasks=siblings)
        append_trace(eid, {'event': 'execute_cycle_worker_finished', 'result': worker_result.get('status', '?')})
        results.append(_process_worker_result(row, actor, eid, worker_result))
        processed += 1

    reviewed_count = sum(1 for item in results if item.get('to_status') == 'review')
    done_count = sum(1 for item in results if item.get('to_status') == 'done')
    return {
        'status': 'ok',
        'mode': 'execute-only',
        'processed': processed,
        'reviewed_count': reviewed_count,
        'done_count': done_count,
        'results': results,
        'skipped': skipped,
        'remaining_pending': max(0, len(pending) - processed),
        'safety': 'execute-cycle reads queued envelopes and only advances brain tasks to review/retry/blocked',
    }


def release_claimed_batch_for_escape(claimed_items, escape_info, actor='hermes-parallel'):
    """Fail-soft release for event-driven claims when human-escape is active.

    The escape circuit intentionally blocks worker execution.  Leaving tasks in
    `claimed` after that skip wedges the pool until lease expiry and causes the
    next tick to see zero dispatchable work.  Release only the just-passed claimed
    handoffs back to retry with explicit evidence; do not execute workers and do
    not mark anything done.
    """
    items = list(claimed_items or [])
    ids = [str(item.get('task_id') or item.get('id') or '') for item in items if isinstance(item, dict)]
    ids = [x for x in ids if x]
    row_map = rows_by_id(ids) if ids else {}
    released = []
    skipped = []
    reason = f'event-driven worker blocked by human escape; claim released for retry: {str(escape_info)[:300]}'
    for task_id in ids:
        row = row_map.get(task_id)
        if not row:
            skipped.append({'task_id': task_id, 'reason': 'task_not_found'})
            continue
        if row.get('status') != 'claimed':
            skipped.append({'task_id': task_id, 'reason': f"not_claimed:{row.get('status')}"})
            continue
        task_actor = str(row.get('claimed_by') or actor)
        retry = transition_task(
            task_id,
            'retry',
            task_actor,
            reason,
            evidence=['command:agent_team_controller consume-claimed human_escape_release'],
        )
        released.append({'task_id': task_id, 'retry_transition': retry, 'to_status': 'retry' if retry.get('ok') else 'claimed'})
    return {'released': released, 'skipped': skipped}


def consume_claimed_batch(claimed_items, max_agents=3):
    """Immediately consume tasks just claimed by parallel-claim-and-handoff.

    This is the event-driven bridge between claim/handoff and real worker
    execution.  It advances claimed tasks to running/review and, when a valid
    proof carries a certified conductor packet, may perform the narrow
    digest-bound review->done closeout. Other lifecycle/write paths remain
    separately gated.

    Important: claimed handoffs are already boundary/conflict classified by the
    orchestrator.  Do not serialize the batch here; start all eligible items and
    run workers concurrently up to max_agents so Lark/work bursts can use their
    existing non-overlapping boundaries.
    """
    if not claimed_items:
        return {'status': 'SKIP', 'event_driven': True, 'reason': 'no claimed tasks', 'consumed_count': 0}
    if is_disabled():
        return {'status': 'SKIP', 'event_driven': True, 'reason': 'kill switch active', 'consumed_count': 0}
    escape, escape_info = human_escape_check()
    if escape:
        released = release_claimed_batch_for_escape(claimed_items, escape_info)
        return {
            'status': 'SKIP',
            'event_driven': True,
            'reason': f'Human escape: {escape_info}',
            'consumed_count': 0,
            'released_count': sum(1 for item in released.get('released', []) if (item.get('retry_transition') or {}).get('ok')),
            'released': released.get('released', []),
            'skipped': released.get('skipped', []),
            'safety': 'worker execution skipped; claimed handoffs released to retry to avoid claimed-without-progress wedge',
        }
    try:
        max_agents = max(1, int(max_agents or 3))
    except Exception:
        max_agents = 3
    # Do not truncate the claimed batch.  `max_agents` is a worker concurrency
    # limit, not a consumption limit: every already-claimed handoff must be
    # either advanced to running/review or explicitly released by the timeout /
    # escape cleanup paths.  Truncating here leaves overflow items stuck in
    # claimed with no worker or controller ownership.
    claimed_items = list(claimed_items)
    ids = [str(item.get('task_id') or item.get('id') or '').strip() for item in claimed_items if isinstance(item, dict)]
    ids = [x for x in ids if x]
    row_map = rows_by_id(ids)
    consumed = []
    skipped = []
    launch_records = []

    for item in claimed_items:
        task_id = str(item.get('task_id') or item.get('id') or '').strip() if isinstance(item, dict) else ''
        if not task_id:
            skipped.append({'task_id': '', 'reason': 'missing_task_id'})
            continue
        row = row_map.get(task_id)
        if not row:
            skipped.append({'task_id': task_id, 'reason': 'task_not_found'})
            continue
        if row.get('status') != 'claimed':
            skipped.append({'task_id': task_id, 'reason': f"not_claimed:{row.get('status')}"})
            continue
        actor = str(row.get('claimed_by') or 'hermes-parallel')
        group = row.get('parallel_group') or row.get('conflict_group') or row.get('parallel_boundary') or row.get('project') or 'default'
        eid = create(
            type='TASK',
            title=row.get('title', 'untitled'),
            project=row.get('project', ''),
            assignee=f'agent-team-{group}',
            payload={
                'brain_id': task_id,
                'boundary': row.get('parallel_boundary', ''),
                'conflict_group': group,
                'event_driven_claim': True,
                'handoff': item.get('handoff', '') if isinstance(item, dict) else '',
            },
            appetite_seconds=1800,
        )
        update_status(eid, 'RUNNING')
        append_trace(eid, {'event': 'event_driven_claim_consumed', 'task_id': task_id, 'actor': actor})
        running = transition_task(task_id, 'running', actor, 'event-driven worker trigger after parallel claim/handoff')
        if not running.get('ok'):
            if _is_stale_claim_transition_error(running):
                skipped.append(_release_stale_claim_after_running_failure(
                    task_id,
                    actor,
                    eid,
                    running,
                    source='consume-claimed',
                ))
            else:
                update_status(eid, 'FAILED', error=str(running)[:200])
                skipped.append({'task_id': task_id, 'reason': 'running_transition_failed', 'detail': running})
            continue
        launch_records.append({'task_id': task_id, 'row': row, 'actor': actor, 'group': str(group), 'eid': eid})

    def _run_one(record):
        task_id = record['task_id']
        eid = record['eid']
        actor = record['actor']
        siblings = page_batch_siblings_for(record['row'])
        worker_result = delegate_to_worker(record['row'], record['group'], eid, sibling_tasks=siblings)
        append_trace(eid, {'event': 'event_worker_finished', 'result': worker_result.get('status', '?')})
        out = {'task_id': task_id, 'envelope_id': eid, 'worker_result': worker_result.get('status', '?')}

        def _requeue(reason, evidence, *, envelope_status='FAILED', envelope_error=None):
            current = rows_by_id([task_id]).get(task_id) or {}
            current_status = str(current.get('status') or '').strip()
            if current_status and current_status not in {'claimed', 'running'}:
                # A worker process may time out after it already wrote a valid
                # lifecycle result (for example running -> review). Never demote
                # a progressed task back to retry from a late timeout/failure.
                ignored_reason = f'worker_result_ignored_current_status_{current_status}'
                update_status(eid, 'SKIPPED', error=ignored_reason)
                out['retry_transition'] = {'ok': True, 'skipped': ignored_reason, 'current_status': current_status}
                out['envelope_status'] = 'SKIPPED'
                out['to_status'] = current_status
                return out
            retry = transition_task(task_id, 'retry', actor, reason, evidence=evidence)
            out['retry_transition'] = retry
            if retry.get('ok'):
                update_status(eid, envelope_status, error=envelope_error or reason[:200])
                out['envelope_status'] = envelope_status
                out['to_status'] = 'retry'
            else:
                update_status(eid, 'FAILED', error=str(retry)[:200])
                out['envelope_status'] = 'FAILED'
                out['to_status'] = 'running'
            return out

        if worker_result.get('status') == 'done':
            proof = worker_result.get('proof') or {}
            PROOF_DIR.mkdir(parents=True, exist_ok=True)
            proof_path = PROOF_DIR / f'{task_id}.json'
            if not proof_path.exists():
                proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2))
            review = transition_task(
                task_id,
                'review',
                actor,
                'event-driven worker produced proof; controller stops at review for proof-gated closeout',
                evidence=[f'artifact:{proof_path}'],
            )
            out['review_transition'] = review
            if review.get('ok'):
                closeout = apply_conductor_done_closeout(task_id, actor, eid, proof, proof_path, source='consume-claimed')
                out['conductor_done_closeout'] = closeout
                if closeout.get('readback_verified'):
                    update_status(eid, 'DONE')
                    out['to_status'] = 'done'
                else:
                    update_status(eid, 'DONE')
                    out['to_status'] = 'review'
            else:
                _requeue(
                    'event-driven worker proof produced but review transition failed; requeue to avoid false running',
                    ['command:agent_team_controller consume-claimed review_transition_failed'],
                    envelope_status='FAILED',
                    envelope_error=str(review)[:200],
                )
        elif worker_result.get('status') == 'blocked':
            blocked = transition_task(
                task_id,
                'blocked',
                actor,
                'event-driven worker reported blocked; release running task to blocked state',
                evidence=['command:agent_team_controller consume-claimed worker blocked'],
            )
            out['blocked_transition'] = blocked
            if blocked.get('ok'):
                # Task-level blockers are now captured on the brain task; the
                # envelope release itself succeeded and should not trip global
                # human_escape for unrelated work.
                update_status(eid, 'SKIPPED', error='task_blocked_released')
                out['envelope_status'] = 'SKIPPED'
                out['to_status'] = 'blocked'
            else:
                update_status(eid, 'FAILED', error=str(blocked)[:200])
                out['to_status'] = 'running'
        elif worker_result.get('status') == 'continuation_pending':
            _requeue(
                'event-driven worker requested continuation; requeue checkpointed task for next continuation pass',
                ['command:agent_team_controller consume-claimed continuation_pending'],
                envelope_status='SKIPPED',
                envelope_error='continuation_pending_requeued',
            )
        elif worker_result.get('status') == 'timeout':
            _requeue(
                'event-driven worker timed out without proof; requeue for proof-gated retry',
                ['command:agent_team_controller consume-claimed worker timeout'],
                envelope_status='SKIPPED',
                envelope_error='worker_timeout_requeued',
            )
        else:
            _requeue(
                f"event-driven worker failed without completion proof; requeue to avoid false running: {worker_result.get('reason') or worker_result.get('status') or 'unknown'}",
                ['command:agent_team_controller consume-claimed worker failed'],
                envelope_status='FAILED',
                envelope_error=str(worker_result)[:200],
            )
        return out

    if launch_records:
        workers = min(max_agents, len(launch_records))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_run_one, rec): rec for rec in launch_records}
            for future in as_completed(futures):
                rec = futures[future]
                try:
                    consumed.append(future.result())
                except Exception as exc:
                    retry = transition_task(
                        rec['task_id'],
                        'retry',
                        rec['actor'],
                        'event-driven worker raised exception; requeue to avoid false running',
                        evidence=['command:agent_team_controller consume-claimed worker exception'],
                    )
                    update_status(rec['eid'], 'FAILED', error=str(exc)[:200])
                    consumed.append({
                        'task_id': rec['task_id'],
                        'envelope_id': rec['eid'],
                        'worker_result': 'error',
                        'error': str(exc)[:200],
                        'retry_transition': retry,
                        'to_status': 'retry' if retry.get('ok') else 'running',
                    })

    reviewed_count = sum(1 for item in consumed if item.get('to_status') == 'review')
    done_count = sum(1 for item in consumed if item.get('to_status') == 'done')
    return {
        'status': 'ok',
        'event_driven': True,
        'requested_count': len(claimed_items),
        'launched_count': len(launch_records),
        'consumed_count': len(consumed),
        'running_count': sum(1 for item in consumed if item.get('to_status') == 'running'),
        'reviewed_count': reviewed_count,
        'done_count': done_count,
        'claimed': consumed,
        'skipped': skipped,
        'safety': 'controller-consumed claimed handoffs in parallel; worker cannot mark done; only digest-bound certified conductor closeout may perform review->done',
        'next_tick_requested': bool(reviewed_count),
    }

def run_dynamic_cycle(max_claims=3, max_workers=3, claim_wall_budget_seconds=20, execute_wall_budget_seconds=600):
    """Compatibility wrapper: claim/enqueue first, then execute under a worker budget."""
    claim_result = claim_cycle(max_claims=max_claims, wall_budget_seconds=claim_wall_budget_seconds)
    if claim_result.get('status') not in {'ok', 'idle'}:
        return claim_result
    execute_result = execute_cycle(max_workers=max_workers, wall_budget_seconds=execute_wall_budget_seconds)
    if execute_result.get('status') not in {'ok', 'idle'}:
        return {
            'status': execute_result.get('status'),
            'mode': 'claim-then-execute',
            'claim': claim_result,
            'execute': execute_result,
        }
    return {
        'status': 'ok',
        'mode': 'claim-then-execute',
        'claim': claim_result,
        'execute': execute_result,
        'n_info': claim_result.get('n_info', {}),
        'conflict_groups': claim_result.get('conflict_groups', 0),
        'total_dispatchable': claim_result.get('total_dispatchable', 0),
        'tasks_claimed': claim_result.get('tasks_claimed', 0),
        'claimed': claim_result.get('claimed', []),
        'deferred_groups': claim_result.get('deferred_groups', []),
        'processed': execute_result.get('processed', 0),
        'reviewed_count': execute_result.get('reviewed_count', 0),
        'remaining_pending': execute_result.get('remaining_pending', 0),
        'safety': 'cycle is now a wrapper over claim-cycle + execute-cycle',
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
        claude_model = os.environ.get('HERMES_TASKPOOL_CLAUDE_VERIFY_MODEL', 'claude-opus-4-8')
        r = _sp.run(['claude','-p',prompt,'--model',claude_model,'--max-turns','1','--output-format','json'],
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
            parser = argparse.ArgumentParser(prog='agent_team_controller.py cycle')
            parser.add_argument('--max-claims', type=int, default=3)
            parser.add_argument('--max-workers', type=int, default=3)
            parser.add_argument('--claim-wall-budget-seconds', type=int, default=20)
            parser.add_argument('--execute-wall-budget-seconds', type=int, default=600)
            ns = parser.parse_args(sys.argv[2:])
            print(json.dumps(run_dynamic_cycle(
                max_claims=ns.max_claims,
                max_workers=ns.max_workers,
                claim_wall_budget_seconds=ns.claim_wall_budget_seconds,
                execute_wall_budget_seconds=ns.execute_wall_budget_seconds,
            ), indent=2, ensure_ascii=False))
        elif cmd == 'claim-cycle':
            parser = argparse.ArgumentParser(prog='agent_team_controller.py claim-cycle')
            parser.add_argument('--max-claims', type=int, default=3)
            parser.add_argument('--wall-budget-seconds', type=int, default=20)
            ns = parser.parse_args(sys.argv[2:])
            print(json.dumps(claim_cycle(max_claims=ns.max_claims, wall_budget_seconds=ns.wall_budget_seconds), indent=2, ensure_ascii=False))
        elif cmd == 'execute-cycle':
            parser = argparse.ArgumentParser(prog='agent_team_controller.py execute-cycle')
            parser.add_argument('--max-workers', type=int, default=3)
            parser.add_argument('--wall-budget-seconds', type=int, default=600)
            ns = parser.parse_args(sys.argv[2:])
            print(json.dumps(execute_cycle(max_workers=ns.max_workers, wall_budget_seconds=ns.wall_budget_seconds), indent=2, ensure_ascii=False))
        elif cmd == 'consume-claimed':
            parser = argparse.ArgumentParser(prog='agent_team_controller.py consume-claimed')
            parser.add_argument('--claimed-json', default='[]')
            parser.add_argument('--max-agents', type=int, default=3)
            parser.add_argument('--batch-id', default='')
            parser.add_argument('--background', action='store_true', help='spawn durable async worker job and return immediately')
            ns = parser.parse_args(sys.argv[2:])
            try:
                claimed_items = json.loads(ns.claimed_json or '[]')
            except json.JSONDecodeError as exc:
                print(json.dumps({'status': 'ERROR', 'event_driven': True, 'reason': 'invalid_claimed_json', 'error': str(exc)}, ensure_ascii=False))
                raise SystemExit(2)
            if ns.background:
                print(json.dumps(start_consume_claimed_background(claimed_items, max_agents=ns.max_agents, batch_id=ns.batch_id), indent=2, ensure_ascii=False))
            else:
                print(json.dumps(consume_claimed_batch(claimed_items, max_agents=ns.max_agents), indent=2, ensure_ascii=False))
        elif cmd == 'worker-jobs':
            print(json.dumps(command_worker_jobs(), indent=2, ensure_ascii=False))
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
            print('Usage: agent_team_controller.py [cycle|claim-cycle|execute-cycle|consume-claimed|worker-jobs|status|enable|disable]')
    else:
        print('Usage: agent_team_controller.py [cycle|claim-cycle|execute-cycle|consume-claimed|worker-jobs|status|enable|disable]')


