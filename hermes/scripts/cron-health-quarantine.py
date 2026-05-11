#!/usr/bin/env python3
"""Report failing Hermes cron jobs; safe report-only by default.

Old transient cron errors can remain in jobs.json until the job's next scheduled
run. Mark those as stale instead of counting them as live bad jobs; the stale
line remains auditable in cron-quarantine.jsonl.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

H = Path.home() / ".hermes"
LOG = H / "logs" / "cron-quarantine.jsonl"
JOBS = H / "cron" / "jobs.json"
STALE_TRANSIENT_RE = re.compile(r"interpreter shutdown|timeout_recorded|degraded_recorded|partial_fail_recorded", re.I)


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(s: Any) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def append(obj: Dict[str, Any]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def load_jobs() -> List[Dict[str, Any]]:
    if not JOBS.exists():
        return []
    data = json.loads(JOBS.read_text())
    jobs = data.get("jobs", data) if isinstance(data, dict) else data
    return jobs if isinstance(jobs, list) else []


def stale_job(j: Dict[str, Any], now: datetime) -> bool:
    status = str(j.get("last_status") or "").lower()
    err = str(j.get("last_error") or "")
    if status not in {"error", "failed"}:
        return False
    last = parse_ts(j.get("last_run_at"))
    nxt = parse_ts(j.get("next_run_at"))
    if not last or not nxt:
        return False
    return (now - last).total_seconds() > 86400 and nxt > now and bool(STALE_TRANSIENT_RE.search(err))


def jobs_report() -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    live_bad = []
    stale = []
    for j in load_jobs():
        if not j.get("enabled", True):
            continue
        status = str(j.get("last_status") or "").lower()
        if status not in {"error", "failed"}:
            continue
        rec = {
            "id": j.get("id"),
            "name": j.get("name"),
            "last_run_at": j.get("last_run_at"),
            "next_run_at": j.get("next_run_at"),
            "last_status": j.get("last_status"),
            "last_error": j.get("last_error"),
        }
        if stale_job(j, now):
            rec["stale"] = True
            stale.append(rec)
        else:
            rec["stale"] = False
            live_bad.append(rec)
    return {"bad_jobs": live_bad, "stale_jobs": stale}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    try:
        txt = subprocess.run(["hermes", "cron", "list", "--all"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30).stdout
    except Exception as e:
        txt = "ERROR " + repr(e)
    report = jobs_report()
    bad_lines = [f"{j.get('name')}: {j.get('last_error')}" for j in report["bad_jobs"]]
    stale_lines = [f"{j.get('name')}: {j.get('last_error')}" for j in report["stale_jobs"]]
    # If jobs.json was unavailable, fall back to textual scan so failures are not hidden.
    if not report["bad_jobs"] and not report["stale_jobs"]:
        bad_lines = [line.strip() for line in txt.splitlines() if re.search(r"\berror\b", line, re.I)]
    rec = {
        "ts": utc(),
        "mode": "apply" if args.apply else "report",
        "bad_count": len(bad_lines),
        "bad_lines": bad_lines[:20],
        "stale_count": len(stale_lines),
        "stale_lines": stale_lines[:20],
        "stale_jobs": report["stale_jobs"][:20],
    }
    append(rec)
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
