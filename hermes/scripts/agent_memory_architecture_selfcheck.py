#!/usr/bin/env python3
"""Agent Memory Architecture Selfcheck Script v3.0.0

Performs runtime and structural verification of the ~/.hermes/memory/ architecture.
Run after any file operation to validate the system.
"""
import os, sys, json, fcntl, re, time
from pathlib import Path
from datetime import datetime

MEMORY_ROOT = Path.home() / '.hermes' / 'memory'
REPORT_PATH = MEMORY_ROOT / '_report' / 'last_selfcheck.json'
VERSION = '3.0.0'
MAX_MEMORY_MD_KB = 2
MAX_UNASSIGNED = 3
MAX_P90_KB = 8
COLLAPSE_SECONDS = 7 * 24 * 3600

class Issue:
    def __init__(self, severity, category, message, path=None):
        self.severity = severity  # 'CRITICAL' | 'WARN'
        self.category = category
        self.message = message
        self.path = path

    def to_dict(self):
        d = {'severity': self.severity, 'category': self.category, 'message': self.message}
        if self.path:
            d['path'] = str(self.path)
        return d

issues = []
metrics = {}

def check_memory_md():
    """S1: MEMORY.md 必须是 symlink 指向 memory/system/memory.md"""
    p = MEMORY_ROOT / 'MEMORY.md'
    if not p.exists():
        issues.append(Issue('CRITICAL', 'S1', 'MEMORY.md missing'))
        return
    if not p.is_symlink():
        issues.append(Issue('CRITICAL', 'S1', 'MEMORY.md is not a symlink', p))
        return
    target = p.resolve()
    expected = (MEMORY_ROOT / 'system' / 'memory.md').resolve()
    if target != expected:
        issues.append(Issue('CRITICAL', 'S1', f'MEMORY.md symlink points to {target}, expected {expected}', p))

def check_locked_files():
    """S2: 锁定文件必须存在且非空"""
    locks = [
        MEMORY_ROOT / 'system' / 'SELF.md',
        MEMORY_ROOT / 'config' / 'paths.md',
        MEMORY_ROOT / 'config' / 'conventions.md',
    ]
    for p in locks:
        if not p.exists():
            issues.append(Issue('CRITICAL', 'S2', f'Locked file missing: {p.name}', p))
        elif p.stat().st_size == 0:
            issues.append(Issue('CRITICAL', 'S2', f'Locked file empty: {p.name}', p))

def check_must_exist():
    """S3: 必须存在的文件"""
    must = [
        MEMORY_ROOT / 'system' / 'memory.md',
        MEMORY_ROOT / 'system' / 'active_tasks.md',
        MEMORY_ROOT / 'config' / 'models.md',
        MEMORY_ROOT / 'config' / 'preferences.md',
        MEMORY_ROOT / 'MIGRATION_NOTES.md',
    ]
    for p in must:
        if not p.exists():
            issues.append(Issue('CRITICAL', 'S3', f'Required file missing: {p.name}', p))

def check_temp_leaks():
    """S5: temp/ 中无超过 3 天的文件"""
    temp_dir = MEMORY_ROOT / 'temp'
    if not temp_dir.exists():
        return
    now = time.time()
    for f in temp_dir.iterdir():
        if f.name.startswith('.'):
            continue
        age_hours = (now - f.stat().st_mtime) / 3600
        if age_hours > 72:
            issues.append(Issue('CRITICAL', 'S5', f'temp/ file older than 72h: {f.name} ({age_hours:.0f}h)', f))

def check_archive_quarantine():
    """S5: archive/ 和 quarantine/ 中禁止时间标记文件"""
    for dname in ['archive', 'quarantine']:
        d = MEMORY_ROOT / dname
        if not d.exists():
            continue
        for f in d.rglob('*'):
            if f.is_file() and re.search(r'20[0-9]{6}', f.name):
                issues.append(Issue('CRITICAL', 'S5', f'Timestamp leak in {dname}/: {f.relative_to(MEMORY_ROOT)}', f))

def check_template_instantiated():
    """S6: template/ 中禁止实例化对象"""
    template_dir = MEMORY_ROOT / 'template'
    if not template_dir.exists():
        return
    for f in template_dir.iterdir():
        if f.name.startswith('.'):
            continue
        if f.is_file():
            issues.append(Issue('CRITICAL', 'S6', f'Template file must not be instantiated: {f.name}', f))

