#!/usr/bin/env python3
"""
PA Daily Report — 个人助理日报
每日 23:00 自动发送给用户
"""

import os, json, datetime

PA_HEALTH = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/pa-health-history.jsonl")
HEALTH = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/health-history.jsonl")
PATTERNS = os.path.expanduser("~/.hermes/notes/user-routine-patterns.json")

def load_today_sessions():
    today = datetime.datetime.now().date().isoformat()
    sessions = []
    for path in [HEALTH, PA_HEALTH]:
        if not os.path.exists(path):
            continue
        with open(path, "r") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if rec["timestamp"].startswith(today):
                        sessions.append(rec)
                except:
                    pass
    return sessions

def load_patterns():
    if os.path.exists(PATTERNS):
        with open(PATTERNS, "r") as f:
            return json.load(f)
    return {}

def main():
    sessions = load_today_sessions()
    patterns = load_patterns()
    
    # 最新 PA 健康度
    V_pa = 0.5
    Vdot_pa = 0
    if os.path.exists(PA_HEALTH):
        with open(PA_HEALTH, "r") as f:
            lines = [l for l in f if l.strip()]
            if lines:
                latest = json.loads(lines[-1])
                V_pa = latest.get("V_pa", 0.5)
                Vdot_pa = latest.get("Vdot_pa", 0)
    
    lines = []
    lines.append("═══════════════════════════════════════════════════════════════")
    lines.append("                  🤖 个人助理 — 每日进化报告")
    lines.append("═══════════════════════════════════════════════════════════════")
    lines.append(f"日期: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    
    lines.append("【今日交互】")
    lines.append(f"  Sessions: {len(sessions)}")
    lines.append("")
    
    lines.append("【PA 健康度】")
    status = "🟢" if V_pa > 0.7 else "🟡" if V_pa > 0.5 else "🔴"
    lines.append(f"  {status} V_PA = {V_pa:.4f}  (目标: 0.85)")
    lines.append(f"     V̇_PA = {Vdot_pa:+.4f}")
    if Vdot_pa > 0.05:
        lines.append("     ↑ 显著进化")
    elif Vdot_pa < -0.05:
        lines.append("     ↓ 退化告警，建议复盘")
    lines.append("")
    
    lines.append("【习得模式】")
    if patterns.get("task_types"):
        for task_type, count in sorted(patterns["task_types"].items(), key=lambda x: -x[1])[:5]:
            status = "🔒" if count >= 3 else "📊"
            lines.append(f"  {status} {task_type}: {count} 次")
    else:
        lines.append("  持续观察中...")
    lines.append("")
    
    lines.append("【进化建议】")
    if V_pa < 0.6:
        lines.append("  • 多与我交互，帮助我学习您的偏好")
    if V_pa < 0.7:
        lines.append("  • 纠正我的输出，我会记住并改进")
    if not any(v >= 3 for v in patterns.get("task_types", {}).values()):
        lines.append("  • 重复任务类型出现 3 次后，我会自动优化")
    if V_pa > 0.7:
        lines.append("  • 运行良好！我可以开始尝试主动建议")
    lines.append("")
    
    lines.append("【等级】")
    if V_pa < 0.6:
        level = "Level 1: 指令执行"
    elif V_pa < 0.72:
        level = "Level 2: 主动确认"
    elif V_pa < 0.82:
        level = "Level 3: 主动建议"
    elif V_pa < 0.90:
        level = "Level 4: 自主执行"
    else:
        level = "Level 5: 预见性伙伴"
    lines.append(f"  {level}")
    lines.append("")
    
    lines.append("═══════════════════════════════════════════════════════════════")
    
    report = "\n".join(lines)
    print(report)
    
    # 保存报告
    report_dir = os.path.expanduser("~/.hermes/notes/reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"pa-daily-{datetime.datetime.now().date().isoformat()}.md")
    with open(report_path, "w") as f:
        f.write(report)

if __name__ == "__main__":
    main()
