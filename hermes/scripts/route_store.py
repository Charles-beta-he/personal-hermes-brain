#!/usr/bin/env python3
"""
route_outcomes — SQLite 存储层
每个 trace 记录对应 L0 一次 skill 执行的结果，被 L1 hook 写入、L2 router 读取。

Schema:
  CREATE TABLE route_outcomes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,            -- ISO 8601
    skill        TEXT NOT NULL,            -- 执行的 skill 名
    task_class   TEXT NOT NULL DEFAULT '', -- task 分类 (triage 输出)
    route        TEXT NOT NULL DEFAULT '', -- 路由路径
    verdict      TEXT NOT NULL DEFAULT 'unknown', -- pass / fail / partial
    duration_s   REAL DEFAULT 0,
    tokens_in    INTEGER DEFAULT 0,
    tokens_out   INTEGER DEFAULT 0,
    task_id      TEXT DEFAULT '',
    model_chain  TEXT DEFAULT '',          -- JSON array
    cost_usd     REAL DEFAULT 0,
    error        TEXT DEFAULT '',          -- 失败原因
    is_synthetic INTEGER DEFAULT 0,        -- 0=real trace, 1=synthetic/generated
    chain_id     TEXT                       -- L2 protocol chain identifier
  );

用法:
  from route_store import RouteStore
  store = RouteStore()
  store.append(...)
  rows = store.query(task_class='feature.frontend', limit=50)
  stats = store.stats(task_class='feature.frontend')
"""

import datetime
import json
import os
import sqlite3
import sys

