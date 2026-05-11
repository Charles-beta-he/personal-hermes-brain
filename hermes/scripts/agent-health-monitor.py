#!/usr/bin/env python3
"""
Agent 健康度监控脚本 — 基于钱学森工程控制论的李雅普诺夫函数

计算 V(x) = 0.30*成功率 + 0.25*满意度 + 0.20*skill覆盖率 + 0.15*构建通过率 + 0.10*迭代效率
保存历史，计算 V̇，触发告警。

保存路径: ~/.hermes/notes/engineering-cybernetics/health-history.jsonl
"""

import json, os, sys, subprocess, re
from datetime import datetime, timedelta

HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, ".hermes", "notes", "engineering-cybernetics")
HISTORY_FILE = os.path.join(BASE, "health-history.jsonl")

os.makedirs(BASE, exist_ok=True)

# ===================== 数据采集 =====================

def collect_success_rate():
    """从 builder-journal 和 feedback 统计成功率"""
    success = 0
    total = 0
    
    # 读取 feedback
    fb_path = os.path.join(HOME, ".pua", "feedback.jsonl")
    if os.path.exists(fb_path):
        with open(fb_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    total += 1
                    # rating 为"很有用"或没有明确负面标记视为成功
                    r = obj.get("rating", "")
                    if "有用" in r or "good" in r.lower() or r == "":
                        success += 1
                except:
                    pass
    
    # 读取 builder-journal 中的 failure_count
    bj_path = os.path.join(HOME, ".pua", "builder-journal.md")
    recent_failures = 0
    recent_total = 0
    if os.path.exists(bj_path):
        with open(bj_path) as f:
            content = f.read()
        # 简单启发：查找 failure_count
        m = re.search(r'failure_count[:\s]+(\d+)', content)
        if m:
            recent_failures = int(m.group(1))
            recent_total = max(recent_total, recent_failures + 1)
    
    if total == 0 and recent_total == 0:
        return 0.85  # 默认基线
    
    if total > 0:
        return success / total
    return max(0.5, 1 - recent_failures / max(recent_total, 1))

def collect_satisfaction():
    """用户满意度 ≈ 1 - 纠正频率"""
    # 从 feedback 中推断
    fb_path = os.path.join(HOME, ".pua", "feedback.jsonl")
    good = 0
    total = 0
    if os.path.exists(fb_path):
        with open(fb_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    total += 1
                    r = obj.get("rating", "")
                    if "有用" in r or "good" in r.lower():
                        good += 1
                except:
                    pass
    if total == 0:
        return 0.80
    return good / total

def collect_skill_coverage():
    """skill 覆盖率 ≈ 已安装 skill 数 / 目标 skill 数"""
    skills_dir = os.path.join(HOME, ".hermes", "skills")
    if not os.path.exists(skills_dir):
        return 0.5
    
    # 统计所有子目录下的 SKILL.md
    count = 0
    for root, dirs, files in os.walk(skills_dir):
        if "SKILL.md" in files:
            count += 1
    
    # 目标 skill 数（根据当前工作流估算）
    target = 35  # 当前已有 + 规划中
    return min(1.0, count / target)

def collect_build_pass_rate():
    """构建通过率 — 从最近 git log 推断"""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-20"],
            capture_output=True, text=True, cwd=os.path.join(HOME, "Desktop", "folder")
        )
        if result.returncode != 0:
            # 尝试其他路径
            result = subprocess.run(
                ["git", "log", "--oneline", "-20"],
                capture_output=True, text=True, cwd=HOME
            )
    except:
        result = None
    
    if result is None or result.returncode != 0:
        return 0.90
    
    lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
    if not lines:
        return 0.90
    
    total = len(lines)
    # [verified] 前缀表示通过独立审查
    verified = sum(1 for l in lines if "[verified]" in l.lower() or "verified" in l.lower())
    # fix 开头可能表示修复了失败
    fixes = sum(1 for l in lines if l.lower().startswith("fix") or "fix:" in l.lower())
    
    # 简单估计：verified 算通过，fix 算曾经失败
    pass_rate = (total - fixes * 0.5) / total
    return max(0.5, min(1.0, pass_rate))

def collect_iteration_efficiency():
    """迭代效率 ≈ 1 / 平均轮次"""
    # 从 builder-journal 读取 pressure_level 和 iteration 信息
    bj_path = os.path.join(HOME, ".pua", "builder-journal.md")
    if not os.path.exists(bj_path):
        return 0.70  # 默认 1/1.4 轮次
    
    with open(bj_path) as f:
        content = f.read()
    
    # 查找 iteration 或 pua_triggered_count 作为代理指标
    m = re.search(r'pua_triggered_count[:\s]+(\d+)', content)
    if m:
        triggers = int(m.group(1))
        # 触发次数多 = 效率低（需要更多轮次修正）
        # 映射：0 触发 -> 1.0, 10+ 触发 -> 0.3
        eff = max(0.3, 1.0 - triggers * 0.07)
        return eff
    
    return 0.70

# ===================== V 计算 =====================

def calculate_health():
    r_success = collect_success_rate()
    r_satisfaction = collect_satisfaction()
    r_coverage = collect_skill_coverage()
    r_build = collect_build_pass_rate()
    r_efficiency = collect_iteration_efficiency()
    
    V = (0.30 * r_success +
         0.25 * r_satisfaction +
         0.20 * r_coverage +
         0.15 * r_build +
         0.10 * r_efficiency)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "V": round(V, 4),
        "components": {
            "success_rate": round(r_success, 4),
            "satisfaction": round(r_satisfaction, 4),
            "skill_coverage": round(r_coverage, 4),
            "build_pass_rate": round(r_build, 4),
            "iteration_efficiency": round(r_efficiency, 4)
        }
    }

