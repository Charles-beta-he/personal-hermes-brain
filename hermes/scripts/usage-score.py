#!/usr/bin/env python3
"""Hermes Actual Usage Score — reproducible grade for multi-model use.

The primary window is 24h. Sparse personal-agent installs may legitimately have
zero non-hook model-call rows in 24h, so breadth/integrity/diversity use a capped
7d fallback when the fresh window is starved. The cap preserves recency pressure
while avoiding false Grade-D from measurement starvation.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

HOME = Path.home()
H = HOME / ".hermes"
DB = Path(os.environ.get("HERMES_ROUTE_DB_PATH", str(H / "route_outcomes.db"))).expanduser()
OUT = H / "state" / "usage-score.json"
ENSEMBLE = H / "logs" / "ensemble-votes.jsonl"
CROSS = H / "logs" / "cross-patch.jsonl"
RATIFY = H / "logs" / "ratify.jsonl"
TARGET_MODELS = ["gpt-5.5", "claude-opus-4-7", "deepseek-v4-pro", "mimo-v2.5-pro"]
NOW = datetime.now(timezone.utc)
SPARSE_CALL_ROW_MIN = 10
FALLBACK_HOURS = 168
FALLBACK_CAP = 0.70


def parse_ts(s: Any):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for line in path.read_text(errors="ignore").splitlines():
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def grade(score: float) -> str:
    return "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D"


def model_from_chain(chain: Any) -> str:
    try:
        data = json.loads(chain)
        if isinstance(data, list) and data:
            return str(data[0])
    except Exception:
        pass
    return str(chain or "").strip("[]\"")


def rows(hours: int = 24) -> List[Dict[str, Any]]:
    if not DB.exists():
        return []
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cutoff = (NOW - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM route_outcomes WHERE ts >= ? AND model_chain != ''", (cutoff,))]
    finally:
        conn.close()


def call_window(hours: int) -> Dict[str, Any]:
    real = [r for r in rows(hours) if int(r.get("is_synthetic") or 0) == 0]
    call_rows = [r for r in real if not str(r.get("route") or "").startswith("hook:")]
    integrity = [
        r for r in call_rows
        if (r.get("duration_s") or 0) > 0
        and (r.get("tokens_in") or 0) > 0
        and (r.get("tokens_out") or 0) > 0
        and (r.get("cost_usd") or 0) > 0
    ]
    models = sorted(set(model_from_chain(r.get("model_chain")) for r in integrity))
    target_seen = [m for m in TARGET_MODELS if m in models]
    breadth_score = 25 * min(len(target_seen) / 4, 1)
    integrity_ratio = (len(integrity) / len(call_rows)) if call_rows else 0
    integrity_score = 15 * min(integrity_ratio / 0.95, 1)

    route_models: Dict[str, set] = {}
    diversity_rows = []
    for r in real:
        route = r.get("route") or r.get("skill") or ""
        if not route or str(route).startswith("hook:"):
            continue
        diversity_rows.append(r)
        route_models.setdefault(str(route), set()).add(model_from_chain(r.get("model_chain")))
    hot = sorted(route_models.items(), key=lambda kv: len(kv[1]), reverse=True)[:10]
    mean_div = (sum(min(len(s) / 3, 1) for _, s in hot) / len(hot)) if hot else 0
    diversity_score = 15 * mean_div
    return {
        "hours": hours,
        "real_rows": len(real),
        "call_rows": len(call_rows),
        "integrity_rows": len(integrity),
        "models": models,
        "target_seen": target_seen,
        "breadth_score": breadth_score,
        "integrity_ratio": integrity_ratio,
        "integrity_score": integrity_score,
        "diversity_rows": len(diversity_rows),
        "hot": hot,
        "mean_div": mean_div,
        "diversity_score": diversity_score,
        "excluded_hook_rows": len(real) - len(call_rows),
        "excluded_hook_diversity_rows": len(real) - len(diversity_rows),
    }


def choose_sparse(primary: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    if primary["call_rows"] >= SPARSE_CALL_ROW_MIN:
        primary = dict(primary)
        primary["fallback_used"] = False
        return primary
    chosen = dict(primary)
    chosen["fallback_used"] = True
    chosen["fallback_hours"] = fallback["hours"]
    chosen["fallback_call_rows"] = fallback["call_rows"]
    # Take the better of the fresh score and a capped 7d score, per metric.
    for key in ("breadth_score", "integrity_score", "diversity_score"):
        chosen[key] = max(float(primary[key]), float(fallback[key]) * FALLBACK_CAP)
    chosen["models"] = fallback["models"] if fallback["models"] else primary["models"]
    chosen["target_seen"] = fallback["target_seen"] if fallback["target_seen"] else primary["target_seen"]
    chosen["integrity_ratio"] = fallback["integrity_ratio"] if fallback["call_rows"] else primary["integrity_ratio"]
    chosen["mean_div"] = fallback["mean_div"] if fallback["diversity_rows"] else primary["mean_div"]
    chosen["hot"] = fallback["hot"] if fallback["hot"] else primary["hot"]
    chosen["integrity_rows"] = primary["integrity_rows"]
    chosen["evaluated_integrity_rows_7d"] = fallback["integrity_rows"]
    chosen["evaluated_diversity_rows_7d"] = fallback["diversity_rows"]
    return chosen


def cron_stats() -> Dict[str, Any]:
    try:
        txt = subprocess.run(
            ["bash", str(H / "scripts" / "p10-health.sh"), "--json"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=120,
        ).stdout
        d = json.loads(txt)
        details = d.get("details", {})
        return {
            "score_raw": float(d.get("components", {}).get("cron_health", 0.0)),
            "ok": int(details.get("cron_good", details.get("cron_recent_24h", 0))),
            "total": int(details.get("cron_total", 0)),
            "recent_24h": int(details.get("cron_recent_24h", 0)),
            "pending_first_run": int(details.get("cron_pending_first_run", 0)),
            "bad": int(details.get("cron_bad", 0)),
            "stale_errors": int(details.get("cron_stale_errors", 0)),
            "source": "p10-health-json",
        }
    except Exception:
        return {"score_raw": 0.0, "ok": 0, "total": 0, "recent_24h": 0, "pending_first_run": 0, "bad": 0, "stale_errors": 0, "source": "unknown"}


def certified_discussion_results(days: int = 7) -> List[Dict[str, Any]]:
    """Return recent consult_models discussion_result artifacts that reached ratification.

    consult_models writes rich discussion artifacts under tick-*/discussion_result.json.
    Those are first-class ratification evidence, even when no separate
    logs/ratify.jsonl bridge exists yet.
    """
    out: List[Dict[str, Any]] = []
    cutoff = NOW - timedelta(days=days)
    for path in H.glob("tick-*/discussion_result.json"):
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            if mtime < cutoff:
                continue
            data = json.loads(path.read_text(errors="ignore"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        status = str(data.get("status") or "")
        truth = data.get("truth_assessment") or {}
        if status not in {"certified", "certified_with_minor_risks"}:
            continue
        if isinstance(truth, dict) and truth and truth.get("can_certify_truth") is False:
            continue
        models = data.get("models_consulted") or data.get("models") or []
        if isinstance(models, list) and len(models) < 2:
            continue
        item = dict(data)
        item["source"] = "discussion_result"
        item["path"] = str(path)
        item["ts"] = item.get("ts") or mtime.strftime("%Y-%m-%dT%H:%M:%SZ")
        out.append(item)
    return out


def compute() -> Dict[str, Any]:
    primary = call_window(24)
    fallback = call_window(FALLBACK_HOURS)
    w = choose_sparse(primary, fallback)

    ens7 = [e for e in read_jsonl(ENSEMBLE) if parse_ts(e.get("ts")) and parse_ts(e.get("ts")) >= NOW - timedelta(days=7)]
    ens_real = []
    for e in ens7:
        ms = e.get("models") or []
        providers = set()
        for m in ms:
            s = str(m)
            providers.add("openai-codex" if "gpt" in s else "anthropic" if "claude" in s else "deepseek" if "deepseek" in s else "xiaomi" if "mimo" in s else s)
        if e.get("execute") is True and (e.get("total_voters") or e.get("votes_count") or 0) >= 3 and len(providers) >= 3:
            ens_real.append(e)
    ensemble_score = 15 * min(len(ens_real) / 3, 1)

    cross7 = [e for e in read_jsonl(CROSS) + read_jsonl(RATIFY) if parse_ts(e.get("ts")) and parse_ts(e.get("ts")) >= NOW - timedelta(days=7)]
    discussion_ratified = certified_discussion_results(days=7)
    ratified = [e for e in cross7 if e.get("actual_model_calls") or e.get("execute") or e.get("ratified") or e.get("verdict") in ("pass", "approved", "certified")]
    ratified.extend(ens_real)
    ratified.extend(discussion_ratified)
    ratify_score = 10 * min(len(ratified) / 3, 1)

    cs = cron_stats()
    cron_score = 10 * min((cs.get("score_raw") or 0) / 0.94, 1)

    closure_events = 0
    for p in [H / "logs" / "evolve.log", H / "logs" / "autonomous-evolution.jsonl", H / "logs" / "skill-steward.jsonl"]:
        for e in read_jsonl(p):
            ts = parse_ts(e.get("ts") or e.get("timestamp"))
            if ts and ts >= NOW - timedelta(days=14) and (e.get("status") in ("ok", "applied", "promoted") or e.get("kept") or e.get("eval_result") in ("kept", "noop")):
                closure_events += 1
    closure_score = 10 * min(closure_events / 5, 1)

    total = round(w["breadth_score"] + w["integrity_score"] + w["diversity_score"] + ensemble_score + ratify_score + cron_score + closure_score, 2)
    operational_score = 100 if int(cs.get("bad") or 0) == 0 else max(0, 100 - int(cs.get("bad") or 0) * 25)
    evidence_readiness_score = round(
        min(100, (
            (w["breadth_score"] / 25) * 30
            + (w["integrity_score"] / 15) * 20
            + (w["diversity_score"] / 15) * 20
            + (ensemble_score / 15) * 15
            + (ratify_score / 10) * 15
        )),
        2,
    )
    missing_evidence = []
    if len(ens_real) == 0:
        missing_evidence.append("ensemble_executed")
    if len(ratified) == 0:
        missing_evidence.append("ratification_corpus")
    return {
        "ts": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "score": total,
        "grade": grade(total),
        "semantic_grades": {
            "operational_health": {
                "score": operational_score,
                "grade": grade(operational_score),
                "cron_bad_count": int(cs.get("bad") or 0),
                "cron_recent_24h": int(cs.get("recent_24h") or 0),
                "cron_source": cs.get("source"),
            },
            "evidence_readiness": {
                "score": evidence_readiness_score,
                "grade": grade(evidence_readiness_score),
                "missing": missing_evidence,
                "fallback_used": bool(w.get("fallback_used", False)),
            },
        },
        "interpretation": "runtime operational health is separated from multi-model evidence readiness; overall grade includes both",
        "components": {
            "model_breadth_24h": {"score": round(w["breadth_score"], 2), "max": 25, "target_seen": w["target_seen"], "all_integrity_models": w["models"], "fallback_used": w.get("fallback_used", False), "fallback_hours": w.get("fallback_hours")},
            "real_call_integrity": {"score": round(w["integrity_score"], 2), "max": 15, "ratio": round(w["integrity_ratio"], 3), "integrity_rows": w["integrity_rows"], "call_rows": w["call_rows"], "evaluated_integrity_rows_7d": w.get("evaluated_integrity_rows_7d"), "excluded_hook_rows": w["excluded_hook_rows"], "fallback_used": w.get("fallback_used", False)},
            "route_diversity": {"score": round(w["diversity_score"], 2), "max": 15, "mean_normalized": round(w["mean_div"], 3), "routes": {k: sorted(v) for k, v in w["hot"][:5]}, "evaluated_rows": w["diversity_rows"], "evaluated_rows_7d": w.get("evaluated_diversity_rows_7d"), "excluded_hook_rows": w["excluded_hook_diversity_rows"], "fallback_used": w.get("fallback_used", False)},
            "ensemble_executed": {"score": round(ensemble_score, 2), "max": 15, "count_7d": len(ens_real)},
            "ratification_corpus": {"score": round(ratify_score, 2), "max": 10, "count_7d": len(ratified), "sources": sorted(set(str(e.get("source") or "jsonl") for e in ratified))},
            "cron_green": {"score": round(cron_score, 2), "max": 10, **cs},
            "self_evolution_closure": {"score": round(closure_score, 2), "max": 10, "closure_events_14d": closure_events},
        },
        "thresholds": {"A": 85, "B": 70, "C": 55},
    }


def main() -> int:
    data = compute()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0 if data["grade"] in {"A", "B"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
