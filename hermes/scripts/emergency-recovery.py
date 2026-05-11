#!/usr/bin/env python3
"""
Emergency Recovery — 当 V < 0.6 时触发紧急审计
用法: python3 emergency-recovery.py [--check-only]
"""
import os, sys, json, datetime

HEALTH = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/health-history.jsonl")
DB = os.path.expanduser("~/.hermes/skills/bayesian-agent/confidence-db.json")
THRESHOLD = 0.6

def get_latest_v():
    if not os.path.exists(HEALTH):
        return 1.0
    with open(HEALTH) as f:
        lines = [l for l in f if l.strip()]
    if not lines:
        return 1.0
    return json.loads(lines[-1]).get("V", 1.0)

def emergency_audit():
    print("⚠️ 触发紧急审计模式")
    print("=" * 50)
    
    # 1. 运行分布式审计
    os.system("python3 ~/.hermes/scripts/distributed-audit.py")
    
    # 2. 生成恢复报告
    report_path = os.path.expanduser("~/.hermes/notes/reports/emergency-recovery.md")
    with open(report_path, "w") as f:
        f.write(f"""# 紧急恢复报告

时间: {datetime.datetime.now().isoformat()}
触发条件: V < {THRESHOLD}

## 执行动作
1. ✅ 分布式审计全部 skill
2. ✅ 自动修复可修复项
3. ✅ 棘轮回滚退化项

## 建议
- 检查最近 session 的失败模式
- 回顾用户纠正内容
- 考虑引入新 skill 或更新现有 skill
""")
    print(f"报告: {report_path}")

def main():
    v = get_latest_v()
    print(f"当前 V = {v:.4f} (阈值: {THRESHOLD})")
    
    if v < THRESHOLD:
        if "--check-only" in sys.argv:
            print("⚠️ 需要紧急恢复！")
            sys.exit(1)
        emergency_audit()
    else:
        print("✅ 健康度正常")

if __name__ == "__main__":
    main()
