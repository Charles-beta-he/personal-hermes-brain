#!/usr/bin/env python3
"""Detect enabled cron jobs whose last_run_at is older than their cadence.

Observation-only guard: writes logs/cron-missed-runs.jsonl and improvement
signals, but never triggers jobs or edits jobs.json.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

H = Path.home() / ".hermes"
JOBS = H / "cron" / "jobs.json"
LOG = H / "logs" / "cron-missed-runs.jsonl"
SIGNALS = H / "notes" / "improvement-signals.jsonl"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_str(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(s: Any) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def cadence_seconds(expr: str) -> Optional[int]:
    parts = str(expr or "").split()
    if len(parts) != 5:
        return None
    minute, hour, dom, month, dow = parts
    if hour == "*" and dom == month == dow == "*":
        return 3600
    if hour.startswith("*/") and dom == month == dow == "*":
        try:
            return int(hour[2:]) * 3600
        except Exception:
            return None
    if dom == month == dow == "*":
        return 86400
    if dow != "*" and dom == "*" and month == "*":
        return 7 * 86400
    return None


def load_jobs() -> List[Dict[str, Any]]:
    if not JOBS.exists():
        return []
    data = json.loads(JOBS.read_text())
    jobs = data.get("jobs", data) if isinstance(data, dict) else data
    return jobs if isinstance(jobs, list) else []


def main() -> int:
    now = utc_now()
    misses = []
    for j in load_jobs():
        if not j.get("enabled", True):
            continue
        sched = j.get("schedule") or {}
        expr = sched.get("expr") or sched.get("display") or sched if isinstance(sched, str) else ""
        cadence = cadence_seconds(str(expr))
        if not cadence:
            continue
        last = parse_ts(j.get("last_run_at"))
        nxt = parse_ts(j.get("next_run_at"))
        # First-run future jobs (e.g. weekly GC) are not misses.
        if not last and nxt and nxt > now:
            continue
        if not last:
            misses.append({"id": j.get("id"), "name": j.get("name"), "reason": "never_ran", "schedule": expr})
            continue
        age = (now - last).total_seconds()
        threshold = cadence * 1.5
        if age > threshold:
            misses.append({
                "id": j.get("id"),
                "name": j.get("name"),
                "schedule": expr,
                "last_run_at": j.get("last_run_at"),
                "next_run_at": j.get("next_run_at"),
                "age_hours": round(age / 3600, 2),
                "threshold_hours": round(threshold / 3600, 2),
                "last_status": j.get("last_status"),
            })
    rec = {"ts": utc_str(now), "status": "ok" if not misses else "missed_runs_recorded", "missed_count": len(misses), "missed": misses[:50]}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.open("a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    if misses:
        SIGNALS.parent.mkdir(parents=True, exist_ok=True)
        sig = {
            "timestamp": utc_str(now),
            "source": "cron-missed-run-guard",
            "signals": [{"type": "scheduler_lag", "count": len(misses), "detail": ", ".join(str(m.get("name")) for m in misses[:10])}],
        }
        SIGNALS.open("a", encoding="utf-8").write(json.dumps(sig, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