DB_PATH = os.path.expanduser(
    os.environ.get("HERMES_ROUTE_DB_PATH", "~/.hermes/route_outcomes.db")
)
DEFAULT_EXCLUDED_MAIN_ROUTES = ("", "planner-")


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class RouteStore:
    """thread-safe 的单写多读存储 (WAL mode)"""

    def __init__(self, db_path=None):
        self.path = os.path.expanduser(db_path or DB_PATH)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._ensure_schema()

    def _ensure_schema(self):
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS route_outcomes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                ts           TEXT NOT NULL,
                skill        TEXT NOT NULL,
                task_class   TEXT NOT NULL DEFAULT '',
                route        TEXT NOT NULL DEFAULT '',
                verdict      TEXT NOT NULL DEFAULT 'unknown',
                duration_s   REAL DEFAULT 0,
                tokens_in    INTEGER DEFAULT 0,
                tokens_out   INTEGER DEFAULT 0,
                task_id      TEXT DEFAULT '',
                model_chain  TEXT DEFAULT '',
                cost_usd     REAL DEFAULT 0,
                error        TEXT DEFAULT '',
                is_synthetic INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_ro_ts ON route_outcomes(ts);
            CREATE INDEX IF NOT EXISTS idx_ro_class ON route_outcomes(task_class);
            CREATE INDEX IF NOT EXISTS idx_ro_skill ON route_outcomes(skill);
            CREATE INDEX IF NOT EXISTS idx_ro_verdict ON route_outcomes(verdict);
            """
        )
        # Migration: add chain_id column for L2 protocol traceability
        try:
            self._conn.execute(
                "ALTER TABLE route_outcomes ADD COLUMN chain_id TEXT"
            )
        except sqlite3.OperationalError:
            pass  # column already exists
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ro_chain_id ON route_outcomes(chain_id)"
        )

    def append(
        self,
        skill="",
        task_class="",
        route="",
        verdict="unknown",
        duration_s=0,
        tokens_in=0,
        tokens_out=0,
        task_id="",
        model_chain="",
        cost_usd=0,
        error="",
        is_synthetic=0,
        chain_id=None,
    ):
        """写入一条 trace"""
        if isinstance(model_chain, (list, tuple)):
            model_chain = json.dumps(model_chain)
        self._conn.execute(
            """INSERT INTO route_outcomes
               (ts, skill, task_class, route, verdict, duration_s,
                tokens_in, tokens_out, task_id, model_chain, cost_usd, error, is_synthetic, chain_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                utc_now().strftime("%FT%TZ"),
                skill,
                task_class,
                route,
                verdict,
                duration_s,
                tokens_in,
                tokens_out,
                task_id,
                model_chain,
                cost_usd,
                error,
                is_synthetic,
                chain_id,
            ),
        )
        self._conn.commit()
        cursor = self._conn.execute("SELECT last_insert_rowid()")
        return cursor.fetchone()[0]

    def append_from_stdin(self):
        """从 stdin JSON 读取并写入（给 shell hook 用）"""
        payload = json.loads(sys.stdin.read())
        self.append(
            skill=payload.get("skill", ""),
            task_class=payload.get("task_class", ""),
            route=payload.get("route", ""),
            verdict=payload.get("verdict", "unknown"),
            duration_s=payload.get("duration_s", 0),
            tokens_in=payload.get("tokens_in", 0),
            tokens_out=payload.get("tokens_out", 0),
            task_id=payload.get("task_id", ""),
            model_chain=payload.get("model_chain", ""),
            cost_usd=payload.get("cost_usd", 0),
            error=payload.get("error", ""),
            is_synthetic=payload.get("is_synthetic", 0),
            chain_id=payload.get("chain_id"),
        )

    def _build_where(self, task_class=None, skill=None, verdict=None, since_hours=0):
        where = []
        params = []
        if task_class:
            where.append("task_class = ?")
            params.append(task_class)
        if skill:
            where.append("skill = ?")
            params.append(skill)
        if verdict:
            where.append("verdict = ?")
            params.append(verdict)
        if since_hours and since_hours > 0:
            cutoff = utc_now() - datetime.timedelta(hours=since_hours)
            where.append("ts >= ?")
            params.append(cutoff.strftime("%FT%TZ"))
        return where, params

    def _aggregate(
        self,
        base_where=None,
        base_params=None,
        synthetic=None,
        include_routes=None,
        exclude_routes=None,
    ):
        where = list(base_where or [])
        params = list(base_params or [])

        if synthetic is not None:
            where.append("is_synthetic = ?")
            params.append(int(synthetic))

        if include_routes:
            placeholders = ", ".join(["?"] * len(include_routes))
            where.append(f"route IN ({placeholders})")
            params.extend(include_routes)

        if exclude_routes:
            placeholders = ", ".join(["?"] * len(exclude_routes))
            where.append(f"route NOT IN ({placeholders})")
            params.extend(exclude_routes)

        w = (" WHERE " + " AND ".join(where)) if where else ""

        row = self._conn.execute(
            f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN verdict='pass' THEN 1 ELSE 0 END) as passed,
                SUM(CASE WHEN verdict='fail' THEN 1 ELSE 0 END) as failed,
                ROUND(AVG(duration_s), 1) as avg_duration,
                ROUND(AVG(cost_usd), 4) as avg_cost,
                SUM(CASE WHEN is_synthetic=1 THEN 1 ELSE 0 END) as synthetic,
                SUM(CASE WHEN is_synthetic=0 THEN 1 ELSE 0 END) as real
            FROM route_outcomes{w}
            """,
            params,
        ).fetchone()

        result = {
            "total": int((row["total"] if row else 0) or 0),
            "passed": int((row["passed"] if row else 0) or 0),
            "failed": int((row["failed"] if row else 0) or 0),
            "avg_duration": float((row["avg_duration"] if row else 0) or 0),
            "avg_cost": float((row["avg_cost"] if row else 0) or 0),
            "synthetic": int((row["synthetic"] if row else 0) or 0),
            "real": int((row["real"] if row else 0) or 0),
        }
        result["pass_rate"] = round(result["passed"] / result["total"], 3) if result["total"] else 0.0

        route_rows = self._conn.execute(
            f"""
            SELECT
                route,
                COUNT(*) as cnt,
                SUM(CASE WHEN verdict='pass' THEN 1 ELSE 0 END) as passed,
                ROUND(AVG(duration_s), 1) as avg_dur,
                ROUND(AVG(cost_usd), 4) as avg_cost,
                SUM(CASE WHEN is_synthetic=1 THEN 1 ELSE 0 END) as synthetic,
                SUM(CASE WHEN is_synthetic=0 THEN 1 ELSE 0 END) as real
            FROM route_outcomes{w}
            GROUP BY route
            ORDER BY cnt DESC
            """,
            params,
        ).fetchall()

        result["routes"] = [
            {
                "route": r["route"],
                "cnt": int(r["cnt"] or 0),
                "passed": int(r["passed"] or 0),
                "avg_dur": float(r["avg_dur"] or 0),
                "avg_cost": float(r["avg_cost"] or 0),
                "synthetic": int(r["synthetic"] or 0),
                "real": int(r["real"] or 0),
            }
            for r in route_rows
        ]
        return result

    def query(self, task_class=None, skill=None, verdict=None, limit=50, offset=0, since_hours=0):
        """查询路由结果"""
        where, params = self._build_where(task_class=task_class, skill=skill, verdict=verdict, since_hours=since_hours)
        sql = "SELECT * FROM route_outcomes"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def query_by_chain(self, chain_id, limit=50, offset=0):
        """按 chain_id 查询路由结果 (L2 协议可追溯性)"""
        rows = self._conn.execute(
            "SELECT * FROM route_outcomes WHERE chain_id = ? ORDER BY ts DESC LIMIT ? OFFSET ?",
            (chain_id, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]

    def stats(self, task_class=None, skill=None, since_hours=168):
        """聚合统计：同时输出 overall / real-only / synthetic-only / main 四口径"""
        where, params = self._build_where(task_class=task_class, skill=skill, since_hours=since_hours)

        overall = self._aggregate(where, params)
        real_only = self._aggregate(where, params, synthetic=0)
        synthetic_only = self._aggregate(where, params, synthetic=1)
        main = self._aggregate(where, params, synthetic=0, exclude_routes=DEFAULT_EXCLUDED_MAIN_ROUTES)

        excluded_from_main = []
        for route in DEFAULT_EXCLUDED_MAIN_ROUTES:
            bucket = self._aggregate(where, params, include_routes=[route])
            bucket.pop("routes", None)
            bucket["route"] = route
            excluded_from_main.append(bucket)

        result = dict(overall)
        result["views"] = {
            "overall": overall,
            "real_only": real_only,
            "synthetic_only": synthetic_only,
            "main": main,
        }
        result["excluded_from_main"] = excluded_from_main
        result["main_pass_rate"] = main.get("pass_rate", 0.0)
        return result

    def route_scores(self, task_class=None, since_hours=168, lambda_cost=0.1, lambda_time=0.01, view="main"):
        """计算每条路由的 bandit score
        score = pass_rate - lambda_cost * avg_cost - lambda_time * avg_duration
        默认基于 main 口径（排除历史污染路由）
        """
        stats = self.stats(task_class=task_class, since_hours=since_hours)
        source = stats.get("views", {}).get(view, stats)
        scored = []
        for r in source.get("routes", []):
            pass_rate = r["passed"] / max(r["cnt"], 1)
            score = pass_rate - lambda_cost * r.get("avg_cost", 0) - lambda_time * r.get("avg_dur", 0) / 60
            scored.append(
                {
                    "route": r["route"],
                    "count": r["cnt"],
                    "pass_rate": round(pass_rate, 3),
                    "avg_dur": r["avg_dur"],
                    "avg_cost": r["avg_cost"],
                    "real": r.get("real", 0),
                    "synthetic": r.get("synthetic", 0),
                    "score": round(score, 4),
                }
            )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def model_stats(self, task_class=None, since_hours=168, lambda_cost=0.1, lambda_time=0.01):
        """按模型分组统计: pass_rate, cost, duration, bandit score
        model_chain 是 JSON 数组, 取第一个元素作为主模型
        """
        where, params = self._build_where(task_class=task_class, since_hours=since_hours)
        w = (" WHERE " + " AND ".join(where)) if where else ""

        rows = self._conn.execute(
            f"""
            SELECT
                json_extract(model_chain, '$[0]') as model,
                COUNT(*) as cnt,
                SUM(CASE WHEN verdict='pass' THEN 1 ELSE 0 END) as passed,
                ROUND(AVG(duration_s), 1) as avg_dur,
                ROUND(AVG(cost_usd), 4) as avg_cost,
                SUM(CASE WHEN is_synthetic=1 THEN 1 ELSE 0 END) as synthetic,
                SUM(CASE WHEN is_synthetic=0 THEN 1 ELSE 0 END) as real
            FROM route_outcomes{w}
            GROUP BY model
            ORDER BY cnt DESC
            """,
            params,
        ).fetchall()

        result = []
        for r in rows:
            model_name = r["model"] or "unknown"
            cnt = int(r["cnt"] or 0)
            passed = int(r["passed"] or 0)
            pass_rate = round(passed / cnt, 3) if cnt else 0.0
            score = pass_rate - lambda_cost * float(r["avg_cost"] or 0) - lambda_time * float(r["avg_dur"] or 0) / 60
            result.append({
                "model": model_name,
                "count": cnt,
                "passed": passed,
                "pass_rate": pass_rate,
                "avg_dur": float(r["avg_dur"] or 0),
                "avg_cost": float(r["avg_cost"] or 0),
                "synthetic": int(r["synthetic"] or 0),
                "real": int(r["real"] or 0),
                "score": round(score, 4),
            })
        result.sort(key=lambda x: x["score"], reverse=True)
        return result

    def summary(self, since_hours=168):
        """系统总览摘要"""
        stats = self.stats(since_hours=since_hours)
        views = stats.get("views", {})

        def line(label, view_stats):
            return (
                f"  {label}: total={view_stats.get('total', 0)} "
                f"pass={view_stats.get('pass_rate', 0):.1%} "
                f"real={view_stats.get('real', 0)} synthetic={view_stats.get('synthetic', 0)}"
            )

        lines = [
            f"Route Outcomes — {since_hours}h window",
            line("Overall", views.get("overall", stats)),
            line("Real-only", views.get("real_only", {})),
            line("Synthetic-only", views.get("synthetic_only", {})),
            line("Main (exclude blank/planner-)", views.get("main", {})),
            f"  Avg duration (overall): {stats.get('avg_duration', 0):.1f}s",
            f"  Avg cost (overall): ${stats.get('avg_cost', 0):.4f}",
        ]

        excluded = stats.get("excluded_from_main", [])
        if excluded:
            lines.append("  Excluded from main score:")
            for bucket in excluded:
                route_label = bucket.get("route") or "<blank>"
                lines.append(
                    f"    - {route_label}: total={bucket.get('total', 0)} "
                    f"pass={bucket.get('pass_rate', 0):.1%} "
                    f"real={bucket.get('real', 0)} synthetic={bucket.get('synthetic', 0)}"
                )

        top_scores = self.route_scores(since_hours=since_hours, view="main")[:5]
        if top_scores:
            lines.append("  Top main routes:")
            for r in top_scores:
                route_label = r["route"] or "<blank>"
                lines.append(
                    f"    - route={route_label}: {r['count']}x pass={r['pass_rate']:.0%} "
                    f"dur={r['avg_dur']:.0f}s score={r['score']:.3f}"
                )
        return "\n".join(lines)

    def close(self):
        self._conn.close()


def cli():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Route Outcomes — 自进化存储层")
    sub = parser.add_subparsers(dest="cmd")

    ap = sub.add_parser("append", help="追加一条 trace")
    for f in ["skill", "task_class", "route", "verdict", "task_id", "model_chain", "error"]:
        ap.add_argument(f"--{f}", default="")
    for f in ["duration_s", "tokens_in", "tokens_out", "cost_usd"]:
        ap.add_argument(f"--{f}", type=float, default=0)
    ap.add_argument("--synthetic", type=int, default=0, help="1=synthetic trace, 0=real")
    ap.add_argument("--chain-id", default=None, help="L2 protocol chain identifier")
    ap.add_argument("--stdin", action="store_true", help="从 stdin 读取 JSON")

    qp = sub.add_parser("query", help="查询路由记录")
    qp.add_argument("--task-class", default="")
    qp.add_argument("--skill", default="")
    qp.add_argument("--verdict", default="")
    qp.add_argument("--limit", type=int, default=20)
    qp.add_argument("--hours", type=int, default=0)

    qcp = sub.add_parser("query-by-chain", help="按 chain_id 查询路由记录")
    qcp.add_argument("--chain-id", required=True, help="L2 protocol chain identifier")
    qcp.add_argument("--limit", type=int, default=50)
    qcp.add_argument("--offset", type=int, default=0)

    sp = sub.add_parser("stats", help="聚合统计")
    sp.add_argument("--task-class", default="")
    sp.add_argument("--skill", default="")
    sp.add_argument("--hours", type=int, default=168)

    scp = sub.add_parser("scores", help="bandit 路线评分")
    scp.add_argument("--task-class", default="")
    scp.add_argument("--hours", type=int, default=168)
    scp.add_argument("--lambda-cost", type=float, default=0.1)
    scp.add_argument("--lambda-time", type=float, default=0.01)
    scp.add_argument("--view", default="main", choices=["overall", "real_only", "synthetic_only", "main"])

    msp = sub.add_parser("model-stats", help="按模型分组统计")
    msp.add_argument("--task-class", default="")
    msp.add_argument("--hours", type=int, default=168)
    msp.add_argument("--lambda-cost", type=float, default=0.1)
    msp.add_argument("--lambda-time", type=float, default=0.01)

    smp = sub.add_parser("summary", help="系统摘要")
    smp.add_argument("--hours", type=int, default=168)

    args = parser.parse_args()
    store = RouteStore()

    if args.cmd == "append":
        if args.stdin:
            store.append_from_stdin()
        else:
            row_id = store.append(
                skill=args.skill,
                task_class=args.task_class,
                route=args.route,
                verdict=args.verdict,
                duration_s=args.duration_s,
                tokens_in=int(args.tokens_in),
                tokens_out=int(args.tokens_out),
                task_id=args.task_id,
                model_chain=args.model_chain,
                cost_usd=args.cost_usd,
                error=args.error,
                is_synthetic=args.synthetic,
                chain_id=args.chain_id,
            )
            print(json.dumps({"id": row_id}))

    elif args.cmd == "query":
        rows = store.query(
            task_class=args.task_class or None,
            skill=args.skill or None,
            verdict=args.verdict or None,
            limit=args.limit,
            since_hours=args.hours,
        )
        print(json.dumps(rows, indent=2, ensure_ascii=False, default=str))

    elif args.cmd == "query-by-chain":
        rows = store.query_by_chain(
            chain_id=args.chain_id,
            limit=args.limit,
            offset=args.offset,
        )
        print(json.dumps(rows, indent=2, ensure_ascii=False, default=str))

    elif args.cmd == "stats":
        result = store.stats(
            task_class=args.task_class or None,
            skill=args.skill or None,
            since_hours=args.hours,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    elif args.cmd == "scores":
        scores = store.route_scores(
            task_class=args.task_class or None,
            since_hours=args.hours,
            lambda_cost=args.lambda_cost,
            lambda_time=args.lambda_time,
            view=args.view,
        )
        print(json.dumps(scores, indent=2, ensure_ascii=False, default=str))

    elif args.cmd == "model-stats":
        results = store.model_stats(
            task_class=args.task_class or None,
            since_hours=args.hours,
            lambda_cost=args.lambda_cost,
            lambda_time=args.lambda_time,
        )
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))

    elif args.cmd == "summary":
        print(store.summary(since_hours=args.hours))

    else:
        parser.print_help()

    store.close()


if __name__ == "__main__":
    cli()
