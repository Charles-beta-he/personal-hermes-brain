#!/usr/bin/env python3
"""
claude-budget-tracker.py — Claude Code token 预算保护器
每日/每周 token 使用追踪, 超限自动降级路由

用法:
  python3 claude-budget-tracker.py status       # 查看当前预算
  python3 claude-budget-tracker.py spend 5000 3000  # 记录消费 (tokens_in, tokens_out)
  python3 claude-budget-tracker.py can-use      # 检查是否可用 → exit 0/1
  python3 claude-budget-tracker.py reset-daily  # 每日重置 (cron)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta

HERMES_HOME = os.path.expanduser(os.environ.get("HERMES_HOME", "~/.hermes"))
STATE_DIR = os.path.join(HERMES_HOME, "state")
TRACKER_PATH = os.path.join(STATE_DIR, "claude_budget.json")


def _now():
    return datetime.now(timezone.utc)


def _today_key():
    return _now().strftime("%Y-%m-%d")


def _week_key():
    """ISO week key"""
    now = _now()
    return f"{now.year}-W{now.isocalendar()[1]:02d}"


def load_budget():
    os.makedirs(STATE_DIR, exist_ok=True)
    if os.path.exists(TRACKER_PATH):
        with open(TRACKER_PATH) as f:
            return json.load(f)
    return {
        "daily": {},
        "weekly": {},
        "total_tokens_in": 0,
        "total_tokens_out": 0,
        "last_reset_daily": None,
        "last_reset_weekly": None,
    }


def save_budget(data):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(TRACKER_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _ensure_day(data):
    today = _today_key()
    if data.get("last_reset_daily") != today:
        data["last_reset_daily"] = today
        # 不删除历史, 但标记新的一天
        if today not in data["daily"]:
            data["daily"][today] = {"tokens_in": 0, "tokens_out": 0, "tasks": 0}
    if today not in data["daily"]:
        data["daily"][today] = {"tokens_in": 0, "tokens_out": 0, "tasks": 0}
    return data


def _ensure_week(data):
    week = _week_key()
    if data.get("last_reset_weekly") != week:
        data["last_reset_weekly"] = week
        if week not in data["weekly"]:
            data["weekly"][week] = {"tokens_in": 0, "tokens_out": 0, "tasks": 0}
    if week not in data["weekly"]:
        data["weekly"][week] = {"tokens_in": 0, "tokens_out": 0, "tasks": 0}
    return data


def load_config():
    try:
        import yaml
        config_path = os.path.join(HERMES_HOME, "config.yaml")
        with open(config_path) as f:
            c = yaml.safe_load(f)
        return c.get("claude_budget", {})
    except:
        return {}


def spend(tokens_in: int, tokens_out: int):
    """记录一次 Claude 调用"""
    data = load_budget()
    data = _ensure_day(data)
    data = _ensure_week(data)
    
    today = _today_key()
    week = _week_key()
    
    data["daily"][today]["tokens_in"] += tokens_in
    data["daily"][today]["tokens_out"] += tokens_out
    data["daily"][today]["tasks"] += 1
    
    data["weekly"][week]["tokens_in"] += tokens_in
    data["weekly"][week]["tokens_out"] += tokens_out
    data["weekly"][week]["tasks"] += 1
    
    data["total_tokens_in"] += tokens_in
    data["total_tokens_out"] += tokens_out
    
    save_budget(data)
    return data


def can_use(config=None) -> tuple:
    """检查 Claude 是否可用
    
    Returns: (allowed: bool, reason: str, usage_ratio: float)
    """
    if config is None:
        config = load_config()
    
    if not config.get("enabled", False):
        return True, "budget_tracking_disabled", 0.0
    
    data = load_budget()
    data = _ensure_day(data)
    
    today = _today_key()
    daily_used = data["daily"].get(today, {}).get("tokens_in", 0) + \
                 data["daily"].get(today, {}).get("tokens_out", 0)
    
    daily_limit = config.get("daily_token_limit", 250000)
    hard_threshold = config.get("hard_block_threshold", 0.95)
    soft_threshold = config.get("soft_warn_threshold", 0.6)
    
    usage_ratio = daily_used / daily_limit if daily_limit > 0 else 0
    
    if usage_ratio >= hard_threshold:
        return False, f"hard_limit_exceeded ({daily_used}/{daily_limit} = {usage_ratio:.0%})", usage_ratio
    
    if usage_ratio >= soft_threshold:
        return True, f"soft_warn ({daily_used}/{daily_limit} = {usage_ratio:.0%})", usage_ratio
    
    return True, "ok", usage_ratio


def status():
    """显示预算状态"""
    config = load_config()
    data = load_budget()
    data = _ensure_day(data)
    data = _ensure_week(data)
    
    today = _today_key()
    week = _week_key()
    
    daily = data["daily"].get(today, {"tokens_in": 0, "tokens_out": 0, "tasks": 0})
    weekly = data["weekly"].get(week, {"tokens_in": 0, "tokens_out": 0, "tasks": 0})
    
    daily_used = daily["tokens_in"] + daily["tokens_out"]
    weekly_used = weekly["tokens_in"] + weekly["tokens_out"]
    
    daily_limit = config.get("daily_token_limit", 250000)
    weekly_limit = config.get("weekly_token_limit", 800000)
    
    allowed, reason, ratio = can_use(config)
    
    status_icon = "✓" if allowed and ratio < 0.6 else ("⚠" if allowed else "✗")
    
    print(f"Claude Budget — {_now().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Status:   {status_icon} {reason}")
    print(f"  Daily:    {daily_used:,}/{daily_limit:,} tokens ({ratio:.1%})  [{daily['tasks']} tasks]")
    print(f"  Weekly:   {weekly_used:,}/{weekly_limit:,} tokens ({weekly_used/weekly_limit:.1%})  [{weekly['tasks']} tasks]")
    print(f"  Lifetime: {data['total_tokens_in']+data['total_tokens_out']:,} tokens")
    print()
    
    # 降级路径
    deg = config.get("degradation", {})
    if ratio >= 0.95:
        print(f"  ⚠ HARD BLOCK — T3 fallback: {deg.get('T3_fallback', '?')}")
        print(f"  ⚠ T2 arbiter fallback: {deg.get('T2_arbiter_fallback', '?')}")
    elif ratio >= 0.6:
        print(f"  ⚡ T2 arbiter demoted → {deg.get('T2_arbiter_fallback', '?')}")
    
    return data


def cli():
    parser = argparse.ArgumentParser(description="Claude Budget Tracker — token 预算保护")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status", help="显示预算状态")
    
    sp = sub.add_parser("spend", help="记录一次调用")
    sp.add_argument("tokens_in", type=int)
    sp.add_argument("tokens_out", type=int)

    sub.add_parser("can-use", help="检查是否可用 (exit 0=yes, 1=no)")
    sub.add_parser("reset-daily", help="每日重置 (仅清理旧数据)")

    args = parser.parse_args()

    if args.cmd == "status":
        status()

    elif args.cmd == "spend":
        data = spend(args.tokens_in, args.tokens_out)
        allowed, reason, ratio = can_use()
        print(f"Recorded: +{args.tokens_in}/{args.tokens_out} tokens")
        print(f"Status: {reason} ({ratio:.1%})")

    elif args.cmd == "can-use":
        allowed, reason, ratio = can_use()
        if allowed:
            sys.exit(0)
        else:
            sys.exit(1)

    elif args.cmd == "reset-daily":
        data = load_budget()
        today = _today_key()
        # 清理7天前的数据
        cutoff = (_now() - timedelta(days=7)).strftime("%Y-%m-%d")
        data["daily"] = {k: v for k, v in data["daily"].items() if k >= cutoff}
        data["last_reset_daily"] = _today_key()
        save_budget(data)
        print("Daily budget state cleaned.")
        status()

    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
