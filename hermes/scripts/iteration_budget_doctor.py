#!/usr/bin/env python3
"""Hermes iteration-budget doctor.

Read-only diagnostic for automation runs that may hit:
`Iteration budget reached (N/N) — response may be incomplete`.

It emits compact JSON and never prints secret values. `.env` is inspected only for
selected key presence.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WARNING_RE = re.compile(r"Iteration budget reached\s*\((\d+)/(\d+)\)", re.I)
SECRET_FILE_NAMES = {".env", "auth.json", "credentials.json", "token.json"}
MAX_SCAN_BYTES = 2_000_000
DEFAULT_LOG_GLOBS = [
    "logs/**/*.log",
    "logs/**/*.jsonl",
    "logs/**/*.txt",
    "sessions/session_*.json",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser().resolve()


def brain_vault() -> Path:
    return Path(
        os.environ.get(
            "HERMES_BRAIN_VAULT",
            os.environ.get("OBSIDIAN_VAULT_PATH", str(Path.home() / "Documents" / "brain")),
        )
    ).expanduser().resolve()


def load_yamlish_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        # Minimal fallback for the few keys we need.
        data: dict[str, Any] = {}
        stack: list[tuple[int, dict[str, Any]]] = [(-1, data)]
        for raw in text.splitlines():
            if not raw.strip() or raw.lstrip().startswith("#") or ":" not in raw:
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            key, value = raw.strip().split(":", 1)
            while stack and indent <= stack[-1][0]:
                stack.pop()
            parent = stack[-1][1]
            value = value.strip()
            if not value:
                child: dict[str, Any] = {}
                parent[key] = child
                stack.append((indent, child))
            else:
                lowered = value.lower()
                if lowered in {"true", "false"}:
                    parent[key] = lowered == "true"
                else:
                    try:
                        parent[key] = int(value)
                    except ValueError:
                        parent[key] = value.strip('"\'')
        return data


def get_nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def env_presence(home: Path) -> dict[str, Any]:
    keys = {
        "HERMES_MAX_ITERATIONS",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "TELEGRAM_BOT_TOKEN",
    }
    out = {k: {"present": k in os.environ, "source": "process" if k in os.environ else None} for k in keys}
    env_path = home / ".env"
    if env_path.exists():
        try:
            for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key = line.split("=", 1)[0].strip()
                if key in out and not out[key]["present"]:
                    out[key] = {"present": True, "source": str(env_path)}
        except Exception as exc:
            out[".env_read_error"] = {"present": False, "error_type": type(exc).__name__}
    return out


def scan_warning_hits(home: Path, max_files: int, max_hits: int) -> dict[str, Any]:
    files: list[Path] = []
    for pat in DEFAULT_LOG_GLOBS:
        files.extend(home.glob(pat))
    files = sorted({p for p in files if p.is_file()}, key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)[:max_files]
    hits: list[dict[str, Any]] = []
    scanned = 0
    for path in files:
        if path.name in SECRET_FILE_NAMES:
            continue
        try:
            raw = path.read_bytes()[:MAX_SCAN_BYTES]
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            continue
        scanned += 1
        for match in WARNING_RE.finditer(text):
            # Do not emit surrounding transcript/log text: sessions and logs may
            # contain user data or credentials. Path + counters are enough to
            # drive the budget policy without copying secrets into artifacts.
            hits.append(
                {
                    "path": str(path),
                    "mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
                    "used": int(match.group(1)),
                    "limit": int(match.group(2)),
                    "source_kind": "session" if path.name.startswith("session_") else "log",
                }
            )
            if len(hits) >= max_hits:
                return {"scanned_files": scanned, "hit_count": len(hits), "hits": hits}
    return {"scanned_files": scanned, "hit_count": len(hits), "hits": hits}


def cron_summary(home: Path) -> dict[str, Any]:
    jobs_path = home / "cron" / "jobs.json"
    if not jobs_path.exists():
        return {"jobs_path": str(jobs_path), "job_count": 0, "jobs": [], "agent_job_count": 0, "script_first_count": 0, "no_agent_count": 0}
    try:
        data = json.loads(jobs_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"jobs_path": str(jobs_path), "error": type(exc).__name__}
    jobs = data.get("jobs") if isinstance(data, dict) else []
    rows = []
    for job in jobs if isinstance(jobs, list) else []:
        if not isinstance(job, dict):
            continue
        no_agent = bool(job.get("no_agent"))
        script = job.get("script") or ""
        has_prompt = bool((job.get("prompt") or "").strip())
        risk_flags: list[str] = []
        if not no_agent and has_prompt:
            risk_flags.append("llm_loop")
        if script and has_prompt and not no_agent:
            risk_flags.append("script_plus_summarizer")
        if not script and not no_agent:
            risk_flags.append("agent_only")
        rows.append(
            {
                "id": job.get("id"),
                "name": job.get("name"),
                "enabled": bool(job.get("enabled")),
                "state": job.get("state"),
                "no_agent": no_agent,
                "script": script,
                "has_prompt": has_prompt,
                "last_status": job.get("last_status"),
                "risk_flags": risk_flags,
            }
        )
    return {
        "jobs_path": str(jobs_path),
        "job_count": len(rows),
        "agent_job_count": sum(1 for r in rows if not r["no_agent"] and r["has_prompt"]),
        "script_first_count": sum(1 for r in rows if r["script"]),
        "no_agent_count": sum(1 for r in rows if r["no_agent"]),
        "jobs": rows,
    }


def task_pool_summary(home: Path, vault: Path) -> dict[str, Any]:
    script = home / "scripts" / "brain_task_orchestrator.py"
    if not script.exists() or not vault.exists():
        return {"available": False, "reason": "missing_script_or_vault", "script": str(script), "vault": str(vault)}
    env = dict(os.environ)
    env["HERMES_BRAIN_VAULT"] = str(vault)
    try:
        proc = subprocess.run([sys.executable, str(script), "list", "--json"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, env=env, check=False)
    except Exception as exc:
        return {"available": False, "reason": type(exc).__name__}
    if proc.returncode != 0:
        return {"available": False, "returncode": proc.returncode, "stderr": proc.stderr[-1000:]}
    try:
        data = json.loads(proc.stdout)
    except Exception as exc:
        return {"available": False, "reason": "json_parse_error", "error_type": type(exc).__name__}
    rows = data.get("rows") or []
    at_risk = []
    for row in rows:
        text = " ".join(str(row.get(k, "")) for k in ["title", "project", "concepts", "workflow_contract"]).lower()
        flags = []
        if any(x in text for x in ["idle", "runner", "自动", "agent", "budget", "cron", "多模型"]):
            flags.append("automation_or_budget_related")
        if row.get("status") in {"running", "claimed", "retry"}:
            flags.append("state_transition_sensitive")
        if flags:
            at_risk.append({k: row.get(k) for k in ["id", "title", "status", "priority", "project", "score", "dispatchable"]} | {"risk_flags": flags})
    return {"available": True, "task_count": data.get("task_count"), "active_count": data.get("active_count"), "at_risk_count": len(at_risk), "at_risk_tasks": at_risk[:20]}


def build_advisories(config: dict[str, Any], warnings: dict[str, Any], cron: dict[str, Any], tasks: dict[str, Any]) -> list[dict[str, str]]:
    advisories: list[dict[str, str]] = []
    agent_max = get_nested(config, "agent", "max_turns")
    if agent_max is None:
        advisories.append({"severity": "medium", "code": "missing_agent_max_turns", "message": "agent.max_turns is not explicitly configured."})
    if warnings.get("hit_count"):
        advisories.append({"severity": "high", "code": "recent_iteration_budget_hits", "message": f"Found {warnings['hit_count']} iteration-budget warning hit(s) in recent logs/sessions."})
    if cron.get("agent_job_count", 0) > cron.get("no_agent_count", 0):
        advisories.append({"severity": "medium", "code": "many_agent_cron_jobs", "message": "More cron jobs use LLM prompts than no_agent deterministic mode; prefer script-first/no_agent for control-plane jobs."})
    if tasks.get("at_risk_count", 0):
        advisories.append({"severity": "medium", "code": "automation_related_tasks", "message": f"{tasks['at_risk_count']} active task-pool items mention automation/budget/agent topics; require bounded tick and proof gates."})
    if not advisories:
        advisories.append({"severity": "info", "code": "no_budget_smell_detected", "message": "No immediate iteration-budget warning was found in recent logs; keep bounded handoff policy."})
    return advisories


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Hermes iteration-budget doctor")
    parser.add_argument("--home", default=str(hermes_home()))
    parser.add_argument("--vault", default=str(brain_vault()))
    parser.add_argument("--max-log-files", type=int, default=80)
    parser.add_argument("--max-hits", type=int, default=20)
    parser.add_argument("--json", action="store_true", help="Retained for consistency; output is always JSON")
    args = parser.parse_args()

    home = Path(args.home).expanduser().resolve()
    vault = Path(args.vault).expanduser().resolve()
    config = load_yamlish_config(home / "config.yaml")
    warnings = scan_warning_hits(home, args.max_log_files, args.max_hits)
    cron = cron_summary(home)
    tasks = task_pool_summary(home, vault)

    budget = {
        "agent_max_turns": get_nested(config, "agent", "max_turns"),
        "legacy_root_max_turns": config.get("max_turns"),
        "delegation_max_iterations": get_nested(config, "delegation", "max_iterations"),
        "compression_enabled": get_nested(config, "compression", "enabled"),
        "compression_threshold": get_nested(config, "compression", "threshold"),
        "process_env_HERMES_MAX_ITERATIONS_present": "HERMES_MAX_ITERATIONS" in os.environ,
    }
    result = {
        "schema": "hermes_iteration_budget_doctor_v1",
        "status": "OK",
        "generated_at": utc_now(),
        "home": str(home),
        "vault": str(vault),
        "budget": budget,
        "env_presence": env_presence(home),
        "recent_iteration_budget_warnings": warnings,
        "cron": cron,
        "task_pool": tasks,
        "advisories": build_advisories(config, warnings, cron, tasks),
        "secret_policy": "secret files are not printed; .env values are never emitted",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
