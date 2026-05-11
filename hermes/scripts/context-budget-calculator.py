#!/usr/bin/env python3
"""
Context Budget Calculator — 运行时 Token 预算监控
估算当前 session 的 context 使用情况，给出行动建议
"""

import os, json, sys

# 假设的平均 token 估算系数
# 中文 ≈ 1.5 tokens/字，英文 ≈ 0.75 tokens/字，代码 ≈ 1.0 tokens/字
CHAR_TO_TOKEN_RATIO = 1.2

def estimate_tokens(text):
    return int(len(text) * CHAR_TO_TOKEN_RATIO)

def calculate_budget(session_log_path=None):
    """
    简化版：从 stdin 或文件读取内容估算
    实际部署时，可由 Agent 在每次 tool call 后调用
    """
    
    # 总预算（假设 128K context window，保留 20% 安全边际）
    TOTAL_BUDGET = 128000
    SAFE_BUDGET = int(TOTAL_BUDGET * 0.8)
    
    # 读取输入
    if session_log_path and os.path.exists(session_log_path):
        with open(session_log_path, "r") as f:
            content = f.read()
    else:
        content = sys.stdin.read()
    
    used = estimate_tokens(content)
    remaining = SAFE_BUDGET - used
    ratio = used / SAFE_BUDGET
    
    # 决策建议
    if ratio < 0.3:
        status = "GREEN"
        advice = "Context 充足，可按标准流程执行"
    elif ratio < 0.6:
        status = "YELLOW"
        advice = "Context 过半，建议优先完成核心任务，避免深度探索"
    elif ratio < 0.8:
        status = "ORANGE"
        advice = "Context 紧张，必须拆分任务或将中间结果写入文件"
    else:
        status = "RED"
        advice = "Context 即将耗尽，立即停止当前任务，固化结果后重启"
    
    report = {
        "status": status,
        "total_budget": TOTAL_BUDGET,
        "safe_budget": SAFE_BUDGET,
        "used_tokens": used,
        "remaining_tokens": remaining,
        "usage_ratio": round(ratio, 2),
        "advice": advice,
        "actions": []
    }
    
    if status == "ORANGE":
        report["actions"] = [
            "将当前进度写入文件（checkpoint）",
            "简化验证步骤（只跑核心测试）",
            "避免读取大文件"
        ]
    elif status == "RED":
        report["actions"] = [
            "立即停止",
            "将 todo 状态和所有中间结果写入文件",
            "向用户请求新 session 继续"
        ]
    
    return report

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Session log file path")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()
    
    report = calculate_budget(args.file)
    
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Context Budget Report")
        print(f"=" * 40)
        print(f"状态:     {report['status']}")
        print(f"已用:     {report['used_tokens']:,} / {report['safe_budget']:,} tokens")
        print(f"剩余:     {report['remaining_tokens']:,} tokens")
        print(f"使用率:   {report['usage_ratio']*100:.0f}%")
        print(f"建议:     {report['advice']}")
        if report['actions']:
            print(f"行动:")
            for a in report['actions']:
                print(f"  - {a}")
        print("=" * 40)

if __name__ == "__main__":
    main()
