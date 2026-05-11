#!/usr/bin/env python3
"""
Session History Analyzer — 系统辨识
从 session 历史中提取成功/失败模式（ch12 系统辨识）
"""

import json, os, sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta

def analyze_sessions():
    # 读取 health history
    health_path = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/health-history.jsonl")
    records = []
    if os.path.exists(health_path):
        with open(health_path, "r") as f:
            for line in f:
                try:
                    records.append(json.loads(line))
                except:
                    pass
    
    # 读取 Darwin results
    results_path = os.path.expanduser("~/.hermes/skills/darwin-skill/results.tsv")
    darwin_records = []
    if os.path.exists(results_path):
        with open(results_path, "r") as f:
            header = f.readline()
            for line in f:
                cols = line.strip().split("\t")
                if len(cols) >= 9:
                    darwin_records.append({
                        "timestamp": cols[0], "commit": cols[1], "skill": cols[2],
                        "old": cols[3], "new": cols[4], "status": cols[5],
                        "note": cols[7], "mode": cols[8]
                    })
    
    # 分析失败模式
    failures = [r for r in darwin_records if r["status"] in ["revert", "D"]]
    failure_patterns = Counter(r["note"] for r in failures)
    
    # 分析 skill 退化
    regressions = [r for r in darwin_records if r["status"] == "revert"]
    
    # 输出报告
    print("=" * 60)
    print("Session 历史分析报告 — 系统辨识")
    print("=" * 60)
    print(f"\n总 health 记录: {len(records)}")
    print(f"总 Darwin 记录: {len(darwin_records)}")
    print(f"失败/回滚记录: {len(failures)}")
    
    if failure_patterns:
        print(f"\nTop-5 失败模式:")
        for pattern, count in failure_patterns.most_common(5):
            print(f"  {count:>3}x {pattern}")
    
    if regressions:
        print(f"\n退化记录:")
        for r in regressions:
            print(f"  {r['skill']}: {r['old']}→{r['new']} ({r['note']})")
    
    # 极限环检测
    skill_counts = defaultdict(int)
    for r in darwin_records:
        if r["status"] in ["revert", "D"]:
            skill_counts[r["skill"]] += 1
    
    limit_cycles = [(s, c) for s, c in skill_counts.items() if c >= 3]
    if limit_cycles:
        print(f"\n⚠️ 极限环告警（同 skill 失败≥3次）:")
        for s, c in limit_cycles:
            print(f"  {s}: {c} 次")
    else:
        print(f"\n✓ 无极限环 detected")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    analyze_sessions()
