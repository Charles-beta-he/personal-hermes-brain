#!/usr/bin/env python3
"""
Quarterly Skill Audit — 季度 Skill 审计
全量 Darwin 评估 + D 级淘汰 + 置信度校准
"""

import os, json, datetime, subprocess

SKILLS_DIR = os.path.expanduser("~/.hermes/skills")
RESULTS_PATH = os.path.join(SKILLS_DIR, "darwin-skill", "results.tsv")
DB_PATH = os.path.join(SKILLS_DIR, "bayesian-agent", "confidence-db.json")

def quick_darwin_score(skill_dir):
    score = 0
    skill_file = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(skill_file):
        return 0
    
    with open(skill_file, "r") as f:
        content = f.read().lower()
    
    if "input" in content or "输入" in content: score += 10
    if "output" in content or "输出" in content: score += 10
    if "constraint" in content or "边界" in content or "边界条件" in content: score += 10
    if "checkpoint" in content or "检查点" in content: score += 10
    if "example" in content or "示例" in content: score += 10
    if "---" in content[:50]: score += 10
    
    if os.path.exists(os.path.join(skill_dir, "CHANGELOG.md")): score += 5
    if os.path.exists(os.path.join(skill_dir, "test-prompts.json")): score += 5
    if os.path.isdir(os.path.join(skill_dir, "references")) and os.listdir(os.path.join(skill_dir, "references")):
        score += 5
    
    if len(content) > 2000: score += 15
    elif len(content) > 1000: score += 10
    elif len(content) > 500: score += 5
    if "## " in content: score += 5
    if "```" in content: score += 5
    
    return min(score, 100)

def grade(score):
    if score >= 85: return "A"
    if score >= 75: return "B"
    if score >= 60: return "C"
    return "D"

def audit():
    print("=" * 60)
    print("季度 Skill 审计")
    print("=" * 60)
    
    # 加载置信度数据库
    with open(DB_PATH, "r") as f:
        db = json.load(f)
    
    skills = [d for d in os.listdir(SKILLS_DIR) if os.path.isdir(os.path.join(SKILLS_DIR, d))]
    skills.sort()
    
    results = []
    d_skills = []
    
    now = datetime.datetime.now().isoformat()
    
    for skill in skills:
        skill_dir = os.path.join(SKILLS_DIR, skill)
        score = quick_darwin_score(skill_dir)
        g = grade(score)
        
        # 更新置信度数据库
        if skill in db["skills"]:
            old_score = db["skills"][skill].get("darwin_score", 0)
            db["skills"][skill]["darwin_score"] = score
            db["skills"][skill]["darwin_grade"] = g
            db["skills"][skill]["last_audit"] = now
            
            # 记录到 results.tsv
            with open(RESULTS_PATH, "a") as f:
                f.write(f"{now}\tquarterly-audit\t{skill}\t{old_score}\t{score}\taccepted\tquarterly-review\tauto\n")
        
        results.append((skill, score, g))
        if g == "D":
            d_skills.append(skill)
    
    # 保存更新后的数据库
    with open(DB_PATH, "w") as f:
        json.dump(db, f, indent=2)
    
    # 输出报告
    print(f"\n审计完成: {len(skills)} 个 skill")
    print(f"  A: {sum(1 for _, _, g in results if g == 'A')}")
    print(f"  B: {sum(1 for _, _, g in results if g == 'B')}")
    print(f"  C: {sum(1 for _, _, g in results if g == 'C')}")
    print(f"  D: {len(d_skills)}")
    
    if d_skills:
        print(f"\n⚠️ D 级 skill（需优化或淘汰）:")
        for s in d_skills:
            print(f"  - {s}")
    
    avg_score = sum(s for _, s, _ in results) / len(results) if results else 0
    print(f"\n平均分: {avg_score:.1f}")
    print(f"目标: >80 分")
    print("=" * 60)

if __name__ == "__main__":
    audit()
