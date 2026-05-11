#!/usr/bin/env python3
"""
model-usage.py — 查看模型使用记录: 什么模型, 什么时候, 用了多少次

用法:
  python3 model-usage.py                    # 摘要 + 最近20条
  python3 model-usage.py --timeline 50      # 最近50条时间线
  python3 model-usage.py --model mimo       # 只看某个模型
  python3 model-usage.py --today            # 只看今天
  python3 model-usage.py --cost             # 按成本排序
"""

import argparse, sqlite3, os, json
from datetime import datetime, timezone

DB = os.path.expanduser(os.environ.get("HERMES_ROUTE_DB_PATH", "~/.hermes/route_outcomes.db"))


def run():
    parser = argparse.ArgumentParser(description="Model Usage — 模型使用记录")
    parser.add_argument("--timeline", type=int, default=0, help="时间线条数")
    parser.add_argument("--model", default="", help="过滤模型名")
    parser.add_argument("--today", action="store_true", help="只看今天")
    parser.add_argument("--cost", action="store_true", help="按成本排序")
    parser.add_argument("--hours", type=int, default=168, help="时间窗口")
    args = parser.parse_args()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    where = "WHERE model_chain IS NOT NULL AND model_chain != ''"
    params = []

    if args.today:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        where += " AND ts >= ?"
        params.append(today + "T00:00:00Z")

    if args.model:
        where += " AND model_chain LIKE ?"
        params.append(f"%{args.model}%")

    if args.hours < 9999:
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=args.hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
        where += " AND ts >= ?"
        params.append(cutoff)

    # 摘要
    summary = conn.execute(f"""
        SELECT json_extract(model_chain, '$[0]') as model,
               COUNT(*) as cnt,
               SUM(CASE WHEN verdict='pass' THEN 1 ELSE 0 END) as passed,
               ROUND(AVG(duration_s), 1) as avg_dur,
               ROUND(SUM(cost_usd), 4) as total_cost,
               MIN(ts) as first_used,
               MAX(ts) as last_used
        FROM route_outcomes {where}
        GROUP BY model
        ORDER BY {'total_cost DESC' if args.cost else 'cnt DESC'}
    """, params).fetchall()

    total = sum(r["cnt"] for r in summary)

    print(f"Model Usage — {args.hours}h window — {total} calls")
    print("=" * 85)
    for r in summary:
        model = r["model"] or "?"
        pr = r["passed"] / r["cnt"] * 100 if r["cnt"] else 0
        bar = "█" * int(pr / 10) + "░" * (10 - int(pr / 10))
        print(f"  {model:30s} {r['cnt']:4d}x  {bar} {pr:5.1f}%  "
              f"avg={r['avg_dur']:5.1f}s  cost=${r['total_cost']:.4f}")
        if r["first_used"]:
            print(f"    {r['first_used'][:19]} → {r['last_used'][:19]}")

    # 时间线
    n = args.timeline or (0 if args.timeline == 0 and not args.cost else 20)
    if n > 0:
        print(f"\nRecent {n} calls:")
        timeline = conn.execute(f"""
            SELECT ts, json_extract(model_chain, '$[0]') as model, 
                   skill, verdict, duration_s, cost_usd
            FROM route_outcomes {where}
            ORDER BY id DESC LIMIT ?
        """, params + [n]).fetchall()

        for t in timeline:
            model = t["model"] or "?"
            icon = "✓" if t["verdict"] == "pass" else "✗"
            cost_str = f"${t['cost_usd']:.4f}" if t["cost_usd"] else ""
            print(f"  {t['ts'][11:19]}  {icon} {model:25s} {t['skill']:20s} {cost_str}")

    # 当前活跃模型
    now = datetime.now(timezone.utc)
    active_rows = conn.execute(f"""
        SELECT json_extract(model_chain, '$[0]') as model,
               COUNT(*) as cnt
        FROM route_outcomes {where}
        AND ts >= ?
        GROUP BY model
        ORDER BY cnt DESC
    """, params + [now.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")]).fetchall()

    if active_rows:
        print(f"\nActive this hour:")
        for r in active_rows:
            print(f"  {r['model']:30s} {r['cnt']}x")

    conn.close()


if __name__ == "__main__":
    run()
