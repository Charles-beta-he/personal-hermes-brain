#!/usr/bin/env python3
"""
Daily Startup Checklist — 每日启动时自检
Agent 每天首次启动时运行，确保基础设施就绪
"""

import os, json, sys

SKILLS_DIR = os.path.expanduser("~/.hermes/skills")
SCRIPTS_DIR = os.path.expanduser("~/.hermes/scripts")
NOTES_DIR = os.path.expanduser("~/.hermes/notes/engineering-cybernetics")

def check():
    checks = []
    
    # 1. 核心 skill 存在
    core_skills = ["p10", "p9", "p7", "loop", "pua", "bayesian-agent", "darwin-skill"]
    for skill in core_skills:
        exists = os.path.exists(os.path.join(SKILLS_DIR, skill, "SKILL.md"))
        checks.append((f"core skill: {skill}", exists))
    
    # 2. 核心脚本存在且可执行
    core_scripts = [
        "agent-health-monitor.py",
        "session-history-analyzer.py",
        "self-scan-4h.py",
        "backup-critical-config.py",
        "session-health-logger.py",
        "refresh-dashboard.py",
        "context-budget-calculator.py"
    ]
    for script in core_scripts:
        path = os.path.join(SCRIPTS_DIR, script)
        exists = os.path.exists(path)
        checks.append((f"script: {script}", exists))
    
    # 3. 数据文件存在
    data_files = [
        (os.path.join(SKILLS_DIR, "bayesian-agent", "confidence-db.json"), "confidence-db"),
        (os.path.join(SKILLS_DIR, "darwin-skill", "results.tsv"), "darwin-results"),
        (os.path.join(NOTES_DIR, "AGENT-EVOLUTION-PLAN.md"), "evolution-plan"),
        (os.path.join(SKILLS_DIR, "p10", "references", "reference-model.md"), "reference-model"),
    ]
    for path, name in data_files:
        checks.append((f"data: {name}", os.path.exists(path)))
    
    # 4. 数据库完整性
    db_path = os.path.join(SKILLS_DIR, "bayesian-agent", "confidence-db.json")
    db_ok = False
    if os.path.exists(db_path):
        try:
            with open(db_path, "r") as f:
                db = json.load(f)
            db_ok = "skills" in db and len(db["skills"]) > 0
        except:
            pass
    checks.append(("db integrity", db_ok))
    
    return checks

def main():
    checks = check()
    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)
    
    print("=" * 50)
    print("Daily Startup Checklist")
    print("=" * 50)
    
    for name, ok in checks:
        status = "✓" if ok else "✗"
        print(f"  {status} {name}")
    
    print("=" * 50)
    print(f"结果: {passed}/{total} 通过")
    
    if passed == total:
        print("✓ 系统就绪，可以开始工作")
        return 0
    else:
        print("✗ 有检查项失败，请修复后再启动")
        return 1

if __name__ == "__main__":
    sys.exit(main())
