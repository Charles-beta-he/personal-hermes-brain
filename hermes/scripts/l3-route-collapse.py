#!/usr/bin/env python3
"""
L3-B: 路线全灭检测
当某个 task_class 的所有候选路线 pass_rate 都低于 0.5 时,
说明目前的 approach 全部失效, 需要提出新方法。

输出: 新 skill 提案, 写入 skills-staging/proposals/

用法:
  python3 ~/.hermes/scripts/l3-route-collapse.py
  python3 ~/.hermes/scripts/l3-route-collapse.py --threshold 0.5
"""

import os, sys, json, datetime
sys.path.insert(0, os.path.expanduser("~/.hermes/scripts"))
from route_store import RouteStore

PROPOSALS_DIR = os.path.expanduser("~/.hermes/skills-staging/proposals")
os.makedirs(PROPOSALS_DIR, exist_ok=True)


def detect_collapsed_routes(threshold=0.5, min_samples=5, hours=168):
    """检测所有 task_class 中路线全灭的情况"""
    store = RouteStore()

    # 获取所有 task_class
    all_stats = store.stats(since_hours=hours)
    task_classes = set()
    for r in all_stats.get("routes", []):
        # route_store.py stats 不按 task_class 分, 需要单独查询
        pass

    # 按 task_class 逐一检查
    # 先查出所有 distinct task_class
    import sqlite3
    conn = store._conn
    rows = conn.execute(
        "SELECT DISTINCT task_class FROM route_outcomes WHERE ts >= ?",
        ((datetime.datetime.utcnow() - datetime.timedelta(hours=hours)).strftime("%FT%TZ"),)
    ).fetchall()
    store.close()

    detected = []
    for row in rows:
        tc = row[0]
        if not tc:
            continue
        local_store = RouteStore()
        scores = local_store.route_scores(task_class=tc, since_hours=hours)
        local_store.close()

        all_dead = True
        viable_routes = []
        for s in scores:
            if s["count"] >= min_samples and s["pass_rate"] < threshold:
                all_dead = False  # 有活着的路线, 但这条死了
            elif s["count"] >= min_samples:
                viable_routes.append(s["route"])

        # 如果所有有足够样本的路线都低于阈值
        if scores and all(s["count"] >= min_samples for s in scores):
            if all(s["pass_rate"] < threshold for s in scores):
                detected.append({
                    "task_class": tc,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "routes": [{"route": s["route"], "pass_rate": s["pass_rate"],
                                "count": s["count"]} for s in scores],
                    "avg_pass_rate": round(sum(s["pass_rate"] for s in scores) / len(scores), 3),
                })

    return detected


def write_proposal(detected):
    """为每个全灭的 task_class 生成 skill 提案"""
    for d in detected:
        tc = d["task_class"]
        slug = tc.replace(".", "-").replace("/", "-")
        filename = f"proposal-{slug}-{datetime.datetime.now().strftime('%Y%m%d')}.md"
        filepath = os.path.join(PROPOSALS_DIR, filename)

        routes_detail = "\n".join(
            f"  - {r['route']}: pass={r['pass_rate']:.0%} ({r['count']} samples)"
            for r in d["routes"]
        )

        content = f"""# New Skill Proposal: {tc}

Detected: {d['timestamp'][:19]}
Avg pass rate: {d['avg_pass_rate']:.0%}

## Problem

All known execution routes for task class '{tc}' have pass rate below 50%.

## Collapsed Routes

{routes_detail}

## Proposed New Approach

(To be filled by learner skill from successful cases)

1. Identify recent successful cases in '{tc}' (including human corrections)
2. Extract common steps
3. Generate new SKILL.md
4. Submit to eval harness

## Next Steps

- [ ] Run learner skill on {tc} successful cases
- [ ] Generate skill draft
- [ ] Run eval harness
- [ ] Promote if approved
"""
        with open(filepath, "w") as f:
            f.write(content)
        print(f"  ➜ Proposal written: {filepath}")

    return len(detected)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="L3-B: 路线全灭检测")
    parser.add_argument("--threshold", type=float, default=0.5, help="pass_rate 阈值 (默认 0.5)")
    parser.add_argument("--min-samples", type=int, default=5, help="最小样本数 (默认 5)")
    parser.add_argument("--hours", type=int, default=168, help="时间窗口 (默认 168h)")
    args = parser.parse_args()

    print(f"Route collapse detection (threshold={args.threshold}, min_samples={args.min_samples}, {args.hours}h)")

    detected = detect_collapsed_routes(args.threshold, args.min_samples, args.hours)

    if not detected:
        print("  ✓ No collapsed routes detected — all task classes have viable paths")
        return

    print(f"  ✗ {len(detected)} task class(es) with all routes collapsed:")
    for d in detected:
        print(f"    {d['task_class']}: avg_pass={d['avg_pass_rate']:.0%} across {len(d['routes'])} routes")

    n = write_proposal(detected)
    print(f"\n  {n} proposal(s) written to {PROPOSALS_DIR}/")


if __name__ == "__main__":
    main()
