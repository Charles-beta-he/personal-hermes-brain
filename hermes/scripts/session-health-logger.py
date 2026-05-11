#!/usr/bin/env python3
"""
Session Health Logger — 每次大任务结束后调用，记录本轮健康度贡献

用法:
  python3 session-health-logger.py \
    --task-type feature \
    --rounds 5 \
    --success true \
    --tests-passed true \
    --build-passed true \
    --user-corrections 0 \
    --context-used 0.7 \
    --skills-used "p10,p9,p7,loop"
"""

import os, json, argparse, datetime

HEALTH_PATH = os.path.expanduser("~/.hermes/notes/engineering-cybernetics/health-history.jsonl")
DB_PATH = os.path.expanduser("~/.hermes/skills/bayesian-agent/confidence-db.json")

def calculate_session_V(args):
    """
    计算本轮 session 的健康度贡献
    简化版 V 计算（单 session 粒度）
    """
    # 基础分
    base = 0.5
    
    # 成功率贡献
    if args.success:
        base += 0.30
    else:
        base -= 0.20
    
    # 构建/测试通过率
    if args.tests_passed:
        base += 0.15
    if args.build_passed:
        base += 0.15
    
    # 用户纠正惩罚
    base -= args.user_corrections * 0.05
    
    # 迭代效率（轮次越少越好）
    if args.rounds <= 3:
        base += 0.10
    elif args.rounds <= 6:
        base += 0.05
    elif args.rounds > 10:
        base -= 0.05
    
    # Context 使用效率
    if args.context_used <= 0.5:
        base += 0.05
    elif args.context_used > 0.9:
        base -= 0.05
    
    return max(0.0, min(1.0, base))

def main():
    parser = argparse.ArgumentParser(description="Session Health Logger")
    parser.add_argument("--task-type", required=True, help="feature|bugfix|refactor|explore")
    parser.add_argument("--rounds", type=int, default=1, help="迭代轮次")
    parser.add_argument("--success", type=lambda x: x.lower() == "true", default=True)
    parser.add_argument("--tests-passed", type=lambda x: x.lower() == "true", default=False)
    parser.add_argument("--build-passed", type=lambda x: x.lower() == "true", default=False)
    parser.add_argument("--user-corrections", type=int, default=0)
    parser.add_argument("--context-used", type=float, default=0.5)
    parser.add_argument("--skills-used", default="", help="逗号分隔的skill名")
    parser.add_argument("--note", default="", help="备注")
    args = parser.parse_args()
    
    V = calculate_session_V(args)
    
    # 读取上一条记录计算 V̇
    prev_V = 0.86
    if os.path.exists(HEALTH_PATH):
        with open(HEALTH_PATH, "r") as f:
            lines = [l for l in f if l.strip()]
            if lines:
                try:
                    prev = json.loads(lines[-1])
                    prev_V = prev.get("V", 0.86)
                except:
                    pass
    
    Vdot = round(V - prev_V, 4)
    
    record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "task_type": args.task_type,
        "rounds": args.rounds,
        "success": args.success,
        "tests_passed": args.tests_passed,
        "build_passed": args.build_passed,
        "user_corrections": args.user_corrections,
        "context_used": args.context_used,
        "skills_used": args.skills_used.split(",") if args.skills_used else [],
        "V": round(V, 4),
        "Vdot": Vdot,
        "note": args.note
    }
    
    os.makedirs(os.path.dirname(HEALTH_PATH), exist_ok=True)
    with open(HEALTH_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    
    print(f"✓ Health logged: V={V:.4f} V̇={Vdot:+.4f}")
    
    # 告警
    if Vdot < -0.05:
        print(f"⚠️ 退化告警: V̇={Vdot:+.4f} < -0.05，建议复盘")
    elif Vdot > 0.05:
        print(f"✓ 显著进化: V̇={Vdot:+.4f} > +0.05")

if __name__ == "__main__":
    main()