def load_history(limit=30):
    if not os.path.exists(HISTORY_FILE):
        return []
    history = []
    with open(HISTORY_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                history.append(json.loads(line))
            except:
                pass
    return history[-limit:]

def save_record(record):
    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def compute_vdot(history, current):
    if not history:
        return None
    prev = history[-1]
    try:
        v_prev = prev.get("V", prev.get("v", 0))
        v_curr = current["V"]
        return round(v_curr - v_prev, 4)
    except:
        return None

def print_banner(text):
    print("=" * 60)
    print(text.center(60))
    print("=" * 60)

def main():
    print_banner("Agent 健康度监控 — 控制论进化引擎")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    record = calculate_health()
    history = load_history()
    vdot = compute_vdot(history, record)
    record["V_dot"] = vdot
    
    save_record(record)
    
    # 输出报告
    print(f"【健康度 V】{record['V']:.4f}")
    if vdot is not None:
        arrow = "▲" if vdot > 0.05 else ("▼" if vdot < -0.05 else "→")
        print(f"【变化率 V̇】{vdot:+.4f} {arrow}")
    else:
        print(f"【变化率 V̇】N/A (首次计算)")
    
    print()
    print("【分项指标】")
    for k, v in record["components"].items():
        bar = "█" * int(v * 20) + "░" * (20 - int(v * 20))
        print(f"  {k:22s} {v:.2f} {bar}")
    
    print()
    
    # 告警判定
    alerts = []
    if vdot is not None:
        if vdot < -0.05:
            alerts.append("🚨 V̇ < -0.05: 系统退化！触发战略复盘")
        elif vdot < 0:
            alerts.append("⚠️  V̇ < 0: 轻微退化，关注趋势")
    
    if record["V"] < 0.60:
        alerts.append("🚨 V < 0.60: 健康度危险！立即全面审计")
    elif record["V"] < 0.70:
        alerts.append("⚠️  V < 0.70: 健康度偏低，建议优化")
    
    if record["components"]["success_rate"] < 0.80:
        alerts.append("⚠️  成功率偏低，检查最近失败模式")
    
    if alerts:
        print("【告警】")
        for a in alerts:
            print(f"  {a}")
    else:
        print("【状态】✓ 系统稳定进化中")
    
    print()
    print(f"历史记录: {HISTORY_FILE}")
    print(f"总记录数: {len(history) + 1}")
    
    # 返回码用于自动化判断
    if any("🚨" in a for a in alerts):
        sys.exit(2)
    elif alerts:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
