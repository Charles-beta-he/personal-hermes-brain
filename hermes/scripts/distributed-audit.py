#!/usr/bin/env python3
"""分布式并行 Skill 审计"""
import os, json, subprocess, concurrent.futures, datetime

SKILLS_DIR = os.path.expanduser("~/.hermes/skills")
DB_PATH = os.path.join(SKILLS_DIR, "bayesian-agent/confidence-db.json")
REPORTS = os.path.expanduser("~/.hermes/notes/reports")

def audit_skill(name, path):
    """审计单个 skill，返回 (name, score, grade, fixes)"""
    score = 0
    fixes = []
    
    skill_md = os.path.join(path, "SKILL.md")
    if os.path.exists(skill_md):
        size = os.path.getsize(skill_md)
        score += min(size / 100, 40)
        if size < 500:
            fixes.append("SKILL.md 过短")
    else:
        fixes.append("缺少 SKILL.md")
    
    has_refs = os.path.exists(os.path.join(path, "references"))
    has_scripts = os.path.exists(os.path.join(path, "scripts"))
    has_templates = os.path.exists(os.path.join(path, "templates"))
    has_changelog = os.path.exists(os.path.join(path, "CHANGELOG.md"))
    has_tests = os.path.exists(os.path.join(path, "test-prompts.json"))
    
    score += 10 if has_refs else 0
    score += 10 if has_scripts else 0
    score += 10 if has_templates else 0
    score += 10 if has_changelog else 0
    score += 10 if has_tests else 0
    
    if not has_refs: fixes.append("缺少 references/")
    if not has_changelog: fixes.append("缺少 CHANGELOG.md")
    if not has_tests: fixes.append("缺少 test-prompts.json")
    
    grade = "S" if score >= 90 else "A" if score >= 85 else "B" if score >= 75 else "C" if score >= 60 else "D"
    return name, score, grade, fixes

def main():
    skills = []
    for root, dirs, files in os.walk(SKILLS_DIR):
        if root == SKILLS_DIR:
            for d in dirs:
                if d.startswith("."): continue
                path = os.path.join(root, d)
                if os.path.exists(os.path.join(path, "SKILL.md")):
                    skills.append((d, path))
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(audit_skill, n, p): (n, p) for n, p in skills}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    # 更新 DB
    with open(DB_PATH) as f:
        db = json.load(f)
    
    updated = 0
    for name, score, grade, fixes in results:
        if name in db["skills"]:
            old = db["skills"][name].get("darwin_score", 0)
            old_g = db["skills"][name].get("darwin_grade", "C")
            if score > old:
                db["skills"][name]["darwin_score"] = round(score, 1)
                db["skills"][name]["darwin_grade"] = grade
                updated += 1
    
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=2)
    
    report_path = os.path.join(REPORTS, "distributed-audit-report.md")
    with open(report_path, "w") as f:
        f.write(f"# 分布式审计报告\n\n时间: {datetime.datetime.now().isoformat()}\n\n")
        f.write(f"审计 Skill 数: {len(results)}\n更新: {updated}\n")
    
    print(f"Audit complete: {len(results)} skills, {updated} updated")

if __name__ == "__main__":
    main()
