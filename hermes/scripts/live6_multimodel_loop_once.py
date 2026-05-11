#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys
import time

HERMES = pathlib.Path('/Users/charles/.hermes')
ROUND_DIR = HERMES / 'state/brain_task_multimodel_loop_live6'
cmd = [
    'python3', 'scripts/brain_task_multimodel_loop_runner.py',
    '--round-dir', str(ROUND_DIR),
    '--max-loop-rounds', '1',
    '--discussion-max-rounds', '1',
    '--timeout', '180',
    '--json',
]

def latest_ticks(limit=8):
    ticks = sorted(HERMES.glob('tick-*'), key=lambda p: p.stat().st_mtime)
    return [str(p) for p in ticks[-limit:]]

payload = {
    'task': 'live6_multimodel_loop_once',
    'cmd': cmd,
    'started_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
}
try:
    proc = subprocess.run(cmd, cwd=str(HERMES), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=900, check=False)
    payload.update({
        'returncode': proc.returncode,
        'stdout_tail': (proc.stdout or '')[-12000:],
        'stderr_tail': (proc.stderr or '')[-4000:],
    })
except subprocess.TimeoutExpired as exc:
    payload.update({
        'returncode': 'timeout',
        'stdout_tail': ((exc.output or '') if isinstance(exc.output, str) else '')[-12000:],
        'stderr_tail': ((exc.stderr or '') if isinstance(exc.stderr, str) else '')[-4000:],
    })
except Exception as exc:
    payload.update({'returncode': 'exception', 'exception': f'{type(exc).__name__}: {exc}'})

payload['latest_ticks'] = latest_ticks()
for rel in ['round-01-issue-ledger.json', 'round-01-ratification-artifact.json', 'round-01-state.json']:
    path = ROUND_DIR / rel
    payload[rel] = {'exists': path.exists(), 'path': str(path)}
    if path.exists() and rel != 'round-01-state.json':
        try:
            data = json.loads(path.read_text())
            if rel == 'round-01-issue-ledger.json':
                payload[rel]['summary'] = {
                    'issue_count': len(data.get('issue_ledger') or []),
                    'risk_count': len(data.get('remaining_risks') or []),
                    'verdict': data.get('verdict'),
                    'top_issues': [
                        {k: item.get(k) for k in ('id','severity','status','claim','resolution','target_file','target_model')}
                        for item in (data.get('issue_ledger') or [])[:6]
                        if isinstance(item, dict)
                    ],
                }
            else:
                cm = data.get('consult_models') or {}
                payload[rel]['summary'] = {
                    'discussion_result_status': cm.get('discussion_result_status'),
                    'agreement_matrix': cm.get('agreement_matrix'),
                    'vote_count': len(cm.get('ratification_votes') or []),
                    'best_within_constraints_all': cm.get('best_within_constraints_all'),
                    'issue_count': len(cm.get('issue_ledger') or []),
                    'risk_count': len(cm.get('remaining_risks') or []),
                    'verifier': data.get('verifier'),
                }
        except Exception as exc:
            payload[rel]['read_error'] = f'{type(exc).__name__}: {exc}'

print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
