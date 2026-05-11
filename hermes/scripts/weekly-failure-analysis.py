#!/usr/bin/env python3
"""
每周失败模式分析 — 极限环检测与系统辨识

扫描最近一周的 session 失败模式，识别：
1. 重复出现的同类问题（极限环预警）
2. Top-5 失败模式
3. Skill 覆盖缺口

输出: ~/.hermes/notes/engineering-cybernetics/weekly-reports/{week}.md
"""

import json, os, re, sys
from datetime import datetime, timedelta

HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, ".hermes", "notes", "engineering-cybernetics")
REPORT_DIR = os.path.join(BASE, "weekly-reports")
os.makedirs(REPORT_DIR, exist_ok=True)

def analyze():
    # 收集失败信号
    failures = []
    
    # 从 builder-journal 读取
    bj_path = os.path.join(HOME, ".pua", "builder-journal.md")
    if os.path.exists(bj_path):
        with open(bj_path) as f:
            content = f.read()
        # 提取失败模式（简单启发式）
        if "failure" in content.lower() or "error" in content.lower():
            failures.append({"source": "builder-journal", "hint": content[:500]})
    
    # 从 feedback 读取失败信号
    fb_path = os.path.join(HOME, ".pua", "feedback.jsonl")
    if os.path.exists(fb_path):
        with open(fb_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    r = obj.get("rating", "")
                    if "一般" in r or "没感觉" in r or "bad" in r.lower():
                        failures.append({"source": "feedback", "rating": r})
                except:
                    pass
    
    # 读取 health history 找退化点
    hh_path = os.path.join(BASE, "health-history.jsonl")
    degradation_events = []
    if os.path.exists(hh_path):
        records = []
        with open(hh_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except:
                    pass
        # 找连续退化
        for i in range(1, len(records)):
            vdot = records[i].get("V_dot")
            if vdot is not None and vdot < -0.05:
                degradation_events.append({
                    "time": records[i].get("timestamp", "unknown"),
                    "V": records[i].get("V"),
                    "V_dot": vdot
                })
    
    # 生成报告
    week_str = datetime.now().strftime("%Y-W%W")
    report_path = os.path.join(REPORT_DIR, f"{week_str}.md")
    
    with open(report_path, 'w') as f:
        f.write(f"# 每周失败模式分析 — {week_str}\n\n")
        f.write(f"生成时间: {datetime.now().isoformat()}\n\n")
        
        f.write("## 退化事件\n\n")
        if degradation_events:
            for ev in degradation_events[-5:]:
                f.write(f"- {ev['time']}: V={ev['V']:.3f}, V̇={ev['V_dot']:+.4f}\n")
        else:
            f.write("- 本周无显著退化事件 ✓\n")
        
        f.write("\n## 失败信号统计\n\n")
        f.write(f"- 总失败信号: {len(failures)}\n")
        f.write(f"- 来源 breakdown: builder-journal={sum(1 for f in failures if f['source']=='builder-journal')}, feedback={sum(1 for f in failures if f['source']=='feedback')}\n")
        
        f.write("\n## 极限环检测\n\n")
        if len(degradation_events) >= 3:
            f.write("⚠️ **警告**: 本周退化事件 ≥3 次，可能存在极限环振荡。\n")
            f.write("建议：检查是否陷入「修A坏B→修B坏A」循环，考虑切换控制策略。\n")
        elif len(degradation_events) >= 1:
            f.write("⚠️ 本周有退化事件，需关注趋势。\n")
        else:
            f.write("✓ 本周无极限环迹象。\n")
        
        f.write("\n## 建议行动\n\n")
        if len(failures) > 5:
            f.write("1. 【高优】执行 systematic-debugging 分析 top 失败模式\n")
        if len(degradation_events) >= 2:
            f.write("2. 【高优】进行 P10 战略复盘，检查参考模型是否需要更新\n")
        f.write("3. 【常规】回顾本周 session_search，提取可固化的模式\n")
        f.write("4. 【常规】检查 skill 覆盖率缺口，规划下周补充\n")
    
    print(f"Report written to: {report_path}")
    print(f"Failures: {len(failures)}, Degradations: {len(degradation_events)}")
    
    if len(degradation_events) >= 3:
        sys.exit(2)  # 极限环告警
    elif len(failures) > 5:
        sys.exit(1)  # 注意
    sys.exit(0)

if __name__ == "__main__":
    analyze()