def check_folder_structure():
    """S7: 顶层目录数量 11-14"""
    dirs = [d for d in MEMORY_ROOT.iterdir() if d.is_dir() and not d.name.startswith(('.', '_'))]
    metrics['top_level_dirs'] = len(dirs)
    if len(dirs) < 11:
        issues.append(Issue('CRITICAL', 'S7', f'Too few top-level dirs: {len(dirs)} (need 11-14)'))
    elif len(dirs) > 14:
        issues.append(Issue('WARN', 'S7', f'Too many top-level dirs: {len(dirs)} (need 11-14)'))

def check_system_completeness():
    """S8: system/ 子目录完整性"""
    system = MEMORY_ROOT / 'system'
    if not system.exists():
        issues.append(Issue('CRITICAL', 'S8', 'system/ directory missing'))
        return
    expected = ['context', 'tasks', 'memory', 'review', 'tool', 'models']
    for d in expected:
        if not (system / d).exists():
            issues.append(Issue('CRITICAL', 'S8', f'system/{d}/ missing'))

def check_docs_structure():
    """S8: docs/ 子目录完整性"""
    docs = MEMORY_ROOT / 'docs'
    if not docs.exists():
        issues.append(Issue('CRITICAL', 'S8', 'docs/ directory missing'))
        return
    for d in ['prds', 'task', 'adr', 'lark']:
        if not (docs / d).exists():
            issues.append(Issue('CRITICAL', 'S8', f'docs/{d}/ missing'))

def check_record_syntax():
    """S9: 所有 record*.md 语法检查"""
    record_re = re.compile(r'\d{14}_[a-z0-9_-]+\.md')
    for f in MEMORY_ROOT.rglob('record*.md'):
        if not record_re.match(f.name):
            issues.append(Issue('WARN', 'S9', f'Record filename non-standard: {f.name}', f))

def check_merge_lock():
    """S9: merge.lock 一致性"""
    lock = MEMORY_ROOT / 'config' / 'merge.lock'
    if lock.exists():
        try:
            data = json.loads(lock.read_text())
            if 'created_at' not in data:
                issues.append(Issue('WARN', 'S9', 'merge.lock missing created_at', lock))
        except json.JSONDecodeError:
            issues.append(Issue('CRITICAL', 'S9', 'merge.lock invalid JSON', lock))

def check_duplicate_leaks():
    """S9: 检测 memory.md 中的标题重复"""
    mm = MEMORY_ROOT / 'system' / 'memory.md'
    if not mm.exists():
        return
    lines = mm.read_text(errors='ignore').splitlines()
    headers = [l for l in lines if l.startswith('## ')]
    seen = set()
    for h in headers:
        if h in seen:
            issues.append(Issue('WARN', 'S9', f'Duplicate header in memory.md: {h}'))
        seen.add(h)

def check_collapse_cadence():
    """S10: 检查 review/pending/ 中是否有超期待折叠的 session"""
    pending = MEMORY_ROOT / 'system' / 'review' / 'pending'
    if not pending.exists():
        return
    now = time.time()
    for f in pending.iterdir():
        if not f.is_file():
            continue
        age = now - f.stat().st_mtime
        if age > COLLAPSE_SECONDS:
            issues.append(Issue('WARN', 'S10', f'Session pending collapse >7d: {f.name} ({age/86400:.1f}d)', f))

def check_view_completeness():
    """S11: 对应视图源文件缺失时输出警告"""
    views = MEMORY_ROOT / 'system' / 'views'
    if not views.exists():
        return
    for f in views.iterdir():
        if not f.is_file() or f.suffix != '.json':
            continue
        try:
            data = json.loads(f.read_text())
            sources = data.get('sources', [])
            for src in sources:
                src_path = MEMORY_ROOT / src
                if not src_path.exists():
                    issues.append(Issue('WARN', 'S11', f'View source missing: {src}', f))
        except (json.JSONDecodeError, KeyError):
            pass

def check_hermes_md():
    """S12: ~/.hermes/HERMES.md 必须存在且非空"""
    p = Path.home() / '.hermes' / 'HERMES.md'
    if not p.exists():
        issues.append(Issue('CRITICAL', 'S12', 'HERMES.md missing'))
    elif p.stat().st_size == 0:
        issues.append(Issue('CRITICAL', 'S12', 'HERMES.md is empty'))

