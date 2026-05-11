#!/usr/bin/env python3
import json, re, sys, subprocess
from pathlib import Path
WORKPAD = Path('/Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/Workpad - uvisa-app-2.0.md')
REVIEW = Path('/Users/charles/Documents/brain/06-治理与评审/reviews/2026-05-08-uvisa-app-2-workpad-multimodel-review.md')
CERT = Path('/Users/charles/Documents/brain/06-治理与评审/reviews/2026-05-08-uvisa-app-2-workpad-certification.json')
REQUIRED_HEADINGS = [
    '# Workpad - uvisa-app-2.0', '## 1. North Star', '## 3. Anchors', '## 4. Red Lines',
    '## 5. Skill Route', '## 6. Business Flow Matrix', '## 7. Acceptance Matrix',
    '## 8. Evidence Ledger', '## 10. Next Loop Queue'
]
REQUIRED_TERMS = [
    'uvisa-app-2.0', 'dead UI', '不丢功能', '不降精度', 'P10/A+',
    'browser-harness', 'Playwright', 'i18n', 'dark', 'mock/real backend',
    'C-001', 'E-001', 'truth_status: grounded', 'current-state baseline'
]
SECRET_PATTERNS = [
    r'sk-[A-Za-z0-9]{20,}', r'ghp_[A-Za-z0-9]{20,}', r'xox[baprs]-[A-Za-z0-9-]{20,}',
    r"(?i)(api[_-]?key|secret|authorization|bearer)\s*[:=]\s*[\"\']?[^\s\"\']{12,}"
]
def brain_search(q):
    cmd=['python3', str(Path.home()/'.hermes/scripts/brainctl.py'), '--json', 'search', q, '--limit', '5']
    p=subprocess.run(cmd, text=True, capture_output=True, timeout=60)
    if p.returncode != 0:
        return {'ok': False, 'error': p.stderr[:500], 'hits': 0}
    try:
        data=json.loads(p.stdout)
        if isinstance(data, list):
            hits=data
        elif isinstance(data, dict):
            hits=data.get('results') or data.get('hits') or []
        else:
            hits=[]
        return {'ok': True, 'hits': len(hits)}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'hits': 0, 'raw': p.stdout[:500]}
def main():
    failures=[]
    for p in [WORKPAD, REVIEW, CERT]:
        if not p.exists(): failures.append(f'missing file: {p}')
    text=WORKPAD.read_text(encoding='utf-8') if WORKPAD.exists() else ''
    if len(text) < 5000: failures.append('workpad too short')
    for h in REQUIRED_HEADINGS:
        if h not in text: failures.append(f'missing heading: {h}')
    for t in REQUIRED_TERMS:
        if t not in text: failures.append(f'missing term: {t}')
    for pat in SECRET_PATTERNS:
        if re.search(pat, text): failures.append(f'possible secret pattern: {pat}')
    try:
        cert=json.loads(CERT.read_text(encoding='utf-8'))
        if cert.get('truth_status') != 'grounded': failures.append('cert truth_status not grounded')
        if cert.get('verified_claim_count') != '5/5': failures.append('cert verified_claim_count not 5/5')
        if cert.get('reference_anchor_decision') != 'current_state_baseline': failures.append('cert reference_anchor_decision not current_state_baseline')
    except Exception as e:
        failures.append(f'cert json invalid: {e}')
    searches={q: brain_search(q) for q in ['Workpad - uvisa-app-2.0','uvisa-app-2.0 dead UI','mock/real backend alignment']}
    for q,r in searches.items():
        if not r.get('ok') or r.get('hits',0) < 1:
            failures.append(f'brain search miss: {q} -> {r}')
    result={'ok': not failures, 'failures': failures, 'files': [str(WORKPAD), str(REVIEW), str(CERT)], 'searches': searches}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 2
if __name__ == '__main__':
    raise SystemExit(main())
