#!/usr/bin/env python3
"""Local-first verifier for the Obsidian main hierarchy migration.
No network, no LLM, no external runtime mutation. It validates the canonical vault.
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys
from pathlib import Path

VAULT = Path.home() / "Documents/brain"
EXPECTED_TOP = [
    "00-索引",
    "01-系统与偏好",
    "02-证据与原文",
    "03-理论与元认知",
    "04-知识原子",
    "05-实践与项目",
    "06-治理与评审",
    "07-仪表盘",
    "08-模板",
    "99-hermes-notes",
]
OLD_TOP = [
    "00-evidence", "00-system", "01-控制论基础", "02-治理理论", "03-系统理论",
    "04-技能生态", "05-进化日志", "06-仪表盘", "07-元认知", "08-实践方案",
    "09-引用原文", "10-ai-systems", "10-atoms", "10-模板", "20-projects",
    "30-tasks", "40-skills", "50-prefs", "60-reviews",
]
# 99-hermes-notes became 09-hermes-notes, so old list intentionally includes it.
REQUIRED_FILES = {
    "root_index": VAULT / "00-索引/00-大脑索引.md",
    "system_moc": VAULT / "01-系统与偏好/00-系统与偏好索引.md",
    "evidence_moc": VAULT / "02-证据与原文/00-证据与原文索引.md",
    "theory_moc": VAULT / "03-理论与元认知/00-理论与元认知索引.md",
    "atoms_moc": VAULT / "04-知识原子/00-知识原子索引.md",
    "practice_moc": VAULT / "05-实践与项目/00-实践与项目索引.md",
    "governance_moc": VAULT / "06-治理与评审/00-治理与评审索引.md",
    "dashboard_moc": VAULT / "07-仪表盘/00-仪表盘索引.md",
    "template_moc": VAULT / "08-模板/00-模板索引.md",
    "hermes_moc": VAULT / "99-hermes-notes/00-hermes-notes索引.md",
    "project": VAULT / "05-实践与项目/projects/local-brain-main-hierarchy-migration/Project - Local Brain Main Hierarchy Migration.md",
    "p10": VAULT / "05-实践与项目/projects/local-brain-main-hierarchy-migration/P10 - Main Hierarchy Migration Strategy.md",
    "p9": VAULT / "05-实践与项目/projects/local-brain-main-hierarchy-migration/P9 - Main Hierarchy Migration Backlog.md",
    "playbook": VAULT / "05-实践与项目/实践方案/08-主层级迁移Playbook.md",
    "review": VAULT / "06-治理与评审/reviews/2026-05-06-main-hierarchy-migration-review.md",
    "task": VAULT / "05-实践与项目/tasks/2026-05-06-main-hierarchy-migration-log.md",
    "evolution": VAULT / "06-治理与评审/进化日志/2026-05-06-本地大脑主层级迁移.md",
    "atom": VAULT / "04-知识原子/atoms/main-hierarchy-migration-as-control-plane.md",
}
REQUIRED_PATTERNS = {
    "root_index": ["Canonical main hierarchy after migration", "P10 control-plane layout", "本地大脑主层级迁移", "无遗留"],
    "p10": ["Strategic decision", "control-plane", "Stop gate", "empty_dirs", "old_top_dirs_remaining"],
    "review": ["Multi-model participation", "weak_consensus", "provenance", "deterministic gates"],
    "task": ["Backup", "Mapping", "Verification", "本地大脑主层级迁移"],
    "playbook": ["Backup manifest", "Rewrite path wikilinks", "self-check", "PUA loop"],
    "atom": ["Main hierarchy as control-plane", "Evidence boundary", "本地大脑主层级迁移"],
}
SECRET_PATTERNS = [
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?i)(secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}"),
    re.compile(r"sk-(?:live|test|proj)-[A-Za-z0-9_-]{16,}"),
]
LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

def run(cmd, timeout=60):
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    return {"cmd": cmd, "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}

def build_note_index(md_files):
    by_base = {}
    by_rel = set()
    for p in md_files:
        rel = str(p.relative_to(VAULT)).replace('\\', '/')
        no_ext = rel[:-3] if rel.endswith('.md') else rel
        by_rel.add(no_ext)
        by_rel.add(rel)
        by_base.setdefault(p.stem, []).append(no_ext)
    return by_base, by_rel

def structure_audit():
    dirs = [p for p in VAULT.rglob('*') if p.is_dir() and not any(part.startswith('.') for part in p.relative_to(VAULT).parts)]
    md_files = [p for p in VAULT.rglob('*.md') if not any(part.startswith('.') for part in p.relative_to(VAULT).parts)]
    top_dirs = sorted([p.name for p in VAULT.iterdir() if p.is_dir() and not p.name.startswith('.')]) if VAULT.exists() else []
    empty_dirs = [str(p.relative_to(VAULT)) for p in dirs if not any(p.iterdir())]
    top_level_no_index = []
    parent_no_direct_md_top = []
    for p in [VAULT / name for name in top_dirs]:
        direct_md = list(p.glob('*.md'))
        has_index = any(f.name.startswith('00-') and ('索引' in f.name or 'index' in f.name.lower()) for f in direct_md)
        if not has_index:
            top_level_no_index.append(p.name)
        if not direct_md and any(x.suffix == '.md' for x in p.rglob('*.md')):
            parent_no_direct_md_top.append(p.name)
    by_base, by_rel = build_note_index(md_files)
    broken = []
    old_path_link_hits = []
    old_prefixes = tuple(x + '/' for x in OLD_TOP)
    for p in md_files:
        text = p.read_text(encoding='utf-8', errors='ignore')
        for m in LINK_RE.finditer(text):
            raw = m.group(1)
            target = raw.split('|', 1)[0].split('#', 1)[0]
            if not target or target.startswith('#'):
                continue
            if target.startswith(old_prefixes) or target in OLD_TOP:
                old_path_link_hits.append({"file": str(p.relative_to(VAULT)), "target": target})
            candidates = []
            if '/' in target:
                candidates.extend([target, target + '.md'])
            else:
                candidates.extend(by_base.get(target, []))
            if not any(c in by_rel for c in candidates):
                broken.append({"file": str(p.relative_to(VAULT)), "target": target})
    secret_hits = []
    for p in md_files:
        text = p.read_text(encoding='utf-8', errors='ignore')
        for i,line in enumerate(text.splitlines(), 1):
            for pat in SECRET_PATTERNS:
                if pat.search(line):
                    secret_hits.append({"file": str(p.relative_to(VAULT)), "line": i})
                    break
    return {
        "top_dirs": top_dirs,
        "expected_top_dirs": EXPECTED_TOP,
        "old_top_dirs_remaining": [x for x in OLD_TOP if (VAULT / x).exists()],
        "empty_dirs": empty_dirs,
        "top_level_no_index": top_level_no_index,
        "parent_no_direct_md_top": parent_no_direct_md_top,
        "broken_wikilinks_count": len(broken),
        "broken_wikilinks_sample": broken[:20],
        "old_path_link_hits_count": len(old_path_link_hits),
        "old_path_link_hits_sample": old_path_link_hits[:20],
        "secret_pattern_hits": len(secret_hits),
        "secret_pattern_files": sorted({h['file'] for h in secret_hits}),
        "md_files": len(md_files),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    checks = []
    ok = True
    def add(name, cond, **extra):
        nonlocal ok
        checks.append({"name": name, "ok": bool(cond), **extra})
        ok = ok and bool(cond)
    add('vault_exists', VAULT.exists(), path=str(VAULT))
    st = structure_audit() if VAULT.exists() else {}
    add('top_dirs_exact', st.get('top_dirs') == EXPECTED_TOP, value=st.get('top_dirs'))
    add('old_top_dirs_remaining', st.get('old_top_dirs_remaining') == [], value=st.get('old_top_dirs_remaining'))
    for key, path in REQUIRED_FILES.items():
        exists = path.exists()
        add(f'file:{key}', exists, path=str(path))
        if exists and key in REQUIRED_PATTERNS:
            text = path.read_text(encoding='utf-8', errors='ignore')
            for pat in REQUIRED_PATTERNS[key]:
                add(f'pattern:{key}:{pat}', pat in text, path=str(path))
    add('structure:empty_dirs', st.get('empty_dirs') == [], value=st.get('empty_dirs'))
    add('structure:top_level_no_index', st.get('top_level_no_index') == [], value=st.get('top_level_no_index'))
    add('structure:parent_no_direct_md_top', st.get('parent_no_direct_md_top') == [], value=st.get('parent_no_direct_md_top'))
    add('structure:broken_wikilinks_count', st.get('broken_wikilinks_count') == 0, value=st.get('broken_wikilinks_count'), sample=st.get('broken_wikilinks_sample'))
    add('structure:old_path_link_hits_count', st.get('old_path_link_hits_count') == 0, value=st.get('old_path_link_hits_count'), sample=st.get('old_path_link_hits_sample'))
    add('structure:secret_pattern_hits', st.get('secret_pattern_hits') == 0, value=st.get('secret_pattern_hits'), files=st.get('secret_pattern_files'))
    brainctl = {}
    script = str(Path.home() / '.hermes/scripts/brainctl.py')
    if Path(script).exists():
        for name, query in {
            'search_migration_zh': '本地大脑主层级迁移 P10 control-plane layout 无遗留',
            'search_control_plane': 'main hierarchy control-plane evidence theory atoms practice governance',
            'search_multimodel': '多模型验证 主层级迁移 weak_consensus provenance_only',
        }.items():
            res = run([sys.executable, script, '--json', 'search', query, '--limit', '8'])
            brainctl[name] = res
            add(f'brainctl:{name}', res['exit_code'] == 0 and '主层级迁移' in res.get('stdout', '') or (name == 'search_control_plane' and 'control-plane' in res.get('stdout','')), exit_code=res['exit_code'])
    else:
        add('brainctl:exists', False, path=script)
    report = {"status": "PASS" if ok else "FAIL", "checks_count": len(checks), "failed_checks": [c for c in checks if not c.get('ok')], "checks": checks, "structure": st, "brainctl": brainctl}
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else report['status'])
    return 0 if ok else 1

if __name__ == '__main__':
    raise SystemExit(main())
