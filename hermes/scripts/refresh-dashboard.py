#!/usr/bin/env python3
"""
Refresh Dashboard — 自动刷新进化仪表盘
由 session-health-logger.py 或 cronjob 触发
"""

import os, json, datetime

SKILLS_DIR = os.path.expanduser("~/.hermes/skills")
HEALTH_PATH = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/health-history.jsonl")
DB_PATH = os.path.join(SKILLS_DIR, "bayesian-agent", "confidence-db.json")
RESULTS_PATH = os.path.join(SKILLS_DIR, "darwin-skill", "results.tsv")
DASHBOARD_PATH = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/evolution-dashboard.md")

def get_vdot(record):
    """Return V̇ across historical schema aliases (Vdot and V_dot)."""
    return record.get('Vdot', record.get('V_dot', 0))

def refresh():
    with open(DB_PATH, "r") as f:
        conf_db = json.load(f)
    
    total = len(conf_db["skills"])
    with_d = sum(1 for s in conf_db["skills"].values() if s.get("darwin_score"))
    grades = {"A": 0, "B": 0, "C": 0, "D": 0, "pending": 0}
    for s in conf_db["skills"].values():
        grades[s.get("darwin_grade", "pending")] = grades.get(s.get("darwin_grade", "pending"), 0) + 1
    
    health_records = []
    if os.path.exists(HEALTH_PATH):
        with open(HEALTH_PATH, "r") as f:
            for line in f:
                try:
                    health_records.append(json.loads(line))
                except:
                    pass
    
    with open(RESULTS_PATH, "r") as f:
        results_lines = f.readlines()
    
    lines = []
    lines.append("═══════════════════════════════════════════════════════════════════════════════")
    lines.append("                    Agent 控制论进化仪表盘")
    lines.append("═══════════════════════════════════════════════════════════════════════════════")
    lines.append(f"Timestamp: {datetime.datetime.now().isoformat()}")
    lines.append("")
    
    lines.append("【健康度】")
    if health_records:
        latest = health_records[-1]
        v = latest.get('V', 0.86)
        vdot = get_vdot(latest)
        lines.append(f"  V = {v:.4f}")
        lines.append(f"  V̇ = {float(vdot):+.4f}")
        lines.append(f"  记录数: {len(health_records)}")
        
        # 趋势
        if len(health_records) >= 3:
            recent_v = [r.get('V', 0) for r in health_records[-5:]]
            trend = "↑" if recent_v[-1] > recent_v[0] else "↓" if recent_v[-1] < recent_v[0] else "→"
            lines.append(f"  趋势: {trend} (近5次)")
    else:
        lines.append("  V = 0.8600 (基线)")
        lines.append("  V̇ = 0.0000")
    lines.append("")
    
    lines.append("【Skill 生态】")
    lines.append(f"  总数: {total}")
    lines.append(f"  已评估: {with_d}")
    lines.append(f"  等级: A={grades.get('A',0)} B={grades.get('B',0)} C={grades.get('C',0)} D={grades.get('D',0)}")
    lines.append("")
    
    lines.append("【Phase 状态】")
    lines.append("  Phase 0: ✅ 跨学科基线")
    lines.append("  Phase 1: ✅ 控制论基线")
    lines.append("  Phase 2: ✅ 反馈优化")
    lines.append("  Phase 3: ✅ 智能升级")
    lines.append("  Phase 4: ✅ 大系统")
    lines.append("  Phase 5: 🔄 数据驱动验证")
    lines.append("")
    
    lines.append("【最近 Darwin 记录】")
    for line in results_lines[-5:]:
        cols = line.strip().split("\t")
        if len(cols) >= 6 and cols[0] != "timestamp":
            lines.append(f"  {cols[0][:10]} {cols[2]:<25} {cols[3]:>3}→{cols[4]:>3} [{cols[5]}]")
    lines.append("")
    
    lines.append("═══════════════════════════════════════════════════════════════════════════════")
    
    dashboard = "\n".join(lines)
    with open(DASHBOARD_PATH, "w") as f:
        f.write(dashboard)
    print("✓ Dashboard refreshed")

if __name__ == "__main__":
    refresh()
