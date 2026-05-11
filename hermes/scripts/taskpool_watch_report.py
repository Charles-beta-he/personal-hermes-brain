#!/usr/bin/env python3
"""Local brain taskpool watcher: emit occasional human report, stay silent otherwise.

No-agent cron semantics: non-empty stdout is delivered; empty stdout is silent.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

HERMES = Path.home() / ".hermes"
STATE_PATH = HERMES / "state" / "taskpool_watch_report_state.json"
ORCH = HERMES / "scripts" / "brain_task_orchestrator.py"
TZ = timezone(timedelta(hours=8))


def now() -> datetime:
    return datetime.now(TZ)


def run_json(*args: str, timeout: int = 90) -> dict[str, Any]:
    cmd = ["python3", str(ORCH), *args]
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    if p.returncode != 0:
        return {"status": "COMMAND_ERROR", "returncode": p.returncode, "cmd": cmd, "stdout": out[-2000:], "stderr": err[-2000:]}
    try:
        return json.loads(out)
    except Exception as exc:
        return {"status": "PARSE_ERROR", "cmd": cmd, "error": str(exc), "stdout": out[-3000:], "stderr": err[-1000:]}


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(STATE_PATH)


def parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    interesting: list[str] = []
    high_score_attention: list[dict[str, Any]] = []
    for r in rows:
        st = str(r.get("status") or "unknown")
        counts[st] = counts.get(st, 0) + 1
        score = int(r.get("score") or 0)
        if st in {"claimed", "running", "review", "retry", "blocked", "expired"}:
            interesting.append(f"{st}: {r.get('id')} ({r.get('project')})")
        if score >= 400 and st not in {"done", "archived"}:
            mm_status = str(r.get("multimodel_status") or "")
            stale = bool(r.get("stale_claim"))
            if stale:
                classification = "stale_claim_stuck"
                next_action = "guardian/reconcile should release stale claim, then dispatch again"
            elif st == "review" and mm_status not in {"certified", "certified_with_minor_risks"}:
                classification = "review_gate_not_closed"
                next_action = "not execution-stuck; needs target-bound 4/4 ratification or human/code-review before done"
            elif not r.get("dispatchable") and st not in {"review", "claimed", "running"}:
                classification = "not_dispatchable"
                next_action = "inspect lifecycle/mission gate before expecting worker progress"
            else:
                classification = "active_high_score"
                next_action = "watch for stale_claim/timeout; keep deterministic evidence before ratification"
            high_score_attention.append({
                "id": r.get("id"),
                "score": score,
                "status": st,
                "project": r.get("project"),
                "multimodel_status": mm_status,
                "classification": classification,
                "next_action": next_action,
            })
    return {"counts": counts, "interesting": interesting, "high_score_attention": high_score_attention}


def stable_fingerprint(list_data: dict[str, Any], proof: dict[str, Any], selfcheck: dict[str, Any]) -> str:
    rows = list_data.get("rows") or []
    compact = {
        "rows": [
            {
                "id": r.get("id"),
                "status": r.get("status"),
                "priority": r.get("priority"),
                "retry_count": r.get("retry_count"),
                "score": r.get("score"),
                "multimodel_status": r.get("multimodel_status"),
                "multimodel_ratification_artifact": r.get("multimodel_ratification_artifact"),
                "claimed_by": r.get("claimed_by"),
                "claim_expires_at": r.get("claim_expires_at"),
                "next_attempt_at": r.get("next_attempt_at"),
            }
            for r in rows
        ],
        "proof_status": proof.get("status"),
        "proof_failures": proof.get("failures") or [],
        "proof_warnings": proof.get("warnings") or [],
        "selfcheck_status": selfcheck.get("status"),
        "selfcheck_failures": selfcheck.get("failures") or [],
        "selfcheck_warnings": selfcheck.get("warnings") or [],
    }
    raw = json.dumps(compact, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def main() -> int:
    current = now()
    list_data = run_json("list", "--json")
    next_data = run_json("next", "--json")
    proof = run_json("proof-check", "--json")
    selfcheck = run_json("selfcheck", "--json")

    rows = list_data.get("rows") or []
    summary = summarize_rows(rows if isinstance(rows, list) else [])
    fp = stable_fingerprint(list_data, proof, selfcheck)
    prev = load_state()
    last_report_at = parse_dt(prev.get("last_report_at"))
    hours_since = None if last_report_at is None else (current - last_report_at).total_seconds() / 3600

    errors = []
    for name, data in [("list", list_data), ("next", next_data), ("proof", proof), ("selfcheck", selfcheck)]:
        if data.get("status") not in {"OK", "PASS"}:
            errors.append(f"{name}:{data.get('status')}")
    if proof.get("failures"):
        errors.append(f"proof_failures={len(proof.get('failures') or [])}")
    if proof.get("warnings"):
        errors.append(f"proof_warnings={len(proof.get('warnings') or [])}")
    if selfcheck.get("failures"):
        errors.append(f"selfcheck_failures={len(selfcheck.get('failures') or [])}")
    if selfcheck.get("warnings"):
        errors.append(f"selfcheck_warnings={len(selfcheck.get('warnings') or [])}")

    changed = fp != prev.get("fingerprint")
    daily_due = hours_since is None or hours_since >= 24
    has_active_attention = bool(summary["interesting"] or summary["high_score_attention"] or errors)

    should_report = changed or daily_due or has_active_attention

    state = {
        "fingerprint": fp,
        "last_seen_at": current.isoformat(timespec="seconds"),
        "last_counts": summary["counts"],
        "last_next": (next_data.get("next") or {}).get("id") if isinstance(next_data.get("next"), dict) else None,
        "last_errors": errors,
        "last_report_at": prev.get("last_report_at"),
    }

    if not should_report:
        save_state(state)
        return 0

    state["last_report_at"] = current.isoformat(timespec="seconds")
    save_state(state)

    next_task = next_data.get("next") if isinstance(next_data.get("next"), dict) else None
    lines = []
    lines.append(f"任务池自动运行汇报 {current.strftime('%Y-%m-%d %H:%M')} CST")
    lines.append(f"状态: {'需要关注' if errors or summary['interesting'] else '正常'}；active={list_data.get('task_count', len(rows))}；counts={summary['counts']}")
    if next_task:
        lines.append(f"下一任务: {next_task.get('id')} / {next_task.get('project')} / score={next_task.get('score')}")
    if summary["interesting"]:
        lines.append("进行中/异常: " + "；".join(summary["interesting"][:5]))
    if summary["high_score_attention"]:
        items = []
        for item in summary["high_score_attention"][:3]:
            items.append(
                f"score={item.get('score')} {item.get('status')} {item.get('classification')}: "
                f"{item.get('id')} → {item.get('next_action')}"
            )
        lines.append("高分任务闭环: " + "；".join(items))
    if errors:
        lines.append("检查异常: " + "；".join(errors[:8]))
    else:
        lines.append("proof-check/selfcheck: PASS")
    if changed:
        lines.append("触发原因: 任务状态或 proof/selfcheck 指纹变化")
    elif daily_due:
        lines.append("触发原因: 24h 心跳")
    else:
        lines.append("触发原因: 有高分未闭环/claimed/running/review/retry/blocked/expired 或检查异常")
    lines.append("说明: 无变化时此 watcher 静默；执行器仍由 local-brain-taskpool-auto-completer 有界推进。")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
