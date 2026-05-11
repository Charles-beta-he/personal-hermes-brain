#!/usr/bin/env python3
"""Local-first deterministic self-check for Agent Cognitive Operating System landing.

Important: this script verifies the deterministic matrix/local-brain gate only. It
surfaces ratification lifecycle fields but does not itself certify multi-model
ratification. Use ratification_gate.py for the certification status transition.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Optional

REQUIRED_FILES = [
    '07-仪表盘/Agent认知操作系统互补矩阵.md',
    '04-知识原子/atoms/agent-cognitive-operating-system.md',
    '05-实践与项目/projects/agent-cognitive-operating-system/Project - Agent Cognitive Operating System.md',
    '05-实践与项目/projects/agent-cognitive-operating-system/P10 - Long-term Strategy.md',
    '05-实践与项目/projects/agent-cognitive-operating-system/P9 - Implementation Backlog.md',
    '05-实践与项目/实践方案/09-Agent认知操作系统Playbook.md',
]

REQUIRED_DOMAINS = [
    '控制论/工程控制论', '系统科学/复杂性', '认知科学', '进化论/生物学', '认识论/科学哲学',
    '经济学/资源理论', '组织管理/军事 C2', '计算机科学/AI', '治理理论', '可靠性工程'
]
REQUIRED_RUBRIC = ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7']
FORBIDDEN_STATUS = ['✗ 缺失', '△ 薄弱', 'missing pair', 'below A+']
CERTIFIED_RATIFICATION_STATUSES = {'CERTIFIED', 'CERTIFIED_WITH_MINOR_RISKS'}


def vault_root() -> Path:
    return Path(os.environ.get('HERMES_BRAIN_VAULT') or os.environ.get('OBSIDIAN_VAULT_PATH') or Path.home() / 'Documents/brain')


def load_contract(text: str):
    m = re.search(r'<!-- COS_CONTRACT_START -->\s*```json\s*(.*?)\s*```\s*<!-- COS_CONTRACT_END -->', text, re.S)
    if not m:
        return None
    return json.loads(m.group(1))


def final_status_from(deterministic_status: str, ratification_status: str, contract_final: str = '') -> str:
    if deterministic_status != 'PASS':
        return 'DETERMINISTIC_BLOCKED'
    if ratification_status in CERTIFIED_RATIFICATION_STATUSES:
        return 'FULLY_CERTIFIED' if ratification_status == 'CERTIFIED' else 'CERTIFIED_WITH_MINOR_RISKS'
    if contract_final and contract_final not in {'FULLY_CERTIFIED', 'CERTIFIED_WITH_MINOR_RISKS'}:
        return contract_final
    return 'LOCAL_COMPLETE_UNRATIFIED'


def run_check(root: Optional[Path] = None) -> dict:
    root = Path(root) if root is not None else vault_root()
    missing_files = [f for f in REQUIRED_FILES if not (root / f).exists()]
    matrix_path = root / '07-仪表盘/Agent认知操作系统互补矩阵.md'
    matrix = matrix_path.read_text(encoding='utf-8') if matrix_path.exists() else ''
    contract = load_contract(matrix) if matrix else None

    parsed_rows = []
    for line in matrix.splitlines():
        if not re.match(r'^\|\s*COS-\d{2}\s*\|', line):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 8:
            parsed_rows.append({
                'id': cells[0],
                'status': cells[-2],
                'grade': cells[-1],
                'raw': line,
            })

    pair_rows = [r['id'] for r in parsed_rows if r['status'] == 'paired' and r['grade'] == 'A+']
    non_a_plus_pair_rows = [r for r in parsed_rows if r['status'] == 'paired' and r['grade'] != 'A+']
    unpaired_rows = [r for r in parsed_rows if r['status'] != 'paired']
    missing_domains = [d for d in REQUIRED_DOMAINS if d not in matrix]
    missing_rubric = [r for r in REQUIRED_RUBRIC if r not in matrix]
    current_section = matrix.split('## 缺失配对归零说明', 1)[0]
    forbidden_hits = [s for s in FORBIDDEN_STATUS if s in current_section]
    duplicate_pair_ids = sorted({x for x in pair_rows if pair_rows.count(x) > 1})

    contract = contract or {}
    matrix_status = contract.get('matrix_status') or contract.get('cos_status') or 'UNKNOWN'
    ratification_status = contract.get('ratification_status') or 'NOT_STARTED'
    required_pairings_count = int(contract.get('required_pairings_count', 24) or 24)

    result = {
        'status': 'PASS',
        'vault': str(root),
        'required_files': len(REQUIRED_FILES),
        'missing_files': missing_files,
        'contract_present': bool(contract),
        'contract': contract,
        'matrix_status': matrix_status,
        'legacy_cos_status': contract.get('cos_status') or contract.get('legacy_cos_status'),
        'deterministic_gate_status': 'PASS',
        'ratification_status': ratification_status,
        'final_integration_status': '',
        'pair_rows_count': len(pair_rows),
        'unique_pair_rows_count': len(set(pair_rows)),
        'duplicate_pair_ids': duplicate_pair_ids,
        'required_pairings_count': required_pairings_count,
        'missing_pairs': 0 if len(set(pair_rows)) >= required_pairings_count and not duplicate_pair_ids else max(0, required_pairings_count - len(set(pair_rows))),
        'below_a_plus': len(non_a_plus_pair_rows),
        'unpaired_rows_count': len(unpaired_rows),
        'missing_domains': missing_domains,
        'missing_rubric': missing_rubric,
        'forbidden_current_status_hits': forbidden_hits,
        'required_domains_ok': not missing_domains,
        'a_plus_rubric_ok': not missing_rubric,
        'ratification_note': 'deterministic selfcheck is evidence only; ratification_gate.py controls certification transition',
    }

    if contract:
        if contract.get('missing_pairs') != 0:
            result['missing_pairs'] = max(result['missing_pairs'], int(contract.get('missing_pairs', 999) or 999))
        if contract.get('below_a_plus') != 0:
            result['below_a_plus'] = max(result['below_a_plus'], int(contract.get('below_a_plus', 999) or 999))

    fail_reasons = []
    for key in ['missing_files', 'missing_domains', 'missing_rubric', 'forbidden_current_status_hits', 'duplicate_pair_ids']:
        if result[key]:
            fail_reasons.append(key)
    if not result['contract_present']:
        fail_reasons.append('contract_present')
    if result['missing_pairs'] != 0:
        fail_reasons.append('missing_pairs')
    if result['below_a_plus'] != 0:
        fail_reasons.append('below_a_plus')
    if len(set(pair_rows)) < required_pairings_count:
        fail_reasons.append('pair_rows_count')
    if matrix_status not in {'A_PLUS_MATRIX_COMPLETE', 'A_PLUS_COMPLETE'}:
        fail_reasons.append('matrix_status')

    if fail_reasons:
        result['status'] = 'FAIL'
        result['deterministic_gate_status'] = 'FAIL'
        result['fail_reasons'] = fail_reasons

    result['final_integration_status'] = final_status_from(
        result['deterministic_gate_status'],
        ratification_status,
        str(contract.get('final_integration_status') or ''),
    )
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    result = run_check()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Agent COS deterministic self-check: {result['status']}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
