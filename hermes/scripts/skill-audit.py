#!/usr/bin/env python3
"""
skill-audit.py — Skill 生态系统审计器
自动检测: 未引用 skill, 重复 skill, stale skill (无变更 >90天), 空/stub skill

用法: python3 skill-audit.py
"""

import os, json, hashlib
from datetime import datetime, timezone
from collections import Counter

HERMES_HOME = os.path.expanduser("~/.hermes")
SKILLS_DIR = os.path.join(HERMES_HOME, "skills")

def scan():
    skills = {}
    for root, dirs, files in os.walk(SKILLS_DIR):
        if "SKILL.md" in files:
            rel = os.path.relpath(root, SKILLS_DIR)
            skmd = os.path.join(root, "SKILL.md")
            stat = os.stat(skmd)
            skills[rel] = {
                "path": skmd,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "is_stub": stat.st_size < 200,
            }

    # Find references in scripts + config + cron
    refs = set()
    for scan_dir in [os.path.join(HERMES_HOME, "scripts"), 
                     os.path.join(HERMES_HOME, "agent-hooks"),
                     os.path.join(HERMES_HOME, "config")]:
        if not os.path.exists(scan_dir):
            continue
        for root, dirs, files in os.walk(scan_dir):
            for f in files:
                if f.endswith(('.py', '.sh', '.yaml', '.yml', '.json')):
                    try:
                        with open(os.path.join(root, f)) as fh:
                            content = fh.read()
                        for skill_name in skills:
                            short = skill_name.split('/')[-1]
                            if short in content:
                                refs.add(skill_name)
                    except:
                        pass

    # Also check cron jobs
    cron_file = os.path.join(HERMES_HOME, "cron", "jobs.json")
    if os.path.exists(cron_file):
        with open(cron_file) as f:
            jobs = json.load(f)
        job_data = json.dumps(jobs)
        for skill_name in skills:
            short = skill_name.split('/')[-1]
            if short in job_data:
                refs.add(skill_name)

    # Classify
    unreferenced = []
    stubs = []
    duplicates = {}
    stale = []

    name_counts = Counter(s.split('/')[-1] for s in skills)
    for name, count in name_counts.items():
        if count > 1:
            duplicates[name] = [s for s in skills if s.split('/')[-1] == name]

    now = datetime.now(timezone.utc).timestamp()
    for name, info in skills.items():
        if info["is_stub"]:
            stubs.append(name)
        if info["mtime"] < now - 90 * 86400:
            stale.append(name)
        if name not in refs:
            # 排除已知的 duplicate (有副本在别处)
            short = name.split('/')[-1]
            if short not in duplicates:
                unreferenced.append(name)

    return {
        "total": len(skills),
        "unreferenced": unreferenced,
        "stubs": stubs,
        "stale_90d": stale,
        "duplicates": {k: v for k, v in list(duplicates.items())[:10]},
        "top_categories": Counter(s.split('/')[0] for s in skills).most_common(10),
        "referenced_count": len(refs),
    }

if __name__ == "__main__":
    result = scan()
    print(f"Skill Audit — {result['total']} skills")
    print(f"  Referenced: {result['referenced_count']}")
    print(f"  Unreferenced: {len(result['unreferenced'])}")
    print(f"  Stubs (<200B): {len(result['stubs'])}")
    print(f"  Stale (>90d): {len(result['stale_90d'])}")
    print(f"  Duplicate names: {len(result['duplicates'])}")
    print()
    
    if result["unreferenced"]:
        print("Unreferenced skills:")
        for s in result["unreferenced"]:
            print(f"  - {s}")
    if result["stubs"]:
        print("\nStub skills (<200B):")
        for s in result["stubs"]:
            print(f"  - {s}")
    
    print(f"\nTop categories:")
    for cat, count in result["top_categories"]:
        print(f"  {cat}: {count}")
    
    print(json.dumps(result, indent=2))
