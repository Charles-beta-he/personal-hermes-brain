#!/usr/bin/env python3
"""
PA Evolution Trigger — 个人助理方向进化自动触发器
每次 session 结束后运行，分析用户行为模式，触发进化动作
"""

import os, json, datetime, re

HEALTH_PATH = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/health-history.jsonl")
PROFILE_PATH = os.path.expanduser("~/.hermes/notes/user-profile.md")
PATTERNS_PATH = os.path.expanduser("~/.hermes/notes/user-routine-patterns.json")
SKILLS_DIR = os.path.expanduser("~/.hermes/skills")
TRIGGER_LOG = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/pa-trigger-log.jsonl")

def load_recent_sessions(days=7):
    sessions = []
    if not os.path.exists(HEALTH_PATH):
        return sessions
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    with open(HEALTH_PATH, "r") as f:
        for line in f:
            try:
                rec = json.loads(line)
                ts = datetime.datetime.fromisoformat(rec["timestamp"])
                if ts > cutoff:
                    sessions.append(rec)
            except:
                pass
    return sessions

def load_patterns():
    if os.path.exists(PATTERNS_PATH):
        with open(PATTERNS_PATH, "r") as f:
            return json.load(f)
    return {"task_types": {}, "time_slots": {}, "preferences": {}}

def save_patterns(patterns):
    os.makedirs(os.path.dirname(PATTERNS_PATH), exist_ok=True)
    with open(PATTERNS_PATH, "w") as f:
        json.dump(patterns, f, indent=2)

def log_trigger(trigger_type, details):
    os.makedirs(os.path.dirname(TRIGGER_LOG), exist_ok=True)
    with open(TRIGGER_LOG, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.datetime.now().isoformat(),
            "trigger": trigger_type,
            "details": details
        }) + "\n")

def detect_task_type_pattern(sessions):
    """检测高频任务类型（3天内≥2次）"""
    from collections import Counter
    recent = [s for s in sessions if datetime.datetime.fromisoformat(s["timestamp"]) > datetime.datetime.now() - datetime.timedelta(days=3)]
    types = Counter(s.get("task_type", "unknown") for s in recent)
    return {t: c for t, c in types.items() if c >= 2}

def detect_corrections(sessions):
    """检测纠正模式"""
    total = len(sessions)
    corrected = sum(1 for s in sessions if s.get("user_corrections", 0) > 0)
    if total == 0:
        return 0.0
    return corrected / total

def calculate_pa_v(sessions):
    """计算 PA 专属健康度 V_PA"""
    if not sessions:
        return 0.5
    
    # 任务一次成功率
    one_shot = sum(1 for s in sessions if s.get("user_corrections", 0) == 0 and s.get("success", False)) / len(sessions)
    
    # 迭代效率（轮次越少越好）
    rounds = [s.get("rounds", 5) for s in sessions]
    avg_rounds = sum(rounds) / len(rounds)
    efficiency = max(0, 1 - (avg_rounds - 3) / 10)  # 3轮=1.0, 13轮=0.0
    
    # 自主完成率（上下文使用低 = 更自主）
    autonomy = sum(1 - s.get("context_used", 0.5) for s in sessions) / len(sessions)
    
    # 跨session记忆（通过纠正频率反推）
    correction_rate = detect_corrections(sessions)
    memory_consistency = max(0, 1 - correction_rate * 2)
    
    # 简化 V_PA
    V_pa = (one_shot * 0.25 + 
            efficiency * 0.20 + 
            autonomy * 0.20 + 
            memory_consistency * 0.15 +
            0.10 +  # 风格匹配基线
            0.10)   # 主动建议基线
    
    return round(min(1.0, max(0.0, V_pa)), 4)

def trigger_actions(sessions, patterns):
    actions = []
    
    # T1: 高频任务固化
    freq_types = detect_task_type_pattern(sessions)
    for task_type, count in freq_types.items():
        if patterns["task_types"].get(task_type, 0) < 3:
            patterns["task_types"][task_type] = patterns["task_types"].get(task_type, 0) + 1
            if patterns["task_types"][task_type] >= 3:
                actions.append({
                    "action": "skill_solidify",
                    "task_type": task_type,
                    "message": f"任务类型 '{task_type}' 已出现 3 次，建议固化为专项 skill"
                })
                log_trigger("skill_solidify", {"task_type": task_type, "count": count})
    
    # T2: 退化检测
    correction_rate = detect_corrections(sessions[-5:] if len(sessions) >= 5 else sessions)
    if correction_rate > 0.3:
        actions.append({
            "action": "degradation_alert",
            "correction_rate": correction_rate,
            "message": f"近5次 session 纠正率 {correction_rate:.0%}，触发退化告警"
        })
        log_trigger("degradation_alert", {"correction_rate": correction_rate})
    
    # T3: 新场景
    recent_types = set(s.get("task_type") for s in sessions[-7:])
    for t in recent_types:
        if t and t not in patterns["task_types"]:
            patterns["task_types"][t] = 1
            actions.append({
                "action": "new_domain",
                "task_type": t,
                "message": f"发现新任务类型 '{t}'，已标记观察"
            })
            log_trigger("new_domain", {"task_type": t})
    
    return actions

def main():
    sessions = load_recent_sessions(days=7)
    patterns = load_patterns()
    
    V_pa = calculate_pa_v(sessions)
    
    # 计算 V̇_PA
    prev_V = 0.5
    if len(sessions) >= 2:
        prev_sessions = sessions[:-1] if len(sessions) > 1 else sessions
        prev_V = calculate_pa_v(prev_sessions)
    V_dot = round(V_pa - prev_V, 4)
    
    actions = trigger_actions(sessions, patterns)
    save_patterns(patterns)
    
    # 输出报告
    print("=" * 60)
    print("PA 进化触发器报告")
    print("=" * 60)
    print(f"分析窗口: 最近 {len(sessions)} 个 sessions")
    print(f"V_PA:     {V_pa:.4f}")
    print(f"V̇_PA:     {V_dot:+.4f}")
    print(f"纠正率:   {detect_corrections(sessions):.0%}")
    print()
    
    if actions:
        print("【触发动作】")
        for a in actions:
            print(f"  [{a['action']}] {a['message']}")
    else:
        print("【无触发】运行平稳，继续观察")
    
    print("=" * 60)
    
    # 保存 PA 健康记录
    pa_health_path = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/pa-health-history.jsonl")
    os.makedirs(os.path.dirname(pa_health_path), exist_ok=True)
    with open(pa_health_path, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.datetime.now().isoformat(),
            "V_pa": V_pa,
            "Vdot_pa": V_dot,
            "session_count": len(sessions),
            "correction_rate": detect_corrections(sessions),
            "actions": [a["action"] for a in actions]
        }) + "\n")

if __name__ == "__main__":
    main()
