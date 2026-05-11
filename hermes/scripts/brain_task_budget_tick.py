#!/usr/bin/env python3
"""Bounded local-brain task budget tick.

This is a control-plane helper, not a general autonomous executor. It prepares a
single bounded execution envelope for a local-brain task and writes a durable
handoff artifact. By default it does not claim or execute anything.

Use this before handing a long task to an LLM/agent so an iteration-budget hit
produces a resumable handoff instead of an incomplete response.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TZ = timezone(timedelta(hours=8))
HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(HOME / ".hermes"))).expanduser().resolve()
BRAIN = Path(os.environ.get("HERMES_BRAIN_VAULT", os.environ.get("OBSIDIAN_VAULT_PATH", str(HOME / "Documents" / "brain")))).expanduser().resolve()
ORCH = HERMES_HOME / "scripts" / "brain_task_orchestrator.py"
DOCTOR = HERMES_HOME / "scripts" / "iteration_budget_doctor.py"
HANDOFF_TEMPLATE = HERMES_HOME / "scripts" / "iteration_budget_handoff_template.md"
ARTIFACT_DIR = HERMES_HOME / "artifacts" / "iteration-budget"

LOW_RISK_MODES = {"script_first_no_agent", "tiny_summarizer", "bounded_agent_tick", "single_shot_capped", "manual"}
DEFAULT_MAX_TOOL_CALLS = 45
DEFAULT_SAFETY_MARGIN = 12


def iso() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def run_json(cmd: list[str], *, timeout: int = 60) -> dict[str, Any]:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
    if proc.returncode != 0:
        return {"status": "ERROR", "cmd": cmd, "returncode": proc.returncode, "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:]}
    try:
        data = json.loads(proc.stdout or "{}")
    except Exception as exc:
        return {"status": "ERROR", "cmd": cmd, "returncode": proc.returncode, "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:], "parse_error": type(exc).__name__}
    data.setdefault("cmd", cmd)
    data.setdefault("returncode", proc.returncode)
    return data


def doctor() -> dict[str, Any]:
    if not DOCTOR.exists():
        return {"status": "ERROR", "reason": "missing_doctor", "path": str(DOCTOR)}
    return run_json([sys.executable, str(DOCTOR), "--json"], timeout=90)


def dispatch_next() -> dict[str, Any]:
    return run_json([sys.executable, str(ORCH), "dispatch-dry-run", "--json"])


def find_task(task_id: str) -> dict[str, Any]:
    data = run_json([sys.executable, str(ORCH), "list", "--json"])
    for row in data.get("rows", []) if isinstance(data.get("rows"), list) else []:
        if row.get("id") == task_id or str(row.get("link", "")).endswith(task_id + "]]"):
            return row
    return {"id": task_id, "missing": True}


def default_task_row(task: str | None) -> dict[str, Any]:
    if task:
        return find_task(task)
    dispatch = dispatch_next()
    return (dispatch.get("next") or {}) if isinstance(dispatch, dict) else {}


def classify_mode(row: dict[str, Any], requested_mode: str) -> dict[str, Any]:
    priority = str(row.get("priority") or "")
    title = str(row.get("title") or row.get("id") or "")
    project = str(row.get("project") or "")
    text = f"{title} {project}".lower()
    risk = "medium"
    if priority == "P0" or any(x in text for x in ["delete", "删除", "deploy", "push", "prod", "secret", "credential"]):
        risk = "high"
    elif priority in {"P2", "P3"} or any(x in text for x in ["read-only", "audit", "审计", "diagnose", "doctor"]):
        risk = "low"

    mode = requested_mode
    if mode == "auto":
        if risk == "high":
            mode = "manual"
        elif "cron" in text or "dashboard" in text or "sync" in text:
            mode = "script_first_no_agent"
        else:
            mode = "bounded_agent_tick"

    allowed = mode in LOW_RISK_MODES and risk != "high"
    return {"risk": risk, "execution_mode": mode, "allowed_for_auto_claim": allowed}


def compute_budget(doctor_data: dict[str, Any], spent_tool_calls: int, max_tool_calls: int, safety_margin: int) -> dict[str, Any]:
    budget = doctor_data.get("budget", {}) if isinstance(doctor_data, dict) else {}
    agent_cap = budget.get("agent_max_turns") or max_tool_calls
    try:
        agent_cap_int = int(agent_cap)
    except Exception:
        agent_cap_int = max_tool_calls
    effective_max = min(int(max_tool_calls), max(1, agent_cap_int - int(safety_margin)))
    remaining = effective_max - int(spent_tool_calls)
    ratio = float(spent_tool_calls) / float(max(1, effective_max))
    if remaining <= 0:
        action = "stop_and_handoff"
    elif ratio >= 0.8:
        action = "handoff_soon"
    else:
        action = "proceed_bounded"
    return {
        "agent_cap": agent_cap_int,
        "max_tool_calls": max_tool_calls,
        "safety_margin": safety_margin,
        "effective_max_before_handoff": effective_max,
        "spent_tool_calls": spent_tool_calls,
        "remaining_before_handoff": remaining,
        "spent_ratio": round(ratio, 3),
        "action": action,
    }


def render_handoff(row: dict[str, Any], classification: dict[str, Any], budget: dict[str, Any], doctor_path: str, next_command: str, reason: str) -> str:
    template = HANDOFF_TEMPLATE.read_text(encoding="utf-8") if HANDOFF_TEMPLATE.exists() else "# Iteration Budget Handoff\n"
    return template + f"""

