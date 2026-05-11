#!/usr/bin/env python3
"""Local-brain idle detector and risk router.

This is a read-only control-plane detector. It does not execute task Markdown,
does not claim leases, and does not mark tasks done. Its job is to decide
whether an autonomous runner *could* be considered, and to route the next task
through a risk-aware execution mode.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TZ = timezone(timedelta(hours=8))
HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(HOME / ".hermes"))).expanduser().resolve()
ORCH = HERMES_HOME / "scripts" / "brain_task_orchestrator.py"
STATE_DIR = Path(os.environ.get("HERMES_BRAIN_IDLE_RUNNER_STATE_DIR", str(HERMES_HOME / "state"))).expanduser()
STATE_FILE = STATE_DIR / "brain_task_idle_runner_state.json"
IDLE_ENV_FLAG = "HERMES_LOCAL_BRAIN_IDLE_RUNNER"

CLAIM_BOUND_STATUSES = {"claimed", "running", "review"}
TERMINAL_STATUSES = {"done", "archived", "expired"}
READ_ONLY_HINTS = (
    "audit", "analysis", "analyze", "review", "inspect", "diagnose", "doctor",
    "多模型分析", "审计", "分析", "评审", "诊断", "检查",
)
HIGH_RISK_HINTS = (
    "delete", "remove", "deploy", "prod", "production", "push", "secret", "credential",
    "token", "password", "destructive", "删除", "移除", "部署", "生产", "密钥", "凭据", "密码",
)
AUTOMATION_HINTS = (
    "autorun", "auto-run", "autonomous", "idle-runner", "runner", "cron", "hook",
    "gateway", "automation", "自动执行", "空闲", "调度", "钩子", "状态机",
)


def iso() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def redact_sensitive(text: str) -> str:
    """Best-effort redaction for subprocess diagnostics."""
    if not text:
        return ""
    patterns = [
        (r"(?i)(api[_-]?key|token|secret|password|passwd|proxy)(\s*[:=]\s*)([^\s,;}]+)", r"\1\2[REDACTED]"),
        (r"(?i)(auth_token|ct0)=([^;\s]+)", r"\1=[REDACTED]"),
    ]
    redacted = text
    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted)
    return redacted


def run_json(cmd: list[str], timeout: int = 90) -> dict[str, Any]:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
    out = redact_sensitive((proc.stdout or "")[-2000:])
    err = redact_sensitive((proc.stderr or "")[-2000:])
    if proc.returncode != 0:
        return {"status": "ERROR", "cmd": cmd, "returncode": proc.returncode, "stdout": out, "stderr": err}
    try:
        data = json.loads(proc.stdout or "{}")
    except Exception as exc:
        return {"status": "ERROR", "cmd": cmd, "returncode": proc.returncode, "stdout": out, "stderr": err, "parse_error": type(exc).__name__}
    data.setdefault("cmd", cmd)
    data.setdefault("returncode", proc.returncode)
    return data


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip("\n")
    body = text[end + 4 :]
    fm: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[str] | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and current_key and current_list is not None:
            current_list.append(line[4:].strip().strip('"\''))
            fm[current_key] = current_list
            continue
        current_key = None
        current_list = None
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "[]":
            fm[key] = []
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            fm[key] = [x.strip().strip('"\'') for x in inner.split(",") if x.strip()]
        elif value == "":
            fm[key] = ""
            current_key = key
            current_list = []
        else:
            fm[key] = value.strip('"\'')
    return fm, body


def task_frontmatter(row: dict[str, Any]) -> dict[str, Any]:
    path = row.get("path")
    if not path:
        return {}
    try:
        text = Path(path).read_text(encoding="utf-8")
    except Exception:
        return {}
    fm, _body = split_frontmatter(text)
    return fm


def as_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    return [x.strip() for x in re.split(r"[, ]+", str(value)) if x.strip()]


def frontmatter_or_row(row: dict[str, Any], fm: dict[str, Any], key: str) -> Any:
    """Prefer orchestrator row fields, but fall back to task frontmatter.

    The orchestrator list row may omit some lease metadata (notably run_id in
    older versions). The idle detector must fail closed on persisted metadata
    even when the row schema is incomplete.
    """
    value = row.get(key)
    if value is not None and value != "":
        return value
    return fm.get(key)


def infer_risk_and_mode(row: dict[str, Any], fm: dict[str, Any]) -> dict[str, Any]:
    priority = str(row.get("priority") or fm.get("priority") or "")
    text = " ".join(str(x or "") for x in [row.get("id"), row.get("title"), row.get("project"), fm.get("workflow_contract"), " ".join(as_list(fm.get("concepts")))])
    text_lower = text.lower()

    explicit_risk = str(fm.get("risk") or "").strip().lower()
    if explicit_risk in {"low", "medium", "high"}:
        risk = explicit_risk
    elif priority == "P0" or any(h in text_lower for h in HIGH_RISK_HINTS):
        risk = "high"
    elif any(h.lower() in text_lower for h in READ_ONLY_HINTS):
        risk = "medium"
    else:
        risk = "medium"

    explicit_mode = str(fm.get("execution_mode") or "").strip()
    if explicit_mode:
        mode = explicit_mode
    elif risk == "high":
        mode = "manual"
    elif any(h.lower() in text_lower for h in AUTOMATION_HINTS):
        mode = "handoff_only"
    elif any(h.lower() in text_lower for h in READ_ONLY_HINTS):
        mode = "read_only_review"
    else:
        mode = "bounded_agent_tick"

    blocked_by = as_list(fm.get("blocked_by"))
    blockers = []
    if blocked_by:
        blockers.append("blocked_by_dag")
    if risk == "high":
        blockers.append("high_risk_manual_gate")
    if mode == "manual":
        blockers.append("manual_execution_mode")

    return {
        "task_id": row.get("id"),
        "status": row.get("status"),
        "priority": priority,
        "project": row.get("project"),
        "claimed_by": frontmatter_or_row(row, fm, "claimed_by") or "",
        "claim_expires_at": frontmatter_or_row(row, fm, "claim_expires_at") or "",
        "run_id": frontmatter_or_row(row, fm, "run_id"),
        "risk": risk,
        "execution_mode": mode,
        "blocked_by": blocked_by,
        "blockers": blockers,
        "eligible_for_idle_handoff": not blockers and mode in {"read_only_review", "handoff_only", "bounded_agent_tick"} and risk in {"low", "medium"},
        "path": row.get("path"),
    }


def load_pool(include_done: bool = False) -> dict[str, Any]:
    args = [sys.executable, str(ORCH), "list", "--json"]
    if include_done:
        args.insert(-1, "--include-done")
    return run_json(args)


def has_active_claim(row: dict[str, Any]) -> bool:
    status = str(row.get("status") or "")
    if status in CLAIM_BOUND_STATUSES:
        return True
    # Fail closed if stale/partial lease metadata survives on a non-terminal row.
    return any(row.get(field) for field in ("claimed_by", "claim_expires_at", "run_id"))


def choose_candidate(routes: list[dict[str, Any]]) -> dict[str, Any] | None:
    for route in routes:
        if route.get("status") == "pending" and route.get("eligible_for_idle_handoff"):
            return route
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only local-brain idle detector and risk router")
    parser.add_argument("--include-done", action="store_true")
    parser.add_argument("--min-idle-minutes", type=int, default=15, help="Policy threshold recorded in output; this script does not inspect private user activity")
    parser.add_argument("--write-state", action="store_true", help="Write detector state snapshot; still does not mutate tasks")
    parser.add_argument("--json", action="store_true", help="Retained for consistency; output is always JSON")
    args = parser.parse_args()

    pool = load_pool(include_done=args.include_done)
    if pool.get("status") not in {"OK", "PASS"}:
        print(json.dumps({"status": "ERROR", "generated_at": iso(), "pool": pool}, ensure_ascii=False, indent=2, sort_keys=True))
        return 2

    rows = pool.get("rows") or []
    routes = [infer_risk_and_mode(row, task_frontmatter(row)) for row in rows if row.get("status") not in TERMINAL_STATUSES]
    active = [r for r in routes if has_active_claim(r)]
    enabled = os.environ.get(IDLE_ENV_FLAG) == "1"
    candidate = choose_candidate(routes)

    deny_reasons: list[str] = []
    if not enabled:
        deny_reasons.append("idle_runner_disabled")
    if active:
        deny_reasons.append("active_lease_or_running_task_present")
    if not candidate:
        deny_reasons.append("no_eligible_pending_task")

    idle_decision = "idle" if enabled and not active else "busy_or_disabled"
    next_action = "observe_only"
    if idle_decision == "idle" and candidate:
        next_action = "handoff_only_possible"

    payload = {
        "schema": "hermes_local_brain_idle_runner_v1",
        "status": "OK",
        "generated_at": iso(),
        "policy": {
            "mutation_policy": "read-only detector; never executes Markdown, never claims, never marks done",
            "kill_switch": IDLE_ENV_FLAG,
            "kill_switch_enabled": enabled,
            "min_idle_minutes": args.min_idle_minutes,
        },
        "idle_decision": idle_decision,
        "next_action": next_action,
        "deny_reasons": deny_reasons,
        "active_count": len(active),
        "candidate": candidate,
        "routes": routes,
    }

    if args.write_state:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        payload["state_file"] = str(STATE_FILE)

    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
