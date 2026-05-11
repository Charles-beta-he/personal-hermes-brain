#!/usr/bin/env python3
"""Bounded nightly multi-brain tick.

Runs consult_models.py state + bounded run, records timeout explicitly, then
always refreshes usage-score. Designed for cron: no silent empty failure.
"""
from __future__ import annotations
import argparse, json, subprocess, datetime, tempfile
from pathlib import Path

H = Path.home() / '.hermes'
LOG = H / 'logs' / 'multi-brain-nightly-safe.jsonl'
STATE_DIR = H / 'state'


def utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def run(cmd: list[str], timeout: int) -> dict:
    try:
        p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return {'ok': p.returncode == 0, 'returncode': p.returncode, 'output_tail': p.stdout[-4000:]}
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or '') if isinstance(e.stdout, str) else ''
        return {'ok': False, 'timeout': True, 'returncode': 124, 'output_tail': out[-4000:]}
    except Exception as e:
        return {'ok': False, 'exception': repr(e), 'returncode': 1, 'output_tail': ''}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--timeout', type=int, default=180, help='timeout seconds for consult_models.py run')
    ap.add_argument('--state-timeout', type=int, default=45)
    args = ap.parse_args()

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_path = STATE_DIR / 'multi-brain-nightly-state.json'
    task = 'Nightly actual-usage self-evolution: inspect usage-score.json and propose one low-risk update-safe action.'
    context = {'scope': 'Hermes ~/.hermes/scripts and cron only', 'mode': 'bounded-cron'}

    state_cmd = [
        'python3', str(H/'scripts'/'consult_models.py'), 'state', task,
        '--context-json', json.dumps(context, ensure_ascii=False),
        '--constraint', 'update-safe changes only',
        '--accept', 'discussion_result emitted or explicit timeout recorded',
        '--out', str(state_path),
    ]
    state_res = run(state_cmd, args.state_timeout)

    consult_res = {'ok': False, 'skipped': True, 'reason': 'state_failed'}
    if state_res.get('ok') and state_path.exists():
        consult_cmd = [
            'python3', str(H/'scripts'/'consult_models.py'), 'run', str(state_path),
            '--tier', 'T1', '--quorum', '3', '--discussion', '--max-rounds', '1', '--keep',
        ]
        consult_res = run(consult_cmd, args.timeout)

    usage_res = run(['python3', str(H/'scripts'/'usage-score.py')], 90)
    usage_score = None
    usage_grade = None
    try:
        usage = json.loads((H/'state'/'usage-score.json').read_text())
        usage_score = usage.get('score')
        usage_grade = usage.get('grade')
    except Exception:
        pass

    status = 'ok' if consult_res.get('ok') else 'timeout_recorded' if consult_res.get('timeout') else 'degraded_recorded'
    rec = {
        'ts': utc(),
        'ok': True,
        'status': status,
        'state': state_res,
        'consult': consult_res,
        'usage': {'ok': usage_res.get('ok'), 'score': usage_score, 'grade': usage_grade},
        'state_path': str(state_path),
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