## Filled handoff

- generated_at: {iso()}
- task_id: {row.get('id')}
- task_title: {row.get('title')}
- project: {row.get('project')}
- priority: {row.get('priority')}
- status: {row.get('status')}
- stop_reason: {reason}
- risk: {classification.get('risk')}
- execution_mode: {classification.get('execution_mode')}
- budget_action: {budget.get('action')}
- spent_tool_calls: {budget.get('spent_tool_calls')}
- effective_max_before_handoff: {budget.get('effective_max_before_handoff')}
- remaining_before_handoff: {budget.get('remaining_before_handoff')}
- doctor_artifact: {doctor_path}

## Completed gates

- [x] selected one canonical local-brain task or dispatch hint
- [x] computed bounded budget envelope
- [x] wrote durable handoff artifact
- [ ] executed task body
- [ ] verified task acceptance criteria
- [ ] marked task done with structured evidence

## Next bounded command

```bash
{next_command}
```

## Resume prompt

Resume task `{row.get('id')}` from this handoff. Reconcile task pool first, claim before execution, stop before budget exhaustion, and either write a new handoff or mark done/retry with structured proof.
"""


def write_artifact(payload: dict[str, Any], handoff_text: str) -> tuple[Path, Path]:
    stamp = datetime.now(TZ).strftime("%Y%m%d-%H%M%S")
    task_id = str((payload.get("task") or {}).get("id") or "no-task")
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in task_id)[:80]
    run_dir = ARTIFACT_DIR / f"{stamp}-{safe}"
    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / "budget_tick.json"
    md_path = run_dir / "handoff.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(handoff_text, encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a bounded local-brain task execution tick")
    parser.add_argument("--task", default="", help="Task id; default uses dispatch-dry-run next task")
    parser.add_argument("--actor", default="hermes-budget-runner")
    parser.add_argument("--execution-mode", default="auto", choices=["auto", *sorted(LOW_RISK_MODES)])
    parser.add_argument("--spent-tool-calls", type=int, default=0)
    parser.add_argument("--max-tool-calls", type=int, default=DEFAULT_MAX_TOOL_CALLS)
    parser.add_argument("--safety-margin", type=int, default=DEFAULT_SAFETY_MARGIN)
    parser.add_argument("--apply-claim-dry-run", action="store_true", help="Validate claim command shape only; does not mutate task")
    parser.add_argument("--json", action="store_true", help="Retained for consistency; output is always JSON")
    args = parser.parse_args()

    doctor_data = doctor()
    row = default_task_row(args.task or None)
    if not row:
        payload = {"schema": "hermes_iteration_budget_tick_v1", "status": "NO_TASK", "generated_at": iso(), "doctor": doctor_data}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    classification = classify_mode(row, args.execution_mode)
    budget = compute_budget(doctor_data, args.spent_tool_calls, args.max_tool_calls, args.safety_margin)
    reason = budget["action"] if classification["allowed_for_auto_claim"] else "manual_or_high_risk_gate"
    next_command = f"python3 ~/.hermes/scripts/brain_task_orchestrator.py claim {row.get('id')} --actor {args.actor} --ttl-minutes 60 --json"

    payload: dict[str, Any] = {
        "schema": "hermes_iteration_budget_tick_v1",
        "status": "OK",
        "generated_at": iso(),
        "task": row,
        "classification": classification,
        "budget": budget,
        "next_command": next_command,
        "mutation_policy": "no task mutation by default; claim/done/retry must be explicit and proof-gated",
        "doctor_summary": {
            "budget": doctor_data.get("budget"),
            "warning_hit_count": ((doctor_data.get("recent_iteration_budget_warnings") or {}).get("hit_count") if isinstance(doctor_data, dict) else None),
            "advisories": doctor_data.get("advisories") if isinstance(doctor_data, dict) else [],
        },
    }
    # Temporarily include doctor payload so the JSON artifact is self-contained.
    payload["doctor"] = doctor_data
    handoff = render_handoff(row, classification, budget, "embedded:budget_tick.json", next_command, reason)
    json_path, md_path = write_artifact(payload, handoff)
    payload.pop("doctor", None)
    payload["artifact"] = {"json": str(json_path), "handoff": str(md_path)}
    payload["handoff_required"] = budget["action"] != "proceed_bounded" or not classification["allowed_for_auto_claim"]
    payload["p10_gate"] = "PASS" if payload["artifact"] and classification["execution_mode"] else "FAIL"
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["p10_gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