def compute_metrics():
    """计算 P90、unassigned 数量等"""
    # P90 of file sizes
    sizes = []
    for f in MEMORY_ROOT.rglob('*.md'):
        if f.is_file():
            sizes.append(f.stat().st_size)
    if sizes:
        sizes.sort()
        p90_idx = int(len(sizes) * 0.9)
        metrics['p90_file_kb'] = round(sizes[min(p90_idx, len(sizes)-1)] / 1024, 2)
        metrics['total_md_files'] = len(sizes)
    else:
        metrics['p90_file_kb'] = 0
        metrics['total_md_files'] = 0

    # Unassigned count (not assigned to any task)
    active_tasks_file = MEMORY_ROOT / 'system' / 'active_tasks.md'
    assigned = set()
    if active_tasks_file.exists():
        text = active_tasks_file.read_text(errors='ignore')
        for m in re.finditer(r'关联文件[:：]\s*(.+)', text):
            for part in re.split(r'[,，、\s]+', m.group(1).strip()):
                part = part.strip()
                if part:
                    assigned.add(part)
    unassigned = 0
    task_dirs = [MEMORY_ROOT / 'task']
    for td in task_dirs:
        if not td.exists():
            continue
        for task_dir in td.iterdir():
            if not task_dir.is_dir():
                continue
            for f in task_dir.rglob('*.md'):
                rel = str(f.relative_to(MEMORY_ROOT))
                if rel not in assigned:
                    unassigned += 1
    metrics['unassigned_records'] = unassigned

    # MEMORY.md symlink size
    mm = MEMORY_ROOT / 'MEMORY.md'
    if mm.exists():
        metrics['memory_md_kb'] = round(mm.stat().st_size / 1024, 2)

    # Lock status
    metrics['merge_lock_exists'] = (MEMORY_ROOT / 'config' / 'merge.lock').exists()

    # Recent collapses
    report = MEMORY_ROOT / '_report' / 'last_selfcheck.json'
    if report.exists():
        try:
            data = json.loads(report.read_text())
            metrics['last_collapse'] = data.get('last_collapse', 'unknown')
        except:
            metrics['last_collapse'] = 'unknown'
    else:
        metrics['last_collapse'] = 'never'

def severity_sort(issue):
    return 0 if issue.severity == 'CRITICAL' else 1

def main():
    checks = [
        check_memory_md,
        check_locked_files,
        check_must_exist,
        check_temp_leaks,
        check_archive_quarantine,
        check_template_instantiated,
        check_folder_structure,
        check_system_completeness,
        check_docs_structure,
        check_record_syntax,
        check_merge_lock,
        check_duplicate_leaks,
        check_collapse_cadence,
        check_view_completeness,
        check_hermes_md,
    ]

    for check in checks:
        try:
            check()
        except Exception as e:
            issues.append(Issue('CRITICAL', 'RUNTIME', f'Check {check.__name__} crashed: {e}'))

    compute_metrics()

    criticals = [i for i in issues if i.severity == 'CRITICAL']
    warnings = [i for i in issues if i.severity == 'WARN']

    # Print report
    print(f'=== Agent Memory Architecture Selfcheck v{VERSION} ===')
    print(f'Time: {datetime.now().isoformat()}')
    print(f'Metrics: {json.dumps(metrics, indent=2)}')
    print()

    if not criticals and not warnings:
        print('PASS: All checks passed.')
        verdict = 'PASS'
    elif criticals:
        verdict = 'FAIL'
        print(f'FAIL: {len(criticals)} CRITICAL, {len(warnings)} WARN')
        issues.sort(key=severity_sort)
        for i in issues:
            print(f'  [{i.severity}] {i.category}: {i.message}')
    else:
        verdict = 'WARN'
        print(f'WARN: {len(warnings)} warnings')
        for i in warnings:
            print(f'  [{i.severity}] {i.category}: {i.message}')

    # Write JSON report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = {
        'version': VERSION,
        'timestamp': datetime.now().isoformat(),
        'verdict': verdict,
        'metrics': metrics,
        'issues': [i.to_dict() for i in issues],
        'checks_run': len(checks),
        'critical_count': len(criticals),
        'warn_count': len(warnings),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f'\nReport saved: {REPORT_PATH}')

    return 0 if verdict == 'PASS' else 1

if __name__ == '__main__':
    sys.exit(main())
