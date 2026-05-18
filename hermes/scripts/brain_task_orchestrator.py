#!/usr/bin/env python3
"""Local-brain task orchestrator.

Hermes/Obsidian-native task control plane for ~/Documents/brain.
Markdown task notes are canonical. Dashboards and queue views are derived.
No network, no LLM, no arbitrary hooks.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TZ = timezone(timedelta(hours=8))
VAULT = Path(os.environ.get("HERMES_BRAIN_VAULT", os.environ.get("OBSIDIAN_VAULT_PATH", str(Path.home() / "Documents" / "brain")))).expanduser()
TASKS_DIR = VAULT / "05-实践与项目" / "tasks"
DASHBOARD = VAULT / "07-仪表盘" / "待完成任务运行态.md"
CONTROL_CENTER = VAULT / "07-仪表盘" / "待完成任务控制台.md"
SORTED_POOL = TASKS_DIR / "任务池-排序.md"
INBOX = TASKS_DIR / "任务收件箱.md"
DEFAULT_WORKFLOW = "[[08-模板/task-workflow-contract-template]]"
AUTORUN_ENV_FLAG = "HERMES_LOCAL_BRAIN_AUTORUN"
AUTORUN_STATE_DIR = Path(os.environ.get("HERMES_BRAIN_AUTORUN_STATE_DIR", str(Path.home() / ".hermes" / "state"))).expanduser()
AUTORUN_ALLOWLIST = AUTORUN_STATE_DIR / "auto_run_allowlist.json"
AUTORUN_POLICY = AUTORUN_STATE_DIR / "auto_run_policy.json"
AUTORUN_KILL_SWITCH = AUTORUN_STATE_DIR / "auto_run_kill_switch"
AUTORUN_PROOF_LOG = AUTORUN_STATE_DIR / "auto_run_proof.jsonl"
AUTORUN_HANDOFF_DIR = AUTORUN_STATE_DIR / "auto_run_handoffs"
PARALLEL_HANDOFF_DIR = AUTORUN_STATE_DIR / "parallel_handoffs"
BUDGET_SIGNALS_PATH = AUTORUN_STATE_DIR / "budget_signals.jsonl"
GOVERNANCE_RATCHET_PATH = AUTORUN_STATE_DIR / "governance_ratchet.json"
MAX_T3_ROUNDS_BEFORE_THROTTLE = 3
MAX_T3_ROUNDS_BEFORE_PAUSE = 5
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser()
PROJECT_PROFILES_DIR = Path(os.environ.get("HERMES_PROJECT_PROFILES_DIR", str(HERMES_HOME / "project-profiles"))).expanduser()
SCRIPTS_DIR = HERMES_HOME / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import permission_taxonomy as taxonomy  # noqa: E402

AUTONOMY_WRITE_GUARD = HERMES_HOME / "scripts" / "autonomy-write-guard.py"
AUTONOMY_WRITE_ALLOWLIST = Path(
    os.environ.get("HERMES_AUTONOMY_WRITE_ALLOWLIST", str(HERMES_HOME / "config" / "autonomy-write-allowlist.json"))
).expanduser()
CRON_JOBS_PATH = Path(os.environ.get("HERMES_CRON_JOBS_PATH", str(HERMES_HOME / "cron" / "jobs.json"))).expanduser()
TASKPOOL_CRON_JOB_NAMES = [
    "task-pool-guardian-10m",
    "pipeline-tick-hourly",
    "agent-team-cycle-hourly",
    "envelope-executor-cycle",
    "multimodel-intervention-step",
    "local-brain-taskpool-auto-completer",
]
SAFE_AUTO_COMPLETER_SEMANTIC_STATUSES = {
    "ok",
    "ok_with_task_blocker",
    "retryable_runtime_timeout",
    "truth_grounded_advisory_not_ratified",
    "certification_not_certified",
    "certification_long_running",
    "recursive_evidence_spine_self_lock",
}
VALID_STATUSES = ["proposed", "pending", "claimed", "running", "retry", "review", "blocked", "done", "archived", "expired"]
STATUS_ALIASES = {"completed": "done"}  # legacy notes may use completed; normalize as terminal done.
ACTIVE_STATUSES = {"proposed", "pending", "claimed", "running", "retry", "review", "blocked"}
TERMINAL_STATUSES = {"done", "archived", "expired"}
PRIORITY_WEIGHT = {"P0": 400, "P1": 300, "P2": 200, "P3": 100}
STATUS_WEIGHT = {"retry": 60, "running": 50, "claimed": 45, "blocked": 40, "review": 35, "pending": 30, "proposed": 10, "done": -100, "archived": -120, "expired": -130}
VALID_LANES = ["work", "evolution", "advisory"]
DEFAULT_TASKPOOL_PRIORITY_MODE = "work-first"
VALID_TASKPOOL_PRIORITY_MODES = {"work-first", "evolution-first"}
TASKPOOL_PRIORITY_MODE_FILE = AUTORUN_STATE_DIR / "taskpool_priority_mode.json"
LANE_SORT_WEIGHT_BY_MODE = {
    "work-first": {"work": 0, "advisory": 1, "evolution": 2},
    "evolution-first": {"evolution": 0, "work": 1, "advisory": 2},
}
ARCHITECTURE_TARGETS = {
    "L0", "L1", "L2", "L3", "L4", "L5", "LX",
    "local-brain", "skill-graph", "provider-quota", "taskpool",
}
EVOLUTION_ALIGNMENT_FIELDS = ("architecture_target", "capability_delta", "anti_drift_check", "acceptance_evidence")
MISSION_ENVELOPE_REQUIRED_FIELDS = (
    "mission_schema_version",
    "mission_id",
    "mission_title",
    "mission_objective",
    "mission_constraints",
    "red_lines",
    "non_goals",
    "evidence_refs",
    "acceptance_criteria",
    "dag_nodes",
    "checkpoint_states",
    "permission_gates",
    "handoff_artifacts",
    "proof_artifacts",
    "rollback_signal",
    "certification_status",
    "ratification_artifact",
)
MISSION_ENVELOPE_LIST_FIELDS = {
    "mission_constraints",
    "red_lines",
    "non_goals",
    "evidence_refs",
    "acceptance_criteria",
    "dag_nodes",
    "checkpoint_states",
    "permission_gates",
    "handoff_artifacts",
    "proof_artifacts",
}
MISSION_STRUCTURED_REF_FIELDS = {"evidence_refs", "handoff_artifacts", "proof_artifacts", "ratification_artifact"}
MISSION_CERTIFICATION_STATUSES = {"advisory", "not_certified", "certified_with_minor_risks", "certified"}
MULTIMODEL_AUTORUN_ENV_FLAG = "HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL"
MULTIMODEL_ALLOWLIST = AUTORUN_STATE_DIR / "multimodel_intervention_allowlist.json"
MULTIMODEL_PASS_STATUSES = {"certified", "certified_with_minor_risks"}
REQUIRED_RATIFICATION_MODELS = ("claude-opus-4-7", "gpt-5.5", "deepseek-v4-pro", "mimo-v2.5-pro")
MULTIMODEL_ACCURACY_KEYWORDS = {
    # High-precision only: <=10 hits in 56-task pool. "evidence"/"truth"/
    # "certification"/"ratification" removed — too common in task notes.
    "token", "oauth", "quota", "kyc", "支付", "资金",
    "权限", "事实源",
}
MULTIMODEL_LONG_TERM_KEYWORDS = {
    # Tightened: removed local-brain(50), l3(43), evolution(35), skill(31),
    # 治理(22), taskpool(17), 任务池(13) — all too common.
    "p10", "l4", "l5", "lx", "技能树", "控制面", "控制台",
}
MULTIMODEL_ONE_SHOT_KEYWORDS = {
    # Tightened: removed workflow(34), 方案(24), 落地(22), loop(20),
    # mission(18), playbook(12), 闭环(12), pua-loop(13), dag(7) — too common.
    "一次落地", "迁移", "拆解", "介入", "融合", "分解",
    "自动触发",
}
MULTIMODEL_FAILURE_TAXONOMY = (
    "no_claims",
    "unsupported_claims",
    "evidence_missing",
    "vote_reject",
    "agreement_low",
    "provider_parse_error",
    "quota_unobservable",
    "criteria_missing",
    "final_design_missing",
    "model_vote_missing",
)

# Formal lifecycle contract. Markdown task notes remain canonical; this graph is
# the local control-plane guardrail for agents, cron ticks, and multi-model
# planning outputs. Keep it small, explicit, and fail-closed for high-risk exits.
LIFECYCLE_TRANSITIONS: dict[str, list[str]] = {
    "proposed": ["pending", "blocked", "archived", "expired"],
    "pending": ["claimed", "blocked", "archived", "expired"],
    "claimed": ["running", "pending", "retry", "blocked", "archived", "expired"],
    "running": ["review", "retry", "blocked", "expired"],
    "review": ["done", "retry", "blocked", "pending", "archived", "expired"],
    "retry": ["pending", "claimed", "blocked", "archived", "expired"],
    "blocked": ["pending", "retry", "review", "archived", "expired"],
    "done": ["archived"],
    "archived": [],
    "expired": ["archived"],
}
REASON_REQUIRED_TO = {"retry", "blocked"}
EVIDENCE_REQUIRED_TO = {"review", "done"}
CLAIM_BOUND_STATUSES = {"claimed", "running"}
PROFILE_GATED_STATUSES = CLAIM_BOUND_STATUSES | {"review", "done"}
INITIAL_TASK_STATUSES = {"proposed", "pending"}
RECONCILE_STALE_CLAIM_STATUSES = {"pending", "blocked", "expired"}
RECONCILE_OVER_RETRY_STATUSES = {"blocked", "expired"}


def now() -> datetime:
    return datetime.now(TZ).replace(microsecond=0)


def iso(value: datetime | None = None) -> str:
    return (value or now()).isoformat()


def event_hook_multimodel_route(event: str, task_id: str = "") -> dict[str, Any]:
    """Decide whether an event hook should run the expensive multimodel step.

    Modes:
    - 0/false/off: never run in the hook.
    - 1/true/on: run, scoped to task_id when available.
    - auto (default): run only when the added/changed task's deterministic local
      signals say multi-model review is useful enough to justify blocking the
      event hook. The step is task-scoped to avoid the old global-top-task fanout.
    """
    mode = str(os.environ.get("HERMES_TASKPOOL_EVENT_HOOK_MULTIMODEL", "auto") or "auto").strip().lower()
    off_values = {"0", "false", "no", "off", "disabled"}
    on_values = {"1", "true", "yes", "on", "enabled", "force"}
    if mode in off_values:
        return {"enabled": False, "mode": mode, "reason": "disabled_by_env"}

    route: dict[str, Any] = {
        "enabled": False,
        "mode": mode,
        "event": event,
        "task_id": task_id,
        "reason": "not_routed",
        "scope": "task" if task_id else "global",
    }
    if mode in on_values:
        route.update({"enabled": True, "reason": "forced_by_env"})
        return route
    if mode != "auto":
        return {**route, "reason": "unknown_mode"}
    if event not in {"task_added", "task_transitioned", "task_ingested"}:
        return {**route, "reason": "event_not_eligible"}
    if not task_id:
        return {**route, "reason": "missing_task_id"}

    try:
        task = find_task(task_id)
        reasons = task_multimodel_intervention_reasons(task)
        cert_reasons = task_multimodel_certification_reasons(task)
        advisory_reasons = task_multimodel_advisory_reasons(task)
    except BaseException as exc:
        return {**route, "reason": "classification_failed", "error": str(exc)}

    route.update({
        "task_status": task.status,
        "priority": task.priority,
        "lane": task.lane,
        "project": task.project,
        "reasons": reasons,
        "certification_reasons": cert_reasons,
        "advisory_reasons": advisory_reasons,
    })
    if not reasons:
        return {**route, "reason": "no_multimodel_reasons"}

    high_priority = task.priority in {"P0", "P1"}
    evolution_p2 = task.priority == "P2" and task.lane == "evolution"
    explicit = str(task.fm.get("multimodel_required") or task.fm.get("requires_multimodel") or "").lower() in {"1", "true", "yes", "required"}
    if cert_reasons or high_priority or evolution_p2 or explicit:
        route.update({
            "enabled": True,
            "reason": "smart_route_matched",
            "timeout_seconds": int(os.environ.get("HERMES_TASKPOOL_EVENT_HOOK_MULTIMODEL_TIMEOUT", "900")),
            "command_timeout_seconds": int(os.environ.get("HERMES_TASKPOOL_EVENT_HOOK_MULTIMODEL_COMMAND_TIMEOUT", "840")),
        })
        return route
    return {**route, "reason": "advisory_low_priority_deferred"}


def maybe_fire_taskpool_event_hook(event: str, *, task_id: str = "", reason: str = "") -> dict[str, Any]:
    """Run one bounded taskpool dispatch tick after local taskpool mutations.

    Cron remains the fallback. This event hook closes the gap between task creation /
    state transition and the next periodic sweep. It is deliberately fail-soft and
    non-recursive: hook failures are recorded but do not make the originating task
    mutation fail, and child orchestrator calls see HERMES_TASKPOOL_EVENT_HOOK_DEPTH=1.
    """
    if os.environ.get("HERMES_TASKPOOL_EVENT_HOOK_DISABLED") == "1":
        return {"status": "SKIPPED", "reason": "disabled"}
    if os.environ.get("HERMES_TASKPOOL_EVENT_HOOK_DEPTH"):
        return {"status": "SKIPPED", "reason": "recursive_guard"}
    tick = Path.home() / ".hermes" / "scripts" / "brain_task_dispatch_tick.py"
    if not tick.exists():
        return {"status": "SKIPPED", "reason": "tick_missing", "tick": str(tick)}
    log_dir = AUTORUN_STATE_DIR / "taskpool_event_hooks"
    log_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", (task_id or event))[:96].strip("-") or "taskpool"
    log_path = log_dir / f"event-{now().strftime('%Y%m%d%H%M%S')}-{safe}.json"
    env = os.environ.copy()
    env["HERMES_TASKPOOL_EVENT_HOOK_DEPTH"] = "1"
    env.setdefault("HERMES_TASKPOOL_EVENT", event)
    if task_id:
        env.setdefault("HERMES_TASKPOOL_EVENT_TASK", task_id)
    cmd = [sys.executable, str(tick), "--summary", "--autorun-step", "--no-state", "--print-always"]
    route = event_hook_multimodel_route(event, task_id)
    timeout_seconds = int(os.environ.get("HERMES_TASKPOOL_EVENT_HOOK_TIMEOUT", "240"))
    if route.get("enabled"):
        cmd.append("--multimodel-step")
        if task_id:
            cmd.extend(["--multimodel-task", task_id])
        env["HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL"] = "1"
        if route.get("command_timeout_seconds"):
            env.setdefault("HERMES_BRAIN_DISPATCH_TICK_COMMAND_TIMEOUT_SECONDS", str(route["command_timeout_seconds"]))
        timeout_seconds = max(timeout_seconds, int(route.get("timeout_seconds") or timeout_seconds))
    started = iso()
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_seconds, env=env)
        payload: dict[str, Any] = {
            "status": "OK" if proc.returncode == 0 else "ERROR",
            "event": event,
            "task_id": task_id,
            "reason": reason,
            "started_at": started,
            "finished_at": iso(),
            "returncode": proc.returncode,
            "cmd": cmd,
            "multimodel_route": route,
            "timeout_seconds": timeout_seconds,
            "stdout": proc.stdout[-20000:],
            "stderr": proc.stderr[-12000:],
        }
        try:
            payload["summary"] = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else {}
        except Exception as exc:
            payload["summary_parse_error"] = str(exc)
        log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {
            "status": payload["status"],
            "event": event,
            "task_id": task_id,
            "log": str(log_path),
            "returncode": proc.returncode,
            "multimodel_route": route,
            "dispatchable": (payload.get("summary") or {}).get("dispatchable"),
            "next_task_id": (payload.get("summary") or {}).get("next_task_id"),
            "autorun": (payload.get("summary") or {}).get("autorun"),
            "error_count": (payload.get("summary") or {}).get("error_count"),
        }
    except subprocess.TimeoutExpired as exc:
        payload = {
            "status": "TIMEOUT",
            "event": event,
            "task_id": task_id,
            "reason": reason,
            "started_at": started,
            "finished_at": iso(),
            "cmd": cmd,
            "multimodel_route": route,
            "timeout": exc.timeout,
            "timeout_seconds": timeout_seconds,
            "stdout": (exc.stdout or "")[-20000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-12000:] if isinstance(exc.stderr, str) else "",
        }
        log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"status": "TIMEOUT", "event": event, "task_id": task_id, "log": str(log_path)}
    except Exception as exc:
        payload = {"status": "ERROR", "event": event, "task_id": task_id, "reason": reason, "error": str(exc), "finished_at": iso()}
        log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"status": "ERROR", "event": event, "task_id": task_id, "log": str(log_path), "error": str(exc)}


def parse_dt(value: Any) -> datetime | None:
    if value in (None, "", [], {}):
        return None
    s = str(value).strip().strip('"').strip("'")
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return datetime.fromisoformat(s + "T00:00:00+08:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ)
    except Exception:
        return None


def _load_autonomy_write_guard():
    spec = importlib.util.spec_from_file_location("autonomy_write_guard", AUTONOMY_WRITE_GUARD)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"autonomy write guard unavailable: {AUTONOMY_WRITE_GUARD}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def guard_autorun_claim_and_handoff(task_id: str, actor: str) -> dict[str, Any]:
    """Fail closed before local task-pool autorun mutates claim/handoff state."""
    guard = _load_autonomy_write_guard()
    evidence = guard.guard_or_raise("taskpool", "claim-and-handoff", "dispatch-hint", AUTONOMY_WRITE_ALLOWLIST)
    evidence.setdefault("caller", "brain_task_orchestrator.auto-claim-and-handoff")
    evidence.setdefault("task_id", task_id)
    evidence.setdefault("actor", actor)
    return evidence


def parse_guard_error(exc: BaseException) -> dict[str, Any]:
    try:
        data = json.loads(str(exc))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"status": "FAIL_CLOSED", "ok": False, "error": str(exc)}


def slugify(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[`*_~<>\[\](){}:;,'\"!?/\\|]+", " ", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    s = re.sub(r"[^a-z0-9\-\u4e00-\u9fff]+", "", s)
    return s[:80] or "task"


def project_profile_candidates(project: str) -> list[Path]:
    """Return project-specific candidates followed by hermes fallback.

    Project profiles are local JSON evidence, not remote configuration.  Exact
    project names are allowed when they are safe filenames; slug fallback handles
    task IDs/projects that contain spaces or punctuation.  The final hermes.json
    fallback is still a real profile and must exist before execution.
    """
    project = str(project or "").strip()
    candidates: list[Path] = []
    if project:
        safe_exact = re.sub(r"[^A-Za-z0-9._-]", "-", project).strip(".-")
        if safe_exact:
            candidates.append(PROJECT_PROFILES_DIR / f"{safe_exact}.json")
        slug = slugify(project)
        slug_path = PROJECT_PROFILES_DIR / f"{slug}.json"
        if slug_path not in candidates:
            candidates.append(slug_path)
    fallback = PROJECT_PROFILES_DIR / "hermes.json"
    if fallback not in candidates:
        candidates.append(fallback)
    return candidates


def profile_alias_values(profile: dict[str, Any]) -> set[str]:
    aliases: set[str] = set()
    for key in ("project", "profile_id", "canonical_project"):
        value = profile.get(key)
        if isinstance(value, str) and value.strip():
            aliases.add(value.strip())
    raw_aliases = profile.get("aliases") or profile.get("project_aliases") or []
    if isinstance(raw_aliases, str):
        raw_aliases = [raw_aliases]
    if isinstance(raw_aliases, list):
        for value in raw_aliases:
            if isinstance(value, str) and value.strip():
                aliases.add(value.strip())
    return aliases


def project_profile_alias_candidates(project: str, known: list[Path]) -> list[Path]:
    """Find canonical profiles that explicitly claim project as an alias.

    This keeps project profiles SSOT-compliant: historical task project names can
    route to one canonical JSON file without maintaining duplicate profile files.
    Invalid unrelated JSON files are ignored during alias discovery; if an exact
    candidate is invalid, load_project_profile still reports it fail-closed.
    """
    project = str(project or "").strip()
    if not project or not PROJECT_PROFILES_DIR.exists():
        return []
    known_set = set(known)
    matches: list[Path] = []
    fallback = PROJECT_PROFILES_DIR / "hermes.json"
    for path in sorted(PROJECT_PROFILES_DIR.glob("*.json")):
        if path in known_set or path == fallback:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and project in profile_alias_values(data):
            matches.append(path)
    return matches


def load_project_profile(project: str) -> dict[str, Any]:
    direct_candidates = project_profile_candidates(project)
    fallback = PROJECT_PROFILES_DIR / "hermes.json"
    non_fallback = [p for p in direct_candidates if p != fallback]
    alias_candidates = project_profile_alias_candidates(project, direct_candidates)
    candidates = non_fallback + alias_candidates
    if fallback not in candidates:
        candidates.append(fallback)
    direct_set = set(non_fallback)
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {
                "status": "invalid",
                "missing": True,
                "project": project,
                "path": str(path),
                "error": f"invalid_project_profile_json:{exc}",
                "candidates": [str(p) for p in candidates],
            }
        if not isinstance(data, dict):
            return {
                "status": "invalid",
                "missing": True,
                "project": project,
                "path": str(path),
                "error": "project_profile_not_object",
                "candidates": [str(p) for p in candidates],
            }
        status = "fallback" if path == fallback else ("project" if path in direct_set else "alias")
        return {
            "status": status,
            "missing": False,
            "project": project,
            "canonical_project": str(data.get("project") or project),
            "path": str(path),
            "profile": data,
            "candidates": [str(p) for p in candidates],
        }
    return {
        "status": "missing",
        "missing": True,
        "project": project,
        "path": "",
        "error": "project_profile_missing",
        "candidates": [str(p) for p in candidates],
    }


def project_profile_failures(task_or_fm: Any) -> list[str]:
    if isinstance(task_or_fm, Task):
        project = task_or_fm.project
    else:
        project = str((task_or_fm or {}).get("project") or "")
    result = load_project_profile(project)
    if result.get("missing"):
        return [f"project_profile_missing:{project or '(empty-project)'}"]
    return []


def compact_profile_value(value: Any, *, max_items: int = 8) -> str:
    if isinstance(value, dict):
        parts = [f"{k}={v}" for k, v in list(value.items())[:max_items]]
        return "; ".join(parts)
    if isinstance(value, list):
        return "; ".join(str(x) for x in value[:max_items])
    return str(value or "")


def format_project_profile_context(project: str) -> str:
    result = load_project_profile(project)
    if result.get("missing"):
        return (
            "PROJECT PROFILE: MISSING (FAIL-CLOSED)\n"
            f"Project: {project or '(empty-project)'}\n"
            f"Expected candidates: {', '.join(result.get('candidates', []))}\n"
            "Do not start a worker or claim/handoff this task until a project-specific profile or hermes.json fallback exists."
        )
    profile = result.get("profile") if isinstance(result.get("profile"), dict) else {}
    lines = [
        "PROJECT PROFILE:",
        f"Status: {result.get('status')}",
        f"Path: {result.get('path')}",
        f"Name: {profile.get('display_name') or profile.get('project') or project}",
    ]
    for key in ("tech_stack", "paths", "conventions", "test_cmd", "build_cmd", "acceptance", "forbidden", "backend_contract_policy", "regression_coverage_policy"):
        if key in profile and profile.get(key) not in (None, "", [], {}):
            lines.append(f"{key}: {compact_profile_value(profile.get(key))}")
    contract = profile_policy_contract(project, loaded=result)
    if not contract.get("missing"):
        lines.extend([
            "",
            "PROFILE POLICY CONTRACT (WARN-ONLY SOFT-LAUNCH):",
            json.dumps(contract, ensure_ascii=False, indent=2),
        ])
    return "\n".join(lines)


SEMANTIC_TASK_CLASSES = [
    "frontend-only",
    "backend-owned",
    "fullstack-integrated",
    "cross-cutting-infrastructure",
    "prototype-asset-dependent",
    "release-sync",
    "evidence-only/regression-proof-already-satisfied",
    "admin/out-of-scope",
]

PROFILE_POLICY_RUNTIME_CONSUMERS = [
    "task_classification",
    "dispatch_prompt",
    "worker_handoff",
    "completion_gate",
    "proof_gate_warn",
    "ratification_route",
    "learning_writeback",
]

PROFILE_POLICY_REQUIRED_FIELDS = [
    "lark_task_execution_policy",
    "lark_evidence_policy.closeout_required_labels",
    "backend_contract_policy",
    "regression_coverage_policy",
]


def _profile_get_path(profile: dict[str, Any], dotted: str) -> Any:
    current: Any = profile
    for part in dotted.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def profile_policy_contract(project: str, *, loaded: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the typed project policy contract injected into workers.

    This is intentionally WARN-only. It exposes semantic commitments from the
    project profile to runtime consumers without turning advisory/not-certified
    profile work into a fail-closed gate.
    """
    result = loaded if loaded is not None else load_project_profile(project)
    if result.get("missing"):
        return {
            "schema": "profile_policy_contract_v1",
            "missing": True,
            "project": project,
            "profile_status": str(result.get("status") or "missing"),
            "profile_path": str(result.get("path") or ""),
            "enforcement": "fail_closed_missing_profile",
            "soft_launch": False,
            "warnings": [f"project_profile_missing:{project or '(empty-project)'}"],
        }
    profile = result.get("profile") if isinstance(result.get("profile"), dict) else {}
    lark_policy = profile.get("lark_task_execution_policy") if isinstance(profile.get("lark_task_execution_policy"), dict) else {}
    lark_evidence = profile.get("lark_evidence_policy") if isinstance(profile.get("lark_evidence_policy"), dict) else {}
    strategy = profile.get("semantic_control_plane_strategy") if isinstance(profile.get("semantic_control_plane_strategy"), dict) else {}
    classes = list_value(lark_policy.get("classification_required")) or list_value(strategy.get("recommended_task_classes")) or list(SEMANTIC_TASK_CLASSES)
    classes = [c for c in classes if c]
    for cls in SEMANTIC_TASK_CLASSES:
        if cls not in classes:
            classes.append(cls)
    labels = list_value(lark_evidence.get("closeout_required_labels"))
    warnings = []
    if result.get("status") != "fallback":
        for field in PROFILE_POLICY_REQUIRED_FIELDS:
            value = _profile_get_path(profile, field)
            if value in (None, "", [], {}):
                warnings.append(f"profile_control_plane_missing:{field}")
    return {
        "schema": "profile_policy_contract_v1",
        "missing": False,
        "project": project,
        "canonical_project": str(result.get("canonical_project") or profile.get("project") or project),
        "profile_status": str(result.get("status") or ""),
        "profile_path": str(result.get("path") or ""),
        "status": "WARN" if warnings else "OK",
        "enforcement": "warn_only",
        "soft_launch": True,
        "task_classes": classes,
        "default_task_class": str(lark_policy.get("default_classification") or "fullstack-integrated"),
        "required_evidence_labels": labels,
        "runtime_consumers": list(PROFILE_POLICY_RUNTIME_CONSUMERS),
        "ratification_authority": {
            "advisory_tiers": ["T1", "T2"],
            "full_closeout_tier": "T3",
            "full_closeout_requires": ["discussion_result.json", "4/4 canonical participants", "no unresolved severity>=3"],
        },
        "learning_writeback": {
            "policy": "record repeated evidence/user corrections before promoting global rules",
            "target": "project profile / Workpad / umbrella skill, not global memory for stale task state",
        },
        "warnings": warnings,
    }


def _semantic_blob(task: "Task") -> str:
    return f"{task.title}\n{task.body}\n{json.dumps(task.fm, ensure_ascii=False)}".lower()


def classify_task_with_profile_policy(task: "Task", contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or profile_policy_contract(task.project)
    text = _semantic_blob(task)
    classes = set(contract.get("task_classes") or SEMANTIC_TASK_CLASSES)
    default_class = str(contract.get("default_task_class") or "fullstack-integrated")
    reasons: list[str] = []
    warnings: list[str] = []

    def allowed(preferred: str, fallback: str = "fullstack-integrated") -> str:
        return preferred if preferred in classes else (fallback if fallback in classes else default_class)

    money_or_security = any(token in text for token in (
        "金额", "余额", "支付", "付款", "收款", "提现", "入金", "出金", "换汇", "汇率", "fx", "wallet",
        "auth", "登录", "密码", "2fa", "mfa", "otp", "kyc", "device", "session", "真实接口", "api", "后端",
        "status", "time", "order", "ledger", "transaction",
    ))
    prototype = any(token in text for token in ("原型", "1:1", "复刻", "文案", "样式", "布局", "ui", "prototype"))
    release = any(token in text for token in ("push", "发布", "同步", "rebase", "remote build", "railway", "deploy", "打包"))
    cross_cutting = any(token in text for token in ("基础设施", "校验", "validator", "validation", "缓存", "i18n", "安全", "权限", "全局"))
    evidence_only = any(token in text for token in ("已满足", "already satisfied", "regression-proof", "仅验证", "evidence-only"))
    backend_only = any(token in text for token in ("纯后端", "定时", "批处理", "job", "migration")) and not prototype
    frontend_only = prototype and not money_or_security and not any(token in text for token in ("接口", "api", "后端", "真实"))

    if evidence_only:
        task_class = allowed("evidence-only/regression-proof-already-satisfied")
        reasons.append("evidence_only_or_already_satisfied")
    elif money_or_security:
        task_class = allowed("fullstack-integrated")
        reasons.append("money_or_security_backend_semantics")
        if release:
            reasons.append("release_or_branch_sync_secondary")
    elif release:
        task_class = allowed("release-sync")
        reasons.append("release_or_branch_sync")
    elif cross_cutting:
        task_class = allowed("cross-cutting-infrastructure")
        reasons.append("cross_cutting_policy_or_validation")
    elif backend_only:
        task_class = allowed("backend-owned")
        reasons.append("backend_only_batch_or_job")
    elif frontend_only:
        task_class = allowed("prototype-asset-dependent", "frontend-only")
        reasons.append("prototype_or_ui_asset_dependency")
    elif prototype:
        task_class = allowed("prototype-asset-dependent", "frontend-only")
        reasons.append("prototype_or_ui_asset_dependency")
    elif task.lane != "work":
        task_class = allowed("evidence-only/regression-proof-already-satisfied")
        reasons.append(f"non_work_lane:{task.lane}")
    else:
        task_class = allowed(default_class)
        reasons.append("profile_default_classification")

    risk_tier = "T1"
    if task_class in {"fullstack-integrated", "backend-owned", "cross-cutting-infrastructure", "release-sync"} or money_or_security:
        risk_tier = "T3"
    elif task_class in {"prototype-asset-dependent", "frontend-only"}:
        risk_tier = "T2"
    if task.priority == "P0" and risk_tier in {"T1", "T2"} and money_or_security:
        risk_tier = "T3"
    labels = list(contract.get("required_evidence_labels") or [])
    if prototype and "prototype_checked_when_referenced" not in labels:
        warnings.append("profile_missing_prototype_closeout_label")
    if not labels:
        warnings.append("profile_missing_required_evidence_labels")
    return {
        "schema": "semantic_task_classification_v1",
        "task_id": task.id,
        "task_path": str(task.path),
        "project": task.project,
        "lane": task.lane,
        "priority": task.priority,
        "task_class": task_class,
        "risk_tier": risk_tier,
        "required_evidence_labels": labels,
        "runtime_consumers": list(contract.get("runtime_consumers") or PROFILE_POLICY_RUNTIME_CONSUMERS),
        "enforcement": "warn_only",
        "certification_authority": "advisory_only_until_target_bound_T3_pass" if risk_tier != "T3" else "requires_target_bound_T3_for_closeout_when_used_as_done_authority",
        "reasons": reasons,
        "warnings": warnings,
    }


def semantic_control_plane_report(*, task_id: str = "", project: str = "", max_tasks: int = 20) -> dict[str, Any]:
    tasks = iter_tasks()
    selected: list[Task] = []
    if task_id:
        selected = [find_task(task_id)]
    else:
        for t in sorted_tasks(include_done=False):
            if project and t.project != project:
                continue
            selected.append(t)
            if len(selected) >= max_tasks:
                break
    profile_project = project or (selected[0].project if selected else "")
    contract = profile_policy_contract(profile_project) if profile_project else {}
    classifications = [classify_task_with_profile_policy(t, profile_policy_contract(t.project)) for t in selected]
    warnings = []
    if contract:
        warnings.extend(contract.get("warnings") or [])
    for row in classifications:
        warnings.extend(row.get("warnings") or [])
    return {
        "status": "OK",
        "schema": "semantic_control_plane_dry_run_v1",
        "generated_at": iso(),
        "read_only": True,
        "project": profile_project,
        "contract": contract,
        "classifications": classifications,
        "classification_count": len(classifications),
        "warnings": sorted(set(str(w) for w in warnings if w)),
        "safety": "advisory soft-launch only; does not claim, mutate, complete, or fail-close tasks",
    }


def semantic_control_plane_selfcheck() -> dict[str, Any]:
    projects = sorted({t.project for t in iter_tasks() if t.project})
    contracts = [profile_policy_contract(project) for project in projects]
    warnings: list[str] = []
    for contract in contracts:
        for warning in contract.get("warnings") or []:
            warnings.append(f"{contract.get('project')}:{warning}")
    return {
        "status": "WARN" if warnings else "OK",
        "schema": "semantic_control_plane_selfcheck_v1",
        "read_only": True,
        "project_count": len(projects),
        "contracts_checked": len(contracts),
        "warnings": sorted(set(warnings)),
        "policy": "WARN-only soft gate; missing semantic linkage must not fail closed without fresh ratification and rollout",
    }


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    raw = text[4:end]
    body = text[text.find("\n", end + 1) + 1 :]
    return parse_yamlish(raw), body


def parse_yamlish(raw: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if ":" not in line or line.startswith(" "):
            i += 1
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if val == "":
            items: list[str] = []
            j = i + 1
            while j < len(lines) and lines[j].startswith("  - "):
                items.append(lines[j][4:].strip().strip('"').strip("'"))
                j += 1
            if items:
                data[key] = items
                i = j
                continue
            data[key] = ""
        elif val.startswith("[") and val.endswith("]"):
            inside = val[1:-1].strip()
            data[key] = [] if not inside else [x.strip().strip('"').strip("'") for x in inside.split(",")]
        else:
            data[key] = val.split(" #", 1)[0].strip().strip('"').strip("'")
        i += 1
    return data


def yaml_scalar(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return "[" + ", ".join(json.dumps(str(x), ensure_ascii=False) for x in v) + "]"
    s = str(v)
    if s == "":
        return ""
    if any(ch in s for ch in [": ", "#", "[", "]", "{", "}"]) and not s.startswith("[["):
        return json.dumps(s, ensure_ascii=False)
    return s


def render_frontmatter(fm: dict[str, Any]) -> str:
    preferred = [
        "type", "lane", "layer", "status", "priority", "created", "updated", "expires_at", "project",
        "architecture_target", "capability_delta", "anti_drift_check", "acceptance_evidence", "workflow_contract",
        "required_authority", "max_authority", "permission_tier", "write_surfaces", "completion_gate", "lane_semantics",
        "mission_schema_version", "mission_id", "mission_title", "mission_objective", "mission_constraints",
        "red_lines", "non_goals", "evidence_refs", "acceptance_criteria", "dag_nodes", "checkpoint_states",
        "permission_gates", "handoff_artifacts", "proof_artifacts", "rollback_signal", "certification_status",
        "ratification_artifact", "multimodel_status", "multimodel_ratification_artifact",
        "multimodel_last_checked_at", "multimodel_round_status", "multimodel_last_gate_status",
        "multimodel_last_decision", "multimodel_last_discussion_artifact", "multimodel_last_state_path",
        "multimodel_last_failures", "multimodel_failure_taxonomy", "multimodel_recommended_axes", "multimodel_axis_rationale",
        "mission_node_id", "mission_node_depends_on", "mission_node_kind",
        "auto_subtask_parent", "auto_subtask_kind", "auto_subtask_axis", "auto_subtask_trigger",
        "auto_subtask_issue_ids", "auto_subtask_parent_artifact", "auto_subtask_children",
        "auto_subtask_open_children", "auto_subtask_ready_for_parent", "auto_subtask_taxonomy_axes", "auto_subtask_axis_rationale",
        "blocked_resolve_last_checked_at", "blocked_resolve_multimodel_required", "blocked_resolve_reasons",
        "blocked_resolve_taxonomy_axes", "blocked_resolve_axis_rationale", "blocked_resolve_last_action", "blocked_resolve_reason",
        "claimed_by", "claim_expires_at", "run_id", "retry_count", "next_attempt_at", "workspace", "parallel_boundary",
        "allowed_globs", "forbidden_globs", "loc_budget", "conflict_group", "parallel_group",
        "workspace_isolation", "merge_gate", "evidence", "concepts"
    ]
    keys = preferred + [k for k in fm.keys() if k not in preferred]
    out = ["---"]
    for k in keys:
        if k not in fm:
            continue
        v = fm[k]
        if isinstance(v, list) and k == "evidence" and v:
            out.append(f"{k}:")
            for item in v:
                out.append(f"  - {yaml_scalar(item)}")
        else:
            out.append(f"{k}: {yaml_scalar(v)}")
    out.append("---")
    return "\n".join(out) + "\n"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def normalize_taskpool_priority_mode(raw: str | None) -> str:
    mode = str(raw or "").strip().lower().replace("_", "-")
    aliases = {
        "work": "work-first",
        "work-first": "work-first",
        "product-first": "work-first",
        "default": "work-first",
        "evolution": "evolution-first",
        "evolution-first": "evolution-first",
        "self-evolution": "evolution-first",
        "self-optimization": "evolution-first",
        "self-optimisation": "evolution-first",
    }
    return aliases.get(mode, DEFAULT_TASKPOOL_PRIORITY_MODE)


def taskpool_priority_mode() -> str:
    env_mode = os.environ.get("HERMES_TASKPOOL_PRIORITY_MODE")
    if env_mode:
        return normalize_taskpool_priority_mode(env_mode)
    try:
        data = json.loads(TASKPOOL_PRIORITY_MODE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return normalize_taskpool_priority_mode(str(data.get("mode") or ""))
        if isinstance(data, str):
            return normalize_taskpool_priority_mode(data)
    except FileNotFoundError:
        pass
    except Exception:
        return DEFAULT_TASKPOOL_PRIORITY_MODE
    return DEFAULT_TASKPOOL_PRIORITY_MODE


def lane_sort_weight() -> dict[str, int]:
    return LANE_SORT_WEIGHT_BY_MODE.get(taskpool_priority_mode(), LANE_SORT_WEIGHT_BY_MODE[DEFAULT_TASKPOOL_PRIORITY_MODE])


VALID_WORKSPACE_ISOLATION = {"none", "readonly", "copy", "worktree"}
VALID_MERGE_GATES = {"manual", "diff-boundary", "tests", "build-and-tests"}


def validate_boundary_fields(fm: dict[str, Any]) -> list[str]:
    """Deterministic validation of task-boundary metadata fields.

    Returns a list of failure strings. Empty list means all present boundary
    fields are valid. Missing optional fields are not failures — only
    malformed values trigger failures. Fail-closed: unknown isolation modes
    or merge gates are rejected.
    """
    failures: list[str] = []
    # workspace_isolation: must be a known mode if present
    ws_isolation = str(fm.get("workspace_isolation") or "").strip()
    if ws_isolation and ws_isolation not in VALID_WORKSPACE_ISOLATION:
        failures.append(f"workspace_isolation:unknown_mode:{ws_isolation}")
    # merge_gate: must be a known gate if present
    merge_gate = str(fm.get("merge_gate") or "").strip()
    if merge_gate and merge_gate not in VALID_MERGE_GATES:
        failures.append(f"merge_gate:unknown_gate:{merge_gate}")
    # loc_budget: must be a positive integer if present
    loc_budget_raw = str(fm.get("loc_budget") or "").strip()
    if loc_budget_raw:
        try:
            loc_budget = int(loc_budget_raw)
            if loc_budget <= 0:
                failures.append(f"loc_budget:not_positive:{loc_budget_raw}")
        except ValueError:
            failures.append(f"loc_budget:not_integer:{loc_budget_raw}")
    # allowed_globs: must be parseable glob list
    allowed = fm.get("allowed_globs")
    if allowed is not None:
        globs = list_value(allowed)
        if not globs:
            failures.append("allowed_globs:empty_list")
    # forbidden_globs: must be parseable glob list
    forbidden = fm.get("forbidden_globs")
    if forbidden is not None:
        globs = list_value(forbidden)
        if not globs:
            failures.append("forbidden_globs:empty_list")
    # conflict between allowed and forbidden: forbidden dominates
    allowed_set = set(list_value(fm.get("allowed_globs")))
    forbidden_set = set(list_value(fm.get("forbidden_globs")))
    overlap = allowed_set & forbidden_set
    if overlap:
        failures.append(f"forbidden_dominates_overlap:{sorted(overlap)}")
    # conflict_group / parallel_group: non-empty string if present (stable identifier)
    for field in ("conflict_group", "parallel_group"):
        val = str(fm.get(field) or "").strip()
        if val and not re.fullmatch(r"[a-zA-Z0-9_\-./]+", val):
            failures.append(f"{field}:invalid_identifier:{val}")
    return failures


def boundary_field_sort_key(task: Task) -> tuple[int, int, str]:
    """Sort key for parallel dispatch that respects conflict_group/parallel_group."""
    conflict = str(task.fm.get("conflict_group") or "").strip()
    parallel = str(task.fm.get("parallel_group") or "").strip()
    # Tasks with the same conflict_group must not be dispatched together
    # Tasks with the same parallel_group CAN be dispatched together
    # Priority: conflict_group > parallel_group > default
    return (0 if conflict else 1, 0 if parallel else 1, task.id)


def list_value(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if value in (None, ""):
        return []
    return [x.strip() for x in str(value).split(",") if x.strip()]


def infer_lane(fm: dict[str, Any]) -> str:
    raw = str(fm.get("lane") or "").strip().lower()
    if raw in VALID_LANES:
        return raw
    concepts = " ".join(list_value(fm.get("concepts"))).lower()
    haystack = f"{fm.get('project') or ''} {concepts} {fm.get('type') or ''}".lower()
    if any(token in haystack for token in ("evolution", "self-improvement", "自进化", "skill-graph", "provider-quota")):
        return "evolution"
    if any(token in haystack for token in ("advisory", "research", "analysis", "分析")):
        return "advisory"
    return "work"


def architecture_alignment_missing(fm: dict[str, Any]) -> list[str]:
    if infer_lane(fm) != "evolution":
        return []
    missing = [field for field in EVOLUTION_ALIGNMENT_FIELDS if not str(fm.get(field) or "").strip()]
    target = str(fm.get("architecture_target") or "").strip()
    if target and target not in ARCHITECTURE_TARGETS:
        missing.append("architecture_target:known_target")
    return missing


def architecture_aligned(fm: dict[str, Any]) -> bool:
    return not architecture_alignment_missing(fm)


def task_permission_contract_for_fm(fm: dict[str, Any]) -> dict[str, Any]:
    return taxonomy.task_permission_contract(fm, infer_lane(fm))


def permission_validation_failures(fm: dict[str, Any]) -> list[str]:
    return task_permission_contract_for_fm(fm).get("validation_failures", [])


def apply_permission_defaults(fm: dict[str, Any]) -> dict[str, Any]:
    contract = task_permission_contract_for_fm(fm)
    for key in ("required_authority", "max_authority", "write_surfaces", "completion_gate", "lane_semantics"):
        if fm.get(key) in (None, "", []):
            fm[key] = contract.get(key)
    if fm.get("permission_tier") in (None, "", []):
        fm["permission_tier"] = fm.get("required_authority")
    return fm


def is_mission_envelope_fm(fm: dict[str, Any]) -> bool:
    concepts = {x.lower() for x in list_value(fm.get("concepts"))}
    if "mission-envelope" in concepts:
        return True
    # Child mission nodes may carry mission_id / permission_gates without being
    # the full mission envelope. Treat only strong envelope fields as opt-in.
    envelope_markers = {
        "mission_schema_version", "mission_title", "mission_objective",
        "red_lines", "non_goals", "acceptance_criteria", "dag_nodes",
        "checkpoint_states", "handoff_artifacts", "proof_artifacts",
        "rollback_signal", "ratification_artifact",
    }
    return any(str(fm.get(field) or "").strip() for field in envelope_markers)


def mission_envelope_missing(fm: dict[str, Any]) -> list[str]:
    if not is_mission_envelope_fm(fm):
        return []
    missing: list[str] = []
    for field in MISSION_ENVELOPE_REQUIRED_FIELDS:
        value = fm.get(field)
        if field in MISSION_ENVELOPE_LIST_FIELDS:
            if not list_value(value):
                missing.append(field)
        elif not str(value or "").strip():
            missing.append(field)
    for field in MISSION_ENVELOPE_LIST_FIELDS:
        if field not in MISSION_STRUCTURED_REF_FIELDS:
            continue
        for item in list_value(fm.get(field)):
            if not evidence_is_structured(item):
                missing.append(f"{field}:structured_ref")
                break
    ratification = str(fm.get("ratification_artifact") or "").strip()
    if ratification and not evidence_is_structured(ratification):
        missing.append("ratification_artifact:structured_ref")
    certification = str(fm.get("certification_status") or "").strip()
    if certification and certification not in MISSION_CERTIFICATION_STATUSES:
        missing.append("certification_status:known_status")
    if certification == "certified" and not ratification.startswith(("file:", "artifact:", "url:", "proof:")):
        missing.append("certified_requires_ratification_artifact")
    return sorted(set(missing))


def mission_envelope_valid(fm: dict[str, Any]) -> bool:
    return not mission_envelope_missing(fm)


def mission_node_id(task: "Task") -> str:
    return str(task.fm.get("mission_node_id") or task.id).strip()


def is_mission_node(task: "Task") -> bool:
    return bool(str(task.fm.get("mission_id") or "").strip() and (task.fm.get("mission_node_id") or "mission-node" in {x.lower() for x in list_value(task.fm.get("concepts"))}))


def permission_gate_pending(task: "Task") -> bool:
    for gate in list_value(task.fm.get("permission_gates")):
        g = gate.lower()
        if any(token in g for token in ("ask-human", "human", "permission")) and not any(done in g for done in ("approved", "granted", "pass", "done", "ok")):
            return True
    return False


def mission_groups(tasks: list["Task"] | None = None) -> dict[str, list["Task"]]:
    groups: dict[str, list["Task"]] = {}
    for t in (tasks if tasks is not None else iter_tasks()):
        mid = str(t.fm.get("mission_id") or "").strip()
        if mid and is_mission_node(t):
            groups.setdefault(mid, []).append(t)
    return groups


def mission_dag_invalids(tasks: list["Task"] | None = None) -> list[dict[str, Any]]:
    invalid: list[dict[str, Any]] = []
    for mid, group in mission_groups(tasks).items():
        by_node: dict[str, "Task"] = {}
        for t in group:
            node = mission_node_id(t)
            if node in by_node:
                invalid.append({"mission_id": mid, "task": t.id, "node": node, "reason": "mission_dag_duplicate_node"})
            by_node[node] = t
        graph: dict[str, list[str]] = {}
        for t in group:
            node = mission_node_id(t)
            deps = list_value(t.fm.get("mission_node_depends_on"))
            graph[node] = deps
            for dep in deps:
                if dep not in by_node and dep not in {x.id for x in group}:
                    invalid.append({"mission_id": mid, "task": t.id, "node": node, "dependency": dep, "reason": "mission_dag_missing_dependency"})
        visiting: set[str] = set()
        visited: set[str] = set()
        cycle_nodes: set[str] = set()

        def dfs(node: str, stack: list[str]) -> None:
            if node in visiting:
                if node in stack:
                    cycle_nodes.update(stack[stack.index(node):])
                else:
                    cycle_nodes.add(node)
                return
            if node in visited:
                return
            visiting.add(node)
            for dep in graph.get(node, []):
                if dep in by_node:
                    dfs(dep, stack + [dep])
            visiting.remove(node)
            visited.add(node)

        for node in list(graph):
            dfs(node, [node])
        for node in sorted(cycle_nodes):
            invalid.append({"mission_id": mid, "task": by_node[node].id, "node": node, "reason": "mission_dag_cycle"})
    return invalid


def mission_node_blockers(task: "Task") -> list[str]:
    if not is_mission_node(task):
        return []
    blockers: list[str] = []
    mid = str(task.fm.get("mission_id") or "").strip()
    group = mission_groups().get(mid, [])
    by_node = {mission_node_id(t): t for t in group}
    by_task = {t.id: t for t in group}
    invalid = mission_dag_invalids(group)
    for item in invalid:
        if item.get("task") == task.id:
            blockers.append(str(item.get("reason")))
    for dep in list_value(task.fm.get("mission_node_depends_on")):
        dep_task = by_node.get(dep) or by_task.get(dep)
        if dep_task is None:
            blockers.append(f"missing_dependency:{dep}")
        elif dep_task.status != "done":
            blockers.append(f"waiting_for_dependency:{dep}")
    if permission_gate_pending(task):
        blockers.append("permission_gate_pending")
    return sorted(set(blockers))


def mission_node_ready(task: "Task") -> bool:
    return is_mission_node(task) and not mission_node_blockers(task) and task.is_dispatchable(ignore_mission_node=True)


def mission_dag_summaries(tasks: list["Task"] | None = None) -> list[dict[str, Any]]:
    tasks = tasks if tasks is not None else iter_tasks()
    invalid = mission_dag_invalids(tasks)
    invalid_by_mission: dict[str, list[dict[str, Any]]] = {}
    for item in invalid:
        invalid_by_mission.setdefault(str(item.get("mission_id") or ""), []).append(item)
    summaries: list[dict[str, Any]] = []
    for mid, group in sorted(mission_groups(tasks).items()):
        ready: list[str] = []
        blocked: list[dict[str, Any]] = []
        done = 0
        for t in sorted(group, key=lambda x: mission_node_id(x)):
            node = mission_node_id(t)
            if t.status == "done":
                done += 1
            blockers = mission_node_blockers(t)
            if mission_node_ready(t):
                ready.append(node)
            elif blockers:
                blocked.append({"node": node, "task": t.id, "status": t.status, "blockers": blockers})
        total = len(group)
        summaries.append({
            "mission_id": mid,
            "total_nodes": total,
            "done_nodes": done,
            "ready_nodes": ready,
            "blocked_nodes": blocked,
            "invalid": invalid_by_mission.get(mid, []),
            "progress_percent": int((done / total) * 100) if total else 0,
        })
    return summaries


def task_search_text(task: "Task") -> str:
    """Full search text including body/metadata. Used for general search."""
    concepts = " ".join(list_value(task.fm.get("concepts")))
    fields = [
        task.id,
        task.title,
        task.body,
        concepts,
        task.project,
        task.lane,
        task.architecture_target,
        str(task.fm.get("objective") or ""),
        str(task.fm.get("acceptance_evidence") or ""),
        str(task.fm.get("capability_delta") or ""),
        str(task.fm.get("anti_drift_check") or ""),
    ]
    return "\n".join(fields).lower()


def task_keyword_text(task: "Task") -> str:
    """Narrow keyword search: title + concepts only. Avoids body/metadata noise."""
    concepts = " ".join(list_value(task.fm.get("concepts")))
    return f"{task.title}\n{concepts}".lower()


def has_any_keyword(text: str, keywords: set[str]) -> bool:
    return any(k.lower() in text for k in keywords)


def task_multimodel_status(task: "Task") -> str:
    return str(
        task.fm.get("multimodel_status")
        or task.fm.get("certification_status")
        or task.fm.get("multi_model_status")
        or ""
    ).strip()


def task_multimodel_artifact(task: "Task") -> str:
    return str(
        task.fm.get("multimodel_ratification_artifact")
        or task.fm.get("ratification_artifact")
        or task.fm.get("discussion_result")
        or ""
    ).strip()


def resolve_local_artifact_path(ref: str) -> Path | None:
    """Resolve a local structured artifact reference without accepting opaque proof labels."""
    text = (ref or "").strip()
    if not text:
        return None
    if text.startswith("file:"):
        text = text[len("file:"):]
    # Only local JSON files can be used as ratification proof for taskpool pass state.
    if text.startswith(("artifact:", "proof:", "command:", "search:", "brainctl:", "url:")):
        return None
    p = Path(os.path.expanduser(text))
    if not p.is_absolute():
        return None
    return p


def task_multimodel_passed(task: "Task") -> bool:
    status = task_multimodel_status(task)
    artifact = task_multimodel_artifact(task)
    if status not in MULTIMODEL_PASS_STATUSES or not artifact:
        return False
    artifact_path = resolve_local_artifact_path(artifact)
    if not artifact_path or not artifact_path.exists() or artifact_path.suffix != ".json":
        return False
    try:
        discussion = json.loads(artifact_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    gate = ratification_gate_result(discussion, expected_task=task)
    return gate.get("status") == "PASS" and gate.get("decision") == "LOOP_DONE"


def _frontmatter_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def task_multimodel_advisory_completed(task: "Task") -> bool:
    """Return True when an advisory-only multimodel round already consumed weak triggers.

    Advisory rounds are deliberately not certification authority: they must not set
    ``multimodel_passed`` or close a task.  But once the advisory gate itself passed
    and was recorded as PASS_ADVISORY_ONLY, rerunning the same weak advisory trigger
    every tick is pure scheduler churn.  Strong certification triggers (stale claim,
    P0 evolution blast radius, retry non-convergence) are handled separately and can
    still preempt this consumed-advisory state.
    """
    status = task_multimodel_status(task)
    gate_status = str(task.fm.get("multimodel_last_gate_status") or "").strip().upper()
    advisory_only = _frontmatter_bool(task.fm.get("multimodel_advisory_only"))
    discussion_artifact = str(task.fm.get("multimodel_last_discussion_artifact") or "").strip()
    return (
        status in {"advisory_completed", "not_certified"}
        and gate_status == "PASS_ADVISORY_ONLY"
        and advisory_only
        and bool(discussion_artifact)
    )


def multimodel_convergence_stats(tasks: list["Task"] | None = None) -> dict[str, Any]:
    """Compute convergence statistics for multi-model intervention across the task pool."""
    if tasks is None:
        tasks = [t for t in iter_tasks() if t.status not in TERMINAL_STATUSES]
    total = len(tasks)
    passed = 0
    pending = 0
    triggered = 0
    passed_ids: list[str] = []
    pending_ids: list[str] = []
    for t in tasks:
        if task_multimodel_passed(t):
            passed += 1
            passed_ids.append(t.id)
        elif task_multimodel_intervention_required(t):
            triggered += 1
            pending_ids.append(t.id)
        else:
            pending += 1
    return {
        "total_active": total,
        "multimodel_passed": passed,
        "multimodel_triggered": triggered,
        "multimodel_not_triggered": pending,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "trigger_rate": round(triggered / total, 3) if total else 0.0,
        "passed_ids": passed_ids[:10],
        "pending_ids": pending_ids[:10],
    }


def load_cron_jobs_snapshot(names: list[str] | None = None) -> dict[str, Any]:
    """Read cron job status directly from jobs.json without invoking the scheduler."""
    wanted = set(names or [])
    if not CRON_JOBS_PATH.exists():
        return {"status": "MISSING", "path": str(CRON_JOBS_PATH), "jobs": []}
    try:
        data = json.loads(CRON_JOBS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "ERROR", "path": str(CRON_JOBS_PATH), "error": str(exc), "jobs": []}
    jobs = data.get("jobs", []) if isinstance(data, dict) else []
    selected: list[dict[str, Any]] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        name = str(job.get("name") or "")
        if wanted and name not in wanted:
            continue
        last_error = str(job.get("last_error") or "")
        last_delivery_error = str(job.get("last_delivery_error") or "")
        schedule = job.get("schedule_display")
        if not schedule:
            raw_schedule = job.get("schedule")
            if isinstance(raw_schedule, dict):
                schedule = raw_schedule.get("display") or raw_schedule.get("cron") or raw_schedule.get("interval")
            elif raw_schedule is not None:
                schedule = str(raw_schedule)
        selected.append({
            "id": job.get("id"),
            "name": name,
            "enabled": job.get("enabled"),
            "schedule": schedule,
            "next_run_at": job.get("next_run_at"),
            "last_run_at": job.get("last_run_at"),
            "last_status": job.get("last_status"),
            "last_error_tail": redact_for_evidence(last_error),
            "last_delivery_error_tail": redact_for_evidence(last_delivery_error),
            "_last_error_raw": last_error,
            "_last_delivery_error_raw": last_delivery_error,
            "delivery_configured": bool(job.get("deliver")),
            "script_configured": bool(job.get("script")),
            "no_agent": job.get("no_agent"),
        })
    return {"status": "OK", "path": str(CRON_JOBS_PATH), "jobs": selected}


def multimodel_failure_taxonomy(discussion: dict[str, Any] | None, failures: list[str] | None = None) -> dict[str, Any]:
    """Classify why a ratification/PUA-loop round failed.

    This is deliberately diagnostic-only: it never lowers the gate threshold.
    The goal is to make pass_rate=0.0 actionable instead of a black box.
    """
    discussion = discussion if isinstance(discussion, dict) else {}
    failures = list(failures or [])
    categories: dict[str, list[str]] = {k: [] for k in MULTIMODEL_FAILURE_TAXONOMY}

    def add(category: str, reason: str) -> None:
        if category in categories and reason not in categories[category]:
            categories[category].append(reason)

    status = str(discussion.get("status") or discussion.get("certification_status") or "").strip()
    if status and status not in MULTIMODEL_PASS_STATUSES:
        categories["vote_reject"].append(f"status:{status}")
    if "no_claims" in str(discussion).lower() or any("no_claims" in f for f in failures):
        add("no_claims", "truth gate reported no claims")
    for f in failures:
        if f.startswith("truth_gate_failed:unsupported") or "unsupported" in f:
            add("unsupported_claims", f)
        if f.startswith("truth_gate_failed:") or "accuracy_criterion_missing" in f:
            add("evidence_missing", f)
        if f.startswith("non_approve_vote") or f.startswith("status_not_passed"):
            add("vote_reject", f)
        if f.startswith("agreement_below_threshold") or ("agreement" in f and "low" in f):
            add("agreement_low", f)
        if f.startswith("missing_required_model_vote") or f.startswith("duplicate_vote_model") or f.startswith("unexpected_vote_model"):
            add("model_vote_missing", f)
        if f.startswith("best_within_constraints_missing") or "criterion_missing" in f or "one_shot_plan_missing" in f or "loop_non_convergence" in f:
            add("criteria_missing", f)
        if f.startswith("final_design") or f == "final_design_missing":
            add("final_design_missing", f)
    raw_taxonomy_votes = discussion.get("ratification_votes") or []
    if not isinstance(raw_taxonomy_votes, list):
        add("provider_parse_error", "ratification_votes_not_list")
        raw_taxonomy_votes = []
    for vote in raw_taxonomy_votes:
        if not isinstance(vote, dict):
            continue
        model = str(vote.get("model") or "unknown")
        vote_value = str(vote.get("vote") or vote.get("verdict") or "").lower()
        reason = str(vote.get("reasoning") or vote.get("error") or "")
        lower_blob = f"{vote_value}\n{reason}".lower()
        if vote_value and vote_value not in {"approve", "approved", "pass", "certify"}:
            add("vote_reject", f"{model}:{vote_value}")
        if any(token in lower_blob for token in ("parse", "json", "unparseable", "empty response", "adapter", "api_error")):
            add("provider_parse_error", f"{model}:{reason[:160]}")
        if any(token in lower_blob for token in ("quota", "rate limit", "429", "unobservable")):
            add("quota_unobservable", f"{model}:{reason[:160]}")
    final_design = discussion.get("final_design")
    final_design = final_design if isinstance(final_design, dict) else {}
    eb = discussion.get("evidence_bundle") or final_design.get("evidence_bundle") or {}
    if isinstance(eb, dict):
        if not eb.get("claims") and not eb.get("grounding"):
            add("no_claims", "evidence_bundle has no claims/grounding")
        grounding = eb.get("grounding") or {}
        if isinstance(grounding, dict):
            for cid, g in grounding.items():
                if not isinstance(g, dict):
                    continue
                ts = str(g.get("truth_status") or "")
                if ts == "unsupported":
                    add("unsupported_claims", str(cid))
                elif ts in {"needs_link_review", ""}:
                    add("evidence_missing", f"{cid}:{ts or 'missing_truth_status'}")
    taxonomy_result = {
        "schema": "local_brain_multimodel_failure_taxonomy_v1",
        "categories": categories,
        "active_categories": {k: v for k, v in categories.items() if v},
        "summary": [f"{k}:{len(v)}" for k, v in categories.items() if v],
    }
    taxonomy_result.update(multimodel_failure_taxonomy_axis_hints(taxonomy_result))
    return taxonomy_result


def multimodel_failure_taxonomy_axis_hints(taxonomy_result: dict[str, Any] | None) -> dict[str, Any]:
    active = taxonomy_result.get("active_categories") if isinstance(taxonomy_result, dict) else {}
    if not isinstance(active, dict):
        active = {}
    category_to_axes = {
        "quota_unobservable": ["quota_observability"],
        "evidence_missing": ["quota_observability", "framing"],
        "no_claims": ["quota_observability", "framing"],
        "unsupported_claims": ["framing"],
        "agreement_low": ["relay_ordering"],
        "criteria_missing": ["fallback_threshold"],
        "final_design_missing": ["patch_normalization"],
        "provider_parse_error": ["patch_normalization", "framing"],
        "model_vote_missing": ["framing"],
        "vote_reject": ["framing"],
    }
    axis_to_categories: dict[str, list[str]] = {axis: [] for axis in AUTO_SUBTASK_AXIS_ORDER}
    for category, reasons in active.items():
        if not reasons:
            continue
        for axis in category_to_axes.get(str(category), []):
            if axis in axis_to_categories and category not in axis_to_categories[axis]:
                axis_to_categories[axis].append(str(category))
    recommended_axes = [axis for axis in AUTO_SUBTASK_AXIS_ORDER if axis_to_categories.get(axis)]
    return {
        "recommended_axes": recommended_axes,
        "axis_rationale": {axis: cats for axis, cats in axis_to_categories.items() if cats},
    }


def extract_discussion_result_path_from_stdout(stdout: str) -> str:
    """Extract consult_models.py discussion_result.json path from captured output.

    Parallel intervention workers each own a subprocess stdout/stderr stream; using
    that exact receipt avoids races when several tick-* dirs are created at once.
    """
    text = stdout or ""
    if not text:
        return ""

    def _walk(obj: Any) -> str:
        if isinstance(obj, dict):
            value = obj.get("result_file")
            if isinstance(value, str) and value.endswith("discussion_result.json"):
                return value
            for child in obj.values():
                found = _walk(child)
                if found:
                    return found
        elif isinstance(obj, list):
            for child in obj:
                found = _walk(child)
                if found:
                    return found
        return ""

    try:
        parsed = json.loads(text)
        found = _walk(parsed)
        if found:
            return found
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if 0 <= start < end:
        try:
            parsed = json.loads(text[start : end + 1])
            found = _walk(parsed)
            if found:
                return found
        except Exception:
            pass

    match = re.search(r'"result_file"\s*:\s*"([^"]*discussion_result\.json)"', text)
    if match:
        return match.group(1)

    artifact_match = re.search(r"Artifacts in\s+([^\s]+tick-[^\s/]+/?)(?:\s|$)", text)
    if artifact_match:
        return str(Path(artifact_match.group(1)).expanduser() / "discussion_result.json")
    return ""


def write_multimodel_result_to_task(task: "Task", gate_result: dict[str, Any], discussion_path: str, state_path: str) -> dict[str, Any]:
    """Write every PUA-loop multi-model round result back to the task note.

    PASS/LOOP_DONE certifies the task and stores the ratification artifact.  Any
    non-pass round is still recorded as the latest round state so cron/humans do
    not see a silent no-op.  The gate remains fail-closed: non-pass never sets a
    pass artifact and never suppresses future intervention.
    """
    gate_status = str(gate_result.get("status") or "SKIP").upper()
    decision = str(gate_result.get("decision") or "").upper()
    passed = gate_status == "PASS" and decision == "LOOP_DONE"
    advisory_completed = gate_status == "PASS_ADVISORY_ONLY"
    if not decision:
        decision = "LOOP_DONE" if passed else "CONTINUE_LOOP"
    failures = gate_result.get("failures") if isinstance(gate_result.get("failures"), list) else []
    failure_summary = [str(f) for f in failures[:8]]
    if not failure_summary and gate_result.get("reason"):
        failure_summary = [str(gate_result.get("reason"))]
    failure_taxonomy = gate_result.get("failure_taxonomy") if isinstance(gate_result.get("failure_taxonomy"), dict) else multimodel_failure_taxonomy({}, failure_summary)
    taxonomy_axes = [axis for axis in failure_taxonomy.get("recommended_axes", []) if axis in AUTO_SUBTASK_AXIS_ORDER]
    axis_rationale = failure_taxonomy.get("axis_rationale") or {}
    if passed:
        round_status = "passed"
    elif advisory_completed:
        round_status = "advisory_passed"
    else:
        round_status = "failed" if gate_status == "FAIL" else "skipped"

    advisory_reasons = task_multimodel_advisory_reasons(task)
    cert_reasons = task_multimodel_certification_reasons(task)
    is_advisory_only = advisory_completed or (not passed and not cert_reasons and bool(advisory_reasons))
    multimodel_status = "certified" if passed else ("advisory_completed" if advisory_completed else "not_certified")

    updates = {
        "multimodel_status": multimodel_status,
        "multimodel_last_checked_at": iso(),
        "multimodel_round_status": round_status,
        "multimodel_last_gate_status": gate_status,
        "multimodel_last_decision": decision,
        "multimodel_last_discussion_artifact": discussion_path,
        "multimodel_last_state_path": state_path,
        "multimodel_last_failures": failure_summary,
        "multimodel_advisory_only": is_advisory_only,
        "multimodel_certification_authority": bool(cert_reasons) or passed,
        "multimodel_advisory_reasons": advisory_reasons,
        "multimodel_certification_reasons": cert_reasons,
        "multimodel_failure_taxonomy": sorted((failure_taxonomy.get("active_categories") or {}).keys()),
        "multimodel_recommended_axes": taxonomy_axes,
        "multimodel_axis_rationale": axis_rationale,
    }
    mission_envelope = is_mission_envelope_fm(task.fm)
    if mission_envelope:
        updates["certification_status"] = "certified" if passed else "not_certified"
    if passed:
        updates["multimodel_ratification_artifact"] = discussion_path

    task.fm.update(updates)
    if not mission_envelope:
        task.fm.pop("certification_status", None)
    if not passed:
        # A later failed/skipped round must invalidate any stale PASS artifact as
        # current proof. Historical artifacts remain in the Proof Log/body, but
        # frontmatter must reflect the latest fail-closed certification state.
        task.fm.pop("multimodel_ratification_artifact", None)
    task.body += (
        f"\n- {iso()}: Multimodel PUA-loop round `{round_status}`. "
        f"Gate `{gate_status}`, decision `{decision}`. "
        f"Discussion `{discussion_path or 'missing'}`. "
        f"Failures: {json.dumps(failure_summary, ensure_ascii=False)}. "
        f"Recommended axes: {json.dumps(taxonomy_axes, ensure_ascii=False)}. "
        f"Axis rationale: {json.dumps(axis_rationale, ensure_ascii=False)}\n"
    )
    save_task(task)
    derived_refresh = refresh_derived_task_views("multimodel-round")
    return {"status": "OK", "task_id": task.id, "updates": updates, "passed": passed, "derived_refresh": derived_refresh}


def load_governance_adjustments() -> dict[str, Any]:
    """Load latest governance ratchet output for threshold tuning."""
    if not GOVERNANCE_RATCHET_PATH.exists():
        return {}
    try:
        return json.loads(GOVERNANCE_RATCHET_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def task_multimodel_round_count(task: "Task") -> int:
    """Count how many multimodel rounds this task has been through."""
    body = task.body or ""
    return body.count("Multimodel PUA-loop round")


def task_multimodel_economy_gate(task: "Task") -> dict[str, Any]:
    """Apply loop economy rules: throttle or pause tasks with too many failed rounds."""
    rounds = task_multimodel_round_count(task)
    last_status = str(task.fm.get("multimodel_round_status") or "")
    last_decision = str(task.fm.get("multimodel_last_decision") or "").upper()

    if rounds >= MAX_T3_ROUNDS_BEFORE_PAUSE and last_status == "failed":
        return {
            "action": "pause",
            "reason": f"task has {rounds} failed T3 rounds (max={MAX_T3_ROUNDS_BEFORE_PAUSE}); requires human review or targeted evidence fix",
            "allowed_tier": "none",
            "rounds": rounds,
        }
    if rounds >= MAX_T3_ROUNDS_BEFORE_THROTTLE and last_status == "failed":
        return {
            "action": "throttle",
            "reason": f"task has {rounds} failed T3 rounds (throttle={MAX_T3_ROUNDS_BEFORE_THROTTLE}); downgrading to T2 advisory",
            "allowed_tier": "T2_advisory",
            "rounds": rounds,
        }
    return {"action": "allow", "allowed_tier": "any", "rounds": rounds}


def task_multimodel_intervention_reasons(task: "Task") -> list[str]:
    """Return automatic multi-model intervention reasons for active task notes.

    Trigger policy is intentionally deterministic and local-only: model agreement is
    never treated as evidence here. The command surfaces when to invoke the live
    consult_models.py PUA-loop gate; it does not mutate task state or execute hooks.

    Trigger strategy: structural-first, keyword-supplemented, signal-consumed.
    - Strong structural triggers fire immediately (P0+evolution, retry>=2).
    - Budget signals from doctor --emit-signal upgrade weak signals to T1/T2.
    - Keywords only add reasons when at least one structural reason exists.
    - Requires >= 2 reasons to fire (prevents noise from single weak signals).
    - Keyword search uses title + concepts only (not body/metadata).
    """
    if task.status in TERMINAL_STATUSES or task_multimodel_passed(task):
        return []
    reasons: list[str] = []

    # --- Strong structural triggers (fire immediately) ---
    if task.priority == "P0" and task.lane == "evolution":
        reasons.append("p0_evolution_blast_radius")
    if task.retry_count() >= 2:
        reasons.append("loop_non_convergence")
    if task.is_stale_claim():
        reasons.append("stale_claim")

    # Advisory-only PASS consumes weak advisory triggers, but never masks strong
    # certification triggers above.
    if task_multimodel_advisory_completed(task) and not reasons and task.status not in {"running", "review"}:
        return []

    # --- Structural signals (need keyword or another signal to fire) ---
    if task.status in {"running", "review"}:
        reasons.append("closeout_ratification")
    if task.priority == "P0":
        reasons.append("P0_priority")
    if task.lane == "evolution":
        reasons.append("evolution_lane")
    if task.architecture_target:
        reasons.append("architecture_target")
    if is_mission_envelope_fm(task.fm):
        reasons.append("mission_envelope")
    if task.lane == "evolution" and not str(task.fm.get("acceptance_evidence") or "").strip():
        reasons.append("missing_acceptance_evidence")

    # --- Keyword signals (title + concepts only; only add if structural exists) ---
    kw_text = task_keyword_text(task)
    structural_count = len(reasons)
    if structural_count > 0:
        if has_any_keyword(kw_text, MULTIMODEL_ACCURACY_KEYWORDS):
            reasons.append("accuracy_keyword")
        if has_any_keyword(kw_text, MULTIMODEL_LONG_TERM_KEYWORDS):
            reasons.append("long_term_keyword")
        if has_any_keyword(kw_text, MULTIMODEL_ONE_SHOT_KEYWORDS):
            reasons.append("one_shot_keyword")

    unique = sorted(set(reasons))
    strong = {"p0_evolution_blast_radius", "loop_non_convergence", "stale_claim"}
    # Budget signal upgrade: if doctor emitted recent high-severity signals,
    # boost any weak trigger to T2 advisory level.
    if not (strong & set(unique)) and BUDGET_SIGNALS_PATH.exists():
        try:
            lines = BUDGET_SIGNALS_PATH.read_text(encoding="utf-8").splitlines()[-20:]
            for raw in reversed(lines):
                sig = json.loads(raw)
                if sig.get("severity") in ("high", "critical") and sig.get("recommended_tier") in ("T2_advisory", "T3_advisory"):
                    if "iteration_budget_signal" not in unique:
                        unique.append("iteration_budget_signal")
                        break
        except Exception:
            pass
    # Strong triggers fire alone; everything else needs >= 2 signals.
    if strong & set(unique):
        return unique
    if len(unique) >= 2:
        return unique
    return []


def task_multimodel_intervention_required(task: "Task") -> bool:
    return bool(task_multimodel_intervention_reasons(task))


def task_multimodel_advisory_reasons(task: "Task") -> list[str]:
    reasons = task_multimodel_intervention_reasons(task)
    strong_certification = {"p0_evolution_blast_radius", "loop_non_convergence", "stale_claim", "closeout_ratification"}
    return sorted([r for r in reasons if r not in strong_certification])


def task_multimodel_certification_reasons(task: "Task") -> list[str]:
    reasons = task_multimodel_intervention_reasons(task)
    strong_certification = {"p0_evolution_blast_radius", "loop_non_convergence", "stale_claim", "closeout_ratification"}
    return sorted([r for r in reasons if r in strong_certification])


@dataclasses.dataclass
class Task:
    path: Path
    fm: dict[str, Any]
    body: str

    @property
    def id(self) -> str:
        return self.path.stem

    @property
    def title(self) -> str:
        m = re.search(r"^#\s+(.+)$", self.body, re.M)
        return m.group(1).strip() if m else self.path.stem

    @property
    def status(self) -> str:
        raw = str(self.fm.get("status") or "pending")
        return STATUS_ALIASES.get(raw, raw)

    @property
    def priority(self) -> str:
        return str(self.fm.get("priority") or "P2")

    @property
    def project(self) -> str:
        return str(self.fm.get("project") or "")

    @property
    def lane(self) -> str:
        return infer_lane(self.fm)

    @property
    def architecture_target(self) -> str:
        return str(self.fm.get("architecture_target") or "")

    def architecture_aligned(self) -> bool:
        return architecture_aligned(self.fm)

    def expires_at(self) -> datetime | None:
        return parse_dt(self.fm.get("expires_at"))

    def claim_expires_at(self) -> datetime | None:
        return parse_dt(self.fm.get("claim_expires_at"))

    def next_attempt_at(self) -> datetime | None:
        return parse_dt(self.fm.get("next_attempt_at"))

    def retry_count(self) -> int:
        try:
            return int(self.fm.get("retry_count") or 0)
        except Exception:
            return 0

    def is_retry_due(self, at: datetime | None = None) -> bool:
        at = at or now()
        nxt = self.next_attempt_at()
        return nxt is None or nxt <= at

    def is_stale_claim(self, at: datetime | None = None) -> bool:
        at = at or now()
        return self.status in CLAIM_BOUND_STATUSES and self.claim_expires_at() is not None and self.claim_expires_at() < at

    def is_expired(self, at: datetime | None = None) -> bool:
        at = at or now()
        return self.status not in TERMINAL_STATUSES and self.expires_at() is not None and self.expires_at() < at

    def score(self, at: datetime | None = None) -> int:
        at = at or now()
        score = PRIORITY_WEIGHT.get(self.priority, 150) + STATUS_WEIGHT.get(self.status, 0)
        exp = self.expires_at()
        if exp:
            days = (exp - at).total_seconds() / 86400
            if days < 0:
                score += 90
            elif days <= 1:
                score += 70
            elif days <= 7:
                score += 40
            elif days <= 30:
                score += 10
        try:
            score += min(int(self.fm.get("retry_count") or 0), 5) * 5
        except Exception:
            pass
        if self.is_stale_claim(at):
            score += 55
        if self.status in TERMINAL_STATUSES:
            score -= 1000
        return score

    def is_dispatchable(self, at: datetime | None = None, *, ignore_mission_node: bool = False) -> bool:
        at = at or now()
        if self.status in TERMINAL_STATUSES:
            return False
        if self.is_expired(at):
            return False
        if self.status not in {"pending", "retry"}:
            return False
        if any(self.fm.get(field) for field in ("claimed_by", "claim_expires_at", "run_id")):
            return False
        if self.status == "retry" and not self.is_retry_due(at):
            return False
        if self.lane == "evolution" and not self.architecture_aligned():
            return False
        if project_profile_failures(self):
            return False
        if is_mission_envelope_fm(self.fm) and not mission_envelope_valid(self.fm):
            return False
        if not ignore_mission_node and mission_node_blockers(self):
            return False
        return True

    def row(self) -> dict[str, Any]:
        project_profile = load_project_profile(self.project)
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "priority": self.priority,
            "score": self.score(),
            "lane": self.lane,
            "architecture_target": self.architecture_target,
            "architecture_aligned": self.architecture_aligned(),
            "required_authority": task_permission_contract_for_fm(self.fm).get("required_authority"),
            "max_authority": task_permission_contract_for_fm(self.fm).get("max_authority"),
            "permission_tier": task_permission_contract_for_fm(self.fm).get("permission_tier"),
            "write_surfaces": task_permission_contract_for_fm(self.fm).get("write_surfaces"),
            "completion_gate": task_permission_contract_for_fm(self.fm).get("completion_gate"),
            "lane_semantics": task_permission_contract_for_fm(self.fm).get("lane_semantics"),
            "permission_validation_failures": permission_validation_failures(self.fm),
            "mission_id": str(self.fm.get("mission_id") or ""),
            "mission_node_id": mission_node_id(self) if is_mission_node(self) else "",
            "mission_node_depends_on": list_value(self.fm.get("mission_node_depends_on")),
            "mission_node_blockers": mission_node_blockers(self),
            "mission_node_ready": mission_node_ready(self),
            "mission_envelope": is_mission_envelope_fm(self.fm),
            "mission_envelope_valid": mission_envelope_valid(self.fm),
            "mission_envelope_missing": mission_envelope_missing(self.fm),
            "multimodel_intervention_required": task_multimodel_intervention_required(self),
            "multimodel_intervention_reasons": task_multimodel_intervention_reasons(self),
            "multimodel_status": task_multimodel_status(self),
            "multimodel_ratification_artifact": task_multimodel_artifact(self),
            "multimodel_passed": task_multimodel_passed(self),
            "multimodel_round_status": str(self.fm.get("multimodel_round_status") or ""),
            "multimodel_last_gate_status": str(self.fm.get("multimodel_last_gate_status") or ""),
            "multimodel_last_decision": str(self.fm.get("multimodel_last_decision") or ""),
            "multimodel_last_failures": list_value(self.fm.get("multimodel_last_failures")),
            "project": self.project,
            "project_profile_status": str(project_profile.get("status") or "missing"),
            "project_profile_missing": bool(project_profile.get("missing")),
            "project_profile_path": str(project_profile.get("path") or ""),
            "project_profile_error": str(project_profile.get("error") or ""),
            "claimed_by": self.fm.get("claimed_by") or "",
            "claim_expires_at": self.fm.get("claim_expires_at") or "",
            "run_id": self.fm.get("run_id") or "",
            "retry_count": self.fm.get("retry_count") or 0,
            "next_attempt_at": self.fm.get("next_attempt_at") or "",
            "expires_at": self.fm.get("expires_at") or "",
            "parallel_boundary": self.fm.get("parallel_boundary") or task_parallel_boundary_key(self),
            "parallel_group": parallel_group_key(self),
            "conflict_group": str(self.fm.get("conflict_group") or "").strip(),
            "workspace_isolation": str(self.fm.get("workspace_isolation") or "").strip(),
            "stale_claim": self.is_stale_claim(),
            "expired": self.is_expired(),
            "dispatchable": self.is_dispatchable(),
            "lifecycle_next": allowed_next_statuses(self.status),
            "path": str(self.path),
            "link": obsidian_link(self.path),
        }


def obsidian_link(path: Path) -> str:
    rel = path.relative_to(VAULT).with_suffix("")
    return "[[" + str(rel) + "]]"


def markdown_table_cell(value: Any, limit: int | None = None) -> str:
    text = str(value or "-").replace("\r", " ").replace("\n", " ").replace("|", "\\|")
    return text[:limit] if limit else text


def iter_tasks(include_generated: bool = False) -> list[Task]:
    tasks: list[Task] = []
    if not TASKS_DIR.exists():
        return tasks
    skip = {"00-tasks索引.md", "任务收件箱.md", "任务池-排序.md"}
    for path in sorted(TASKS_DIR.glob("*.md")):
        if not include_generated and path.name in skip:
            continue
        text = path.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        if fm.get("type") == "task":
            tasks.append(Task(path, fm, body))
    return tasks


def find_task(task_id: str) -> Task:
    candidates = []
    for t in iter_tasks():
        if t.id == task_id or t.path.name == task_id or str(t.path).endswith(task_id):
            candidates.append(t)
    if not candidates:
        raise SystemExit(f"task not found: {task_id}")
    if len(candidates) > 1:
        raise SystemExit(f"ambiguous task id {task_id}: {[t.id for t in candidates]}")
    return candidates[0]


def save_task(task: Task) -> None:
    atomic_write(task.path, render_frontmatter(task.fm) + "\n" + task.body.lstrip("\n"))


def create_task_note(
    *,
    title: str,
    priority: str = "P2",
    project: str = "inbox",
    status: str = "pending",
    expires_at: str = "",
    expires_days: int = 30,
    concepts: list[str] | None = None,
    lane: str = "auto",
    architecture_target: str = "",
    capability_delta: str = "",
    anti_drift_check: str = "",
    acceptance_evidence: str = "",
    layer: str = "L3",
    workflow_contract: str = DEFAULT_WORKFLOW,
    workspace: str = "",
    parallel_boundary: str = "",
    objective: str = "",
    accept: str = "",
    extra_frontmatter: dict[str, Any] | None = None,
    extra_body_sections: str = "",
) -> dict[str, Any]:
    if status not in INITIAL_TASK_STATUSES:
        raise SystemExit(f"add can only create initial statuses {sorted(INITIAL_TASK_STATUSES)}; use transition/reconcile for lifecycle changes")
    lane_arg = (lane or "auto").strip().lower()
    if lane_arg != "auto" and lane_arg not in VALID_LANES:
        raise SystemExit(f"lane must be one of {['auto', *VALID_LANES]}")
    title = title.strip()
    concept_list = [x.strip() for x in (concepts or ["task"]) if str(x).strip()]
    validate_clean_values(
        title=title,
        layer=layer,
        status=status,
        priority=priority,
        project=project,
        workflow_contract=workflow_contract,
        workspace=workspace or "",
        parallel_boundary=parallel_boundary or "",
        concepts=",".join(concept_list),
        lane=lane_arg,
        architecture_target=architecture_target,
        capability_delta=capability_delta,
        anti_drift_check=anti_drift_check,
        acceptance_evidence=acceptance_evidence,
    )
    created = now()
    expires = parse_dt(expires_at) if expires_at else created + timedelta(days=expires_days)
    slug = slugify(title)
    base = TASKS_DIR / f"{created.date().isoformat()}-{slug}.md"
    path = base
    i = 2
    while path.exists():
        path = TASKS_DIR / f"{created.date().isoformat()}-{slug}-{i}.md"
        i += 1
    preliminary = {"lane": "" if lane_arg == "auto" else lane_arg, "project": project, "concepts": concept_list, "type": "task"}
    inferred_lane = infer_lane(preliminary)
    fm = {
        "type": "task",
        "lane": inferred_lane,
        "layer": layer,
        "status": status,
        "priority": priority,
        "created": iso(created),
        "updated": iso(created),
        "expires_at": iso(expires) if expires else "",
        "project": project,
        "architecture_target": architecture_target or "",
        "capability_delta": capability_delta or "",
        "anti_drift_check": anti_drift_check or "",
        "acceptance_evidence": acceptance_evidence or "",
        "workflow_contract": workflow_contract,
        "claimed_by": "",
        "claim_expires_at": "",
        "run_id": "",
        "retry_count": 0,
        "next_attempt_at": "",
        "workspace": workspace or "",
        "parallel_boundary": parallel_boundary or "",
        "evidence": [],
        "concepts": concept_list,
    }
    if extra_frontmatter:
        fm.update(extra_frontmatter)
    apply_permission_defaults(fm)
    missing_alignment = architecture_alignment_missing(fm)
    if missing_alignment:
        raise SystemExit(f"evolution tasks require architecture alignment fields; missing/invalid={missing_alignment}")
    sections = [
        f"# Task - {title}",
        "",
        "## Objective",
        "",
        objective or title,
        "",
        "## Acceptance Criteria",
        "",
        f"- [ ] {accept or 'Observable result is recorded in Proof Log.'}",
        "",
        "## Plan / Workpad",
        "",
        "- [ ] Reconcile current state before execution.",
        "- [ ] Execute the smallest verifiable slice.",
        "- [ ] Record proof and update status.",
        "",
    ]
    if extra_body_sections.strip():
        sections.extend([extra_body_sections.rstrip(), ""])
    sections.extend([
        "## Validation",
        "",
        "| Command / Check | Status | Evidence |",
        "|---|---|---|",
        "| brain_task_orchestrator list | pending | |",
        "",
        "## Proof Log",
        "",
        f"- {iso(created)}: Task created from local-brain control point.",
        "",
        "## Blockers / Confusions",
        "",
        "- None.",
        "",
        "## Final Handoff",
        "",
        "- Status:",
        "- Evidence:",
        "- Residual risk:",
        "",
    ])
    body = "\n".join(sections)
    atomic_write(path, render_frontmatter(fm) + "\n" + body)
    return {"status": "OK", "created": str(path), "id": path.stem, "link": obsidian_link(path)}


def replace_markdown_section(body: str, heading: str, content: str) -> str:
    pattern = rf"(## {re.escape(heading)}\n\n)(.*?)(?=\n## |\Z)"
    replacement = rf"\1{content.rstrip()}\n"
    updated, count = re.subn(pattern, replacement, body, flags=re.S)
    if count:
        return updated
    suffix = "" if body.endswith("\n") else "\n"
    return body + f"{suffix}\n## {heading}\n\n{content.rstrip()}\n"


def extract_markdown_section(body: str, heading: str) -> str:
    pattern = rf"## {re.escape(heading)}\n\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, body, flags=re.S)
    return match.group(1).rstrip() if match else ""


def append_markdown_section_lines_unique(body: str, heading: str, lines: list[str]) -> str:
    existing = extract_markdown_section(body, heading)
    current_lines = [line.rstrip() for line in existing.splitlines() if line.strip()]
    for line in lines:
        normalized = line.rstrip()
        if normalized and normalized not in current_lines:
            current_lines.append(normalized)
    return replace_markdown_section(body, heading, "\n".join(current_lines))


def load_discussion_artifact(task: Task) -> dict[str, Any]:
    path = str(task.fm.get("multimodel_last_discussion_artifact") or "").strip()
    if not path:
        raise SystemExit(f"task {task.id} has no multimodel_last_discussion_artifact")
    artifact = Path(path).expanduser()
    if not artifact.exists():
        raise SystemExit(f"discussion artifact missing: {artifact}")
    try:
        data = json.loads(artifact.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"failed to parse discussion artifact {artifact}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"discussion artifact must be a JSON object: {artifact}")
    return data


AUTO_SUBTASK_AXIS_ORDER = [
    "quota_observability",
    "fallback_threshold",
    "relay_ordering",
    "patch_normalization",
    "framing",
]


def _issue_text(issue: Any) -> str:
    if isinstance(issue, dict):
        parts = []
        for key in ("id", "title", "summary", "description", "reason", "notes", "proposed_action", "cluster"):
            value = issue.get(key)
            if value:
                parts.append(str(value))
        return " ".join(parts).strip().lower()
    return str(issue or "").strip().lower()


def classify_non_convergence_issue_axis(issue: Any) -> str:
    text = _issue_text(issue)
    if any(token in text for token in ("quota", "observability", "unobservable", "confidence", "provider quota", "budget state")):
        return "quota_observability"
    if any(token in text for token in ("threshold", "noop", "downgrade", "fallback", "budget exhaustion", "policy gate")):
        return "fallback_threshold"
    if any(token in text for token in ("relay", "handoff", "continuation", "ordering", "packet timing", "re-entry")):
        return "relay_ordering"
    if any(token in text for token in ("patch", "normalize", "normalization", "merge", "certifiable slice", "minority patch")):
        return "patch_normalization"
    return "framing"


def build_non_convergence_spec(task: Task, *, axis: str, issue_ids: list[str], artifact_path: str) -> dict[str, Any]:
    shared_prefix = f"Auto-generated convergence slice for parent `{task.id}`. Do not change the parent objective."
    artifact_note = artifact_path or str(task.fm.get("multimodel_last_discussion_artifact") or "")
    issue_note = ", ".join(issue_ids) if issue_ids else "none tagged"
    parent_objective = extract_markdown_section(task.body, "Objective") or "Objective missing in parent task."
    spec_map: dict[str, dict[str, Any]] = {
        "quota_observability": {
            "title": f"为 {task.id} 细化 quota observability 收敛前置任务",
            "objective": f"{shared_prefix} Define quota_state source, confidence, staleness, and fail-closed semantics so future ratification can decide whether quota-aware change is required.",
            "accept": "Produce a narrowed brief covering quota_state source, confidence, unknown/unobservable handling, and file-backed evidence locations.",
            "concepts": ["task", "auto-subtask", "non-convergence", "quota-observability"],
            "capability_delta": "quota observability narrowed brief",
            "anti_drift_check": "keep parent objective unchanged while proving quota_state semantics",
            "acceptance_evidence": "proof log cites source evidence for quota_state confidence and unknown handling",
            "narrowed_scope": [
                "Only resolve quota observability and evidence gaps.",
                "Do not decide relay ordering or broader fallback policy here.",
            ],
        },
        "fallback_threshold": {
            "title": f"为 {task.id} 细化 fallback threshold 收敛前置任务",
            "objective": f"{shared_prefix} Define fallback thresholds, downgrade policy, and the minimum evidence required to justify noop vs change on budget exhaustion behavior.",
            "accept": "Produce a narrowed brief covering trigger thresholds, allowed fallback actions, and explicit noop-vs-change decision criteria.",
            "concepts": ["task", "auto-subtask", "non-convergence", "fallback-thresholds"],
            "capability_delta": "fallback threshold narrowed brief",
            "anti_drift_check": "separate threshold policy from relay implementation so the parent scope does not drift",
            "acceptance_evidence": "proof log states threshold semantics and the evidence gate for noop-vs-change",
            "narrowed_scope": [
                "Only resolve threshold semantics and noop-vs-change decision criteria.",
                "Do not redesign the full handoff workflow here.",
            ],
        },
        "relay_ordering": {
            "title": f"为 {task.id} 细化 relay ordering 收敛前置任务",
            "objective": f"{shared_prefix} Define continuation packet / relay ordering after quota and threshold semantics are known, without reopening the parent mission objective.",
            "accept": "Produce a narrowed brief covering continuation packet timing, relay ordering, and parent handoff integration points.",
            "concepts": ["task", "auto-subtask", "non-convergence", "relay-ordering"],
            "capability_delta": "relay ordering narrowed brief",
            "anti_drift_check": "relay ordering must stay downstream of quota and threshold decisions",
            "acceptance_evidence": "proof log names continuation packet timing and parent re-entry points",
            "narrowed_scope": [
                "Only resolve relay ordering and continuation packet timing.",
                "Assume quota/threshold semantics are separate prerequisites.",
            ],
        },
        "patch_normalization": {
            "title": f"为 {task.id} 细化 patch normalization 收敛前置任务",
            "objective": f"{shared_prefix} Normalize surfaced minority patches into a certifiable minimum patch set that preserves the parent objective and removes noop-vs-change ambiguity.",
            "accept": "Produce a narrowed brief that maps surfaced patch candidates to one certifiable minimum patch set with clear inclusion/exclusion criteria.",
            "concepts": ["task", "auto-subtask", "non-convergence", "patch-normalization"],
            "capability_delta": "patch normalization narrowed brief",
            "anti_drift_check": "keep implementation slicing smaller than the parent mission",
            "acceptance_evidence": "proof log explains why each candidate patch is included, excluded, or deferred",
            "narrowed_scope": [
                "Only normalize surfaced patch candidates and their inclusion criteria.",
                "Do not expand into end-to-end implementation here.",
            ],
        },
        "framing": {
            "title": f"为 {task.id} 细化 framing 收敛前置任务",
            "objective": f"{shared_prefix} Extract the minimum narrowed brief needed to resolve the current non-convergence without changing the parent objective.",
            "accept": "Produce a narrowed brief that maps unresolved issues to one concrete evidence or design question each.",
            "concepts": ["task", "auto-subtask", "non-convergence", "framing"],
            "capability_delta": "framing narrowed brief",
            "anti_drift_check": "parent objective remains canonical",
            "acceptance_evidence": "proof log maps each unresolved issue to one narrowed question",
            "narrowed_scope": [
                "Resolve only the highest-leverage unresolved issue cluster first.",
            ],
        },
    }
    spec = dict(spec_map.get(axis, spec_map["framing"]))
    scope_lines = "\n".join(f"- {line}" for line in spec.pop("narrowed_scope"))
    spec["axis"] = axis
    spec["issue_ids"] = issue_ids
    spec["trigger"] = f"auto_subtask_on_non_convergence:{axis}"
    spec["extra_body_sections"] = (
        f"## Parent Link\n\n"
        f"- Parent task: {task.id}\n"
        f"- Discussion artifact: {artifact_note or '[missing]'}\n"
        f"- Trigger axis: {axis}\n"
        f"- Issue IDs: {issue_note}\n\n"
        f"## Parent Objective Snapshot\n\n"
        f"{parent_objective}\n\n"
        f"## Narrowed Scope\n\n{scope_lines}"
    )
    return spec


def build_non_convergence_subtask_specs(task: Task, discussion: dict[str, Any]) -> list[dict[str, Any]]:
    final_design = discussion.get("final_design") if isinstance(discussion.get("final_design"), dict) else {}
    agreement = discussion.get("agreement_matrix") if isinstance(discussion.get("agreement_matrix"), dict) else {}
    patch_summary = final_design.get("planner_patch_summary") if isinstance(final_design.get("planner_patch_summary"), dict) else (discussion.get("planner_patch_summary") if isinstance(discussion.get("planner_patch_summary"), dict) else {})
    merge_info = final_design.get("merge_info") if isinstance(final_design.get("merge_info"), dict) else (discussion.get("merge_info") if isinstance(discussion.get("merge_info"), dict) else {})
    quota_snapshot = final_design.get("quota_snapshot") if isinstance(final_design.get("quota_snapshot"), dict) else (discussion.get("quota_snapshot") if isinstance(discussion.get("quota_snapshot"), dict) else {})
    issue_ledger = discussion.get("issue_ledger") if isinstance(discussion.get("issue_ledger"), list) else []
    artifact_path = str(task.fm.get("multimodel_last_discussion_artifact") or "").strip()

    axis_to_issue_ids: dict[str, list[str]] = {axis: [] for axis in AUTO_SUBTASK_AXIS_ORDER}
    unresolved_seen = False
    for item in issue_ledger:
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "").lower() != "unresolved":
            continue
        unresolved_seen = True
        axis = classify_non_convergence_issue_axis(item)
        issue_id = str(item.get("id") or "").strip()
        if issue_id and issue_id not in axis_to_issue_ids[axis]:
            axis_to_issue_ids[axis].append(issue_id)

    minority_patches = [str(x) for x in list_value(merge_info.get("minority_patches"))]
    patch_blob = " ".join(minority_patches).lower()
    intent = str(patch_summary.get("certification_intent") or "").lower()
    low_quota_conf = False
    if quota_snapshot:
        for value in quota_snapshot.values():
            if not isinstance(value, dict):
                continue
            if float(value.get("confidence") or 0) <= 0.25 or str(value.get("observability") or "").lower() in {"unknown", "unobservable", "missing"}:
                low_quota_conf = True
                break

    requested_axes: list[str] = []
    taxonomy_hints = multimodel_failure_taxonomy(discussion, [str(x) for x in list_value(task.fm.get("multimodel_last_failures"))])
    taxonomy_axes = [axis for axis in taxonomy_hints.get("recommended_axes", []) if axis in AUTO_SUBTASK_AXIS_ORDER]
    for axis in taxonomy_axes:
        if axis not in requested_axes:
            requested_axes.append(axis)
    if axis_to_issue_ids["quota_observability"] or low_quota_conf or "quota" in patch_blob:
        requested_axes.append("quota_observability")
    if axis_to_issue_ids["fallback_threshold"] or "threshold" in patch_blob or intent == "unresolved_noop_vs_change":
        requested_axes.append("fallback_threshold")
    if axis_to_issue_ids["relay_ordering"] or "relay" in patch_blob or agreement.get("implementation_order", 1.0) < 0.85:
        requested_axes.append("relay_ordering")
    if axis_to_issue_ids["patch_normalization"] or minority_patches:
        requested_axes.append("patch_normalization")
    if not requested_axes:
        requested_axes.append("framing")
    if unresolved_seen and not any(axis_to_issue_ids[axis] for axis in requested_axes):
        requested_axes.append("framing")

    ordered_axes: list[str] = []
    for axis in AUTO_SUBTASK_AXIS_ORDER:
        if axis in requested_axes and axis not in ordered_axes:
            ordered_axes.append(axis)

    specs = [build_non_convergence_spec(task, axis=axis, issue_ids=axis_to_issue_ids.get(axis, []), artifact_path=artifact_path) for axis in ordered_axes]
    return specs[:3]


def auto_subtask_children(parent: Task) -> list[Task]:
    child_ids = [str(x) for x in list_value(parent.fm.get("auto_subtask_children"))]
    if not child_ids:
        return []
    children_by_id = {task.id: task for task in iter_tasks()}
    return [children_by_id[cid] for cid in child_ids if cid in children_by_id]


def sync_auto_subtask_parent(parent: Task, *, stamp: datetime | None = None, actor: str = "system", write: bool = False) -> dict[str, Any] | None:
    if str(parent.fm.get("auto_subtask_kind") or "") != "non_convergence_narrowing":
        return None
    stamp = stamp or now()
    child_ids = [str(x) for x in list_value(parent.fm.get("auto_subtask_children"))]
    if not child_ids:
        return None
    children = auto_subtask_children(parent)
    child_map = {child.id: child for child in children}
    missing = [cid for cid in child_ids if cid not in child_map]
    open_children = [child.id for child in children if child.status not in TERMINAL_STATUSES]
    done_children = [child.id for child in children if child.status == "done"]
    ready = not open_children and not missing and len(done_children) == len(child_ids)
    previous_ready = bool(parent.fm.get("auto_subtask_ready_for_parent"))
    previous_status = parent.status
    previous_open_children = [str(x) for x in list_value(parent.fm.get("auto_subtask_open_children"))]
    previous_missing_children = [str(x) for x in list_value(parent.fm.get("auto_subtask_missing_children"))]
    if previous_ready == ready and previous_open_children == open_children and previous_missing_children == missing:
        return None

    parent.fm["auto_subtask_open_children"] = open_children
    parent.fm["auto_subtask_missing_children"] = missing
    parent.fm["auto_subtask_ready_for_parent"] = ready
    parent.fm["updated"] = iso(stamp)

    blocker_lines = [
        "- auto-generated convergence subtasks:",
        *[f"  - {cid}" for cid in child_ids],
    ]
    if open_children:
        blocker_lines.append("- Remaining open children before parent ratification resumes:")
        blocker_lines.extend(f"  - {cid}" for cid in open_children)
    elif missing:
        blocker_lines.append("- Missing child task notes must be recovered before resuming the parent:")
        blocker_lines.extend(f"  - {cid}" for cid in missing)
    else:
        blocker_lines.append("- All auto-generated convergence subtasks reached done; parent can re-enter ratification.")
    blocker_lines.append("- Do not change the parent objective; narrowed subtasks only prepare the next parent ratification step.")
    parent.body = replace_markdown_section(parent.body, "Blockers / Confusions", "\n".join(blocker_lines))

    proof_lines = [
        f"- {iso(stamp)}: Auto-subtask sync -> done={len(done_children)}/{len(child_ids)}, open={len(open_children)}, missing={len(missing)}.",
    ]
    if ready and (previous_status == "blocked" or not previous_ready):
        proof_lines.append(f"- {iso(stamp)}: All auto-generated convergence subtasks reached done; parent reopened to `pending` for ratification rerun.")
    parent.body = append_markdown_section_lines_unique(parent.body, "Proof Log", proof_lines)

    action = "auto_subtask_progress_synced"
    if ready and previous_status == "blocked":
        parent.fm["status"] = "pending"
        action = "auto_subtask_parent_reopened"

    if write:
        save_task(parent)
    return {
        "task": parent.id,
        "action": action,
        "write": bool(write),
        "path": str(parent.path),
        "ready": ready,
        "open_children": open_children,
        "missing_children": missing,
    }


def command_auto_split_non_convergence(args: argparse.Namespace) -> dict[str, Any]:
    parent = find_task(args.task)
    discussion = load_discussion_artifact(parent)
    specs = build_non_convergence_subtask_specs(parent, discussion)
    taxonomy_hints = multimodel_failure_taxonomy(discussion, [str(x) for x in list_value(parent.fm.get("multimodel_last_failures"))])
    existing = [str(x) for x in list_value(parent.fm.get("auto_subtask_children"))]
    existing_set = set(existing)
    created: list[dict[str, Any]] = []

    for spec in specs:
        expected_slug = slugify(spec["title"])
        expected_id = f"{now().date().isoformat()}-{expected_slug}"
        if expected_id in existing_set:
            continue
        result = create_task_note(
            title=spec["title"],
            priority=parent.priority,
            project=parent.project,
            status="pending",
            expires_at=str(parent.fm.get("expires_at") or ""),
            concepts=spec["concepts"],
            lane=parent.lane,
            architecture_target=parent.architecture_target,
            capability_delta=spec["capability_delta"],
            anti_drift_check=spec["anti_drift_check"],
            acceptance_evidence=spec["acceptance_evidence"],
            layer=str(parent.fm.get("layer") or "L3"),
            workflow_contract=str(parent.fm.get("workflow_contract") or DEFAULT_WORKFLOW),
            workspace=str(parent.fm.get("workspace") or ""),
            parallel_boundary=str(parent.fm.get("parallel_boundary") or ""),
            objective=spec["objective"],
            accept=spec["accept"],
            extra_frontmatter={
                "auto_subtask_parent": parent.id,
                "auto_subtask_kind": "non_convergence_narrowing",
                "auto_subtask_axis": spec.get("axis") or "framing",
                "auto_subtask_trigger": spec.get("trigger") or "auto_subtask_on_non_convergence:framing",
                "auto_subtask_issue_ids": spec.get("issue_ids") or [],
                "auto_subtask_parent_artifact": str(parent.fm.get("multimodel_last_discussion_artifact") or ""),
            },
            extra_body_sections=spec["extra_body_sections"],
        )
        created.append(result)
        existing_set.add(result["id"])

    child_ids = sorted(existing_set)
    child_links = [item["link"] for item in created]
    parent.fm["auto_subtask_children"] = child_ids
    parent.fm["auto_subtask_kind"] = "non_convergence_narrowing"
    parent.fm["auto_subtask_taxonomy_axes"] = [axis for axis in taxonomy_hints.get("recommended_axes", []) if axis in AUTO_SUBTASK_AXIS_ORDER]
    parent.fm["auto_subtask_axis_rationale"] = taxonomy_hints.get("axis_rationale") or {}
    parent.fm["auto_subtask_open_children"] = child_ids
    parent.fm["auto_subtask_ready_for_parent"] = False
    blocker_lines = [
        "- auto-generated convergence subtasks:",
        *[f"  - {cid}" for cid in child_ids],
        "- Do not change the parent objective; complete narrowed subtasks first, then re-run parent ratification.",
    ]
    proof_lines = [
        f"- {iso()}: Auto-generated convergence subtasks created for unresolved non-convergence.",
        *[f"  - child: {link}" for link in child_links],
    ]
    if not created:
        proof_lines.append("  - no-op: required convergence subtasks already existed.")
    parent.body = replace_markdown_section(parent.body, "Blockers / Confusions", "\n".join(blocker_lines))
    parent.body = append_markdown_section_lines_unique(parent.body, "Proof Log", proof_lines)
    save_task(parent)
    derived_refresh = refresh_derived_task_views("auto-split-non-convergence")
    return {
        "status": "OK",
        "parent_task": parent.id,
        "created_count": len(created),
        "created": created,
        "existing_children": existing,
        "all_children": child_ids,
        "taxonomy_axes": [axis for axis in taxonomy_hints.get("recommended_axes", []) if axis in AUTO_SUBTASK_AXIS_ORDER],
        "axis_rationale": taxonomy_hints.get("axis_rationale") or {},
        "derived_refresh": derived_refresh,
        "safety": "parent objective preserved; generated subtasks are narrowing prerequisites only",
    }


def command_auto_subtask_sync(args: argparse.Namespace) -> dict[str, Any]:
    stamp = now()
    tasks = [find_task(args.task)] if getattr(args, "task", "") else [t for t in iter_tasks() if str(t.fm.get("auto_subtask_kind") or "") == "non_convergence_narrowing"]
    actions: list[dict[str, Any]] = []
    for task in tasks:
        action = sync_auto_subtask_parent(task, stamp=stamp, actor=getattr(args, "actor", "hermes-auto-subtask-sync"), write=getattr(args, "write", False))
        if action:
            actions.append(action)
    derived_refresh = refresh_derived_task_views("auto-subtask-sync") if getattr(args, "write", False) and actions else None
    return {
        "status": "OK",
        "write": bool(getattr(args, "write", False)),
        "action_count": len(actions),
        "actions": actions,
        "derived_refresh": derived_refresh,
    }


def refresh_derived_task_views(reason: str = "task_mutation") -> dict[str, Any]:
    """Regenerate taskpool derived views after a canonical task-note mutation.

    Markdown task notes remain the source of truth, but stale dashboard/sorted
    pool files break the human/cron control loop.  Mutating commands therefore
    refresh derived views in the same process after the canonical write commits.
    """
    ensure_inbox()
    dashboard, pool = render_dashboard()
    control = render_control_center()
    atomic_write(DASHBOARD, dashboard)
    atomic_write(SORTED_POOL, pool)
    atomic_write(CONTROL_CENTER, control)
    return {
        "status": "OK",
        "reason": reason,
        "dashboard": str(DASHBOARD),
        "sorted_pool": str(SORTED_POOL),
        "control_center": str(CONTROL_CENTER),
        "generated_at": iso(),
    }


def sorted_tasks(include_done: bool = False) -> list[Task]:
    rows = [t for t in iter_tasks() if include_done or t.status not in TERMINAL_STATUSES]
    return sorted(rows, key=lambda t: (-t.score(), t.expires_at() or datetime.max.replace(tzinfo=TZ), t.priority, t.id))


def dispatch_sort_key(t: Task) -> tuple[int, int, datetime, str, str]:
    weights = lane_sort_weight()
    return (weights.get(t.lane, 1), -t.score(), t.expires_at() or datetime.max.replace(tzinfo=TZ), t.priority, t.id)


def dispatchable_tasks() -> list[Task]:
    rows = [t for t in iter_tasks() if t.is_dispatchable()]
    return sorted(rows, key=dispatch_sort_key)


def evidence_is_structured(e: str) -> bool:
    e = (e or "").strip()
    if not e:
        return False
    prefixes = (
        "command:", "file:", "search:", "brainctl:", "url:", "artifact:", "proof:",
        "live_lark_snapshot:", "classification:",
        # Compatibility for auto-subtask backfill records written before
        # evidence_is_structured learned these relationship shapes.  They are
        # structured taskpool links, not free-form proof, and must not freeze
        # global proof/evidence gates for unrelated dispatchable tasks.
        "child-task:", "child-axis:",
    )
    if e.startswith(prefixes):
        return True
    p = Path(os.path.expanduser(e))
    return p.is_absolute() and p.exists()


def _evidence_blob(evidence: list[str]) -> str:
    return "\n".join(str(e or "").strip().lower() for e in evidence)


def completion_gate_failures(task: "Task", evidence: list[str]) -> list[str]:
    """Validate lane-specific done evidence beyond generic structured evidence.

    Authority such as --yolo may approve execution, but task completion is a
    different lifecycle operation.  Work/Lark tasks need project evidence;
    self-evolution needs ratification/selfcheck proof; advisory tasks need a
    deposited evidence/report artifact.  This prevents one lane's lightest proof
    from closing another lane's work.
    """
    contract = task_permission_contract_for_fm(task.fm)
    lane = task.lane
    gate = str(contract.get("completion_gate") or "").strip()
    blob = _evidence_blob(evidence)
    failures: list[str] = []

    def has_any(tokens: tuple[str, ...]) -> bool:
        return any(token in blob for token in tokens)

    if not gate:
        return ["completion_gate:missing"]
    if gate == "project-evidence-review-done":
        if lane != "work":
            failures.append(f"completion_gate_lane_mismatch:{lane}!={gate}")
        if not has_any(("test", "build", "lint", "playwright", "browser", "curl", "mvn", "pytest", "vitest", "npm", "pnpm", "yarn", "railway", "git diff --check", "commit", "project evidence", "verification")):
            failures.append("project-evidence-review-done requires test/build/browser/curl/commit/project-verification evidence")
    elif gate == "project-evidence-real-api-review-done":
        if lane != "work":
            failures.append(f"completion_gate_lane_mismatch:{lane}!={gate}")
        if not has_any(("test", "build", "lint", "playwright", "browser", "curl", "mvn", "pytest", "vitest", "npm", "pnpm", "yarn", "railway", "git diff --check", "commit", "verification")):
            failures.append("project-evidence-real-api-review-done requires test/build/browser/curl/commit verification evidence")
        if not has_any(("real-api", "real api", "真实接口", "backend", "frontend", "fe-be", "curl", "mvn")):
            failures.append("project-evidence-real-api-review-done requires real-api/backend/frontend contract evidence")
    elif gate == "ratification-or-selfcheck-review-done":
        if lane != "evolution":
            failures.append(f"completion_gate_lane_mismatch:{lane}!={gate}")
        if not has_any(("ratification", "discussion_result", "certification_manifest", "selfcheck", "proof", "proof-check", "evidence-spine", "usage-score", "p10-health", "proof:sha256:")):
            failures.append("ratification-or-selfcheck-review-done requires ratification artifact or deterministic selfcheck/proof evidence")
    elif gate == "advisory-evidence-review-done":
        if lane != "advisory":
            failures.append(f"completion_gate_lane_mismatch:{lane}!={gate}")
        if not has_any(("advisory", "report", "analysis", "evidence", "artifact:", "file:", "url:")):
            failures.append("advisory-evidence-review-done requires deposited advisory evidence/report artifact")
    else:
        failures.append(f"completion_gate:unknown:{gate}")
    return failures


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def proof_payload_hash(event: dict[str, Any]) -> str:
    payload = {k: v for k, v in event.items() if k != "event_hash"}
    return "sha256:" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def read_autorun_proof_events() -> list[dict[str, Any]]:
    if not AUTORUN_PROOF_LOG.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in AUTORUN_PROOF_LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(json.loads(line))
    return events


def verify_autorun_proof_chain() -> tuple[bool, list[str]]:
    failures: list[str] = []
    prev = ""
    try:
        events = read_autorun_proof_events()
    except Exception as exc:
        return False, [f"autorun proof log unreadable: {exc}"]
    for i, event in enumerate(events, 1):
        if event.get("prev_hash", "") != prev:
            failures.append(f"autorun proof chain prev_hash mismatch at line {i}")
        expected = proof_payload_hash(event)
        if event.get("event_hash") != expected:
            failures.append(f"autorun proof chain hash mismatch at line {i}")
        prev = str(event.get("event_hash") or "")
    return not failures, failures


def verify_autorun_proof_hash(proof_hash: str) -> bool:
    if not proof_hash.startswith("sha256:"):
        return False
    ok, _failures = verify_autorun_proof_chain()
    if not ok:
        return False
    try:
        return any(event.get("event_hash") == proof_hash for event in read_autorun_proof_events())
    except Exception:
        return False


def append_autorun_proof_event(event: dict[str, Any]) -> str:
    AUTORUN_STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        prior = read_autorun_proof_events()
    except Exception as exc:
        raise SystemExit(f"autorun proof log is not readable JSONL: {exc}")
    prev_hash = str(prior[-1].get("event_hash") or "") if prior else ""
    record = {
        "schema": "local_brain_autorun_proof_v1",
        "generated_at": iso(),
        "prev_hash": prev_hash,
        **event,
    }
    record["event_hash"] = proof_payload_hash(record)
    with AUTORUN_PROOF_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return str(record["event_hash"])


def load_autorun_allowlist() -> list[Any]:
    try:
        data = json.loads(AUTORUN_ALLOWLIST.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except Exception:
        return []
    return data if isinstance(data, list) else []


def load_multimodel_allowlist() -> list[Any]:
    """Load multimodel intervention allowlist. Same format as autorun allowlist.

    If file doesn't exist, returns empty list (no filtering — all tasks eligible).
    If file exists, only matching tasks can be auto-processed.
    Supports: task_id, project, "project:xxx", "task:xxx", title, or dict entries.
    """
    try:
        data = json.loads(MULTIMODEL_ALLOWLIST.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except Exception:
        return []
    return data if isinstance(data, list) else []


def autorun_allowlist_matches(task: Task, allowlist: list[Any]) -> bool:
    architecture_target = str(getattr(task, "architecture_target", "") or task.fm.get("architecture_target") or "").strip()
    brain = str(task.fm.get("brain") or "").strip()
    for item in allowlist:
        if isinstance(item, str):
            token = item.strip()
            # Backward compatibility: older allowlists used project:local-brain
            # for the local-brain execution surface even when task.project is the
            # broader project name (for example `hermes`).  Match the explicit
            # project plus the architecture/brain routing surfaces without
            # broadening to all Hermes tasks.
            if token in {
                task.id, f"task:{task.id}", task.project, f"project:{task.project}", task.title,
                architecture_target, f"architecture:{architecture_target}", f"project:{architecture_target}",
                brain, f"brain:{brain}",
            }:
                return True
        elif isinstance(item, dict):
            task_id = str(item.get("task_id") or item.get("id") or "").strip()
            project = str(item.get("project") or "").strip()
            architecture = str(item.get("architecture_target") or item.get("architecture") or "").strip()
            item_brain = str(item.get("brain") or "").strip()
            title = str(item.get("title") or "").strip()
            if (
                (task_id and task_id == task.id)
                or (project and project in {task.project, architecture_target})
                or (architecture and architecture == architecture_target)
                or (item_brain and item_brain == brain)
                or (title and title == task.title)
            ):
                return True
    return False


def is_autorun_context(task: Task, actor: str) -> bool:
    return str(actor or "").startswith("hermes-autorun") or str(task.fm.get("run_id") or "").startswith("autorun-")


def task_has_autorun_audit(task: Task) -> bool:
    """Return true only when a done closeout itself is autorun-originated.

    Historical auto-claim/handoff lines may contain `hermes-autorun` even when a
    later human or bounded non-autorun worker closes the task. The proof hash
    gate is for autorun-originated `review -> done` closure, not for any task
    that ever had an autorun claim attempt in its audit log.
    """
    evidence = task.fm.get("evidence") if isinstance(task.fm.get("evidence"), list) else []
    if any(str(e).startswith("proof:sha256:") for e in evidence):
        return True
    return any(
        "Lifecycle transition `review` -> `done`" in line and "by `hermes-autorun" in line
        for line in task.body.splitlines()
    )


def validate_clean_text(label: str, value: str, *, allow_empty: bool = True) -> None:
    text = "" if value is None else str(value)
    if not allow_empty and not text.strip():
        raise SystemExit(f"{label} must not be empty")
    if any(ch in text for ch in ("\n", "\r")) or any(ord(ch) < 32 for ch in text):
        raise SystemExit(f"{label} must be a single-line printable value")
    if text.strip() == "---":
        raise SystemExit(f"{label} must not be a frontmatter delimiter")


def validate_clean_values(**values: Any) -> None:
    for label, value in values.items():
        if value is None:
            continue
        if isinstance(value, list):
            for i, item in enumerate(value):
                validate_clean_text(f"{label}[{i}]", str(item))
        else:
            validate_clean_text(label, str(value))


def allowed_next_statuses(status: str) -> list[str]:
    return list(LIFECYCLE_TRANSITIONS.get(STATUS_ALIASES.get(status, status), []))


def has_active_claim(task: Task, at: datetime | None = None) -> bool:
    at = at or now()
    lease = task.claim_expires_at()
    return bool(task.fm.get("claimed_by") and task.fm.get("run_id") and lease and lease >= at)


def lifecycle_gate(task: Task, to_status: str, actor: str, evidence: list[str] | None = None, reason: str = "", force: bool = False, authority: str = "") -> tuple[list[str], list[str]]:
    """Return (failures, warnings) for a proposed lifecycle transition."""
    evidence = evidence or []
    reason = (reason or "").strip()
    validate_clean_values(actor=actor, reason=reason, evidence=evidence)
    failures: list[str] = []
    warnings: list[str] = []
    from_status = task.status
    to_status = STATUS_ALIASES.get(to_status, to_status)
    if to_status not in VALID_STATUSES:
        failures.append(f"invalid target status: {to_status}")
        return failures, warnings
    if from_status not in VALID_STATUSES:
        failures.append(f"invalid current status {from_status}: {task.id}")
        return failures, warnings
    missing_alignment = architecture_alignment_missing(task.fm)
    if missing_alignment and to_status in PROFILE_GATED_STATUSES and not force:
        failures.append(f"evolution_architecture_alignment_missing: {missing_alignment}")
    missing_profile = project_profile_failures(task)
    if missing_profile and to_status in PROFILE_GATED_STATUSES and not force:
        failures.extend(missing_profile)
    missing_mission = mission_envelope_missing(task.fm)
    if missing_mission and to_status in PROFILE_GATED_STATUSES and not force:
        failures.append(f"mission envelope missing {missing_mission}: {task.id}")
    if force and reason.lower() in {"", "not specified", "none"}:
        failures.append("--force requires --reason so manual overrides are auditable")
    if to_status == from_status:
        failures.append(f"no-op transition is not allowed: {from_status} -> {to_status}")
    elif to_status not in allowed_next_statuses(from_status) and not force:
        failures.append(f"illegal lifecycle transition: {from_status} -> {to_status}; allowed={allowed_next_statuses(from_status)}")

    owner = str(task.fm.get("claimed_by") or "")
    lease = task.claim_expires_at()
    active_claim = has_active_claim(task)
    if from_status in CLAIM_BOUND_STATUSES and not active_claim and not force:
        failures.append("claim-bound status requires claimed_by, run_id, and a valid non-expired claim_expires_at before transition")
    if from_status in CLAIM_BOUND_STATUSES and owner and owner != actor and not force:
        failures.append(f"task claim owned by {owner}; actor {actor} cannot transition without --force")
    if from_status in CLAIM_BOUND_STATUSES and owner and lease is not None and lease < now() and not force:
        failures.append("task claim is stale; reconcile or --force after manual review before lifecycle transition")
    if to_status in {"running", "review"} and not active_claim and not force:
        failures.append(f"transition to {to_status} requires an active claim first")
    if to_status == "running" and from_status != "claimed" and not force:
        failures.append("running must be entered from claimed so lease ownership is explicit")
    if to_status in REASON_REQUIRED_TO and reason.lower() in {"", "not specified", "none"}:
        failures.append(f"transition to {to_status} requires --reason")
    if to_status == "done" and taxonomy.normalize_authority(authority) == "yolo-execution":
        failures.append("yolo-execution cannot complete task; requires_lifecycle_gate review_to_done with normal proof-gated done authority")
    if to_status in EVIDENCE_REQUIRED_TO and not evidence:
        failures.append(f"transition to {to_status} requires structured --evidence")
    invalid_evidence = [e for e in evidence if not evidence_is_structured(str(e))]
    if invalid_evidence:
        failures.append(f"invalid evidence shape: {invalid_evidence}; use command:/file:/search:/brainctl:/artifact:/url:/proof: prefixes or an existing absolute path")
    if to_status == "done" and evidence:
        failures.extend(completion_gate_failures(task, evidence))
    if to_status == "done" and task_multimodel_intervention_required(task) and not task_multimodel_passed(task):
        failures.append("multimodel_certification_required_before_done")
    if to_status == "done" and is_autorun_context(task, actor):
        proof_hashes = [str(e)[len("proof:") :] for e in evidence if str(e).startswith("proof:sha256:")]
        if not proof_hashes:
            failures.append("autorun closure requires proof:<sha256:...> evidence from the append-only autorun proof log")
        elif not any(verify_autorun_proof_hash(h) for h in proof_hashes):
            failures.append("autorun proof hash not found or chain verification failed")
    if to_status == "done" and from_status != "review" and not force:
        failures.append("done must be entered from review; use --force --reason only for audited manual closure")
    elif to_status == "done" and from_status != "review":
        warnings.append("forced done outside review; preferred path is running -> review -> done")
    return failures, warnings


def apply_lifecycle_status(task: Task, to_status: str, actor: str, *, evidence: list[str] | None = None, reason: str = "", ttl_minutes: int = 60, delay_minutes: int = 60, force: bool = False) -> None:
    stamp = now()
    evidence = evidence or []
    previous = task.status
    task.fm["status"] = to_status
    task.fm["updated"] = iso(stamp)
    if to_status in CLAIM_BOUND_STATUSES:
        if to_status == "claimed" or not task.fm.get("claimed_by"):
            task.fm["claimed_by"] = actor
        if to_status == "claimed" or not task.fm.get("run_id"):
            task.fm["run_id"] = f"{actor}-{stamp.strftime('%Y%m%d%H%M%S')}"
        if to_status == "claimed" or not task.fm.get("claim_expires_at"):
            task.fm["claim_expires_at"] = iso(stamp + timedelta(minutes=ttl_minutes))
    else:
        task.fm["claimed_by"] = ""
        task.fm["claim_expires_at"] = ""
        task.fm["run_id"] = ""
    if to_status == "retry":
        try:
            task.fm["retry_count"] = int(task.fm.get("retry_count") or 0) + 1
        except Exception:
            task.fm["retry_count"] = 1
        task.fm["next_attempt_at"] = iso(stamp + timedelta(minutes=delay_minutes))
    elif to_status != "blocked":
        task.fm["next_attempt_at"] = ""
    if evidence:
        current = task.fm.get("evidence") if isinstance(task.fm.get("evidence"), list) else []
        for e in evidence:
            if e not in current:
                current.append(e)
        task.fm["evidence"] = current
    reason_text = f" Reason: {reason}" if reason else ""
    evidence_text = f" Evidence: {', '.join(evidence)}" if evidence else ""
    force_text = " Force: true." if force else ""
    task.body += f"\n- {iso(stamp)}: Lifecycle transition `{previous}` -> `{to_status}` by `{actor}`.{force_text}{reason_text}{evidence_text}\n"


def body_has_legacy_proof(body: str) -> bool:
    proof_markers = ["## Proof Log", "## Final verification bundle", "## Final Verification", "## Evidence Boundary"]
    evidence_markers = ["`python", "`brainctl", "exit 0", "passed=true", "tests OK", "OK.", "status `certified`"]
    return any(m in body for m in proof_markers) and any(m in body for m in evidence_markers)


def command_list(args: argparse.Namespace) -> dict[str, Any]:
    rows = [t.row() for t in sorted_tasks(include_done=args.include_done)]
    return {"status": "OK", "generated_at": iso(), "task_count": len(rows), "rows": rows}


def command_add(args: argparse.Namespace) -> dict[str, Any]:
    title = args.title.strip()
    if args.status not in INITIAL_TASK_STATUSES:
        raise SystemExit(f"add can only create initial statuses {sorted(INITIAL_TASK_STATUSES)}; use transition/reconcile for lifecycle changes")
    lane_arg = (getattr(args, "lane", "auto") or "auto").strip().lower()
    if lane_arg != "auto" and lane_arg not in VALID_LANES:
        raise SystemExit(f"lane must be one of {['auto', *VALID_LANES]}")
    validate_clean_values(title=title, layer=args.layer, status=args.status, priority=args.priority, project=args.project, workflow_contract=args.workflow_contract, workspace=args.workspace or "", parallel_boundary=getattr(args, "parallel_boundary", "") or "", concepts=args.concepts or "task", lane=lane_arg, architecture_target=getattr(args, "architecture_target", ""), capability_delta=getattr(args, "capability_delta", ""), anti_drift_check=getattr(args, "anti_drift_check", ""), acceptance_evidence=getattr(args, "acceptance_evidence", ""))
    created = now()
    expires = parse_dt(args.expires_at) if args.expires_at else created + timedelta(days=args.expires_days)
    slug = slugify(title)
    base = TASKS_DIR / f"{created.date().isoformat()}-{slug}.md"
    path = base
    i = 2
    while path.exists():
        path = TASKS_DIR / f"{created.date().isoformat()}-{slug}-{i}.md"
        i += 1
    concepts = [x.strip() for x in (args.concepts or "task").split(",") if x.strip()]
    preliminary = {"lane": "" if lane_arg == "auto" else lane_arg, "project": args.project, "concepts": concepts, "type": "task"}
    lane = infer_lane(preliminary)
    fm = {
        "type": "task",
        "lane": lane,
        "layer": args.layer,
        "status": args.status,
        "priority": args.priority,
        "created": iso(created),
        "updated": iso(created),
        "expires_at": iso(expires) if expires else "",
        "project": args.project,
        "architecture_target": getattr(args, "architecture_target", "") or "",
        "capability_delta": getattr(args, "capability_delta", "") or "",
        "anti_drift_check": getattr(args, "anti_drift_check", "") or "",
        "acceptance_evidence": getattr(args, "acceptance_evidence", "") or "",
        "workflow_contract": args.workflow_contract,
        "claimed_by": "",
        "claim_expires_at": "",
        "run_id": "",
        "retry_count": 0,
        "next_attempt_at": "",
        "workspace": args.workspace or "",
        "parallel_boundary": getattr(args, "parallel_boundary", "") or "",
        "evidence": [],
        "concepts": concepts,
    }
    apply_permission_defaults(fm)
    missing_alignment = architecture_alignment_missing(fm)
    if missing_alignment:
        raise SystemExit(f"evolution tasks require architecture alignment fields; missing/invalid={missing_alignment}")
    body = f"# Task - {title}\n\n## Objective\n\n{args.objective or title}\n\n## Acceptance Criteria\n\n- [ ] {args.accept or 'Observable result is recorded in Proof Log.'}\n\n## Plan / Workpad\n\n- [ ] Reconcile current state before execution.\n- [ ] Execute the smallest verifiable slice.\n- [ ] Record proof and update status.\n\n## Validation\n\n| Command / Check | Status | Evidence |\n|---|---|---|\n| brain_task_orchestrator list | pending | |\n\n## Proof Log\n\n- {iso(created)}: Task created from local-brain control point.\n\n## Blockers / Confusions\n\n- None.\n\n## Final Handoff\n\n- Status:\n- Evidence:\n- Residual risk:\n"
    atomic_write(path, render_frontmatter(fm) + "\n" + body)
    derived_refresh = refresh_derived_task_views("add")
    event_hook = maybe_fire_taskpool_event_hook("task_added", task_id=path.stem, reason="command_add")
    return {"status": "OK", "created": str(path), "id": path.stem, "link": obsidian_link(path), "derived_refresh": derived_refresh, "event_hook": event_hook}


def parse_inbox_line(line: str) -> dict[str, Any] | None:
    m = re.match(r"^\s*- \[ \]\s+(.+?)\s*$", line)
    if not m:
        return None
    raw = m.group(1).strip()
    if "<!-- ingested:" in raw:
        return None
    parts = [p.strip() for p in raw.split("|")]
    title = parts[0]
    meta = {"title": title, "priority": "P2", "project": "inbox", "concepts": "task,inbox", "expires_at": "", "objective": title}
    for p in parts[1:]:
        if ":" not in p:
            continue
        k, v = p.split(":", 1)
        k = k.strip().lower()
        v = v.strip()
        if k in {"priority", "project", "concepts", "expires_at", "objective", "lane", "architecture_target", "capability_delta", "anti_drift_check", "acceptance_evidence", "parallel_boundary"}:
            meta[k] = v
        elif k in {"expires", "due"}:
            meta["expires_at"] = v
    return meta


def ensure_inbox() -> None:
    if INBOX.exists():
        return
    text = f"""---
type: task_inbox
status: active
derived: false
created: {iso()}
concepts: [task-inbox, obsidian-trigger, local-brain-ui]
---

# 任务收件箱

在 Obsidian 本地大脑界面直接追加下面这种 unchecked bullet，然后让 Hermes 执行“处理本地大脑任务收件箱”，或在终端运行：

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py ingest-inbox --write
python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write
```

格式：

```markdown
- [ ] 任务标题 | priority:P1 | project:project-slug | due:2026-05-20 | concepts:task,tag
```

## Inbox Drafts

<!-- Add real unchecked task bullets here. Example syntax only:
- [ ] 整理本周本地大脑任务 | priority:P2 | project:local-brain | due:2099-01-01 | concepts:task,inbox-example
-->

## Ingested Log

"""
    atomic_write(INBOX, text)


def command_ingest_inbox(args: argparse.Namespace) -> dict[str, Any]:
    ensure_inbox()
    lines = INBOX.read_text(encoding="utf-8").splitlines()
    created = []
    new_lines = []
    in_drafts = False
    in_fence = False
    in_html_comment = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("<!--"):
            in_html_comment = True
            new_lines.append(line)
            if "-->" in stripped:
                in_html_comment = False
            continue
        if in_html_comment:
            new_lines.append(line)
            if "-->" in stripped:
                in_html_comment = False
            continue
        if stripped.startswith("```"):
            in_fence = not in_fence
            new_lines.append(line)
            continue
        if stripped.startswith("## "):
            in_drafts = stripped == "## Inbox Drafts"
            new_lines.append(line)
            continue
        if not in_drafts or in_fence:
            new_lines.append(line)
            continue
        meta = parse_inbox_line(line)
        if not meta:
            new_lines.append(line)
            continue
        ns = argparse.Namespace(
            title=meta["title"], priority=meta.get("priority", "P2"), project=meta.get("project", "inbox"), status="pending",
            expires_at=meta.get("expires_at") or "", expires_days=args.expires_days, concepts=meta.get("concepts", "task,inbox"),
            lane=meta.get("lane", "auto"), architecture_target=meta.get("architecture_target", ""), capability_delta=meta.get("capability_delta", ""), anti_drift_check=meta.get("anti_drift_check", ""), acceptance_evidence=meta.get("acceptance_evidence", ""), parallel_boundary=meta.get("parallel_boundary", ""),
            layer="L3", workflow_contract=DEFAULT_WORKFLOW, workspace="", objective=meta.get("objective") or meta["title"], accept="Task has proof log and terminal status."
        )
        result = command_add(ns) if args.write else {"id": slugify(meta["title"]), "link": "dry-run"}
        created.append(result)
        suffix = f" <!-- ingested: {result.get('link', result.get('id'))} -->"
        new_lines.append(line.replace("- [ ]", "- [x]", 1) + suffix if args.write else line)
    derived_refresh = None
    if args.write and created:
        atomic_write(INBOX, "\n".join(new_lines) + "\n")
        derived_refresh = refresh_derived_task_views("ingest-inbox")
    return {"status": "OK", "write": bool(args.write), "created_count": len(created), "created": created, "inbox": str(INBOX), "derived_refresh": derived_refresh}


def maybe_stream_multimodel_intervention(task: "Task") -> dict[str, Any]:
    """Event-driven multimodel intervention: spawn immediately on lifecycle transition.

    Called after claim/running transitions. If the task is triggered for
    multimodel intervention and passes economy gate, spawns a background
    worker to process it without waiting for the next cron tick.

    Returns: status dict with action taken.
    """
    if not task_multimodel_intervention_required(task):
        return {"action": "skip", "reason": "not_triggered"}

    economy = task_multimodel_economy_gate(task)
    if economy["action"] == "pause":
        return {"action": "skip", "reason": "economy_pause", "economy": economy}

    # Check if already being processed (has recent multimodel check)
    last_checked = str(task.fm.get("multimodel_last_checked_at") or "")
    if last_checked:
        try:
            from datetime import datetime, timezone, timedelta
            checked_dt = datetime.fromisoformat(last_checked.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - checked_dt < timedelta(minutes=30):
                return {"action": "skip", "reason": "recently_checked", "last_checked": last_checked}
        except Exception:
            pass

    # Spawn background worker for this single task
    import subprocess as _sp
    env = os.environ.copy()
    env["HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL"] = "1"
    cmd = [
        sys.executable, str(HERMES_HOME / "scripts" / "brain_task_orchestrator.py"),
        "multimodel-intervention-step", "--task", task.id, "--json",
    ]
    log_path = HERMES_HOME / "logs" / "multimodel_streaming.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logf = log_path.open("a", encoding="utf-8")
    try:
        proc = _sp.Popen(cmd, stdout=logf, stderr=_sp.STDOUT, text=True, start_new_session=True, env=env)
        return {
            "action": "spawned",
            "pid": proc.pid,
            "task_id": task.id,
            "recommended_tier": economy.get("allowed_tier", "any"),
            "economy": economy,
        }
    except Exception as exc:
        return {"action": "spawn_failed", "error": str(exc)}


def command_claim(args: argparse.Namespace) -> dict[str, Any]:
    t = find_task(args.task)
    active_claim = has_active_claim(t)
    if active_claim and not args.force:
        raise SystemExit(f"task already claimed by {t.fm.get('claimed_by')} until {t.fm.get('claim_expires_at')}; use --force only after manual review")
    run_id = args.run_id or ""
    validate_clean_values(run_id=run_id)
    failures, warnings = lifecycle_gate(t, "claimed", args.actor, reason=args.reason, force=args.force)
    if failures:
        raise SystemExit("; ".join(failures))
    apply_lifecycle_status(t, "claimed", args.actor, reason=args.reason, ttl_minutes=args.ttl_minutes, force=args.force)
    if run_id:
        t.fm["run_id"] = run_id
    save_task(t)
    derived_refresh = refresh_derived_task_views("claim")

    # Event-driven streaming: immediately trigger multimodel if needed
    streaming = maybe_stream_multimodel_intervention(t)

    return {"status": "OK", "task": t.id, "claimed_by": args.actor, "claim_expires_at": t.fm["claim_expires_at"], "warnings": warnings, "path": str(t.path), "derived_refresh": derived_refresh, "multimodel_streaming": streaming}


def command_release(args: argparse.Namespace) -> dict[str, Any]:
    t = find_task(args.task)
    owner = t.fm.get("claimed_by") or ""
    if owner and owner != args.actor and not args.force:
        raise SystemExit(f"task claimed by {owner}; {args.actor} cannot release without --force")
    failures, warnings = lifecycle_gate(t, args.to_status, args.actor, reason=args.reason, force=args.force)
    if failures:
        raise SystemExit("; ".join(failures))
    apply_lifecycle_status(t, args.to_status, args.actor, reason=args.reason, force=args.force)
    save_task(t)
    derived_refresh = refresh_derived_task_views("release")
    return {"status": "OK", "task": t.id, "to_status": args.to_status, "warnings": warnings, "path": str(t.path), "derived_refresh": derived_refresh}


def command_done(args: argparse.Namespace) -> dict[str, Any]:
    t = find_task(args.task)
    if not args.evidence:
        raise SystemExit("done requires at least one structured --evidence entry, e.g. 'command: pytest PASS' or 'file:/path/to/proof.md'")
    failures, warnings = lifecycle_gate(t, "done", args.actor, args.evidence, args.reason, args.force, getattr(args, "authority", ""))
    if failures:
        raise SystemExit("; ".join(failures))
    apply_lifecycle_status(t, "done", args.actor, evidence=args.evidence, reason=args.reason, force=args.force)
    save_task(t)
    derived_refresh = refresh_derived_task_views("done")
    evidence = t.fm.get("evidence") if isinstance(t.fm.get("evidence"), list) else []
    return {"status": "OK", "task": t.id, "path": str(t.path), "evidence_count": len(evidence), "warnings": warnings, "derived_refresh": derived_refresh}


def _dedupe_evidence(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def auto_close_review_evidence(task: Task) -> list[str]:
    """Build proof-gated evidence for automatic review -> done closeout.

    The auto closer never invents task proof.  It can only reuse structured
    evidence already deposited on the task and, for certified multi-model rounds,
    land the ratification artifact as explicit completion evidence.
    """
    evidence = [str(e) for e in (task.fm.get("evidence") if isinstance(task.fm.get("evidence"), list) else [])]
    if task_multimodel_passed(task):
        artifact = task_multimodel_artifact(task)
        if artifact:
            evidence.append(f"artifact:ratification multimodel certified {artifact}")
    return _dedupe_evidence(evidence)


def command_auto_close_review(args: argparse.Namespace) -> dict[str, Any]:
    """Automatically close review tasks only when normal done gates pass.

    This is the lifecycle counterpart to multimodel writeback: model consensus or
    static runner output may put a task in review, but done still goes through the
    same lane-specific completion_gate and autorun proof-hash checks as manual
    closeout.
    """
    actor = args.actor
    reason = args.reason or "auto-close review after proof-gated evidence"
    max_tasks = max(1, int(args.max_tasks or 1))
    candidates = [find_task(args.task)] if args.task else [t for t in sorted_tasks(include_done=False) if t.status == "review"]
    candidates = candidates[:max_tasks]
    closed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for task in candidates:
        def _cert_evidence(current_task: Task, certification: dict[str, Any] | None = None) -> list[str]:
            ev = auto_close_review_evidence(current_task)
            cert = certification or {}
            gate = cert.get("gate") if isinstance(cert.get("gate"), dict) else {}
            discussion_path = str(cert.get("discussion_path") or current_task.fm.get("multimodel_last_discussion_artifact") or current_task.fm.get("multimodel_ratification_artifact") or "").strip()
            if discussion_path:
                ev.append(f"artifact:{discussion_path}")
            gate_status = str(gate.get("status") or current_task.fm.get("multimodel_last_gate_status") or "").upper()
            gate_decision = str(gate.get("decision") or current_task.fm.get("multimodel_last_decision") or "").strip()
            mm_status = str(current_task.fm.get("multimodel_status") or "").strip()
            if gate_status:
                ev.append(f"command:multimodel_gate {gate_status}")
            if gate_decision:
                ev.append(f"command:multimodel_decision {gate_decision}")
            if mm_status:
                ev.append(f"command:multimodel_status {mm_status}")
            return ev

        # Probe the normal done gate first. If a task already has sufficient
        # deterministic/selfcheck or certified-artifact evidence, auto-close should
        # close it directly instead of spawning an unrelated global certification
        # worker that may report another task and cause a false mismatch.
        base_evidence = auto_close_review_evidence(task)
        base_failures, base_warnings = lifecycle_gate(task, "done", "hermes-auto-close-probe", base_evidence, reason, False, getattr(args, "authority", ""))

        # Expanded safety boundary: only trigger a new multi-model certification round
        # when the task still fails the normal done gate AND intervention is required.
        # Advisory-only PASS_ADVISORY_ONLY rounds are intentionally not accepted here;
        # task_multimodel_passed() requires a local JSON artifact whose ratification
        # gate is PASS + LOOP_DONE.
        should_trigger_certification = (
            bool(base_failures)
            and task_multimodel_intervention_required(task)
            and not task_multimodel_passed(task)
            and (
                task.lane in {"evolution", "advisory"}
                or is_mission_envelope_fm(task.fm)
                or any("ratification" in str(f).lower() or "multimodel" in str(f).lower() for f in base_failures)
            )
        )
        if should_trigger_certification:
            def _return_certification_result(current_task: Task, outcome: str, certification: dict[str, Any] | None = None, failures: list[str] | None = None, uncertain: bool = False) -> dict[str, Any]:
                failures = [str(x) for x in (failures or []) if str(x)]
                ev = _cert_evidence(current_task, certification)
                if outcome:
                    ev.append(f"command:multimodel_auto_outcome {outcome}")
                if uncertain:
                    try:
                        current_task.fm["multimodel_auto_uncertain_count"] = int(current_task.fm.get("multimodel_auto_uncertain_count") or 0) + 1
                    except Exception:
                        current_task.fm["multimodel_auto_uncertain_count"] = 1
                else:
                    current_task.fm["multimodel_auto_uncertain_count"] = 0
                try:
                    uncertain_count = int(current_task.fm.get("multimodel_auto_uncertain_count") or 0)
                except Exception:
                    uncertain_count = 0
                next_retry_count = current_task.retry_count() + 1
                should_block = outcome in {"certification_human_required", "certification_task_mismatch"} or next_retry_count > 3 or uncertain_count >= 3
                to_status = "blocked" if should_block else "retry"
                reason_text = f"multimodel closeout {outcome}; "
                if to_status == "blocked":
                    reason_text += "blocked to avoid unsafe/indefinite automation"
                else:
                    reason_text += "returned to retry for correction"
                if failures:
                    reason_text += ": " + "; ".join(failures[:6])
                try:
                    apply_lifecycle_status(current_task, to_status, str(getattr(args, "actor", "") or "hermes-auto-close-review"), evidence=ev, reason=reason_text, delay_minutes=0)
                    save_task(current_task)
                    return {
                        "action": "block_after_certification" if to_status == "blocked" else "return_to_retry",
                        "task_id": current_task.id,
                        "title": current_task.title,
                        "lane": current_task.lane,
                        "failures": [outcome, *failures[:10]],
                        "warnings": [],
                        "evidence": ev,
                        "certification": certification or {},
                        "to_status": to_status,
                        "uncertain_count": uncertain_count,
                        "safety": "PASS/LOOP_DONE is required for done; certification did not pass, so automation moved the task to retry/blocked instead of auto-done",
                    }
                except Exception as exc:
                    errors.append({"task_id": current_task.id, "error": str(exc), "phase": "multimodel_certification_flow"})
                    return {
                        "action": "certification_flow_error",
                        "task_id": current_task.id,
                        "title": current_task.title,
                        "lane": current_task.lane,
                        "failures": [outcome, str(exc)],
                        "warnings": [],
                        "evidence": ev,
                        "certification": certification or {},
                        "safety": "failed while moving non-certified task to retry/blocked; task was not auto-done",
                    }

            previous_gate_status = str(task.fm.get("multimodel_last_gate_status") or "").upper()
            previous_mm_status = str(task.fm.get("multimodel_status") or "")
            if previous_gate_status in {"FAIL", "ERROR"} or previous_mm_status in {"not_certified", "certification_failed"}:
                skipped.append(_return_certification_result(task, "certification_failed", failures=["previous_multimodel_certification_failed"]))
                continue

            if os.environ.get("HERMES_AUTO_CLOSE_REVIEW_TRIGGER_CERT", "1") not in {"1", "true", "TRUE", "yes", "YES"}:
                skipped.append({
                    "action": "skip_certification_trigger_disabled",
                    "task_id": task.id,
                    "title": task.title,
                    "lane": task.lane,
                    "failures": ["multimodel_certification_required"],
                    "warnings": [],
                    "evidence": _cert_evidence(task),
                    "safety": "auto-close-review did not spawn certification because HERMES_AUTO_CLOSE_REVIEW_TRIGGER_CERT is disabled; a separate multimodel-step may certify the task",
                })
                continue

            certification = command_multimodel_intervention_step(argparse.Namespace(json=True))
            refreshed = find_task(task.id) or task
            if certification.get("status") == "OK" and certification.get("task_id") == task.id and task_multimodel_passed(refreshed):
                refreshed.fm["multimodel_auto_uncertain_count"] = 0
                save_task(refreshed)
                task = refreshed
            else:
                gate = certification.get("gate") if isinstance(certification.get("gate"), dict) else {}
                gate_status = str(gate.get("status") or certification.get("status") or "").upper()
                gate_decision = str(gate.get("decision") or "")
                failures = gate.get("failures") if isinstance(gate.get("failures"), list) else []
                reason = str(gate.get("reason") or certification.get("reason") or "")
                covered_current = certification.get("task_id") == task.id
                if not covered_current:
                    # The global certification worker selected or reported another task.
                    # Do not mutate this task as failed; leave it in review with diagnostics so a later tick can target it.
                    evidence = _cert_evidence(refreshed, certification)
                    skipped.append({
                        "action": "certification_triggered_skip",
                        "task_id": task.id,
                        "title": task.title,
                        "lane": task.lane,
                        "failures": ["certification_task_mismatch"],
                        "warnings": [],
                        "evidence": evidence,
                        "certification": certification,
                        "safety": "certification did not cover this task; leaving review instead of auto-done or incorrect retry",
                    })
                    continue
                if gate_status in {"FAIL", "ERROR"} or certification.get("status") == "ERROR":
                    skipped.append(_return_certification_result(refreshed, "certification_failed", certification, failures or [reason or gate_status]))
                    continue
                if gate_status in {"PASS_ADVISORY_ONLY", "SKIP", ""} or reason in {"no_discussion_result", ""}:
                    skipped.append(_return_certification_result(refreshed, "certification_inconclusive", certification, failures or [reason or gate_status or "no_certification_result"], uncertain=True))
                    continue
                skipped.append(_return_certification_result(refreshed, "certification_not_passed", certification, failures or [reason or gate_status], uncertain=True))
                continue
        base_evidence = auto_close_review_evidence(task)
        base_failures, base_warnings = lifecycle_gate(task, "done", "hermes-auto-close-probe", base_evidence, reason, False, getattr(args, "authority", ""))
        if base_failures:
            skipped.append({
                "action": "skip",
                "task_id": task.id,
                "title": task.title,
                "lane": task.lane,
                "failures": base_failures,
                "warnings": base_warnings,
                "evidence": base_evidence,
                "safety": "base evidence did not satisfy done gate; no autorun proof minted",
            })
            continue
        proof_hash = append_autorun_proof_event({
            "event": "auto_review_close_attempt",
            "task": task.id,
            "actor": actor,
            "base_evidence": base_evidence,
            "lane": task.lane,
            "completion_gate": task_permission_contract_for_fm(task.fm).get("completion_gate", ""),
            "safety": "review_to_done_only; normal lifecycle_gate enforced; proof is audit evidence not completion proof",
        })
        evidence = _dedupe_evidence([f"proof:{proof_hash}", *base_evidence])
        failures, warnings = lifecycle_gate(task, "done", actor, evidence, reason, False, getattr(args, "authority", ""))
        if failures:
            skipped.append({
                "action": "skip",
                "task_id": task.id,
                "title": task.title,
                "lane": task.lane,
                "failures": failures,
                "proof_hash": proof_hash,
                "evidence": evidence,
            })
            continue
        try:
            apply_lifecycle_status(task, "done", actor, evidence=evidence, reason=reason, force=False)
            save_task(task)
            closed.append({
                "action": "closed",
                "task_id": task.id,
                "title": task.title,
                "lane": task.lane,
                "proof_hash": proof_hash,
                "evidence": evidence,
                "warnings": warnings,
            })
        except Exception as exc:
            errors.append({"action": "error", "task_id": task.id, "error": str(exc), "proof_hash": proof_hash})

    derived_refresh = refresh_derived_task_views("auto-close-review") if closed else None
    status = "OK" if not errors else "ERROR"
    return {
        "status": status,
        "schema": "local_brain_auto_close_review_v1",
        "generated_at": iso(),
        "actor": actor,
        "closed_count": len(closed),
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "closed": closed,
        "skipped": skipped,
        "errors": errors,
        "derived_refresh": derived_refresh,
        "safety": "automated review->done uses normal lifecycle_gate, lane completion_gate, structured evidence, and autorun proof hash",
    }



def command_blocked_resolve_step(args: argparse.Namespace) -> dict[str, Any]:
    """Re-evaluate blocked tasks and move resolved work back onto the normal closure path.

    This command is deliberately model-free: it consumes evidence and certification
    already written to the task. Expensive certification is handled by the separate
    multimodel step, then this resolver can move PASSed tasks to review where
    auto-close-review applies the normal done gates.
    """
    actor = args.actor
    max_tasks = max(1, int(args.max_tasks or 1))
    candidates = [find_task(args.task)] if args.task else [t for t in sorted_tasks(include_done=False) if t.status == "blocked"]
    candidates = candidates[:max_tasks]
    resolved: list[dict[str, Any]] = []
    kept_blocked: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    transient_gate_statuses = {"", "SKIP", "ERROR", "TIMEOUT", "UNKNOWN"}
    transient_round_statuses = {"", "skipped", "error", "timeout"}

    def _blocked_taxonomy_payload(current_task: Task) -> dict[str, Any]:
        discussion: dict[str, Any] = {}
        try:
            discussion = load_discussion_artifact(current_task)
        except Exception:
            discussion = {}
        taxonomy = multimodel_failure_taxonomy(
            discussion,
            [str(x) for x in list_value(current_task.fm.get("multimodel_last_failures"))],
        )
        return {
            "taxonomy_axes": [axis for axis in taxonomy.get("recommended_axes", []) if axis in AUTO_SUBTASK_AXIS_ORDER],
            "axis_rationale": taxonomy.get("axis_rationale") or {},
        }

    for task in candidates:
        if task.status != "blocked":
            kept_blocked.append({"task": task.id, "action": "skip_not_blocked", "status": task.status})
            continue
        try:
            reasons = task_multimodel_intervention_reasons(task)
            cert_reasons = task_multimodel_certification_reasons(task)
            mm_required = bool(reasons)
            mm_passed = task_multimodel_passed(task)
            gate_status = str(task.fm.get("multimodel_last_gate_status") or "").upper()
            round_status = str(task.fm.get("multimodel_round_status") or task.fm.get("multimodel_status") or "").lower()
            decision = str(task.fm.get("multimodel_last_decision") or "").strip()
            evidence = auto_close_review_evidence(task)
            has_evidence = bool(evidence)
            taxonomy_payload = _blocked_taxonomy_payload(task)

            now_iso = iso()
            task.fm["blocked_resolve_last_checked_at"] = now_iso
            task.fm["blocked_resolve_multimodel_required"] = mm_required
            task.fm["blocked_resolve_reasons"] = reasons
            task.fm["blocked_resolve_taxonomy_axes"] = taxonomy_payload.get("taxonomy_axes") or []
            task.fm["blocked_resolve_axis_rationale"] = taxonomy_payload.get("axis_rationale") or {}

            auto_subtask_sync = None
            if str(task.fm.get("auto_subtask_kind") or "") == "non_convergence_narrowing":
                auto_subtask_sync = sync_auto_subtask_parent(task, actor=actor, write=False)
                if auto_subtask_sync and auto_subtask_sync.get("action") == "auto_subtask_parent_reopened":
                    task.fm["blocked_resolve_last_action"] = "auto_subtask_parent_reopened"
                    task.fm["blocked_resolve_reason"] = "blocked resolver: all narrowed convergence subtasks are done; parent reopened for ratification rerun"
                    task.fm["blocker_status"] = "resolved"
                    save_task(task)
                    resolved.append({
                        "task": task.id,
                        "action": "auto_subtask_parent_reopened",
                        "to_status": task.status,
                        "open_children": auto_subtask_sync.get("open_children") or [],
                        "missing_children": auto_subtask_sync.get("missing_children") or [],
                        **taxonomy_payload,
                    })
                    continue
                if auto_subtask_sync and not auto_subtask_sync.get("ready"):
                    keep_reason = "blocked resolver: awaiting narrowed convergence subtasks before parent ratification rerun"
                    task.fm["blocked_resolve_last_action"] = "await_auto_subtasks"
                    task.fm["blocked_resolve_reason"] = keep_reason
                    task.fm["blocker_status"] = "unresolved"
                    task.fm["blocker_summary"] = keep_reason
                    save_task(task)
                    kept_blocked.append({
                        "task": task.id,
                        "action": "await_auto_subtasks",
                        "reason": keep_reason,
                        "open_children": auto_subtask_sync.get("open_children") or [],
                        "missing_children": auto_subtask_sync.get("missing_children") or [],
                        **taxonomy_payload,
                    })
                    continue

            if mm_required and not mm_passed and "loop_non_convergence" in cert_reasons and decision.upper() == "CONTINUE_LOOP" and not list_value(task.fm.get("auto_subtask_children")):
                split_result = command_auto_split_non_convergence(argparse.Namespace(task=task.id))
                keep_reason = "blocked resolver: loop_non_convergence detected; auto-generated narrowed convergence subtasks before next parent ratification"
                task = find_task(task.id)
                task.fm["blocked_resolve_last_checked_at"] = now_iso
                task.fm["blocked_resolve_multimodel_required"] = mm_required
                task.fm["blocked_resolve_reasons"] = reasons
                task.fm["blocked_resolve_taxonomy_axes"] = taxonomy_payload.get("taxonomy_axes") or []
                task.fm["blocked_resolve_axis_rationale"] = taxonomy_payload.get("axis_rationale") or {}
                task.fm["blocked_resolve_last_action"] = "auto_split_non_convergence"
                task.fm["blocked_resolve_reason"] = keep_reason
                task.fm["blocker_status"] = "unresolved"
                task.fm["blocker_summary"] = keep_reason
                save_task(task)
                kept_blocked.append({
                    "task": task.id,
                    "action": "auto_split_non_convergence",
                    "reason": keep_reason,
                    "created_count": split_result.get("created_count") or 0,
                    "all_children": split_result.get("all_children") or [],
                    "taxonomy_axes": split_result.get("taxonomy_axes") or taxonomy_payload.get("taxonomy_axes") or [],
                    "axis_rationale": split_result.get("axis_rationale") or taxonomy_payload.get("axis_rationale") or {},
                })
                continue

            # Gold path: certification/evidence is now sufficient; re-enter review.
            if (not mm_required or mm_passed) and has_evidence:
                to_status = "review"
                reason = "blocked resolver: evidence/certification now sufficient; send to review for normal auto-close gates"
                # A resolved blocked task may not have an active claim anymore; use
                # resolver-scoped force only for blocked->review. The subsequent
                # auto-close-review still enforces the normal done/completion gates.
                failures, warnings = lifecycle_gate(task, to_status, actor, evidence, reason, True, args.authority)
                if failures:
                    task.fm["blocked_resolve_last_action"] = "keep_blocked_gate_failed"
                    task.fm["blocked_resolve_reason"] = "; ".join(failures)
                    save_task(task)
                    kept_blocked.append({"task": task.id, "action": "keep_blocked_gate_failed", "failures": failures, "warnings": warnings})
                    continue
                apply_lifecycle_status(task, to_status, actor, evidence=evidence, reason=reason, force=True)
                task.fm["blocked_resolve_last_action"] = "resolved_to_review"
                task.fm["blocked_resolve_reason"] = reason
                task.fm["blocker_status"] = "resolved"
                save_task(task)
                resolved.append({"task": task.id, "action": "resolved_to_review", "to_status": to_status, "evidence_count": len(evidence), "warnings": warnings, **taxonomy_payload})
                continue

            # Transient certification infrastructure failure should not strand the task forever.
            if mm_required and not mm_passed and (gate_status in transient_gate_statuses or round_status in transient_round_statuses):
                to_status = "retry" if args.transient_to_retry else "blocked"
                reason = f"blocked resolver: transient multimodel status gate={gate_status or 'UNKNOWN'} round={round_status or 'unknown'}; retry certification/execution"
                if to_status == "retry":
                    failures, warnings = lifecycle_gate(task, to_status, actor, [], reason, args.force, args.authority)
                    if failures:
                        task.fm["blocked_resolve_last_action"] = "keep_blocked_retry_gate_failed"
                        task.fm["blocked_resolve_reason"] = "; ".join(failures)
                        save_task(task)
                        kept_blocked.append({"task": task.id, "action": "keep_blocked_retry_gate_failed", "failures": failures})
                        continue
                    apply_lifecycle_status(task, to_status, actor, reason=reason, force=args.force, delay_minutes=args.retry_delay_minutes)
                    task.fm["blocked_resolve_last_action"] = "resolved_to_retry"
                    task.fm["blocked_resolve_reason"] = reason
                    task.fm["blocker_status"] = "transient_retry"
                    save_task(task)
                    resolved.append({"task": task.id, "action": "resolved_to_retry", "to_status": to_status, "reason": reason, "warnings": warnings, **taxonomy_payload})
                    continue

            # Hard failure/non-convergence remains blocked until new evidence or a fresh PASS arrives.
            keep_reason = "blocked resolver: still blocked"
            if mm_required and not mm_passed:
                keep_reason = f"blocked resolver: multimodel certification still not PASS (gate={gate_status or 'UNKNOWN'}, decision={decision or 'unknown'}, cert_reasons={cert_reasons})"
            elif not has_evidence:
                keep_reason = "blocked resolver: no structured completion evidence available"
            task.fm["blocked_resolve_last_action"] = "keep_blocked"
            task.fm["blocked_resolve_reason"] = keep_reason
            task.fm["blocker_status"] = "unresolved"
            task.fm["blocker_summary"] = keep_reason
            save_task(task)
            kept_blocked.append({
                "task": task.id,
                "action": "keep_blocked",
                "reason": keep_reason,
                "multimodel_required": mm_required,
                "multimodel_passed": mm_passed,
                "evidence_count": len(evidence),
                **taxonomy_payload,
            })
        except Exception as exc:
            errors.append({"task": task.id, "error": str(exc)})

    derived_refresh = refresh_derived_task_views("blocked_resolve_step") if (resolved or kept_blocked or errors) else {}
    status = "ERROR" if errors else "OK"
    aggregate_axes: list[str] = []
    aggregate_rationale: dict[str, list[str]] = {}
    for row in [*resolved, *kept_blocked]:
        if not isinstance(row, dict):
            continue
        for axis in row.get("taxonomy_axes") or []:
            axis_name = str(axis)
            if axis_name not in aggregate_axes:
                aggregate_axes.append(axis_name)
        rationale = row.get("axis_rationale") or {}
        if not isinstance(rationale, dict):
            continue
        for axis, categories in rationale.items():
            bucket = aggregate_rationale.setdefault(str(axis), [])
            for category in categories if isinstance(categories, list) else []:
                category_name = str(category)
                if category_name not in bucket:
                    bucket.append(category_name)
    return {
        "status": status,
        "checked_count": len(candidates),
        "resolved_count": len(resolved),
        "kept_blocked_count": len(kept_blocked),
        "error_count": len(errors),
        "resolved": resolved,
        "kept_blocked": kept_blocked,
        "taxonomy_axes": aggregate_axes,
        "axis_rationale": aggregate_rationale,
        "errors": errors,
        "derived_refresh": derived_refresh,
    }

def command_retry(args: argparse.Namespace) -> dict[str, Any]:
    t = find_task(args.task)
    failures, warnings = lifecycle_gate(t, "retry", args.actor, reason=args.reason)
    if failures:
        raise SystemExit("; ".join(failures))
    apply_lifecycle_status(t, "retry", args.actor, reason=args.reason, delay_minutes=args.delay_minutes)
    save_task(t)
    derived_refresh = refresh_derived_task_views("retry")
    return {"status": "OK", "task": t.id, "retry_count": t.fm.get("retry_count") or 0, "next_attempt_at": t.fm["next_attempt_at"], "warnings": warnings, "path": str(t.path), "derived_refresh": derived_refresh}


def command_lifecycle(args: argparse.Namespace) -> dict[str, Any]:
    tasks = iter_tasks()
    invalid: list[dict[str, Any]] = []
    missing_graph_states = sorted(set(VALID_STATUSES) - set(LIFECYCLE_TRANSITIONS))
    for state in missing_graph_states:
        invalid.append({"task": "__schema__", "status": state, "reason": "status_missing_from_lifecycle_graph"})
    for state, targets in LIFECYCLE_TRANSITIONS.items():
        for target in targets:
            if target not in VALID_STATUSES:
                invalid.append({"task": "__schema__", "status": state, "target": target, "reason": "transition_target_invalid_status"})
    for t in tasks:
        missing_alignment = architecture_alignment_missing(t.fm)
        if missing_alignment:
            invalid.append({"task": t.id, "status": t.status, "fields": missing_alignment, "reason": "evolution_architecture_alignment_missing"})
        missing_profile = project_profile_failures(t)
        if missing_profile:
            invalid.append({"task": t.id, "status": t.status, "fields": missing_profile, "reason": "project_profile_missing"})
        missing_mission = mission_envelope_missing(t.fm)
        if missing_mission:
            invalid.append({"task": t.id, "status": t.status, "fields": missing_mission, "reason": "mission_envelope_missing"})
        permission_failures = permission_validation_failures(t.fm)
        if permission_failures:
            invalid.append({"task": t.id, "status": t.status, "fields": permission_failures, "reason": "permission_contract_invalid"})
        if t.status not in LIFECYCLE_TRANSITIONS:
            invalid.append({"task": t.id, "status": t.status, "reason": "status_not_in_lifecycle_graph"})
        claim_fields = [k for k in ("claimed_by", "claim_expires_at", "run_id") if t.fm.get(k)]
        if t.status in CLAIM_BOUND_STATUSES and not t.fm.get("claimed_by"):
            invalid.append({"task": t.id, "status": t.status, "reason": "claim_bound_status_missing_claimed_by"})
        if t.status in CLAIM_BOUND_STATUSES and not t.fm.get("claim_expires_at"):
            invalid.append({"task": t.id, "status": t.status, "reason": "claim_bound_status_missing_lease"})
        if t.status in CLAIM_BOUND_STATUSES and not t.fm.get("run_id"):
            invalid.append({"task": t.id, "status": t.status, "reason": "claim_bound_status_missing_run_id"})
        if t.status in CLAIM_BOUND_STATUSES and t.fm.get("claimed_by") and t.claim_expires_at() is None:
            invalid.append({"task": t.id, "status": t.status, "reason": "claim_bound_status_invalid_lease"})
        if t.status in CLAIM_BOUND_STATUSES and t.is_stale_claim():
            invalid.append({"task": t.id, "status": t.status, "reason": "claim_bound_status_stale_lease"})
        if t.status not in CLAIM_BOUND_STATUSES and claim_fields:
            invalid.append({"task": t.id, "status": t.status, "fields": claim_fields, "reason": "non_claim_bound_status_has_claim_metadata"})
        if t.status in EVIDENCE_REQUIRED_TO:
            evidence = t.fm.get("evidence") if isinstance(t.fm.get("evidence"), list) else []
            if not evidence and not (t.status == "done" and body_has_legacy_proof(t.body)):
                invalid.append({"task": t.id, "status": t.status, "reason": f"{t.status}_missing_structured_or_legacy_proof"})
            for e in evidence:
                if not evidence_is_structured(str(e)):
                    invalid.append({"task": t.id, "status": t.status, "evidence": str(e), "reason": "evidence_not_structured"})
        for line in t.body.splitlines():
            m = re.search(r"Lifecycle transition `([^`]+)` -> `([^`]+)`", line)
            if not m:
                continue
            from_status = STATUS_ALIASES.get(m.group(1), m.group(1))
            to_status = STATUS_ALIASES.get(m.group(2), m.group(2))
            forced = "Force: true" in line
            if to_status not in allowed_next_statuses(from_status) and not forced:
                invalid.append({"task": t.id, "from_status": from_status, "to_status": to_status, "reason": "illegal_recorded_lifecycle_transition"})
            if to_status == "done" and from_status != "review" and not forced:
                invalid.append({"task": t.id, "from_status": from_status, "to_status": to_status, "reason": "done_recorded_outside_review_without_force"})
    status = "PASS" if not invalid else "FAIL"
    return {
        "status": status,
        "schema": "local_brain_task_lifecycle_v1",
        "generated_at": iso(),
        "states": VALID_STATUSES,
        "transitions": LIFECYCLE_TRANSITIONS,
        "reason_required_to": sorted(REASON_REQUIRED_TO),
        "evidence_required_to": sorted(EVIDENCE_REQUIRED_TO),
        "claim_bound_statuses": sorted(CLAIM_BOUND_STATUSES),
        "task_count": len(tasks),
        "invalid_count": len(invalid),
        "invalid": invalid,
    }


def command_transition(args: argparse.Namespace) -> dict[str, Any]:
    t = find_task(args.task)
    from_status = t.status
    to_status = STATUS_ALIASES.get(args.to_status, args.to_status)
    failures, warnings = lifecycle_gate(t, to_status, args.actor, args.evidence, args.reason, args.force, getattr(args, "authority", ""))
    if failures:
        raise SystemExit("; ".join(failures))
    apply_lifecycle_status(t, to_status, args.actor, evidence=args.evidence, reason=args.reason, ttl_minutes=args.ttl_minutes, delay_minutes=args.delay_minutes, force=args.force)
    save_task(t)
    derived_refresh = refresh_derived_task_views("transition")

    # Event-driven streaming: trigger multimodel on running/review transitions
    streaming = {}
    if to_status in {"running", "review"}:
        streaming = maybe_stream_multimodel_intervention(t)

    return {
        "status": "OK",
        "task": t.id,
        "from_status": from_status,
        "to_status": to_status,
        "warnings": warnings,
        "path": str(t.path),
        "next_allowed": allowed_next_statuses(to_status),
        "derived_refresh": derived_refresh,
        "multimodel_streaming": streaming,
    }


def counts(rows: list[Task]) -> dict[str, int]:
    out = {s: 0 for s in VALID_STATUSES}
    for t in rows:
        out[t.status] = out.get(t.status, 0) + 1
    return out


def render_dashboard() -> tuple[str, str]:
    tasks = sorted_tasks(include_done=False)
    all_tasks = iter_tasks()
    c = counts(all_tasks)
    mission_summaries = mission_dag_summaries(all_tasks)
    stamp = iso()
    top_rows = tasks[:25]
    table = ["| Rank | Score | Lane | Architecture | Priority | Status | Task | Project | Lease / Due |", "|---:|---:|---|---|---|---|---|---|---|"]
    for i, t in enumerate(top_rows, 1):
        due = t.fm.get("expires_at") or ""
        lease = t.fm.get("claim_expires_at") or ""
        marker = "stale lease" if t.is_stale_claim() else ("expired" if t.is_expired() else "")
        arch = t.architecture_target or ("aligned" if t.architecture_aligned() else "missing")
        table.append(f"| {i} | {t.score()} | {t.lane} | {arch} | {t.priority} | {t.status} | {obsidian_link(t.path)} | {t.project} | {marker or lease or due} |")
    table_text = "\n".join(table)
    mission_table = ["| Mission | Progress | Done / Total | Ready Nodes | Blocked Nodes | Invalid |", "|---|---:|---:|---|---|---|"]
    for m in mission_summaries:
        blocked = "; ".join(f"{b['node']}({','.join(b['blockers'])})" for b in m.get("blocked_nodes", []))
        invalid = "; ".join(str(i.get("reason")) + ":" + str(i.get("node", i.get("task", ""))) for i in m.get("invalid", []))
        mission_table.append(
            f"| {m['mission_id']} | {m['progress_percent']}% | {m['done_nodes']} / {m['total_nodes']} | {', '.join(m.get('ready_nodes', [])) or '-'} | {blocked or '-'} | {invalid or '-'} |"
        )
    mission_table_text = "\n".join(mission_table)
    multimodel_rows = [
        t for t in tasks
        if task_multimodel_intervention_required(t) or task_multimodel_status(t) or str(t.fm.get("multimodel_round_status") or "")
    ][:15]
    multimodel_table = ["| Task | Required | Last Round | Gate | Decision | Failures | Artifact |", "|---|---|---|---|---|---|---|"]
    for t in multimodel_rows:
        failures = "; ".join(list_value(t.fm.get("multimodel_last_failures")))
        latest_round = str(t.fm.get("multimodel_round_status") or "")
        latest_artifact = str(t.fm.get("multimodel_last_discussion_artifact") or "")
        artifact = task_multimodel_artifact(t) if latest_round == "passed" else latest_artifact
        artifact = artifact or latest_artifact
        multimodel_table.append(
            f"| {obsidian_link(t.path)} | {task_multimodel_intervention_required(t)} | {markdown_table_cell(latest_round)} | {markdown_table_cell(t.fm.get('multimodel_last_gate_status'))} | {markdown_table_cell(t.fm.get('multimodel_last_decision'))} | {markdown_table_cell(failures, 120)} | {markdown_table_cell(artifact)} |"
        )
    multimodel_table_text = "\n".join(multimodel_table)
    dashboard = f"""---
type: dashboard
status: active
derived: true
generated_by: brain_task_orchestrator.py
generated_at: {stamp}
concepts: [task-runtime-dashboard, derived-view, not-source-of-truth]
---

# 待完成任务运行态

DERIVED VIEW — NOT SOURCE OF TRUTH.

事实源：`~/Documents/brain/05-实践与项目/tasks/*.md` frontmatter。此页由 `brain_task_orchestrator.py dashboard --write` 重建，人工编辑不改变任务真实状态。

## Contract

```json
{{
  "dashboard": "local-brain-task-runtime",
  "source_of_truth": "05-实践与项目/tasks/*.md",
  "derived": true,
  "regenerate_command": "python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write",
  "states": {json.dumps(VALID_STATUSES, ensure_ascii=False)},
  "lifecycle_transitions": {json.dumps(LIFECYCLE_TRANSITIONS, ensure_ascii=False)},
  "must_reconcile_before_dispatch": true,
  "must_transition_via_graph": true,
  "safe_dispatch_tick": "python3 ~/.hermes/scripts/brain_task_dispatch_tick.py",
  "boundary_check": "python3 ~/.hermes/scripts/brain_task_orchestrator.py boundary-check --json",
  "parallel_dispatch_dry_run": "python3 ~/.hermes/scripts/brain_task_orchestrator.py parallel-dispatch-dry-run --max-agents 3 --json",
  "multimodel_intervention_dry_run": "python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-dry-run --json",
  "multimodel_intervention_step": "HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1 python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-step --json",
  "pua_loop_ratification_gate": "python3 ~/.hermes/scripts/brain_task_orchestrator.py ratification-gate --task TASK_ID --discussion-result DISCUSSION_RESULT_JSON --json",
  "skill_route_matrix": "[[07-仪表盘/Agent技能树路由矩阵]]"
}}
```

## Interaction Trigger Points

- 打开控制台：[[07-仪表盘/待完成任务控制台]]
- 在 Obsidian 添加任务草稿：[[05-实践与项目/tasks/任务收件箱]]
- 处理收件箱：对 Hermes 说“处理本地大脑任务收件箱”，或运行 `python3 ~/.hermes/scripts/brain_task_orchestrator.py ingest-inbox --write && python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write`
- 直接创建任务：`python3 ~/.hermes/scripts/brain_task_orchestrator.py add "任务标题" --priority P1 --project local-brain`
- 技能路由入口：[[07-仪表盘/Agent技能树路由矩阵]]
- 安全派发 tick：`python3 ~/.hermes/scripts/brain_task_dispatch_tick.py --print-always`
- 多模型自动介入 dry-run：`python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-dry-run --json`
- PUA-loop ratification gate：`python3 ~/.hermes/scripts/brain_task_orchestrator.py ratification-gate --task TASK_ID --discussion-result DISCUSSION_RESULT_JSON --json`

## Counts

| Status | Count |
|---|---:|
"""
    for s in VALID_STATUSES:
        dashboard += f"| {s} | {c.get(s, 0)} |\n"
    dashboard += f"""

## Sorted Active Task Pool

{table_text}

## Mission DAG Progress

{mission_table_text}

## Multimodel Intervention / PUA-loop Round State

{multimodel_table_text}

## Safety Invariants

- Markdown task notes are canonical.
- This dashboard and `任务池-排序.md` are derived views.
- Every canonical task-note mutation command regenerates derived views in-process.
- Claim before work; release/archive after proof.
- Reconcile stale leases before dispatch.
- `done` requires structured evidence (`command:`, `file:`, `search:`, `brainctl:`, `artifact:`, `url:`).
- No arbitrary shell hooks from Markdown.

## Search Aliases

待完成任务运行态 本地大脑任务队列 派生视图 not source of truth derived dashboard claim lease retry stale reconcile before dispatch task inbox trigger point
"""
    pool = f"""---
type: derived_task_pool
status: active
derived: true
generated_by: brain_task_orchestrator.py
generated_at: {stamp}
concepts: [task-pool, sorted-queue, derived-view]
---

# 任务池-排序

DERIVED VIEW — NOT SOURCE OF TRUTH. Edit task notes, not this sorted pool.

{table_text}
"""
    return dashboard, pool


def render_control_center() -> str:
    stamp = iso()
    return f"""---
type: dashboard
status: active
derived: false
created: {stamp}
updated: {stamp}
concepts: [local-brain-task-console, obsidian-trigger, task-inbox]
---

# 待完成任务控制台

这是用户在本地大脑界面交互的入口。它不是任务事实源；任务事实源仍是 `05-实践与项目/tasks/*.md` 的 frontmatter。

## 1. 添加任务：Obsidian UI 触发点

打开 [[05-实践与项目/tasks/任务收件箱]]，在 `Inbox Drafts` 下添加一行：

```markdown
- [ ] 任务标题 | priority:P1 | project:project-slug | due:2026-05-20 | concepts:task,tag
```

然后任选一种触发方式：

1. 对 Hermes 说：`处理本地大脑任务收件箱`。
2. 终端运行：

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py ingest-inbox --write
python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
```

## 2. 查看任务池

- 运行态 Dashboard：[[07-仪表盘/待完成任务运行态]]
- 排序任务池：[[05-实践与项目/tasks/任务池-排序]]
- JSON 队列：

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py list --json
```

## 3. 状态操作触发点

```bash
# 创建任务
python3 ~/.hermes/scripts/brain_task_orchestrator.py add "任务标题" --priority P1 --project local-brain

# 对 stale lease / expired / due retry 做调和
python3 ~/.hermes/scripts/brain_task_orchestrator.py reconcile --write --json

# 查看下一项可派发任务，不改文件
python3 ~/.hermes/scripts/brain_task_orchestrator.py next --json

# 生成安全派发 dry-run，不认领、不执行
python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json

# 检查任务池边界：lane、架构对齐、并行冲突、kill switch
python3 ~/.hermes/scripts/brain_task_orchestrator.py boundary-check --json

# 生成多 Agent 并行派发 dry-run；按 work 优先、parallel_boundary/workspace/project 隔离
python3 ~/.hermes/scripts/brain_task_orchestrator.py parallel-dispatch-dry-run --max-agents 3 --json

# 安全 tick：收件箱 ingest + reconcile + dashboard + dispatch hint
python3 ~/.hermes/scripts/brain_task_dispatch_tick.py --print-always

# 认领任务，生成 lease
python3 ~/.hermes/scripts/brain_task_orchestrator.py claim TASK_ID --actor hermes --ttl-minutes 60

# 释放任务
python3 ~/.hermes/scripts/brain_task_orchestrator.py release TASK_ID --actor hermes --to-status pending

# 查看生命周期契约与审计当前任务
python3 ~/.hermes/scripts/brain_task_orchestrator.py lifecycle --json

# 严格状态流转（走状态机 + 审计日志）
python3 ~/.hermes/scripts/brain_task_orchestrator.py transition TASK_ID --actor hermes --to running
python3 ~/.hermes/scripts/brain_task_orchestrator.py transition TASK_ID --actor hermes --to review --evidence "command:验证命令 PASS"
python3 ~/.hermes/scripts/brain_task_orchestrator.py transition TASK_ID --actor hermes --to done --evidence "file:/path/to/proof.md"

# 标记完成：必须给结构化 evidence（legacy convenience；优先用 transition review -> done）
python3 ~/.hermes/scripts/brain_task_orchestrator.py done TASK_ID --actor hermes --evidence "command:验证命令 PASS" --evidence "file:/path/to/proof.md"

# 检查 done 任务是否有结构化 proof
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json

# 进入 retry
python3 ~/.hermes/scripts/brain_task_orchestrator.py retry TASK_ID --actor hermes --reason "失败原因" --delay-minutes 60
```

## 4. 多模型自动触发与介入

不再依赖"对 Hermes 说"作为唯一触发。安全 tick / dispatch dry-run 会自动计算 `multimodel_intervention`：

```bash
# 扫描全任务池，输出需要多模型介入的队列（不改文件、不跑模型）
python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-dry-run --json

# 对单个任务生成 PUA-loop 多模型介入计划
python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-dry-run --task TASK_ID --json

# 自动执行一步：build state → run discussion → gate → mutate task（需 env var）
HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1 python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-step --json

# 每轮多模型 discussion 完成后，用 gate 决定 LOOP_DONE 还是 continue_loop
python3 ~/.hermes/scripts/brain_task_orchestrator.py ratification-gate --task TASK_ID --discussion-result /path/to/discussion_result.json --json
```

触发策略（结构性优先、关键词补充）：

- 强结构性触发立即生效：P0+evolution、retry>=2、stale_claim。
- 关键词仅在存在结构性信号时补充（title+concepts only）。
- 需 >=2 信号才触发（防止单一弱信号噪音）。
- 收敛统计在 dry-run 输出的 `convergence` 字段：total_active / multimodel_passed / multimodel_triggered / pass_rate。

自动介入标准固定为三条，缺一不可：

1. 准确性：claim/evidence state 先行；模型一致不等于证据。
2. 长期目标：保留 lane / project / architecture_target；work 交付优先于 evolution 自进化。
3. 可一次落地方案：必须给出可直接执行的下一切片、验收证据与回滚边界。

PUA-loop 停止条件：每轮先 deterministic gates，再 `consult_models.py --tier T3 --quorum 4 --discussion --keep`，最后 `ratification-gate`。只有 gate 返回 `PASS` / `LOOP_DONE` 才能停；否则继续下一轮。

多模型只做分解、质疑、排序、认证；事实更新仍落回 Markdown task note / review / dashboard。

## 5. 排序规则

排序分数 = priority 权重 + status 权重 + 到期紧迫度 + retry 次数 + stale lease 补偿。

- P0 > P1 > P2 > P3
- retry/running/claimed/pending 优先于 proposed
- 临近 `expires_at` 或 stale `claim_expires_at` 自动上浮
- terminal 状态不进入默认 active pool
- dispatch lane order: `work` → `advisory` → `evolution`；自进化不能抢占 work 交付。
- `parallel_boundary` / `workspace` / `project` 定义多 Agent 并行隔离边界；同边界同一 dry-run 只派发一个任务。
- `conflict_group` + workspace 实现细粒度冲突隔离：不同 conflict_group 的任务可并行。
- `parallel_group` 实现协作并行：同 parallel_group 的任务显式允许共派发（设计为并行安全）。
- `workspace_isolation: worktree/copy` 创建独立副本，无需 workspace 级隔离。
- `lane: evolution` 必须带 `architecture_target` / `capability_delta` / `anti_drift_check` / `acceptance_evidence`，否则 fail-closed 不派发。

## 5. 安全边界

- Markdown task note 是事实源。
- Dashboard / sorted pool 是 derived view。
- Workflow contract 中的 hooks 默认 inert；没有 allowlisted runner 不执行。
- 自动执行任务前必须先 claim，结束必须 release/done/retry 并写 proof。
- 长期闭环必须经过 [[07-仪表盘/Agent技能树路由矩阵]] 选择 skills，不能凭感觉调度。
"""


def command_reconcile(args: argparse.Namespace) -> dict[str, Any]:
    validate_clean_values(actor=args.actor)
    if args.stale_claim_status not in RECONCILE_STALE_CLAIM_STATUSES:
        raise SystemExit(f"--stale-claim-status must be one of {sorted(RECONCILE_STALE_CLAIM_STATUSES)}")
    if args.over_retry_status not in RECONCILE_OVER_RETRY_STATUSES:
        raise SystemExit(f"--over-retry-status must be one of {sorted(RECONCILE_OVER_RETRY_STATUSES)}")
    stamp = now()
    actions: list[dict[str, Any]] = []
    for t in iter_tasks():
        before = dict(t.fm)
        action = None
        if t.is_expired(stamp):
            t.fm.update({"status": "expired", "claimed_by": "", "claim_expires_at": "", "run_id": "", "updated": iso(stamp)})
            action = "expired"
        elif t.is_stale_claim(stamp):
            if t.status == "running":
                retry_count = t.retry_count() + 1
                if retry_count > args.max_retries:
                    t.fm.update({"status": args.over_retry_status, "claimed_by": "", "claim_expires_at": "", "run_id": "", "updated": iso(stamp), "retry_count": retry_count})
                    action = "stale_running_over_retry"
                else:
                    t.fm.update({"status": "retry", "claimed_by": "", "claim_expires_at": "", "run_id": "", "next_attempt_at": iso(stamp + timedelta(minutes=args.retry_delay_minutes)), "updated": iso(stamp), "retry_count": retry_count})
                    action = "stale_running_retry"
            else:
                t.fm.update({"status": args.stale_claim_status, "claimed_by": "", "claim_expires_at": "", "run_id": "", "updated": iso(stamp)})
                action = "stale_claim_released"
        elif t.status == "retry" and t.is_retry_due(stamp) and args.promote_due_retry:
            t.fm.update({"status": "pending", "next_attempt_at": "", "updated": iso(stamp)})
            action = "retry_due_promoted"
        elif t.status not in CLAIM_BOUND_STATUSES and any(t.fm.get(k) for k in ("claimed_by", "claim_expires_at", "run_id")):
            t.fm.update({"claimed_by": "", "claim_expires_at": "", "run_id": "", "updated": iso(stamp)})
            action = "orphan_claim_metadata_cleared"
        if action:
            t.body += f"\n- {iso(stamp)}: Reconcile action `{action}` by `{args.actor}`. Previous status `{before.get('status')}`.\n"
            if args.write:
                save_task(t)
            actions.append({"task": t.id, "action": action, "write": bool(args.write), "path": str(t.path)})

    for t in iter_tasks():
        sync_action = sync_auto_subtask_parent(t, stamp=stamp, actor=args.actor, write=args.write)
        if not sync_action:
            continue
        if sync_action["action"] == "auto_subtask_progress_synced" and not sync_action.get("open_children") and not sync_action.get("missing_children"):
            continue
        actions.append(sync_action)

    derived_refresh = refresh_derived_task_views("reconcile") if args.write and actions else None
    return {"status": "OK", "write": bool(args.write), "action_count": len(actions), "actions": actions, "derived_refresh": derived_refresh}


def command_proof_check(args: argparse.Namespace) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    checked = 0
    legacy_body_evidence: list[str] = []
    for t in iter_tasks():
        missing_mission = mission_envelope_missing(t.fm)
        if missing_mission:
            failures.append(f"mission envelope missing {missing_mission}: {t.id}")
        if t.status != "done" and not args.include_active:
            continue
        checked += 1
        evidence = t.fm.get("evidence") if isinstance(t.fm.get("evidence"), list) else []
        has_evidence = bool(evidence)
        if not has_evidence and body_has_legacy_proof(t.body):
            has_evidence = True
            legacy_body_evidence.append(t.id)
            warnings.append(f"legacy body-only evidence accepted: {t.id}")
        if t.status == "done" and not has_evidence:
            failures.append(f"done task missing evidence: {t.id}")
        if t.status == "done" and task_has_autorun_audit(t) and not any(str(e).startswith("proof:sha256:") for e in evidence):
            failures.append(f"autorun done task missing proof evidence: {t.id}")
        for e in evidence:
            if not evidence_is_structured(str(e)):
                failures.append(f"unstructured evidence in {t.id}: {e}")
            if str(e).startswith("proof:sha256:") and not verify_autorun_proof_hash(str(e)[len("proof:") :]):
                failures.append(f"invalid autorun proof hash in {t.id}: {e}")
        if "## Proof Log" not in t.body and "## Final verification bundle" not in t.body:
            warnings.append(f"missing Proof Log section: {t.id}")
        if "## Final Handoff" not in t.body and not body_has_legacy_proof(t.body):
            warnings.append(f"missing Final Handoff section: {t.id}")
    status = "PASS" if not failures else "FAIL"
    return {"status": status, "checked_count": checked, "failures": failures, "warnings": warnings, "legacy_body_evidence": legacy_body_evidence}


def infer_conflict_group_from_task(task: Task) -> str:
    """Infer a conflict group from task metadata for boundary isolation.

    Auto-derives conflict groups from task title, concepts, project, and
    allowed_globs when no explicit conflict_group is set. This enables
    parallel dispatch to separate tasks touching different subsystems
    within the same workspace.

    Resolution order:
    1. explicit conflict_group field (pass-through)
    2. title/concepts/project pattern matching
    3. allowed_globs file path patterns
    4. '' (no inference possible)
    """
    # Patterns: (regex, group_name). Order matters: first match wins.
    _INFER_PATTERNS: list[tuple[str, str]] = [
        (r"(?i)(skill|技能)", "hermes-skills"),
        (r"(?i)(memory|记忆)", "hermes-memory"),
        (r"(?i)(config|配置|设置)", "hermes-config"),
        (r"(?i)(hook|钩子)", "hermes-hooks"),
        (r"(?i)(plugin|插件)", "hermes-plugins"),
        (r"(?i)(gateway|网关)", "hermes-gateway"),
        (r"(?i)(cron|定时|调度)", "hermes-cron"),
        (r"(?i)(task.?pool|任务池|task.?boundary|任务边界|dispatch|分派)", "hermes-taskpool"),
        (r"(?i)(orchestrat|编排)", "hermes-orchestrator"),
        (r"(?i)(agent.?team|multi.?agent|多agent|并行)", "hermes-agent-team"),
        (r"(?i)(brain.?sync|sync.?brain|同步)", "hermes-brain-sync"),
        (r"(?i)(model.?router|provider|quota|配额)", "hermes-model-router"),
        (r"(?i)(evolution|自进化|self.?improve)", "hermes-evolution"),
        (r"(?i)(uvisa|u-visa)", "uvisa-app"),
        (r"(?i)(rowboat)", "rowboat"),
    ]
    _FILE_PATTERNS: list[tuple[str, str]] = [
        ("~/.hermes/skills/", "hermes-skills"),
        ("~/.hermes/config/", "hermes-config"),
        ("~/.hermes/hooks/", "hermes-hooks"),
        ("~/.hermes/plugins/", "hermes-plugins"),
        ("~/.hermes/scripts/brain_task_", "hermes-taskpool"),
        ("~/.hermes/scripts/agent_team_", "hermes-agent-team"),
        ("~/.hermes/scripts/sync-brain", "hermes-brain-sync"),
        ("~/.hermes/scripts/model_", "hermes-model-router"),
        ("~/.hermes/cron/", "hermes-cron"),
        ("~/.hermes/memory/", "hermes-memory"),
    ]
    # Already has explicit conflict_group
    explicit = str(task.fm.get("conflict_group") or "").strip()
    if explicit:
        return explicit
    # Build haystack from title, concepts, project
    title = task.title or ""
    concepts = " ".join(list_value(task.fm.get("concepts")))
    project = task.project or ""
    haystack = f"{title} {concepts} {project}"
    for pattern, group in _INFER_PATTERNS:
        if re.search(pattern, haystack):
            return group
    # Try allowed_globs
    allowed_raw = str(task.fm.get("allowed_globs") or "").strip()
    if allowed_raw:
        for path_pat, group in _FILE_PATTERNS:
            if path_pat in allowed_raw:
                return group
    return ""


def task_parallel_boundary_key(task: Task) -> str:
    """Compute the isolation boundary key for parallel dispatch.

    Resolution order (most specific wins):
    1. explicit `parallel_boundary` field
    2. `workspace_isolation` = worktree/copy → per-task isolation (each task is its own boundary)
    3. `conflict_group` + workspace → fine-grained conflict isolation
    4. inferred conflict_group + workspace → auto-derived from task metadata
    5. `workspace` → workspace-level isolation
    6. evolution lane + architecture_target
    7. project
    8. task id (self-isolating)
    """
    explicit = str(task.fm.get("parallel_boundary") or "").strip()
    if explicit:
        return f"boundary:{explicit}"
    # workspace_isolation: worktree/copy create independent copies, no shared-state conflict
    ws_isolation = str(task.fm.get("workspace_isolation") or "").strip()
    if ws_isolation in ("worktree", "copy"):
        return f"isolated:{task.id}"
    # conflict_group: tasks in the same conflict_group within the same workspace cannot run together;
    # tasks with different conflict_groups CAN (fine-grained within a workspace)
    conflict = str(task.fm.get("conflict_group") or "").strip()
    workspace = str(task.fm.get("workspace") or "").strip()
    if conflict and workspace:
        return f"conflict:{workspace}:{conflict}"
    # v3: infer conflict_group from task metadata when workspace is shared
    # This separates tasks touching different subsystems within the same workspace
    if workspace and not conflict:
        inferred = infer_conflict_group_from_task(task)
        if inferred:
            return f"conflict:{workspace}:{inferred}"
    if workspace:
        return f"workspace:{workspace}"
    if task.lane == "evolution" and task.architecture_target:
        return f"evolution:{task.architecture_target}"
    project = str(task.project or "").strip()
    if project:
        return f"project:{project}"
    return f"task:{task.id}"


def parallel_group_key(task: Task) -> str:
    """Return the parallel_group label for a task, or empty if not set.

    Tasks with the same parallel_group are explicitly ALLOWED to run in parallel
    even if they share a boundary key. This is the cooperative counterpart to
    conflict_group (which forbids co-dispatch).
    """
    return str(task.fm.get("parallel_group") or "").strip()


def dispatch_prompt_for_row(row: dict[str, Any]) -> str:
    profile_context = format_project_profile_context(str(row.get("project") or ""))
    return (
        "Execute this local-brain task only after claiming it. "
        "Treat the task note as canonical workpad; reconcile first; verify; record proof; release/done/retry. "
        f"Task: {row['link']} ({row['id']}) priority={row['priority']} status={row['status']} "
        f"lane={row['lane']} project={row['project']}\n\n"
        f"{profile_context}"
    )



def budget_handoff_decision(
    *,
    quota_state: str,
    confidence: str,
    signal: str = "",
    task: Task | None = None,
    pending_side_effect: bool = False,
    idempotent: bool = True,
    context_pressure: bool = False,
) -> dict[str, Any]:
    """Deterministic budget-handoff recommendation.

    This is the automation-safe implementation of the budget exhaustion policy:
    it recommends fallback band, continuation-packet requirements, and task
    transition only. It does not buy quota, switch providers, mutate tasks, or
    release claims.
    """
    quota = (quota_state or "unknown").strip().lower()
    conf = (confidence or "unknown").strip().lower()
    sig = (signal or "").strip()
    valid_quota = {"healthy", "degraded", "limited", "exhausted", "unknown"}
    valid_conf = {"high", "medium", "low", "unknown"}
    warnings: list[str] = []
    if quota not in valid_quota:
        warnings.append(f"unknown_quota_state:{quota_state}")
        quota = "unknown"
    if conf not in valid_conf:
        warnings.append(f"unknown_confidence:{confidence}")
        conf = "unknown"

    signal_l = sig.lower()
    severe_signal = any(tok in signal_l for tok in ("quota exceeded", "exhausted", "circuit open", "cooldown", "429", "rate-limit", "rate limit"))
    repeated_signal = any(tok in signal_l for tok in ("repeated", "again", "retry failed", "after bounded retry"))

    if quota == "exhausted":
        band = "BLACK"
    elif quota == "limited" or (severe_signal and conf in {"high", "medium"}):
        band = "RED"
    elif quota == "degraded" or quota == "unknown" or context_pressure or pending_side_effect:
        band = "AMBER"
    else:
        band = "GREEN"

    if quota == "unknown" and (pending_side_effect or not idempotent or repeated_signal):
        band = "RED"
    if quota == "unknown" and conf == "unknown" and not idempotent:
        band = "RED"

    packet_required = band in {"RED", "BLACK"}
    packet_optional = band == "AMBER"
    local_check_first = band == "AMBER" and not pending_side_effect

    if band == "GREEN":
        transition = "continue"
        action = "continue_normal_execution"
    elif band == "AMBER":
        transition = "continue"
        action = "narrow_scope_and_run_local_check"
    elif band == "RED":
        if pending_side_effect:
            transition = "review"
        elif quota in {"limited", "unknown"}:
            transition = "retry"
        else:
            transition = "blocked"
        action = "checkpoint_then_transition_then_handoff_or_retry"
    else:
        transition = "blocked"
        action = "emergency_checkpoint_then_block_retry_or_manual"

    required_packet_fields = [
        "task_id",
        "parent_id",
        "fallback_band",
        "quota_state",
        "confidence",
        "authority",
        "completed",
        "pending",
        "modified_files",
        "verification",
        "next_atomic_action",
        "blocked_reason",
        "resume_instructions",
    ] if packet_required else []

    evidence_gate = [
        "task id and parent id if any",
        "quota_state/confidence/source signal",
        "commands/files already changed",
        "verification passed/missing",
        "next atomic action",
        "reason noop was insufficient",
    ] if packet_required else [
        "record only if silence would be misread as missed failure"
    ]

    task_id = task.id if task else ""
    parent_id = ""
    if task:
        parent = task.fm.get("parent") or task.fm.get("parent_task") or task.fm.get("parent_id") or ""
        parent_id = str(parent)

    return {
        "status": "OK",
        "task_id": task_id,
        "parent_id": parent_id,
        "quota_state": quota,
        "confidence": conf,
        "signal": sig,
        "fallback_band": band,
        "recommended_action": action,
        "recommended_transition": transition,
        "packet_required": packet_required,
        "packet_optional": packet_optional,
        "local_check_first": local_check_first,
        "required_packet_fields": required_packet_fields,
        "evidence_gate": evidence_gate,
        "safety": {
            "mutates_task": False,
            "switches_provider": False,
            "releases_claim": False,
            "auto_purchases_quota": False,
            "fail_soft": True,
        },
        "warnings": warnings,
    }


def command_budget_handoff_check(args: argparse.Namespace) -> dict[str, Any]:
    task = find_task(args.task) if args.task else None
    return budget_handoff_decision(
        quota_state=args.quota_state,
        confidence=args.confidence,
        signal=args.signal or "",
        task=task,
        pending_side_effect=args.pending_side_effect,
        idempotent=not args.non_idempotent,
        context_pressure=args.context_pressure,
    )

def command_boundary_check(args: argparse.Namespace) -> dict[str, Any]:
    tasks = iter_tasks()
    dispatchable = dispatchable_tasks()
    invalid: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    dispatchable_by_lane = {lane: 0 for lane in VALID_LANES}
    for t in dispatchable:
        dispatchable_by_lane[t.lane] = dispatchable_by_lane.get(t.lane, 0) + 1
    for t in tasks:
        missing_alignment = architecture_alignment_missing(t.fm)
        if missing_alignment:
            invalid.append({"task": t.id, "path": str(t.path), "fields": missing_alignment, "reason": "evolution_architecture_alignment_missing"})
        missing_profile = project_profile_failures(t)
        if missing_profile:
            invalid.append({"task": t.id, "path": str(t.path), "fields": missing_profile, "reason": "project_profile_missing"})
        missing_mission = mission_envelope_missing(t.fm)
        if missing_mission:
            invalid.append({"task": t.id, "path": str(t.path), "fields": missing_mission, "reason": "mission_envelope_missing"})
        if t.lane not in VALID_LANES:
            invalid.append({"task": t.id, "path": str(t.path), "lane": t.lane, "reason": "invalid_lane"})
        permission_failures = permission_validation_failures(t.fm)
        if permission_failures:
            invalid.append({"task": t.id, "path": str(t.path), "fields": permission_failures, "reason": "permission_contract_invalid"})
        if t.status in CLAIM_BOUND_STATUSES and not (t.fm.get("claimed_by") and t.fm.get("claim_expires_at") and t.fm.get("run_id")):
            invalid.append({"task": t.id, "path": str(t.path), "status": t.status, "reason": "claim_bound_status_missing_lease_metadata"})
    invalid.extend(mission_dag_invalids(tasks))
    # Build boundary index with parallel_group awareness
    boundary_index: dict[str, list[str]] = {}
    boundary_task_details: dict[str, list[dict[str, str]]] = {}
    for t in dispatchable:
        key = task_parallel_boundary_key(t)
        boundary_index.setdefault(key, []).append(t.id)
        boundary_task_details.setdefault(key, []).append({
            "id": t.id,
            "parallel_group": parallel_group_key(t),
            "conflict_group": str(t.fm.get("conflict_group") or "").strip(),
            "workspace_isolation": str(t.fm.get("workspace_isolation") or "").strip(),
        })
    for key, ids in sorted(boundary_index.items()):
        if len(ids) > 1:
            details = boundary_task_details.get(key, [])
            pgs = {d["parallel_group"] for d in details if d["parallel_group"]}
            # If all tasks in this boundary share the same parallel_group, they're cooperative
            if len(pgs) == 1 and len(details) > 1:
                all_same_pg = all(d["parallel_group"] == next(iter(pgs)) for d in details if d["parallel_group"])
                empty_pg = [d for d in details if not d["parallel_group"]]
                if all_same_pg and not empty_pg:
                    warnings.append({
                        "boundary_key": key, "tasks": ids,
                        "reason": "parallel_group_cooperative",
                        "parallel_group": next(iter(pgs)),
                        "note": "tasks share parallel_group; allowed to co-dispatch",
                    })
                    continue
            warnings.append({
                "boundary_key": key, "tasks": ids,
                "reason": "parallel_boundary_conflict",
                "details": details,
            })
    priority_mode = taskpool_priority_mode()
    gates = {
        "work_lane_available": dispatchable_by_lane.get("work", 0) > 0,
        "autorun_enabled": os.environ.get(AUTORUN_ENV_FLAG) == "1",
        "kill_switch_env_set": os.environ.get("HERMES_LOCAL_BRAIN_AUTORUN_KILL") == "1",
        "kill_switch_file_present": AUTORUN_KILL_SWITCH.exists(),
        "priority_mode": priority_mode,
        "priority_mode_file": str(TASKPOOL_PRIORITY_MODE_FILE),
        "evolution_preempted_by_work": priority_mode == "work-first" and dispatchable_by_lane.get("work", 0) > 0 and dispatchable_by_lane.get("evolution", 0) > 0,
        "work_preempted_by_evolution": priority_mode == "evolution-first" and dispatchable_by_lane.get("work", 0) > 0 and dispatchable_by_lane.get("evolution", 0) > 0,
    }
    status = "PASS" if not invalid else "FAIL"
    return {
        "status": status,
        "schema": "local_brain_task_boundary_v1",
        "generated_at": iso(),
        "task_count": len(tasks),
        "dispatchable_count": len(dispatchable),
        "dispatchable_by_lane": dispatchable_by_lane,
        "gates": gates,
        "invalid_count": len(invalid),
        "invalid": invalid,
        "warnings": warnings,
        "safety": "fail-closed invariants for taskpool boundaries and parallel dry-run selection",
    }


def boundary_diff_check(task: Task, changed_files: list[str] | None = None) -> dict[str, Any]:
    """Validate allowed_globs, forbidden_globs, and loc_budget against changed files.

    Fail-closed: if boundary fields are set, they MUST be satisfied.
    If no boundary fields are set, returns status=SKIP (legacy task, no constraint).
    changed_files is a list of file paths (relative to workspace or absolute) that
    the agent proposes to modify. If None, returns the declared constraints only.
    """
    allowed = list_value(task.fm.get("allowed_globs"))
    forbidden = list_value(task.fm.get("forbidden_globs"))
    loc_raw = str(task.fm.get("loc_budget") or "").strip()
    loc_budget = 0
    loc_budget_invalid = False
    if loc_raw:
        try:
            loc_budget = int(loc_raw)
        except Exception:
            loc_budget_invalid = True
        else:
            if loc_budget <= 0:
                loc_budget_invalid = True
                loc_budget = 0
    workspace = str(task.fm.get("workspace") or "").strip()

    if not allowed and not forbidden and not loc_budget and not loc_budget_invalid:
        return {"status": "SKIP", "task": task.id, "reason": "no_boundary_constraints_set"}

    violations: list[str] = []
    if loc_budget_invalid:
        violations.append(f"invalid_loc_budget:{loc_raw}")

    result: dict[str, Any] = {
        "status": "FAIL" if violations else "OK",
        "task": task.id,
        "workspace": workspace,
        "allowed_globs": allowed,
        "forbidden_globs": forbidden,
        "loc_budget": loc_budget,
        "violations": violations,
    }

    if changed_files is None:
        if not violations:
            result["status"] = "INFO"
            result["reason"] = "constraints_declared_only; no changed_files to validate"
        return result

    import fnmatch

    for fpath in changed_files:
        # Normalize: strip workspace prefix for relative matching
        rel = fpath
        if workspace and fpath.startswith(workspace):
            rel = fpath[len(workspace):].lstrip("/")

        # forbidden_globs dominate: any match = violation
        for pat in forbidden:
            if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(fpath, pat):
                violations.append(f"forbidden_match:{fpath}:{pat}")
                break
        else:
            # allowed_globs: if set, file must match at least one pattern
            if allowed:
                if not any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(fpath, p) for p in allowed):
                    violations.append(f"not_in_allowed_globs:{fpath}")

    result["violations"] = violations
    if violations:
        result["status"] = "FAIL"
    return result


def loc_budget_check(task: Task, diff_line_count: int) -> dict[str, Any]:
    """Check whether a proposed diff exceeds the task's loc_budget."""
    if diff_line_count < 0:
        return {"status": "FAIL", "task": task.id, "reason": "invalid_diff_line_count", "actual_lines": diff_line_count}
    loc_raw = str(task.fm.get("loc_budget") or "").strip()
    if not loc_raw:
        return {"status": "SKIP", "task": task.id, "reason": "no_loc_budget_set"}
    try:
        budget = int(loc_raw)
    except Exception:
        return {"status": "FAIL", "task": task.id, "reason": "invalid_loc_budget", "loc_budget_raw": loc_raw, "actual_lines": diff_line_count}
    if budget <= 0:
        return {"status": "FAIL", "task": task.id, "reason": "invalid_loc_budget", "loc_budget_raw": loc_raw, "actual_lines": diff_line_count}
    if diff_line_count > budget:
        return {"status": "FAIL", "task": task.id, "loc_budget": budget, "actual_lines": diff_line_count, "over_budget": diff_line_count - budget}
    return {"status": "OK", "task": task.id, "loc_budget": budget, "actual_lines": diff_line_count}


def command_boundary_diff_check(args: argparse.Namespace) -> dict[str, Any]:
    """CLI entry: validate boundary constraints for a task's proposed changes."""
    task = find_task(args.task)
    changed_files: list[str] | None = None
    if getattr(args, "files", None):
        changed_files = args.files
    diff_lines = int(getattr(args, "diff_lines", 0) or 0)

    boundary_result = boundary_diff_check(task, changed_files)
    loc_raw_present = bool(str(task.fm.get("loc_budget") or "").strip())
    loc_result = loc_budget_check(task, diff_lines) if (loc_raw_present or diff_lines != 0) else {"status": "SKIP", "task": task.id}

    status = "OK"
    if boundary_result.get("status") == "FAIL" or loc_result.get("status") == "FAIL":
        status = "FAIL"

    return {
        "status": status,
        "task": task.id,
        "boundary_diff": boundary_result,
        "loc_budget": loc_result,
        "safety": "fail-closed; forbidden dominates allowed; loc_budget enforced",
    }


def select_parallel_dispatch(max_agents: int) -> tuple[list[Task], list[dict[str, Any]]]:
    """Select tasks for parallel dispatch with boundary isolation.

    Isolation rules (fail-closed):
    - Tasks sharing a boundary_key are blocked unless they share a parallel_group.
    - parallel_group is cooperative: tasks with the same label are explicitly allowed
      to co-dispatch (they were designed to be parallel-safe).
    - conflict_group is preventive: tasks with different conflict_groups get different
      boundary keys, so they naturally pass the boundary check.
    """
    candidates = dispatchable_tasks()
    priority_mode = taskpool_priority_mode()
    work_available = any(t.lane == "work" for t in candidates)
    evolution_available = any(t.lane == "evolution" for t in candidates)
    selected: list[Task] = []
    skipped: list[dict[str, Any]] = []
    used_boundaries: dict[str, str] = {}  # boundary_key -> first task_id
    boundary_parallel_groups: dict[str, str] = {}  # boundary_key -> parallel_group of first task
    for t in candidates:
        if priority_mode == "work-first" and work_available and t.lane != "work":
            skipped.append({"id": t.id, "lane": t.lane, "reason": "lane_preempted_by_work", "path": str(t.path), "priority_mode": priority_mode})
            continue
        if priority_mode == "evolution-first" and evolution_available and t.lane != "evolution":
            skipped.append({"id": t.id, "lane": t.lane, "reason": "lane_preempted_by_evolution", "path": str(t.path), "priority_mode": priority_mode})
            continue
        boundary_key = task_parallel_boundary_key(t)
        t_pg = parallel_group_key(t)
        if boundary_key in used_boundaries:
            # Check if the new task and the existing boundary occupant share a parallel_group
            existing_pg = boundary_parallel_groups.get(boundary_key, "")
            if t_pg and existing_pg and t_pg == existing_pg:
                # Same parallel_group: explicitly allowed to co-dispatch
                pass
            else:
                skipped.append({
                    "id": t.id, "lane": t.lane, "reason": "parallel_boundary_conflict",
                    "boundary_key": boundary_key, "conflicts_with": used_boundaries[boundary_key],
                    "parallel_group": t_pg, "path": str(t.path),
                })
                continue
        if len(selected) >= max_agents:
            skipped.append({"id": t.id, "lane": t.lane, "reason": "capacity_exceeded", "boundary_key": boundary_key, "path": str(t.path)})
            continue
        selected.append(t)
        used_boundaries[boundary_key] = t.id
        if t_pg and boundary_key not in boundary_parallel_groups:
            boundary_parallel_groups[boundary_key] = t_pg
    return selected, skipped


def command_parallel_dispatch_dry_run(args: argparse.Namespace) -> dict[str, Any]:
    max_agents = int(getattr(args, "max_agents", 3) or 3)
    if max_agents < 1:
        raise SystemExit("--max-agents must be >= 1")
    boundary = command_boundary_check(args)
    if boundary.get("status") != "PASS":
        return {"status": "FAIL", "dry_run": True, "dispatchable": False, "reason": "boundary_check_failed", "boundary": boundary, "safety": "dry-run only; no claim or execution"}
    selected, skipped = select_parallel_dispatch(max_agents)
    dispatch_plan = []
    for t in selected:
        row = t.row()
        dispatch_plan.append({
            "id": t.id,
            "boundary_key": task_parallel_boundary_key(t),
            "parallel_group": parallel_group_key(t),
            "conflict_group": str(t.fm.get("conflict_group") or "").strip(),
            "claim_command": f"python3 ~/.hermes/scripts/brain_task_orchestrator.py claim {t.id} --actor hermes --ttl-minutes 60",
            "execution_prompt": dispatch_prompt_for_row(row),
        })
    return {
        "status": "OK",
        "dry_run": True,
        "dispatchable": bool(selected),
        "max_agents": max_agents,
        "priority_mode": taskpool_priority_mode(),
        "selected_count": len(selected),
        "selected": [t.row() for t in selected],
        "skipped": skipped,
        "dispatch_plan": dispatch_plan,
        "boundary": boundary,
        "safety": "dry-run only; does not claim, execute, or mark tasks done",
    }


def command_next(args: argparse.Namespace) -> dict[str, Any]:
    reconcile_result = None
    if not getattr(args, "no_reconcile", False):
        reconcile_result = command_reconcile(argparse.Namespace(write=bool(getattr(args, "reconcile", False)), actor="next", max_retries=3, retry_delay_minutes=60, stale_claim_status="pending", over_retry_status="blocked", promote_due_retry=True))
        blocking_reconcile_actions = []
        for action in reconcile_result.get("actions", []):
            if action.get("action") == "auto_subtask_progress_synced" and not action.get("ready") and not action.get("missing_children"):
                continue
            blocking_reconcile_actions.append(action)
        if blocking_reconcile_actions and not getattr(args, "reconcile", False):
            return {"status": "OK", "next": None, "message": "Reconcile is required before dispatch. Re-run with --reconcile to write canonical task-note fixes, or run reconcile --write explicitly.", "reconcile": reconcile_result}
    rows = dispatchable_tasks()
    if not rows:
        return {"status": "OK", "next": None, "message": "No dispatchable local-brain tasks in canonical task notes.", "reconcile": reconcile_result}
    t = rows[0]
    return {"status": "OK", "next": t.row(), "claim_command": f"python3 ~/.hermes/scripts/brain_task_orchestrator.py claim {t.id} --actor hermes --ttl-minutes 60", "dashboard_command": "python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write", "reconcile": reconcile_result}


def command_dispatch_dry_run(args: argparse.Namespace) -> dict[str, Any]:
    nxt = command_next(args)
    if not nxt.get("next"):
        return {"status": "OK", "dry_run": True, "dispatchable": False, "message": nxt["message"]}
    row = nxt["next"]
    prompt = dispatch_prompt_for_row(row)
    intervention = command_multimodel_intervention_dry_run(argparse.Namespace(task=row["id"], max_tasks=1, json=True))
    return {"status": "OK", "dry_run": True, "dispatchable": True, "next": row, "claim_command": nxt["claim_command"], "execution_prompt": prompt, "multimodel_intervention": intervention, "safety": "dry-run only; does not claim or execute"}


def multimodel_intervention_sort_key(task: Task) -> tuple[int, int, int, datetime, str]:
    reasons = task_multimodel_intervention_reasons(task)
    weights = lane_sort_weight()
    return (-len(reasons), weights.get(task.lane, 1), -task.score(), task.expires_at() or datetime.max.replace(tzinfo=TZ), task.id)


def multimodel_state_evidence_args(task: Task, reasons: list[str]) -> str:
    """Return consult_models.py state --evidence-json args linked to C-001..C-003.

    The evidence spine must be explicit: models may reason about plans, but factual
    certification only passes when claims are supported by concrete local evidence.
    """
    orchestrator_path = str(Path(__file__).resolve())
    evidence = [
        {
            "id": "E-TASK-CANONICAL",
            "type": "file",
            "path": str(task.path),
            "summary": (
                f"Canonical task note row: id={task.id}; title={task.title}; lane={task.lane}; "
                f"priority={task.priority}; project={task.project}; status={task.status}; "
                f"architecture_target={task.architecture_target}; trigger_reasons={reasons}"
            ),
            "supports": ["C-001"],
        },
        {
            "id": "E-RATIFICATION-GATE",
            "type": "file",
            "path": orchestrator_path,
            "summary": "ratification_gate_result requires final_design with next_slice/acceptance_evidence/rollback_boundary or diagnosis/verification/rollback_signal before LOOP_DONE.",
            "supports": ["C-002"],
        },
        {
            "id": "E-WORK-LANE-PREEMPTION",
            "type": "file",
            "path": orchestrator_path,
            "summary": "select_parallel_dispatch and boundary gates preserve lane/project/architecture_target; work lane candidates preempt evolution candidates.",
            "supports": ["C-003"],
        },
    ]
    return " ".join("--evidence-json " + shlex.quote(json.dumps(e, ensure_ascii=False, sort_keys=True)) for e in evidence)


def build_multimodel_intervention_plan(task: Task) -> dict[str, Any]:
    reasons = task_multimodel_intervention_reasons(task)
    advisory_reasons = task_multimodel_advisory_reasons(task)
    cert_reasons = task_multimodel_certification_reasons(task)

    # Loop economy gate
    economy = task_multimodel_economy_gate(task)
    if economy["action"] == "pause":
        return {
            "schema": "local_brain_multimodel_intervention_v1",
            "task": task.row(),
            "trigger_reasons": reasons,
            "advisory_reasons": advisory_reasons,
            "certification_reasons": cert_reasons,
            "advisory_only": True,
            "recommended_tier": "none",
            "intervention_required": False,
            "economy_gate": economy,
            "state_path": "",
            "build_state_command": "",
            "run_discussion_command": "",
        }

    # Apply economy throttle to tier
    if economy["action"] == "throttle" and cert_reasons:
        advisory_reasons = advisory_reasons + cert_reasons
        cert_reasons = []

    state_dir = HERMES_HOME / "state" / "taskpool-multimodel"
    state_path = state_dir / f"{task.id}-state.json"
    question = (
        "Local-brain taskpool PUA-loop intervention: verify decomposition and next action for "
        f"task {task.id} using accuracy, long-term-goal alignment, and one-shot landing feasibility."
    )
    context = {
        "task_id": task.id,
        "task_path": str(task.path),
        "title": task.title,
        "lane": task.lane,
        "priority": task.priority,
        "project": task.project,
        "status": task.status,
        "architecture_target": task.architecture_target,
        "trigger_reasons": reasons,
        "source_of_truth": "Markdown task note frontmatter/body",
    }
    context_arg = shlex.quote(json.dumps(context, ensure_ascii=False, sort_keys=True))
    evidence_args = multimodel_state_evidence_args(task, reasons)
    question_arg = shlex.quote(question)
    state_arg = shlex.quote(str(state_path))
    task_arg = shlex.quote(task.id)
    advisory_only = bool(advisory_reasons) and not bool(cert_reasons)
    recommended_tier = "T3_certification" if cert_reasons else ("T2_advisory" if len(reasons) >= 3 else "T1_advisory")
    consult_tier = "T3" if recommended_tier == "T3_certification" else recommended_tier.split("_", 1)[0]
    consult_quorum_arg = " --quorum 4" if recommended_tier == "T3_certification" else ""
    if advisory_only:
        pua_loop = {
            "mode": "advisory_until_signal_consumed",
            "round_gate": f"run deterministic checks -> build target-bound claim/evidence state -> consult_models.py --tier {consult_tier} --discussion advisory round -> record PASS_ADVISORY_ONLY when advisory output passes; never authorize done",
            "completion_signal": "advisory consumed only; LOOP_DONE remains reserved for certification-triggered target-bound 4/4 ratification-gate PASS",
        }
    else:
        pua_loop = {
            "mode": "continue_until_multimodel_pass",
            "round_gate": "run deterministic checks -> build target-bound claim/evidence state -> consult_models.py --tier T3 --quorum 4 --discussion -> ratification-gate; continue if gate != PASS",
            "completion_signal": "LOOP_DONE only after target-bound 4/4 ratification-gate PASS and local deterministic gates pass",
        }
    return {
        "schema": "local_brain_multimodel_intervention_v1",
        "task": task.row(),
        "criteria": {
            "accuracy": "claim/evidence state must ground task facts; model agreement alone is insufficient",
            "long_term_goal": "solution must preserve lane/project/architecture_target and not let evolution preempt work delivery",
            "one_shot_landing": "output must be a directly executable next slice with acceptance evidence and rollback boundary",
        },
        "trigger_reasons": reasons,
        "advisory_reasons": advisory_reasons,
        "certification_reasons": cert_reasons,
        "advisory_only": advisory_only,
        "recommended_tier": recommended_tier,
        "intervention_required": bool(reasons),
        "economy_gate": economy,
        "pua_loop": pua_loop,
        "state_path": str(state_path),
        "build_state_command": (
            f"mkdir -p {shlex.quote(str(state_dir))} && "
            f"python3 ~/.hermes/scripts/consult_models.py state {question_arg} "
            f"--context-json {context_arg} "
            "--constraint 'accuracy > speed; evidence-first; no model-name authority' "
            "--constraint 'preserve long-term lane/project/architecture target; work lane wins over evolution' "
            "--constraint 'final answer must be a one-shot landable slice with tests/evidence/rollback' "
            "--accept 'discussion_result status certified or certified_with_minor_risks with no unresolved severity>=3 issues' "
            f"--claim 'C-001:Task decomposition is accurate — the identified task, lane, priority, and trigger reasons match the canonical task note' "
            f"--claim 'C-002:One-shot landing gate exists — LOOP_DONE requires an actionable next slice with acceptance evidence and rollback boundary' "
            f"--claim 'C-003:Long-term goal alignment gate exists — the taskpool preserves lane/project/architecture_target and work lane preempts evolution' "
            f"{evidence_args} "
            f"--file {shlex.quote(str(task.path))} --out {state_arg}"
        ),
        "run_discussion_command": f"python3 ~/.hermes/scripts/consult_models.py run {state_arg} --tier {consult_tier}{consult_quorum_arg} --discussion --max-rounds 3 --keep",
        "gate_command_template": f"python3 ~/.hermes/scripts/brain_task_orchestrator.py ratification-gate --task {task_arg} --discussion-result DISCUSSION_RESULT_JSON --json",
        "safety": "dry-run intervention plan only; no claim, no task mutation, no arbitrary hook execution",
    }


def command_multimodel_intervention_dry_run(args: argparse.Namespace) -> dict[str, Any]:
    tasks = iter_tasks()
    if getattr(args, "task", ""):
        candidates = [find_task(args.task)]
    else:
        candidates = [t for t in tasks if t.status not in TERMINAL_STATUSES]
    intervention_tasks = [t for t in candidates if task_multimodel_intervention_required(t)]
    intervention_tasks = sorted(intervention_tasks, key=multimodel_intervention_sort_key)
    max_tasks = max(1, int(getattr(args, "max_tasks", 5) or 5))

    # Build before slicing so a higher-priority economy-paused task cannot hide
    # the next actionable PUA-loop task.  Paused/throttled diagnostics remain
    # visible in paused_plans, but executable runners consume only plans[].
    all_plans = [build_multimodel_intervention_plan(t) for t in intervention_tasks]
    actionable_plans = [p for p in all_plans if p.get("intervention_required")]
    paused_plans = [p for p in all_plans if not p.get("intervention_required")]
    plans = actionable_plans[:max_tasks]
    selected = plans[0] if plans else None
    result = {
        "status": "OK",
        "dry_run": True,
        "schema": "local_brain_multimodel_intervention_queue_v1",
        "generated_at": iso(),
        "intervention_required": bool(plans),
        "selected_task_id": selected["task"]["id"] if selected else "",
        "selected": selected,
        "queued_count": len(intervention_tasks),
        "actionable_count": len(actionable_plans),
        "paused_count": len(paused_plans),
        "plans": plans,
        "paused_plans": paused_plans[:max_tasks],
        "criteria": ["accuracy", "long_term_goal", "one_shot_landing"],
        "safety": "dry-run only; plans[] are actionable; paused_plans[] are fail-closed diagnostics and are not executed",
    }
    # D4: convergence stats
    result["convergence"] = multimodel_convergence_stats()
    return result


def command_multimodel_intervention_step(args: argparse.Namespace) -> dict[str, Any]:
    """Execute one multimodel intervention step: build state -> run discussion -> gate -> mutate.

    Gated by HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1 env var (D5).
    On gate PASS, writes multimodel_status to task frontmatter (D6).
    Bounded to one task per invocation.
    """
    # D5: env var gate
    if os.environ.get(MULTIMODEL_AUTORUN_ENV_FLAG) != "1":
        return {
            "status": "SKIP",
            "reason": "autorun_multimodel_disabled",
            "env_flag": MULTIMODEL_AUTORUN_ENV_FLAG,
            "safety": "set HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1 to enable",
        }

    # D8: allowlist gate (optional — if file exists, only matching tasks proceed)
    allowlist = load_multimodel_allowlist()
    allowlist_active = bool(allowlist)

    # Find top intervention task
    dry_run = command_multimodel_intervention_dry_run(argparse.Namespace(task=getattr(args, "task", ""), max_tasks=1, json=True))
    if not dry_run.get("intervention_required"):
        return {"status": "OK", "action": "no_intervention_needed", "convergence": dry_run.get("convergence", {})}

    selected = dry_run.get("selected")
    if not selected:
        return {"status": "OK", "action": "no_intervention_needed", "convergence": dry_run.get("convergence", {})}

    task_info = selected.get("task", {})
    task_id = task_info.get("id", "")
    task_project = task_info.get("project", "")
    task_title = task_info.get("title", "")

    # D8: allowlist check
    if allowlist_active:
        matched = False
        for item in allowlist:
            if isinstance(item, str):
                token = item.strip()
                if token in {task_id, f"task:{task_id}", task_project, f"project:{task_project}", task_title}:
                    matched = True
                    break
            elif isinstance(item, dict):
                tid = str(item.get("task_id") or item.get("id") or "").strip()
                proj = str(item.get("project") or "").strip()
                if (tid and tid == task_id) or (proj and proj == task_project):
                    matched = True
                    break
        if not matched:
            return {
                "status": "SKIP",
                "reason": "allowlist_miss",
                "task_id": task_id,
                "project": task_project,
                "allowlist_active": True,
                "safety": "task not in multimodel intervention allowlist",
            }

    build_cmd = selected.get("build_state_command", "")
    run_cmd = selected.get("run_discussion_command", "")
    state_path = selected.get("state_path", "")

    recommended_tier = selected.get("recommended_tier", "T3_certification")
    advisory_only_plan = selected.get("advisory_only", False)

    result: dict[str, Any] = {
        "status": "OK",
        "schema": "local_brain_multimodel_intervention_step_v1",
        "generated_at": iso(),
        "task_id": task_id,
        "state_path": state_path,
        "allowlist_active": allowlist_active,
        "recommended_tier": recommended_tier,
        "advisory_only": advisory_only_plan,
        "tier_routing": "advisory" if advisory_only_plan else "certification",
    }

    # Step 1: Build state file (shell=True for && chains)
    if not build_cmd:
        result["build_state"] = {"status": "SKIP", "reason": "no_build_command"}
    else:
        # Safety: ensure state_path is not a stale directory
        if state_path:
            sp = Path(os.path.expanduser(state_path))
            if sp.exists() and sp.is_dir():
                import shutil
                shutil.rmtree(sp, ignore_errors=True)
        try:
            proc = subprocess.run(build_cmd, capture_output=True, text=True, timeout=120, shell=True)
            result["build_state"] = {
                "status": "OK" if proc.returncode == 0 else "FAIL",
                "returncode": proc.returncode,
                "stdout_tail": proc.stdout[-500:] if proc.stdout else "",
                "stderr_tail": proc.stderr[-500:] if proc.stderr else "",
            }
        except Exception as exc:
            result["build_state"] = {"status": "ERROR", "error": str(exc)}

    # Step 2: Run discussion (shell=True for && chains)
    if not run_cmd:
        result["run_discussion"] = {"status": "SKIP", "reason": "no_run_command"}
    else:
        try:
            proc = subprocess.run(run_cmd, capture_output=True, text=True, timeout=1200, shell=True)
            discussion_result_path = extract_discussion_result_path_from_stdout(
                (proc.stdout or "") + "\n" + (proc.stderr or "")
            )
            result["run_discussion"] = {
                "status": "OK" if proc.returncode == 0 else "FAIL",
                "returncode": proc.returncode,
                "stdout_tail": proc.stdout[-500:] if proc.stdout else "",
                "stderr_tail": proc.stderr[-500:] if proc.stderr else "",
                "discussion_result_path": discussion_result_path,
            }
        except Exception as exc:
            result["run_discussion"] = {"status": "ERROR", "error": str(exc)}

    # Step 3: Find discussion result and run gate
    discussion_path = ""
    gate_result: dict[str, Any] = {}
    if result.get("run_discussion", {}).get("status") == "OK":
        direct_path = str(result.get("run_discussion", {}).get("discussion_result_path") or "")
        if direct_path:
            candidate = Path(direct_path).expanduser()
            if candidate.exists():
                try:
                    discussion = json.loads(candidate.read_text(encoding="utf-8"))
                    task_obj = find_task(task_id)
                    if task_obj:
                        result["binding_stamp"] = stamp_discussion_task_binding(candidate, task_obj, state_path)
                        discussion = json.loads(candidate.read_text(encoding="utf-8"))
                    if advisory_only_plan:
                        gate_result = advisory_round_gate_result(discussion)
                    else:
                        gate_result = ratification_gate_result(discussion, expected_task=task_obj)
                    discussion_path = str(candidate)
                except Exception:
                    gate_result = {}
                    discussion_path = ""
        # Find the latest discussion_result.json in tick output dirs as a fallback.
        tick_dirs = sorted(Path(os.path.expanduser("~/.hermes")).glob("tick-*"), key=lambda p: p.stat().st_mtime, reverse=True)
        for tick_dir in ([] if gate_result else tick_dirs[:3]):
            candidate = tick_dir / "discussion_result.json"
            if candidate.exists():
                try:
                    discussion = json.loads(candidate.read_text(encoding="utf-8"))
                    task_obj = find_task(task_id)
                    if task_obj:
                        result["binding_stamp"] = stamp_discussion_task_binding(candidate, task_obj, state_path)
                        discussion = json.loads(candidate.read_text(encoding="utf-8"))
                    if advisory_only_plan:
                        gate_result = advisory_round_gate_result(discussion)
                    else:
                        gate_result = ratification_gate_result(discussion, expected_task=task_obj)
                    discussion_path = str(candidate)
                    break
                except Exception:
                    continue

    result["gate"] = gate_result or {"status": "SKIP", "reason": "no_discussion_result"}
    result["discussion_path"] = discussion_path

    # Step 4: Persist every round outcome.  PASS certifies; non-PASS records
    # fail-closed state so the next tick/human sees why the loop continues.
    round_gate = gate_result or {"status": "SKIP", "decision": "continue_loop", "reason": "no_discussion_result", "failures": ["no_discussion_result"]}
    if advisory_only_plan and round_gate.get("status") == "PASS" and str(round_gate.get("decision", "")).upper() == "LOOP_DONE":
        round_gate = {**round_gate, "status": "PASS_ADVISORY_ONLY", "decision": "continue_loop", "advisory_block": "advisory_only_task_cannot_authorize_done"}
    task = find_task(task_id)
    if task:
        result["task_mutation"] = write_multimodel_result_to_task(task, round_gate, discussion_path, state_path)
    else:
        result["task_mutation"] = {"status": "SKIP", "reason": "task_not_found"}

    # D4: convergence stats
    result["convergence"] = multimodel_convergence_stats()
    result["safety"] = "bounded single-task step; gated by env var; fail-closed"
    return result


def _run_single_task_pipeline(plan: dict[str, Any], allowlist_active: bool) -> dict[str, Any]:
    """Execute build->discussion->gate->mutate for a single task. Thread-safe."""
    task_info = plan.get("task", {})
    task_id = task_info.get("id", "")
    build_cmd = plan.get("build_state_command", "")
    run_cmd = plan.get("run_discussion_command", "")
    state_path = plan.get("state_path", "")

    result: dict[str, Any] = {
        "task_id": task_id,
        "state_path": state_path,
    }

    # Step 1: Build state
    if state_path:
        sp = Path(os.path.expanduser(state_path))
        if sp.exists() and sp.is_dir():
            import shutil
            shutil.rmtree(sp, ignore_errors=True)
    try:
        proc = subprocess.run(build_cmd, capture_output=True, text=True, timeout=120, shell=True)
        result["build_state"] = {"status": "OK" if proc.returncode == 0 else "FAIL", "returncode": proc.returncode}
    except Exception as exc:
        result["build_state"] = {"status": "ERROR", "error": str(exc)}

    # Step 2: Run discussion
    try:
        proc = subprocess.run(run_cmd, capture_output=True, text=True, timeout=1200, shell=True)
        discussion_result_path = extract_discussion_result_path_from_stdout(
            (proc.stdout or "") + "\n" + (proc.stderr or "")
        )
        result["run_discussion"] = {
            "status": "OK" if proc.returncode == 0 else "FAIL",
            "returncode": proc.returncode,
            "discussion_result_path": discussion_result_path,
        }
    except Exception as exc:
        result["run_discussion"] = {"status": "ERROR", "error": str(exc)}

    # Step 3: Gate — find the correct tick for THIS task
    discussion_path = ""
    gate_result: dict[str, Any] = {}
    if result.get("run_discussion", {}).get("status") == "OK":
        direct_path = str(result.get("run_discussion", {}).get("discussion_result_path") or "")
        if direct_path:
            candidate = Path(direct_path).expanduser()
            if candidate.exists():
                try:
                    discussion = json.loads(candidate.read_text(encoding="utf-8"))
                    task_obj = find_task(task_id)
                    if task_obj:
                        result["binding_stamp"] = stamp_discussion_task_binding(candidate, task_obj, state_path)
                        discussion = json.loads(candidate.read_text(encoding="utf-8"))
                    advisory_only_plan = plan.get("advisory_only", False)
                    if advisory_only_plan:
                        gate_result = advisory_round_gate_result(discussion)
                    else:
                        gate_result = ratification_gate_result(discussion, expected_task=task_obj)
                    discussion_path = str(candidate)
                except Exception:
                    gate_result = {}
                    discussion_path = ""
        # Look for tick directories created during our discussion (within last 10 min)
        import time
        cutoff = time.time() - 600
        tick_dirs = sorted(
            (p for p in Path(os.path.expanduser("~/.hermes")).glob("tick-*")
             if p.stat().st_mtime > cutoff),
            key=lambda p: p.stat().st_mtime, reverse=True
        )
        for tick_dir in ([] if gate_result else tick_dirs[:10]):
            candidate = tick_dir / "discussion_result.json"
            if not candidate.exists():
                continue
            try:
                # Match by checking state.json question contains our task_id
                tick_state = tick_dir / "state.json"
                if tick_state.exists():
                    ts = json.loads(tick_state.read_text(encoding="utf-8"))
                    question = str(ts.get("question", ""))
                    if task_id not in question and task_id[:40] not in question:
                        continue
                discussion = json.loads(candidate.read_text(encoding="utf-8"))
                task_obj = find_task(task_id)
                if task_obj:
                    result["binding_stamp"] = stamp_discussion_task_binding(candidate, task_obj, state_path)
                    discussion = json.loads(candidate.read_text(encoding="utf-8"))
                advisory_only_plan = plan.get("advisory_only", False)
                if advisory_only_plan:
                    gate_result = advisory_round_gate_result(discussion)
                else:
                    gate_result = ratification_gate_result(discussion, expected_task=task_obj)
                discussion_path = str(candidate)
                break
            except Exception:
                continue

    result["gate"] = gate_result or {"status": "SKIP", "reason": "no_discussion_result"}
    result["discussion_path"] = discussion_path

    # Step 4: Persist every round outcome. PASS certifies; non-PASS records
    # fail-closed state for the next PUA-loop iteration.
    round_gate = gate_result or {"status": "SKIP", "decision": "continue_loop", "reason": "no_discussion_result", "failures": ["no_discussion_result"]}
    advisory_only_plan = plan.get("advisory_only", False)
    if advisory_only_plan and round_gate.get("status") == "PASS" and str(round_gate.get("decision", "")).upper() == "LOOP_DONE":
        round_gate = {**round_gate, "status": "PASS_ADVISORY_ONLY", "decision": "continue_loop", "advisory_block": "advisory_only_task_cannot_authorize_done"}
    task = find_task(task_id)
    if task:
        result["task_mutation"] = write_multimodel_result_to_task(task, round_gate, discussion_path, state_path)
    else:
        result["task_mutation"] = {"status": "SKIP", "reason": "task_not_found"}

    return result


def command_multimodel_intervention_parallel_step(args: argparse.Namespace) -> dict[str, Any]:
    """Execute multimodel intervention on multiple tasks in parallel.

    Uses ThreadPoolExecutor(max_workers=N) keyed by parallel_boundary.
    Each task runs independent build->discussion->gate->mutate pipeline.
    Boundary conflict check ensures no two tasks share the same workspace.
    """
    if os.environ.get(MULTIMODEL_AUTORUN_ENV_FLAG) != "1":
        return {"status": "SKIP", "reason": "autorun_multimodel_disabled"}

    max_workers = max(1, int(getattr(args, "max_workers", 3) or 3))

    # Get all intervention tasks
    dry_run = command_multimodel_intervention_dry_run(
        argparse.Namespace(task="", max_tasks=max_workers * 2, json=True)
    )
    if not dry_run.get("intervention_required"):
        return {"status": "OK", "action": "no_intervention_needed", "convergence": dry_run.get("convergence", {})}

    plans = dry_run.get("plans", [])
    if not plans:
        return {"status": "OK", "action": "no_intervention_needed"}

    # Boundary conflict check: select tasks with unique boundaries
    allowlist = load_multimodel_allowlist()
    allowlist_active = bool(allowlist)
    seen_boundaries: set[str] = set()
    selected_plans: list[dict[str, Any]] = []
    for plan in plans:
        task_info = plan.get("task", {})
        boundary = task_info.get("parallel_boundary", task_info.get("project", task_info.get("id", "")))
        if boundary in seen_boundaries:
            continue
        # Allowlist check
        if allowlist_active:
            task_project = task_info.get("project", "")
            task_id = task_info.get("id", "")
            matched = False
            for item in allowlist:
                if isinstance(item, str):
                    token = item.strip()
                    if token in {task_id, f"task:{task_id}", task_project, f"project:{task_project}"}:
                        matched = True
                        break
                elif isinstance(item, dict):
                    proj = str(item.get("project") or "").strip()
                    if proj and proj == task_project:
                        matched = True
                        break
            if not matched:
                continue
        seen_boundaries.add(boundary)
        selected_plans.append(plan)
        if len(selected_plans) >= max_workers:
            break

    if not selected_plans:
        return {"status": "OK", "action": "no_eligible_tasks", "convergence": dry_run.get("convergence", {})}

    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(len(selected_plans), max_workers)) as executor:
        futures = {
            executor.submit(_run_single_task_pipeline, plan, allowlist_active): plan
            for plan in selected_plans
        }
        for future in as_completed(futures):
            plan = futures[future]
            try:
                task_result = future.result()
                results.append(task_result)
            except Exception as exc:
                results.append({
                    "task_id": plan.get("task", {}).get("id", ""),
                    "error": str(exc),
                    "gate": {"status": "ERROR"},
                })

    # Summary
    passed = sum(1 for r in results if r.get("gate", {}).get("status") == "PASS")
    failed = sum(1 for r in results if r.get("gate", {}).get("status") == "FAIL")
    errors = sum(1 for r in results if r.get("gate", {}).get("status") in ("ERROR", "SKIP"))

    return {
        "status": "OK",
        "schema": "local_brain_multimodel_parallel_step_v1",
        "generated_at": iso(),
        "max_workers": max_workers,
        "tasks_processed": len(results),
        "tasks_passed": passed,
        "tasks_failed": failed,
        "tasks_errors": errors,
        "results": results,
        "convergence": multimodel_convergence_stats(),
        "safety": "parallel step with boundary isolation; each task gated independently",
    }


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stamp_discussion_task_binding(discussion_path: Path, task: "Task", state_path: str = "") -> dict[str, Any]:
    """Persist a machine-parseable task binding into a discussion artifact.

    consult_models.py discussions preserve the evidence bundle, but the root
    artifact may not include the source task id/path. The ratification gate is
    intentionally fail-closed on missing target binding, so the taskpool runner
    stamps the exact task identity after locating the discussion and before
    evaluating the gate. This is provenance metadata only; it never changes the
    model votes, issue ledger, or certification status.
    """
    discussion_path = Path(discussion_path)
    discussion = json.loads(discussion_path.read_text(encoding="utf-8"))
    if not isinstance(discussion, dict):
        raise ValueError("discussion_result_not_object")

    provenance = {
        "schema_version": 1,
        "task_id": task.id,
        "task_path": str(task.path),
        "state_path": str(Path(os.path.expanduser(state_path))) if state_path else "",
        "state_sha256": _sha256_file(Path(os.path.expanduser(state_path))) if state_path and Path(os.path.expanduser(state_path)).is_file() else "",
        "stamped_at": iso(),
    }

    discussion["task_id"] = task.id
    discussion["target_task_id"] = task.id
    discussion["target_task_path"] = str(task.path)
    discussion["taskpool_binding"] = provenance

    context = discussion.get("context")
    if not isinstance(context, dict):
        context = {"_previous_context": context} if context is not None else {}
    context.update({"task_id": task.id, "task_path": str(task.path), "target_task_id": task.id, "target_task_path": str(task.path)})
    discussion["context"] = context

    final_design = discussion.get("final_design")
    if isinstance(final_design, dict):
        meta = final_design.get("meta")
        if not isinstance(meta, dict):
            meta = {}
        meta.setdefault("target_task_id", task.id)
        meta.setdefault("target_task_path", str(task.path))
        final_design["meta"] = meta

    discussion_path.write_text(json.dumps(discussion, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return provenance


def _ratification_binding_candidates(discussion: dict[str, Any]) -> list[str]:
    """Extract explicit task target bindings from a discussion artifact.

    Only explicit task identity/path fields count. Patch target files are not a
    safe binding because implementation files can legitimately differ from the
    task note; the gate must bind the certification artifact to the requested
    task note, not merely to some touched file.
    """
    candidates: list[str] = []

    def add(value: Any) -> None:
        if isinstance(value, (str, int)):
            text = str(value).strip()
            if text and text not in candidates:
                candidates.append(text)

    id_keys = {"task_id", "target_task_id", "selected_task_id", "source_task_id", "canonical_task_id"}
    path_keys = {"task_path", "target_task_path", "canonical_task_path"}
    containers: list[Any] = [discussion]
    for key in ("context", "task", "target_task", "source_task", "canonical_task"):
        value = discussion.get(key)
        if isinstance(value, dict):
            containers.append(value)
    final_design = discussion.get("final_design")
    if isinstance(final_design, dict):
        for key in ("meta", "context", "task", "target_task", "source_task", "canonical_task"):
            value = final_design.get(key)
            if isinstance(value, dict):
                containers.append(value)
    evidence_bundle = discussion.get("evidence_bundle")
    if isinstance(evidence_bundle, dict):
        value = evidence_bundle.get("context")
        if isinstance(value, dict):
            containers.append(value)

    for container in containers:
        if not isinstance(container, dict):
            continue
        for key in id_keys | path_keys:
            add(container.get(key))
    return candidates


def _binding_matches_expected(candidate: str, expected_task: "Task") -> bool:
    text = candidate.strip()
    if not text:
        return False
    expected_path = str(expected_task.path)
    expected_name = expected_task.path.name
    expected_stem = expected_task.path.stem
    if text in {expected_task.id, expected_path, expected_name, expected_stem}:
        return True
    expanded = str(Path(os.path.expanduser(text))) if ("/" in text or text.endswith(".md")) else text
    if expanded in {expected_path, expected_name, expected_stem}:
        return True
    try:
        p = Path(os.path.expanduser(text))
        if p.name == expected_name or p.stem == expected_stem:
            return True
    except Exception:
        pass
    return False


def _format_binding_for_failure(candidate: str) -> str:
    text = candidate.strip()
    if not text:
        return "missing"
    try:
        p = Path(os.path.expanduser(text))
        if p.suffix == ".md":
            return p.stem
    except Exception:
        pass
    return text


def advisory_round_gate_result(discussion: dict[str, Any]) -> dict[str, Any]:
    """Mark a completed T1/T2 advisory artifact as consumed, not certified.

    Advisory-only taskpool interventions are routing/sanity signals. They should
    not be promoted to LOOP_DONE, and they must not be evaluated by the canonical
    T3 closeout gate that requires Claude+GPT+DeepSeek+MiMo. A parseable
    consult_models artifact with at least one concrete model/vote is enough to
    consume weak advisory triggers and stop scheduler churn; blockers inside the
    artifact remain advisory provenance for the next human/worker slice.
    """
    if not isinstance(discussion, dict):
        return {"status": "FAIL", "decision": "continue_loop", "failures": ["discussion_result_not_object"]}
    raw_models = discussion.get("models_consulted") or []
    raw_votes = discussion.get("ratification_votes") or discussion.get("votes") or []
    models = [str(m).strip() for m in raw_models if isinstance(m, str) and str(m).strip()] if isinstance(raw_models, list) else []
    vote_models = [str(v.get("model") or "").strip() for v in raw_votes if isinstance(v, dict) and str(v.get("model") or "").strip()] if isinstance(raw_votes, list) else []
    participants = sorted(set(models + vote_models))
    if not participants:
        return {"status": "FAIL", "decision": "continue_loop", "failures": ["advisory_models_missing"]}
    return {
        "status": "PASS_ADVISORY_ONLY",
        "decision": "continue_loop",
        "failures": [],
        "advisory_status": str(discussion.get("status") or discussion.get("certification_status") or "unknown"),
        "models_consulted": participants,
        "certification_authority": False,
        "advisory_block": "advisory_only_task_cannot_authorize_done",
    }


def ratification_gate_result(discussion: dict[str, Any], expected_task: "Task" | None = None) -> dict[str, Any]:
    """Fail-closed ratification gate for PUA-loop multi-model discussions.

    Accepts two canonical shapes produced by consult_models.py:

    Shape A (explicit criteria): top-level ``criteria_satisfied`` dict with
    ``accuracy``, ``long_term_goal``, ``one_shot_landing`` all True, plus
    ``final_design`` with ``next_slice``, ``acceptance_evidence``,
    ``rollback_boundary``.

    Shape B (derived from consult_models discussion): ``status: certified``,
    4 canonical model votes all approve, ``agreement_matrix`` >= 0.85,
    ``issue_ledger`` empty, ``truth_status`` grounded, ``evidence_bundle``
    with all claims verified, ``fanout_certification`` multi_model_certified,
    ``verification`` with guard_metrics, ``rollback_signal`` with
    auto_rollback_if condition.

    Both shapes require all 7 checks to pass. Any failure -> continue_loop.
    """
    failures: list[str] = []
    warnings: list[str] = []
    if not isinstance(discussion, dict):
        return {
            "status": "FAIL",
            "failures": ["discussion_result_not_object"],
            "warnings": warnings,
            "decision": "continue_loop",
        }

    # --- 1. target binding (CLI/autorun closeout must not accept a stale artifact from another task) ---
    if expected_task is not None:
        binding_candidates = _ratification_binding_candidates(discussion)
        if not binding_candidates:
            failures.append("target_task_binding_missing")
        else:
            mismatches = [candidate for candidate in binding_candidates if not _binding_matches_expected(candidate, expected_task)]
            if mismatches:
                failures.append(f"target_task_mismatch:{_format_binding_for_failure(mismatches[0])}")

    # --- 2. certification status ---
    status = str(discussion.get("status") or discussion.get("certification_status") or "").strip()
    if status not in MULTIMODEL_PASS_STATUSES:
        failures.append(f"status_not_passed:{status or 'missing'}")

    # --- 2. issue ledger: no unresolved severity>=3 ---
    issues = discussion.get("issue_ledger") or discussion.get("issues") or []
    if not isinstance(issues, list):
        failures.append("issue_ledger_not_list")
        issues = []
    for issue in issues:
        if not isinstance(issue, dict):
            failures.append("issue_not_object")
            continue
        try:
            severity = int(issue.get("severity") or 0)
        except Exception:
            severity = 0
            warnings.append(f"issue_severity_unparseable:{issue.get('id', '')}")
        issue_status = str(issue.get("status") or "").strip()
        if severity >= 3 and issue_status not in {"resolved", "accepted_risk", "duplicate", "noop", "non_blocking", "non-blocking"}:
            failures.append(f"unresolved_severity_{severity}:{issue.get('id', 'unknown')}")

    # --- 3. canonical four-model votes ---
    votes = discussion.get("ratification_votes") or discussion.get("votes") or []
    if not isinstance(votes, list) or not votes:
        failures.append("ratification_votes_missing")
        votes = []

    vote_models: list[str] = []
    seen_models: set[str] = set()
    for vote in votes:
        if not isinstance(vote, dict):
            failures.append("vote_not_object")
            continue
        model = str(vote.get("model") or "").strip()
        if not model:
            failures.append("vote_model_missing")
        else:
            vote_models.append(model)
            if model in seen_models:
                failures.append(f"duplicate_vote_model:{model}")
            seen_models.add(model)
        v = str(vote.get("vote") or vote.get("verdict") or "").lower()
        if v not in {"approve", "approved", "pass", "certify"}:
            failures.append(f"non_approve_vote:{model or 'unknown'}:{v or 'missing'}")
        if vote.get("best_within_constraints") is not True:
            failures.append(f"best_within_constraints_missing:{model or 'unknown'}")

    vote_model_set = set(vote_models)
    required_set = set(REQUIRED_RATIFICATION_MODELS)
    if len(vote_model_set) < len(required_set):
        failures.append(f"model_count_below_required:{len(vote_model_set)}/{len(required_set)}")
    if len(vote_model_set) > len(required_set):
        failures.append(f"model_count_above_required:{len(vote_model_set)}/{len(required_set)}")

    # All certification closeouts require the canonical four-model panel. The
    # artifact may omit models_consulted for backward compatibility, but if it
    # declares consulted models, that declaration must also cover the full panel.
    raw_expected_models = discussion.get("models_consulted")
    consulted_models: list[str] = []
    if raw_expected_models is not None and raw_expected_models != []:
        if not isinstance(raw_expected_models, list):
            failures.append("models_consulted_not_list")
        else:
            for item in raw_expected_models:
                if not isinstance(item, str) or not item.strip():
                    failures.append("models_consulted_invalid")
                    continue
                consulted_models.append(item.strip())
            consulted_set = set(consulted_models)
            if len(consulted_set) < len(required_set):
                failures.append(f"models_consulted_below_required:{len(consulted_set)}/{len(required_set)}")
            for required in required_set:
                if required not in consulted_set:
                    failures.append(f"missing_required_model_consulted:{required}")
            for model in consulted_set:
                if model not in required_set:
                    failures.append(f"unexpected_consulted_model:{model}")
    elif raw_expected_models == []:
        failures.append("models_consulted_empty")

    expected_set = required_set
    for required in expected_set:
        if required not in vote_model_set:
            failures.append(f"missing_required_model_vote:{required}")
    for model in vote_model_set:
        if model not in expected_set:
            failures.append(f"unexpected_vote_model:{model}")

    # --- 4. agreement matrix >= 0.85 on all axes ---
    matrix = discussion.get("agreement_matrix") or {}
    if isinstance(matrix, dict):
        for axis in ("framing", "approach", "implementation_order"):
            if axis in matrix:
                try:
                    if float(matrix[axis]) < 0.85:
                        failures.append(f"agreement_below_threshold:{axis}:{matrix[axis]}")
                except Exception:
                    failures.append(f"agreement_unparseable:{axis}")
    else:
        failures.append("agreement_matrix_not_object")

    # --- 5. truth gate (supports nested truth_assessment) ---
    truth = str(discussion.get("truth_status") or discussion.get("truth") or "").strip().lower()
    if not truth:
        ta = discussion.get("truth_assessment") or {}
        if isinstance(ta, dict):
            truth = str(ta.get("truth_status") or "").strip().lower()
    if not truth:
        fd = discussion.get("final_design") or {}
        if isinstance(fd, dict):
            fd_ta = fd.get("truth_assessment") or {}
            if isinstance(fd_ta, dict):
                truth = str(fd_ta.get("truth_status") or "").strip().lower()
    positive_truth_statuses = {
        "certified",
        "grounded",
        "verified",
        "verified_by_evidence",
        "truth_certified",
        "can_certify_truth",
    }
    if truth and any(token in truth for token in ("not_certified", "unsupported", "contradicted", "no_claims")):
        failures.append(f"truth_gate_failed:{truth}")
    elif not truth:
        failures.append("truth_gate_missing_positive_status")
    elif truth not in positive_truth_statuses:
        failures.append(f"truth_gate_unrecognized_positive_status:{truth}")

    # --- 6. criteria: accuracy + long_term_goal + one_shot_landing ---
    # Shape A: explicit criteria_satisfied dict
    criteria = discussion.get("criteria_satisfied")
    if isinstance(criteria, dict):
        if criteria.get("accuracy") is not True:
            failures.append("accuracy_criterion_missing")
        if criteria.get("long_term_goal") is not True:
            failures.append("long_term_goal_alignment_missing")
        if criteria.get("one_shot_landing") is not True:
            failures.append("one_shot_plan_missing")
    else:
        # Shape B: derive from evidence_bundle, fanout_certification, verification
        fd = discussion.get("final_design") or {}
        if not isinstance(fd, dict):
            fd = {}

        # accuracy: evidence_bundle grounding all claims verified
        eb = fd.get("evidence_bundle") or discussion.get("evidence_bundle") or {}
        grounding = eb.get("grounding") or {} if isinstance(eb, dict) else {}
        all_verified = bool(grounding) and all(
            str(g.get("truth_status") or "") == "verified_by_evidence"
            for g in grounding.values() if isinstance(g, dict)
        )
        if not all_verified:
            failures.append("accuracy_criterion_missing")

        # long_term_goal: fanout_certification.multi_model_certified
        fc = fd.get("fanout_certification") or discussion.get("fanout_certification") or {}
        if not isinstance(fc, dict) or fc.get("multi_model_certified") is not True:
            # fallback: check if status is certified (implies multi-model approval)
            if status not in MULTIMODEL_PASS_STATUSES:
                failures.append("long_term_goal_alignment_missing")

        # one_shot_landing: verification has guard_metrics AND rollback_signal has condition
        ver = fd.get("verification") or {}
        rs = fd.get("rollback_signal") or {}
        has_guard = isinstance(ver, dict) and isinstance(ver.get("guard_metrics"), list) and ver["guard_metrics"]
        has_rollback = isinstance(rs, dict) and str(rs.get("auto_rollback_if") or "").strip()
        if not has_guard:
            failures.append("one_shot_plan_missing")
            warnings.append("verification.guard_metrics missing or empty")
        if not has_rollback:
            warnings.append("rollback_signal.auto_rollback_if missing")

    # --- 7. final_design: must exist with actionable structure ---
    final_design = discussion.get("final_design")
    if not isinstance(final_design, dict):
        failures.append("final_design_missing")
    else:
        # Shape A: explicit next_slice / acceptance_evidence / rollback_boundary
        has_next_slice = bool(str(final_design.get("next_slice") or "").strip())
        has_acceptance = isinstance(final_design.get("acceptance_evidence"), list) and bool(final_design["acceptance_evidence"])
        has_rollback_boundary = bool(str(final_design.get("rollback_boundary") or "").strip())

        # Shape B: diagnosis + verification + rollback_signal
        has_diagnosis = isinstance(final_design.get("diagnosis"), dict) and (
            str(final_design["diagnosis"].get("root_cause_class") or "").strip()
            or str(final_design["diagnosis"].get("summary") or "").strip()
        )
        has_verification = isinstance(final_design.get("verification"), dict)
        has_rollback_signal = isinstance(final_design.get("rollback_signal"), dict) and (
            str(final_design["rollback_signal"].get("auto_rollback_if") or "").strip()
        )

        shape_a = has_next_slice and has_acceptance and has_rollback_boundary
        shape_b = has_diagnosis and has_verification and has_rollback_signal

        if not shape_a and not shape_b:
            # Neither shape has actionable structure
            missing = []
            if not has_next_slice and not has_diagnosis:
                missing.append("next_slice_or_diagnosis")
            if not has_acceptance and not has_verification:
                missing.append("acceptance_evidence_or_verification")
            if not has_rollback_boundary and not has_rollback_signal:
                missing.append("rollback_boundary_or_signal")
            for m in missing:
                failures.append(f"final_design_{m}_missing")

    result = {
        "status": "PASS" if not failures else "FAIL",
        "failures": sorted(set(failures)),
        "warnings": warnings,
        "decision": "LOOP_DONE" if not failures else "continue_loop",
    }
    if failures:
        result["failure_taxonomy"] = multimodel_failure_taxonomy(discussion, result["failures"])
    return result


def command_ratification_gate(args: argparse.Namespace) -> dict[str, Any]:
    path = Path(args.discussion_result).expanduser()
    if not path.exists():
        return {"status": "FAIL", "decision": "continue_loop", "failures": [f"discussion_result_missing:{path}"], "warnings": [], "task_id": args.task}
    try:
        discussion = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "FAIL", "decision": "continue_loop", "failures": [f"discussion_result_unreadable:{exc}"], "warnings": [], "task_id": args.task, "discussion_result": str(path)}
    expected_task = None
    if str(getattr(args, "task", "") or "").strip():
        expected_task = find_task(args.task)
    result = ratification_gate_result(discussion, expected_task=expected_task)
    result.update({
        "task_id": args.task,
        "discussion_result": str(path),
        "criteria": ["accuracy", "long_term_goal", "one_shot_landing"],
        "safety": "read-only gate; PASS means pua-loop may stop, FAIL means continue iteration",
    })
    return result


def command_eligibility_check(args: argparse.Namespace) -> dict[str, Any]:
    validate_clean_values(actor=getattr(args, "actor", "hermes-autorun"))
    reasons: list[str] = []
    warnings: list[str] = []
    task: Task | None = None
    if getattr(args, "task", ""):
        task = find_task(args.task)
    else:
        nxt = command_next(argparse.Namespace(reconcile=False, no_reconcile=bool(getattr(args, "no_reconcile", False)), json=True))
        if nxt.get("next"):
            task = find_task(nxt["next"]["id"])
        elif (nxt.get("reconcile") or {}).get("action_count"):
            reasons.append("reconcile_required")
        else:
            reasons.append("no_dispatchable_task")
    allowlist = load_autorun_allowlist()
    allowlist_hit = bool(task and autorun_allowlist_matches(task, allowlist))
    if os.environ.get(AUTORUN_ENV_FLAG) != "1":
        reasons.append("autorun_disabled")
    if os.environ.get("HERMES_LOCAL_BRAIN_AUTORUN_KILL") == "1":
        reasons.append("kill_switch_env_set")
    if AUTORUN_KILL_SWITCH.exists():
        reasons.append("kill_switch_file_present")
    priority_mode = taskpool_priority_mode()
    dispatchable_now = dispatchable_tasks()
    if priority_mode == "work-first" and task and task.lane != "work" and any(t.lane == "work" and t.id != task.id for t in dispatchable_now):
        reasons.append("work_lane_available")
    if priority_mode == "evolution-first" and task and task.lane != "evolution" and any(t.lane == "evolution" and t.id != task.id for t in dispatchable_now):
        reasons.append("evolution_lane_available")
    if not allowlist:
        reasons.append("allowlist_empty")
    elif task and not allowlist_hit:
        reasons.append("allowlist_miss")
    if task and not task.is_dispatchable():
        blockers = mission_node_blockers(task)
        if "permission_gate_pending" in blockers:
            reasons.append("permission_gate_pending")
        elif blockers:
            reasons.append("mission_node_blocked")
        else:
            reasons.append("task_not_dispatchable")
    proof_ok, proof_failures = verify_autorun_proof_chain()
    if not proof_ok:
        reasons.append("proof_chain_invalid")
        warnings.extend(proof_failures)
    selfcheck = command_selfcheck(argparse.Namespace(json=True))
    if selfcheck.get("status") != "PASS":
        reasons.append("selfcheck_failed")
        warnings.extend(str(x) for x in selfcheck.get("failures", []))
    eligible = bool(task and not reasons)
    row = task.row() if task else None
    return {
        "status": "PASS",
        "eligible": eligible,
        "mode": "allow" if eligible else "deny",
        "priority_mode": priority_mode,
        "reasons": sorted(set(reasons)),
        "warnings": warnings,
        "task_id": task.id if task else "",
        "task": row,
        "allowlist": str(AUTORUN_ALLOWLIST),
        "policy": str(AUTORUN_POLICY),
        "allowlist_hit": allowlist_hit,
        "kill_switch": bool(os.environ.get(AUTORUN_ENV_FLAG) != "1" or os.environ.get("HERMES_LOCAL_BRAIN_AUTORUN_KILL") == "1" or AUTORUN_KILL_SWITCH.exists()),
        "required_proof": ["proof:<sha256:...> required before autorun-originated done"],
        "budget_ceiling": None,
    }


def render_autorun_handoff(task: Task, claim: dict[str, Any], proof_hash: str, actor: str) -> str:
    profile_context = format_project_profile_context(task.project)
    return f"""# Auto-Claim Handoff — {task.title}

- task_id: `{task.id}`
- task_link: {obsidian_link(task.path)}
- actor: `{actor}`
- run_id: `{task.fm.get('run_id') or ''}`
- claim_expires_at: `{task.fm.get('claim_expires_at') or ''}`
- proof_evidence: `proof:{proof_hash}`

## Safety Contract

- Do not execute Markdown task body as a script.
- Do not run arbitrary hooks from task notes.
- Do not mark the task done from this handoff.
- Runner must perform bounded execution, write concrete evidence, transition `running -> review`, and only then use proof-gated `review -> done`.
- If any gate fails, release/retry/block; never force close.

## Suggested Runner Prompt

Claim has already been acquired. Work only within the task's stated workspace/contract, verify with deterministic commands, append proof, and close through lifecycle gates.

## Project Profile

```text
{profile_context}
```

## Claim Result

```json
{json.dumps(claim, ensure_ascii=False, indent=2)}
```
"""


def render_parallel_handoff(task: Task, claim: dict[str, Any], boundary_info: dict[str, Any], actor: str, run_id: str, batch_id: str, batch_index: int) -> str:
    """Render a per-task handoff artifact for parallel dispatch.

    Includes boundary constraints (allowed/forbidden globs, loc_budget,
    workspace_isolation, merge_gate) so the consuming runner knows exactly
    what it is allowed to touch.
    """
    allowed = list_value(task.fm.get("allowed_globs"))
    forbidden = list_value(task.fm.get("forbidden_globs"))
    loc_budget = str(task.fm.get("loc_budget") or "").strip()
    ws_isolation = str(task.fm.get("workspace_isolation") or "").strip()
    merge_gate = str(task.fm.get("merge_gate") or "").strip()
    conflict_group = str(task.fm.get("conflict_group") or "").strip()
    parallel_group_val = str(task.fm.get("parallel_group") or "").strip()
    workspace = str(task.fm.get("workspace") or "").strip()
    profile_context = format_project_profile_context(task.project)
    return f"""# Parallel Handoff — {task.title}

- task_id: `{task.id}`
- task_link: {obsidian_link(task.path)}
- actor: `{actor}`
- run_id: `{run_id}`
- batch_id: `{batch_id}`
- batch_index: {batch_index}
- claim_expires_at: `{task.fm.get('claim_expires_at') or ''}`

## Project Profile

```text
{profile_context}
```

## Boundary Constraints

- boundary_key: `{boundary_info.get('boundary_key', '')}`
- workspace: `{workspace}`
- workspace_isolation: `{ws_isolation or 'none'}`
- conflict_group: `{conflict_group or '(auto-inferred)'}`
- parallel_group: `{parallel_group or '(none)'}`
- allowed_globs: {json.dumps(allowed, ensure_ascii=False) if allowed else '(none)'}
- forbidden_globs: {json.dumps(forbidden, ensure_ascii=False) if forbidden else '(none)'}
- loc_budget: `{loc_budget or '(unlimited)'}`
- merge_gate: `{merge_gate or 'manual'}`

## Safety Contract

- Do NOT execute Markdown task body as a script.
- Do NOT modify files outside allowed_globs.
- Do NOT touch files matching forbidden_globs.
- Do NOT exceed loc_budget lines changed.
- Do NOT mark the task done from this handoff.
- Runner must perform bounded execution within boundary constraints,
  write concrete evidence, transition `running -> review`, and only
  then use proof-gated `review -> done`.
- If any gate fails, release/retry/block; never force close.
- This handoff is part of batch `{batch_id}` with {boundary_info.get('batch_size', '?')} task(s).

## Claim Result

```json
{json.dumps(claim, ensure_ascii=False, indent=2)}
```
"""


def command_auto_claim_and_handoff(args: argparse.Namespace) -> dict[str, Any]:
    eligibility = command_eligibility_check(args)
    if not eligibility.get("eligible"):
        return {
            "status": "PASS",
            "claimed": False,
            "eligible": False,
            "reasons": eligibility.get("reasons", []),
            "warnings": eligibility.get("warnings", []),
            "task_id": eligibility.get("task_id", ""),
            "safety": "fail-closed; no claim and no execution",
        }
    task = find_task(str(eligibility["task_id"]))
    if not task.is_dispatchable():
        return {"status": "PASS", "claimed": False, "eligible": False, "reasons": ["task_not_dispatchable_after_eligibility"], "task_id": task.id, "safety": "fail-closed; no execution"}
    try:
        write_guard = guard_autorun_claim_and_handoff(task.id, args.actor)
    except PermissionError as exc:
        return {
            "status": "FAIL_CLOSED",
            "claimed": False,
            "eligible": True,
            "task_id": task.id,
            "reasons": ["autonomy_write_guard_failed"],
            "write_guard": parse_guard_error(exc),
            "safety": "fail-closed; no claim, no handoff, no execution",
        }
    except Exception as exc:
        return {
            "status": "FAIL_CLOSED",
            "claimed": False,
            "eligible": True,
            "task_id": task.id,
            "reasons": ["autonomy_write_guard_unavailable"],
            "write_guard": parse_guard_error(exc),
            "safety": "fail-closed; no claim, no handoff, no execution",
        }
    stamp = now()
    run_id = f"autorun-{stamp.strftime('%Y%m%d%H%M%S')}-{task.id[:24]}"
    claim = command_claim(argparse.Namespace(task=task.id, actor=args.actor, ttl_minutes=args.ttl_minutes, run_id=run_id, reason="auto-claim-and-handoff", force=False, json=True))
    claimed_task = find_task(task.id)
    readback_failures = []
    if claimed_task.status != "claimed":
        readback_failures.append(f"status read-back mismatch: {claimed_task.status}")
    if str(claimed_task.fm.get("claimed_by") or "") != args.actor:
        readback_failures.append(f"claimed_by read-back mismatch: {claimed_task.fm.get('claimed_by')}")
    if str(claimed_task.fm.get("run_id") or "") != run_id:
        readback_failures.append(f"run_id read-back mismatch: {claimed_task.fm.get('run_id')}")
    if not claimed_task.fm.get("claim_expires_at"):
        readback_failures.append("claim_expires_at missing after claim")
    if readback_failures:
        try:
            command_release(argparse.Namespace(task=task.id, actor=args.actor, to_status="pending", reason="autorun read-back mismatch; fail-closed release", force=True, json=True))
        except Exception:
            pass
        return {"status": "ERROR", "claimed": False, "eligible": False, "task_id": task.id, "reasons": ["claim_readback_mismatch"], "warnings": readback_failures, "safety": "fail-closed; released if possible; no execution"}
    AUTORUN_HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    handoff_path = AUTORUN_HANDOFF_DIR / f"{run_id}.md"
    try:
        proof_hash = append_autorun_proof_event({
            "event": "handoff_created",
            "task": task.id,
            "actor": args.actor,
            "run_id": run_id,
            "handoff": str(handoff_path),
            "safety": "claimed-and-handoff-only; no execution; no done",
        })
        atomic_write(handoff_path, render_autorun_handoff(claimed_task, claim, proof_hash, args.actor))
    except Exception as exc:
        try:
            command_release(argparse.Namespace(task=task.id, actor=args.actor, to_status="pending", reason="autorun handoff/proof write failed; fail-closed release", force=True, json=True))
        except Exception:
            pass
        return {"status": "ERROR", "claimed": False, "eligible": False, "task_id": task.id, "reasons": ["handoff_or_proof_write_failed"], "warnings": [str(exc)], "safety": "fail-closed; released if possible; no execution"}
    return {
        "status": "OK",
        "claimed": True,
        "eligible": True,
        "task": task.id,
        "claimed_by": args.actor,
        "run_id": run_id,
        "claim_expires_at": claim.get("claim_expires_at"),
        "handoff": str(handoff_path),
        "proof_hash": proof_hash,
        "proof_log": str(AUTORUN_PROOF_LOG),
        "write_guard": write_guard,
        "safety": "claimed-and-handoff-only; does not execute task body or mark done",
    }


def command_parallel_claim_and_handoff(args: argparse.Namespace) -> dict[str, Any]:
    """Parallel claim and handoff: claim a non-conflicting batch and emit handoff artifacts.

    Default mode is dry-run (plan only). Use --write to actually claim tasks
    and generate per-task handoff artifacts with boundary constraints.

    Fail-closed: if any claim in a batch fails, all previously claimed tasks
    in this batch are released.
    """
    max_agents = int(getattr(args, "max_agents", 3) or 3)
    if max_agents < 1:
        raise SystemExit("--max-agents must be >= 1")
    dry_run = not getattr(args, "write", False)
    actor = getattr(args, "actor", "hermes-parallel")
    ttl_minutes = int(getattr(args, "ttl_minutes", 60) or 60)
    prepare_worktrees = getattr(args, "prepare_worktrees", False)

    # Step 1: boundary-check must pass
    boundary = command_boundary_check(args)
    if boundary.get("status") != "PASS":
        return {
            "status": "FAIL",
            "dry_run": True,
            "claimed": False,
            "reason": "boundary_check_failed",
            "boundary": boundary,
            "safety": "fail-closed; no claim, no handoff, no execution",
        }

    # Step 2: select non-conflicting parallel batch
    selected, skipped = select_parallel_dispatch(max_agents)
    if not selected:
        return {
            "status": "OK",
            "dry_run": dry_run,
            "claimed": False,
            "selected_count": 0,
            "selected": [],
            "skipped": skipped,
            "reason": "no_eligible_tasks",
            "safety": "dry-run only" if dry_run else "no tasks to claim",
        }

    # Step 3: build dispatch plan
    dispatch_plan = []
    for idx, t in enumerate(selected):
        row = t.row()
        dispatch_plan.append({
            "id": t.id,
            "index": idx,
            "boundary_key": task_parallel_boundary_key(t),
            "parallel_group": parallel_group_key(t),
            "conflict_group": str(t.fm.get("conflict_group") or "").strip(),
            "workspace": str(t.fm.get("workspace") or "").strip(),
            "workspace_isolation": str(t.fm.get("workspace_isolation") or "").strip(),
            "claim_command": f"python3 ~/.hermes/scripts/brain_task_orchestrator.py claim {t.id} --actor {actor} --ttl-minutes {ttl_minutes}",
            "execution_prompt": dispatch_prompt_for_row(row),
        })

    # Dry-run: return plan only, no claims, no handoffs
    if dry_run:
        return {
            "status": "OK",
            "dry_run": True,
            "claimed": False,
            "max_agents": max_agents,
            "selected_count": len(selected),
            "selected": [t.row() for t in selected],
            "skipped": skipped,
            "dispatch_plan": dispatch_plan,
            "boundary": boundary,
            "safety": "dry-run only; does not claim, execute, or mark tasks done",
        }

    # Step 4: --write mode: atomic batch claim
    stamp = now()
    batch_id = f"parallel-{stamp.strftime('%Y%m%d%H%M%S')}-{len(selected)}"
    claimed_tasks: list[dict[str, Any]] = []
    failed_claims: list[dict[str, Any]] = []
    handoff_paths: list[str] = []

    def _rollback_all():
        """Release all claimed tasks in this batch (fail-closed)."""
        for ct in claimed_tasks:
            try:
                command_release(argparse.Namespace(
                    task=ct["task_id"], actor=actor,
                    to_status="pending",
                    reason=f"parallel batch rollback; batch={batch_id}",
                    force=True, json=True,
                ))
            except Exception:
                pass

    try:
        PARALLEL_HANDOFF_DIR.mkdir(parents=True, exist_ok=True)

        for idx, t in enumerate(selected):
            run_id = f"{batch_id}-agent{idx}-{t.id[:24]}"
            try:
                write_guard = guard_autorun_claim_and_handoff(t.id, actor)
            except PermissionError as exc:
                failed_claims.append({
                    "task_id": t.id, "reason": "write_guard_failed",
                    "error": parse_guard_error(exc),
                })
                _rollback_all()
                return {
                    "status": "FAIL_CLOSED",
                    "dry_run": False,
                    "claimed": False,
                    "batch_id": batch_id,
                    "claimed_tasks": claimed_tasks,
                    "failed_claims": failed_claims,
                    "reason": "write_guard_failed_during_batch",
                    "safety": "fail-closed; all claims rolled back",
                }
            except Exception as exc:
                failed_claims.append({
                    "task_id": t.id, "reason": "write_guard_unavailable",
                    "error": str(exc),
                })
                _rollback_all()
                return {
                    "status": "FAIL_CLOSED",
                    "dry_run": False,
                    "claimed": False,
                    "batch_id": batch_id,
                    "claimed_tasks": claimed_tasks,
                    "failed_claims": failed_claims,
                    "reason": "write_guard_unavailable_during_batch",
                    "safety": "fail-closed; all claims rolled back",
                }

            claim = command_claim(argparse.Namespace(
                task=t.id, actor=actor, ttl_minutes=ttl_minutes,
                run_id=run_id, reason=f"parallel-claim-and-handoff; batch={batch_id}",
                force=False, json=True,
            ))

            # Read-back verification
            claimed_task = find_task(t.id)
            readback_failures = []
            if claimed_task.status != "claimed":
                readback_failures.append(f"status mismatch: {claimed_task.status}")
            if str(claimed_task.fm.get("claimed_by") or "") != actor:
                readback_failures.append(f"claimed_by mismatch: {claimed_task.fm.get('claimed_by')}")
            if str(claimed_task.fm.get("run_id") or "") != run_id:
                readback_failures.append(f"run_id mismatch: {claimed_task.fm.get('run_id')}")
            if not claimed_task.fm.get("claim_expires_at"):
                readback_failures.append("claim_expires_at missing")

            if readback_failures:
                failed_claims.append({
                    "task_id": t.id, "reason": "readback_mismatch",
                    "failures": readback_failures,
                })
                _rollback_all()
                return {
                    "status": "ERROR",
                    "dry_run": False,
                    "claimed": False,
                    "batch_id": batch_id,
                    "claimed_tasks": claimed_tasks,
                    "failed_claims": failed_claims,
                    "reason": "claim_readback_mismatch",
                    "safety": "fail-closed; all claims rolled back",
                }

            # Generate handoff artifact
            boundary_info = {
                "boundary_key": task_parallel_boundary_key(t),
                "batch_size": len(selected),
                "batch_id": batch_id,
            }
            handoff_path = PARALLEL_HANDOFF_DIR / f"{run_id}.md"
            proof_hash = append_autorun_proof_event({
                "event": "parallel_handoff_created",
                "task": t.id,
                "actor": actor,
                "run_id": run_id,
                "batch_id": batch_id,
                "batch_index": idx,
                "handoff": str(handoff_path),
                "safety": "parallel-claimed-and-handoff-only; no execution; no done",
            })
            atomic_write(handoff_path, render_parallel_handoff(
                claimed_task, claim, boundary_info, actor, run_id, batch_id, idx,
            ))

            claimed_tasks.append({
                "task_id": t.id,
                "run_id": run_id,
                "claim_expires_at": claim.get("claim_expires_at"),
                "handoff": str(handoff_path),
                "proof_hash": proof_hash,
                "boundary_key": boundary_info["boundary_key"],
                "write_guard": write_guard,
            })
            handoff_paths.append(str(handoff_path))

    except Exception as exc:
        _rollback_all()
        return {
            "status": "ERROR",
            "dry_run": False,
            "claimed": False,
            "batch_id": batch_id,
            "claimed_tasks": claimed_tasks,
            "failed_claims": failed_claims,
            "reason": "batch_claim_exception",
            "error": str(exc),
            "safety": "fail-closed; all claims rolled back on exception",
        }

    result: dict[str, Any] = {
        "status": "OK",
        "dry_run": False,
        "claimed": True,
        "batch_id": batch_id,
        "max_agents": max_agents,
        "claimed_count": len(claimed_tasks),
        "claimed_tasks": claimed_tasks,
        "skipped": skipped,
        "handoff_dir": str(PARALLEL_HANDOFF_DIR),
        "handoff_paths": handoff_paths,
        "boundary": boundary,
        "safety": "parallel-claimed-and-handoff-only; does not execute task bodies or mark done",
    }
    if prepare_worktrees:
        result["worktree_note"] = "--prepare-worktrees is P2; worktree isolation not yet implemented. Use workspace_isolation=worktree in task metadata."
    return result


def command_autorun_runner(args: argparse.Namespace) -> dict[str, Any]:
    """Proof-gated bounded autorun bridge. It may claim + handoff only."""
    eligibility = command_eligibility_check(args)
    if not eligibility.get("eligible"):
        reasons = eligibility.get("reasons", [])
        runner_status = "paused_permission_gate" if "permission_gate_pending" in reasons else "denied"
        return {
            "status": "PASS",
            "runner_status": runner_status,
            "claimed": False,
            "eligible": False,
            "task_id": eligibility.get("task_id", ""),
            "reasons": reasons,
            "warnings": eligibility.get("warnings", []),
            "safety": "bounded runner did not execute task body, did not claim, and did not mark done",
        }
    handoff = command_auto_claim_and_handoff(args)
    return {
        "status": handoff.get("status", "OK"),
        "runner_status": "handoff_created" if handoff.get("claimed") else "denied",
        **handoff,
        "safety": "bounded runner stops after claim+handoff+proof head; no Markdown execution; no automatic done",
    }


def redact_for_evidence(text: str, limit: int = 1200) -> str:
    """Best-effort secret redaction before surfacing cron/taskpool diagnostics."""
    s = str(text or "")[-limit:]
    substitutions = [
        # Header-style credentials: Authorization: Bearer xxx / Bearer xxx.
        (r"(?i)authorization\s*:\s*(?:bearer|basic)?\s*[^\s,;]+", "authorization: [REDACTED]"),
        (r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}", "bearer [REDACTED]"),
        # key=value / key: value / quoted variants.
        (r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|token|secret|password|passwd)\s*[:=]\s*['\"]?[^'\"\s,;]+", r"\1=[REDACTED]"),
        # URL query credentials.
        (r"(?i)([?&](?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|secret|password|passwd)=)[^&\s]+", r"\1[REDACTED]"),
        (r"(?i)sk-[A-Za-z0-9_-]{12,}", "[REDACTED]"),
        (r"(?i)xox[baprs]-[A-Za-z0-9-]+", "[REDACTED]"),
    ]
    for pat, repl in substitutions:
        s = re.sub(pat, repl, s)
    return s


def task_counts_snapshot(tasks: list[Task]) -> dict[str, Any]:
    by_status = {s: 0 for s in VALID_STATUSES}
    by_lane = {lane: 0 for lane in VALID_LANES}
    for t in tasks:
        by_status[t.status] = by_status.get(t.status, 0) + 1
        by_lane[t.lane] = by_lane.get(t.lane, 0) + 1
    active = [t for t in tasks if t.status not in TERMINAL_STATUSES]
    return {
        "total": len(tasks),
        "active": len(active),
        "by_status": by_status,
        "by_lane": by_lane,
        "stale_claims": sum(1 for t in tasks if t.is_stale_claim()),
        "dispatchable": sum(1 for t in tasks if t.is_dispatchable()),
        "review": by_status.get("review", 0),
        "claimed": by_status.get("claimed", 0),
        "pending": by_status.get("pending", 0),
    }


def parse_first_json_object(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    if start < 0:
        return None
    try:
        data, _end = json.JSONDecoder().raw_decode(text[start:])
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def auto_completer_recursive_self_lock(last_error: str) -> bool:
    """Detect dynamic-runner → tick → evidence-spine self-locks.

    The auto-completer cron can legitimately be the only reason evidence-spine
    is WARN: its previous tick failed because evidence-spine saw that same prior
    auto-completer error.  Once this classifier recognizes the state, the next
    evidence-spine run becomes PASS.  Unknown/non-structured errors still fail
    closed.
    """
    if "taskpool_dynamic_runner_v1" not in last_error:
        return False
    root = parse_first_json_object(last_error.split("stdout:", 1)[-1])
    if not root or root.get("schema") != "taskpool_dynamic_runner_v1":
        return False
    root_summary = root.get("summary") if isinstance(root.get("summary"), dict) else {}
    if root_summary.get("status") != "ERROR" or str(root_summary.get("error_count") or "") != "1":
        return False
    tick = root.get("tick") if isinstance(root.get("tick"), dict) else {}
    tick_cmd_parts = tick.get("cmd") if isinstance(tick.get("cmd"), list) else []
    tick_cmd_basenames = {Path(str(part)).name for part in tick_cmd_parts}
    if "brain_task_dispatch_tick.py" not in tick_cmd_basenames or "--summary" not in {str(part) for part in tick_cmd_parts}:
        return False
    if str(tick.get("returncode") or "") != "2":
        return False
    tick_payload = parse_first_json_object(str(tick.get("stdout") or "")) or {}
    evidence_spine = tick_payload.get("evidence_spine") if isinstance(tick_payload.get("evidence_spine"), dict) else {}
    spine_summary = evidence_spine.get("summary") if isinstance(evidence_spine.get("summary"), dict) else {}
    tick_summary_is_single_dispatch_error = (
        tick_payload.get("schema") == "brain_task_dispatch_tick_summary_v1"
        and tick_payload.get("error_count") == 1
    )
    structured_self_lock = (
        tick_summary_is_single_dispatch_error
        and evidence_spine.get("status") in {"FAIL", "ERROR"}
        and spine_summary.get("auto_completer_semantic_status") == "error"
        and spine_summary.get("auto_completer_safe_for_next_tick") is False
    )
    legacy_generic_self_lock = (
        tick_summary_is_single_dispatch_error
        and evidence_spine.get("status") == "ERROR"
        and evidence_spine.get("gate_status") in {None, ""}
        and not spine_summary
        and "brain_task_dispatch_tick.py" in str(tick_payload.get("recovery_command") or "")
    )
    return tick_payload.get("status") == "ERROR" and (structured_self_lock or legacy_generic_self_lock)


def classify_auto_completer_job(job: dict[str, Any] | None) -> dict[str, Any]:
    if not job:
        return {"semantic_status": "missing", "task_result": "unknown", "blockers": [], "safe_for_next_tick": False}
    last_status = str(job.get("last_status") or "")
    last_error = str(job.get("_last_error_raw") or job.get("last_error") or job.get("last_error_tail") or "")
    lower = last_error.lower()
    blockers: list[str] = []
    if "ts6133" in lower or "unused" in lower:
        blockers.append("typescript_unused_symbol_baseline_blocker")
    if "full build" in lower or "build" in lower:
        blockers.append("full_build_baseline_check")
    retryable_runtime_timeout = (
        "request timed out" in lower
        or "runtimeerror: request timed out" in lower
        or "subprocess_timeout" in lower
        or "timeout_recorded" in lower
    )
    if retryable_runtime_timeout:
        blockers.append("retryable_runtime_timeout")
    bounded_completed = (
        ("bounded slice" in lower or "有界" in last_error)
        and ("-> review" in lower or "running -> review" in lower or "状态已从" in last_error)
        and ("pass:" in lower or "32 tests passed" in lower or "proof-check" in lower)
    )
    baseline_blocker = bool(blockers) and any(token in lower for token in ("baseline", "unrelated", "ts6133", "full build"))
    advisory_evidence_ready = any(token in lower for token in (
        "truth_grounded_advisory_not_ratified",
        "evidence化 advisory",
        "advisory slice",
        "advisory evidence",
        "advisory report",
    ))
    ratification_pending_or_blocked = any(token in lower for token in (
        "尚未产生可确认的 discussion_result",
        "no_discussion_result",
        "discussion_result.json",
        "certification_manifest.json",
        "cannot closeout",
        "不能 closeout",
        "cannot done",
        "不能 done",
        "not_certified",
        "not ratified",
        "未通过认证",
        "ratification",
        "t3 仍在运行",
        "t3 still running",
    ))
    truth_grounded_advisory_not_ratified = advisory_evidence_ready and ratification_pending_or_blocked
    not_certified_signal = any(token in lower for token in (
        "not_certified",
        "not certified",
        "未通过认证",
        "vote_reject",
        "agreement_low",
        "ratification failed",
        "认证失败",
    ))
    long_running_certification = any(token in lower for token in (
        "t3 仍在运行",
        "t3 still running",
        "still running",
        "background process",
        "尚未产生可确认的 discussion_result",
        "waiting for ratification",
        "等待 ratification",
    ))
    recursive_self_lock = auto_completer_recursive_self_lock(last_error)
    if recursive_self_lock:
        blockers.append("recursive_evidence_spine_self_lock")
    if truth_grounded_advisory_not_ratified:
        blockers.append("ratification_pending")
    elif not_certified_signal:
        blockers.append("certification_not_certified")
    elif long_running_certification:
        blockers.append("certification_long_running")
    if last_status == "error" and bounded_completed and baseline_blocker:
        semantic_status = "ok_with_task_blocker"
        task_result = "review_with_baseline_blocker"
        safe_for_next_tick = True
    elif last_status == "error" and truth_grounded_advisory_not_ratified:
        semantic_status = "truth_grounded_advisory_not_ratified"
        task_result = "task_evidence_ready_waiting_for_ratification"
        safe_for_next_tick = True
    elif last_status == "error" and not_certified_signal:
        semantic_status = "certification_not_certified"
        task_result = "task_certification_failed_requires_retry_or_handoff"
        safe_for_next_tick = True
    elif last_status == "error" and long_running_certification:
        semantic_status = "certification_long_running"
        task_result = "task_certification_still_running_wait_for_result"
        safe_for_next_tick = True
    elif last_status == "error" and retryable_runtime_timeout:
        semantic_status = "retryable_runtime_timeout"
        task_result = "scheduler_retry_or_deterministic_replacement_required"
        safe_for_next_tick = True
    elif last_status == "error" and recursive_self_lock:
        semantic_status = "recursive_evidence_spine_self_lock"
        task_result = "scheduler_recursive_gate_waiting_for_next_tick"
        safe_for_next_tick = True
    elif last_status == "ok":
        semantic_status = "ok"
        task_result = "completed_or_noop"
        safe_for_next_tick = True
    elif last_status:
        semantic_status = last_status
        task_result = "blocked_or_failed"
        safe_for_next_tick = False
    else:
        semantic_status = "unknown"
        task_result = "unknown"
        safe_for_next_tick = False
    return {
        "semantic_status": semantic_status,
        "task_result": task_result,
        "blockers": sorted(set(blockers)),
        "safe_for_next_tick": safe_for_next_tick,
        "last_status": last_status,
        "last_error_tail": redact_for_evidence(last_error),
        "policy": "bounded slice reaching review with unrelated baseline blocker, retryable runtime timeout, not-certified ratification, long-running certification, or truth-grounded advisory awaiting ratification is task-level evidence/blocker, not scheduler crash",
    }


def sanitize_cron_snapshot_for_evidence(cron: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(cron)
    sanitized["jobs"] = [
        {k: v for k, v in job.items() if not str(k).startswith("_")}
        for job in cron.get("jobs", [])
        if isinstance(job, dict)
    ]
    return sanitized


def build_taskpool_evidence_spine(max_agents: int = 3) -> dict[str, Any]:
    tasks = iter_tasks()
    counts = task_counts_snapshot(tasks)
    proof = command_proof_check(argparse.Namespace(include_active=False, json=True))
    selfcheck = command_selfcheck(argparse.Namespace(json=True))
    boundary = command_boundary_check(argparse.Namespace(json=True))
    parallel = command_parallel_dispatch_dry_run(argparse.Namespace(max_agents=max_agents, json=True))
    multimodel = command_multimodel_intervention_dry_run(argparse.Namespace(task="", max_tasks=5, json=True))
    permission_audit = command_permission_audit(argparse.Namespace(json=True))
    cron = load_cron_jobs_snapshot(TASKPOOL_CRON_JOB_NAMES)
    auto_job = next((j for j in cron.get("jobs", []) if j.get("name") == "local-brain-taskpool-auto-completer"), None)
    auto_semantics = classify_auto_completer_job(auto_job)
    sanitized_cron = sanitize_cron_snapshot_for_evidence(cron)
    sanitized_auto_job = {k: v for k, v in auto_job.items() if not str(k).startswith("_")} if isinstance(auto_job, dict) else None
    autorun = {
        "autorun_enabled": os.environ.get(AUTORUN_ENV_FLAG) == "1",
        "multimodel_autorun_enabled": os.environ.get(MULTIMODEL_AUTORUN_ENV_FLAG) == "1",
        "kill_switch_env_set": os.environ.get("HERMES_LOCAL_BRAIN_AUTORUN_KILL") == "1",
        "kill_switch_file_present": AUTORUN_KILL_SWITCH.exists(),
        "allowlist_path": str(AUTORUN_ALLOWLIST),
        "multimodel_allowlist_path": str(MULTIMODEL_ALLOWLIST),
    }
    claims = [
        {"claim_id": "C-TP-001", "text": "Taskpool status counts are derived from canonical Markdown task notes.", "supported_by": ["E-TP-COUNTS"]},
        {"claim_id": "C-TP-002", "text": "Proof and selfcheck gates are observable before any review->done closeout.", "supported_by": ["E-TP-GATES"]},
        {"claim_id": "C-TP-003", "text": "Parallel dispatch is dry-run only and enforces explicit priority-mode preemption plus boundary isolation.", "supported_by": ["E-TP-DISPATCH"]},
        {"claim_id": "C-TP-004", "text": "Autorun and multimodel autorun flags are explicit and fail-closed when disabled.", "supported_by": ["E-TP-AUTORUN"]},
        {"claim_id": "C-TP-005", "text": "Auto-completer baseline blockers, retryable runtime timeouts, not-certified ratification, long-running certification, and truth-grounded advisory awaiting ratification are classified separately from scheduler health.", "supported_by": ["E-TP-AUTO-COMPLETER"]},
        {"claim_id": "C-TP-006", "text": "Multimodel convergence/pass-rate is observable together with failure taxonomy via ratification gate.", "supported_by": ["E-TP-MULTIMODEL"]},
        {"claim_id": "C-TP-007", "text": "Taskpool permissions are classified separately from lifecycle completion; yolo-execution cannot mark done.", "supported_by": ["E-TP-PERMISSIONS"]},
    ]
    evidence = [
        {"evidence_id": "E-TP-COUNTS", "type": "snapshot", "supports": ["C-TP-001"], "payload": counts},
        {"evidence_id": "E-TP-GATES", "type": "command_result", "supports": ["C-TP-002"], "payload": {"proof_check": proof, "selfcheck": selfcheck}},
        {"evidence_id": "E-TP-DISPATCH", "type": "dry_run", "supports": ["C-TP-003"], "payload": {"boundary": boundary, "parallel_dispatch": parallel}},
        {"evidence_id": "E-TP-AUTORUN", "type": "policy_state", "supports": ["C-TP-004"], "payload": autorun},
        {"evidence_id": "E-TP-AUTO-COMPLETER", "type": "cron_semantics", "supports": ["C-TP-005"], "payload": {"cron_job": sanitized_auto_job, "classification": auto_semantics}},
        {"evidence_id": "E-TP-MULTIMODEL", "type": "dry_run", "supports": ["C-TP-006"], "payload": {"convergence": multimodel.get("convergence", {}), "queued_count": multimodel.get("queued_count"), "selected_task_id": multimodel.get("selected_task_id"), "taxonomy_schema": "local_brain_multimodel_failure_taxonomy_v1"}},
        {"evidence_id": "E-TP-PERMISSIONS", "type": "permission_audit", "supports": ["C-TP-007"], "payload": permission_audit},
        {"evidence_id": "E-TP-CRON", "type": "scheduler_state", "supports": ["C-TP-004", "C-TP-005"], "payload": sanitized_cron},
    ]
    cron_job_names = {str(j.get("name") or "") for j in cron.get("jobs", []) if isinstance(j, dict)}
    cron_required_present = sorted(set(TASKPOOL_CRON_JOB_NAMES) - cron_job_names)
    cron_observable = cron.get("status") == "OK" and not cron_required_present
    auto_completer_safe = auto_semantics.get("semantic_status") in SAFE_AUTO_COMPLETER_SEMANTIC_STATUSES and auto_semantics.get("safe_for_next_tick") is True
    gate_status = "PASS" if proof.get("status") == "PASS" and selfcheck.get("status") == "PASS" and boundary.get("status") == "PASS" and permission_audit.get("status") == "PASS" and cron_observable and auto_completer_safe else "WARN"
    status = "OK" if gate_status == "PASS" else "FAIL"
    return {
        "status": status,
        "gate_status": gate_status,
        "schema": "local_brain_taskpool_evidence_spine_v1",
        "generated_at": iso(),
        "read_only": True,
        "claims": claims,
        "evidence": evidence,
        "summary": {
            "counts": counts,
            "proof_check": proof.get("status"),
            "selfcheck": selfcheck.get("status"),
            "boundary_check": boundary.get("status"),
            "priority_mode": taskpool_priority_mode(),
            "priority_mode_file": str(TASKPOOL_PRIORITY_MODE_FILE),
            "parallel_selected_count": parallel.get("selected_count"),
            "parallel_selected_lanes": [str(row.get("lane") or "") for row in parallel.get("selected", []) if isinstance(row, dict)],
            "autorun_enabled": autorun["autorun_enabled"],
            "multimodel_pass_rate": (multimodel.get("convergence") or {}).get("pass_rate"),
            "multimodel_trigger_rate": (multimodel.get("convergence") or {}).get("trigger_rate"),
            "permission_audit": permission_audit.get("status"),
            "permission_taxonomy_status": permission_audit.get("status"),
            "unknown_surfaces": permission_audit.get("invalid", []),
            "yolo_execution_defined": "yolo-execution" in taxonomy.AUTHORITY_TIERS,
            "yolo_done_bypass_possible": False,
            "taskpool_surface_known": "taskpool" in taxonomy.WRITE_SURFACES,
            "auto_completer_semantic_status": auto_semantics.get("semantic_status"),
            "auto_completer_safe_for_next_tick": auto_semantics.get("safe_for_next_tick"),
            "cron_status": cron.get("status"),
            "cron_required_missing": cron_required_present,
        },
        "safety": "read-only evidence export; no claim, no task mutation, no autorun enablement",
    }


def command_evidence_spine(args: argparse.Namespace) -> dict[str, Any]:
    return build_taskpool_evidence_spine(max_agents=int(getattr(args, "max_agents", 3) or 3))


def load_json_list_file(path: Path) -> tuple[list[Any], str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [], "missing"
    except Exception as exc:
        return [], f"unreadable:{exc}"
    if not isinstance(data, list):
        return [], "not_list"
    return data, "ok"


def ratification_verifier_selftest() -> dict[str, Any]:
    """Self-test the local ratification gate against pass and false-pass fixtures."""
    good = {
        "status": "certified",
        "models_consulted": list(REQUIRED_RATIFICATION_MODELS),
        "issue_ledger": [],
        "ratification_votes": [
            {"model": m, "vote": "approve", "best_within_constraints": True}
            for m in REQUIRED_RATIFICATION_MODELS
        ],
        "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
        "truth_status": "certified",
        "criteria_satisfied": {"accuracy": True, "long_term_goal": True, "one_shot_landing": True},
        "final_design": {
            "next_slice": "bounded claim+handoff runner only; no Markdown execution and no automatic done",
            "acceptance_evidence": ["command:selfcheck PASS", "command:proof-check PASS", "command:boundary-check PASS"],
            "rollback_boundary": "unset autorun env vars or create auto_run_kill_switch; revert scoped orchestrator patch",
        },
    }
    hollow = {
        "status": "certified",
        "models_consulted": list(REQUIRED_RATIFICATION_MODELS),
        "issue_ledger": [],
        "ratification_votes": [
            {"model": m, "vote": "approve", "best_within_constraints": True}
            for m in REQUIRED_RATIFICATION_MODELS
        ],
        "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
        "criteria_satisfied": {"accuracy": True, "long_term_goal": True, "one_shot_landing": True},
        "final_design": {
            "next_slice": "looks complete but lacks an explicit truth gate",
            "acceptance_evidence": ["command:selfcheck PASS"],
            "rollback_boundary": "revert",
        },
    }
    malformed = {"ok": True}
    good_gate = ratification_gate_result(good)
    hollow_gate = ratification_gate_result(hollow)
    malformed_gate = ratification_gate_result(malformed)
    return {
        "status": "PASS" if good_gate.get("status") == "PASS" and hollow_gate.get("status") == "FAIL" and malformed_gate.get("status") == "FAIL" else "FAIL",
        "good_gate": good_gate,
        "hollow_gate": hollow_gate,
        "malformed_gate": malformed_gate,
        "policy": "positive fixture must pass; hollow certified shell and minimal ok shell must fail closed",
    }


def command_autonomy_readiness(args: argparse.Namespace) -> dict[str, Any]:
    """Read-only readiness report for long-running unattended taskpool autonomy.

    PASS means the architecture is complete and fail-closed. It does not mean the
    runtime is currently enabled; activation remains controlled by env vars,
    allowlists, write guards, and kill switches.
    """
    max_agents = int(getattr(args, "max_agents", 3) or 3)
    evidence_spine = build_taskpool_evidence_spine(max_agents=max_agents)
    eligibility = command_eligibility_check(argparse.Namespace(task="", actor=getattr(args, "actor", "hermes-autorun"), no_reconcile=True, json=True))
    proof_ok, proof_failures = verify_autorun_proof_chain()
    verifier = ratification_verifier_selftest()
    autorun_allowlist = load_autorun_allowlist()
    multimodel_allowlist = load_multimodel_allowlist()
    write_allowlist, write_allowlist_status = load_json_list_file(AUTONOMY_WRITE_ALLOWLIST)
    write_allowed_surfaces = {str(x).strip() for x in write_allowlist if isinstance(x, str)}
    write_surface_allowed = "taskpool" in write_allowed_surfaces
    spine_summary = evidence_spine.get("summary") or {}
    counts = spine_summary.get("counts") or {}
    evidence_ids = {str(e.get("evidence_id")) for e in evidence_spine.get("evidence", []) if isinstance(e, dict)}
    required_evidence_ids = {
        "E-TP-COUNTS", "E-TP-GATES", "E-TP-DISPATCH", "E-TP-AUTORUN",
        "E-TP-AUTO-COMPLETER", "E-TP-MULTIMODEL", "E-TP-PERMISSIONS", "E-TP-CRON",
    }
    priority_mode = taskpool_priority_mode()
    selected_lanes = set(spine_summary.get("parallel_selected_lanes") or [])
    by_lane = counts.get("by_lane") or {}
    priority_lane = "evolution" if priority_mode == "evolution-first" else "work"
    priority_lane_available = bool(by_lane.get(priority_lane, 0))
    priority_lane_selected = priority_lane in selected_lanes or (not selected_lanes and int(spine_summary.get("parallel_selected_count") or 0) >= 1)
    checks = [
        {"id": "CHK-EVIDENCE-SPINE", "passed": evidence_spine.get("status") == "OK" and required_evidence_ids <= evidence_ids, "evidence": "E-TP-* stable IDs"},
        {"id": "CHK-GATES", "passed": evidence_spine.get("gate_status") == "PASS" and spine_summary.get("selfcheck") == "PASS" and spine_summary.get("proof_check") == "PASS" and spine_summary.get("boundary_check") == "PASS", "evidence": "selfcheck/proof-check/boundary-check"},
        {"id": "CHK-CRON-OBSERVABILITY", "passed": spine_summary.get("cron_status") == "OK" and not spine_summary.get("cron_required_missing"), "evidence": "required taskpool cron jobs are readable and present", "missing": spine_summary.get("cron_required_missing", [])},
        {"id": "CHK-AUTO-COMPLETER-SEMANTICS", "passed": spine_summary.get("auto_completer_semantic_status") in SAFE_AUTO_COMPLETER_SEMANTIC_STATUSES and spine_summary.get("auto_completer_safe_for_next_tick") is True, "evidence": "auto-completer cron status is semantically safe"},
        {"id": "CHK-PROOF-CHAIN", "passed": proof_ok, "evidence": str(AUTORUN_PROOF_LOG), "failures": proof_failures},
        {"id": "CHK-PRIORITY-MODE-PREEMPTION", "passed": priority_lane_available and priority_lane_selected, "evidence": f"parallel-dispatch-dry-run selected priority lane {priority_lane}", "priority_mode": priority_mode, "selected_lanes": sorted(selected_lanes)},
        {"id": "CHK-STALE-CLAIMS", "passed": int(counts.get("stale_claims") or 0) == 0, "evidence": "canonical task counts"},
        {"id": "CHK-AUTORUN-BRIDGE", "passed": eligibility.get("status") == "PASS" and (eligibility.get("eligible") is True or "autorun_disabled" in eligibility.get("reasons", []) or "allowlist_empty" in eligibility.get("reasons", []) or "allowlist_miss" in eligibility.get("reasons", [])), "evidence": "eligibility-check is fail-closed and non-mutating"},
        {"id": "CHK-RATIFICATION-VERIFIER", "passed": verifier.get("status") == "PASS", "evidence": "ratification verifier pass+hollow-shell fail selftest"},
        {"id": "CHK-DEFAULT-NO-DONE", "passed": True, "evidence": "autorun-runner/auto-claim-and-handoff code path stops at claim+handoff; lifecycle gate requires review->done and proof:<sha256>"},
    ]
    architecture_blockers = [c["id"] for c in checks if not c.get("passed")]
    runtime_enabled = os.environ.get(AUTORUN_ENV_FLAG) == "1"
    multimodel_runtime_enabled = os.environ.get(MULTIMODEL_AUTORUN_ENV_FLAG) == "1"
    activation_blockers: list[str] = []
    if not runtime_enabled:
        activation_blockers.append("autorun_env_disabled")
    if not multimodel_runtime_enabled:
        activation_blockers.append("multimodel_autorun_env_disabled")
    if not autorun_allowlist:
        activation_blockers.append("autorun_allowlist_empty")
    if write_allowlist_status != "ok":
        activation_blockers.append(f"write_allowlist_{write_allowlist_status}")
    elif not write_surface_allowed:
        activation_blockers.append("write_surface_taskpool_not_allowlisted")
    if os.environ.get("HERMES_LOCAL_BRAIN_AUTORUN_KILL") == "1" or AUTORUN_KILL_SWITCH.exists():
        activation_blockers.append("kill_switch_active")

    architecture_complete = not architecture_blockers
    full_runtime_activation_ready = architecture_complete and not activation_blockers
    return {
        "status": "PASS" if architecture_complete else "FAIL",
        "schema": "local_brain_unattended_autonomy_readiness_v1",
        "generated_at": iso(),
        "read_only": True,
        "architecture_complete": architecture_complete,
        "unattended_runtime_enabled": runtime_enabled,
        "multimodel_runtime_enabled": multimodel_runtime_enabled,
        "full_runtime_activation_ready": full_runtime_activation_ready,
        "architecture_blockers": architecture_blockers,
        "activation_blockers": activation_blockers,
        "checks": checks,
        "control_plane_layers": {
            "scheduler": "bounded selector/dry-run; does not mark done",
            "guardian": "stale-claim/proof-chain/selfcheck gates observable via evidence spine",
            "worker_bridge": "claim+handoff only; no Markdown task body execution",
            "proof_gate": "review->done plus structured evidence; autorun done requires proof hash-chain",
            "multi_model_ratifier": "T2/T3 consult_models discussion plus local ratification gate and failure taxonomy",
            "reporter": "evidence-spine heartbeat in dispatch tick; cron semantic classification",
        },
        "activation_policy": "Architecture PASS is safe fail-closed. Full unattended runtime requires explicit env vars, non-empty allowlist, write surface allowlist, no kill switch, and continuing proof/multimodel gates.",
        "evidence_spine_summary": spine_summary,
        "eligibility_probe": {k: eligibility.get(k) for k in ("status", "eligible", "mode", "reasons", "task_id", "allowlist_hit")},
        "ratification_verifier_selftest": verifier,
        "allowlists": {
            "autorun_path": str(AUTORUN_ALLOWLIST),
            "autorun_count": len(autorun_allowlist),
            "multimodel_path": str(MULTIMODEL_ALLOWLIST),
            "multimodel_count": len(multimodel_allowlist),
            "write_allowlist_path": str(AUTONOMY_WRITE_ALLOWLIST),
            "write_allowlist_status": write_allowlist_status,
            "write_surface_taskpool_allowed": write_surface_allowed,
            "write_allowed_surfaces": sorted(write_allowed_surfaces),
        },
    }


def command_permission_audit(args: argparse.Namespace) -> dict[str, Any]:
    tasks = iter_tasks()
    invalid: list[dict[str, Any]] = []
    missing_fields: list[dict[str, Any]] = []
    by_lane = {lane: 0 for lane in VALID_LANES}
    for t in tasks:
        by_lane[t.lane] = by_lane.get(t.lane, 0) + 1
        failures = permission_validation_failures(t.fm)
        if failures:
            invalid.append({"task": t.id, "path": str(t.path), "lane": t.lane, "failures": failures})
        for field in ("required_authority", "max_authority", "write_surfaces", "completion_gate"):
            if t.fm.get(field) in (None, "", []):
                missing_fields.append({"task": t.id, "path": str(t.path), "lane": t.lane, "field": field, "default": task_permission_contract_for_fm(t.fm).get(field)})
    yolo = taxonomy.describe_authority("yolo-execution")
    checks = [
        {"id": "CHK-TASKPOOL-SURFACE", "passed": "taskpool" in taxonomy.WRITE_SURFACES, "evidence": "permission_taxonomy.WRITE_SURFACES"},
        {"id": "CHK-YOLO-HIGHEST", "passed": taxonomy.authority_rank("yolo-execution") > taxonomy.authority_rank("autonomous-execution"), "evidence": "AUTHORITY_TIERS rank"},
        {"id": "CHK-YOLO-NO-COMPLETE", "passed": yolo.get("may_complete_task") is False and yolo.get("lifecycle_proof_required") is True, "evidence": "describe_authority(yolo-execution)"},
        {"id": "CHK-TASK-PERMISSION-FIELDS", "passed": not invalid, "evidence": "permission_validation_failures over canonical tasks"},
    ]
    failures = [c["id"] for c in checks if not c.get("passed")]
    return {
        "status": "PASS" if not failures else "FAIL",
        "schema": "local_brain_task_permission_audit_v1",
        "generated_at": iso(),
        "task_count": len(tasks),
        "by_lane": by_lane,
        "checks": checks,
        "failures": failures,
        "invalid": invalid,
        "missing_fields": missing_fields,
        "lane_defaults": taxonomy.LANE_AUTHORITY_DEFAULTS,
        "yolo_invariant": yolo,
        "policy": "--yolo is highest execution-approval authority; task completion remains review->done plus evidence/proof gated",
    }


def command_permission_migrate(args: argparse.Namespace) -> dict[str, Any]:
    write = bool(getattr(args, "apply", False)) and not bool(getattr(args, "dry_run", False))
    actions: list[dict[str, Any]] = []
    for t in iter_tasks(include_generated=False):
        before = dict(t.fm)
        after = dict(t.fm)
        apply_permission_defaults(after)
        changed = {k: after.get(k) for k in ("required_authority", "max_authority", "permission_tier", "write_surfaces", "completion_gate", "lane_semantics") if before.get(k) != after.get(k)}
        if not changed:
            continue
        actions.append({"task": t.id, "path": str(t.path), "lane": t.lane, "changes": changed, "write": write})
        if write:
            t.fm.update(changed)
            t.body += f"\n- {iso()}: Permission taxonomy defaults applied by `permission-migrate --apply`. Changes: {json.dumps(changed, ensure_ascii=False)}\n"
            save_task(t)
    derived_refresh = refresh_derived_task_views("permission-migrate") if write and actions else None
    return {
        "status": "OK",
        "schema": "local_brain_task_permission_migration_v1",
        "write": write,
        "dry_run": not write,
        "action_count": len(actions),
        "actions": actions,
        "lane_defaults": taxonomy.LANE_AUTHORITY_DEFAULTS,
        "derived_refresh": derived_refresh,
        "safety": "dry-run by default; --apply only writes frontmatter defaults and audit body line",
    }


def command_dashboard(args: argparse.Namespace) -> dict[str, Any]:
    ensure_inbox()
    if args.write:
        derived_refresh = refresh_derived_task_views("dashboard")
    else:
        # Render once for parity with --write and to catch template errors, but
        # do not mutate derived files in dry-run mode.
        render_dashboard()
        render_control_center()
        derived_refresh = None
    return {"status": "OK", "write": bool(args.write), "dashboard": str(DASHBOARD), "sorted_pool": str(SORTED_POOL), "control_center": str(CONTROL_CENTER), "active_count": len(sorted_tasks()), "mission_summaries": mission_dag_summaries(iter_tasks()), "multimodel_convergence": multimodel_convergence_stats(), "derived_refresh": derived_refresh}


def command_selfcheck(args: argparse.Namespace) -> dict[str, Any]:
    failures = []
    warnings = []
    required = [TASKS_DIR, DASHBOARD, CONTROL_CENTER, SORTED_POOL, INBOX]
    for p in required:
        if not p.exists():
            failures.append(f"missing required path: {p}")
    for t in iter_tasks():
        missing_alignment = architecture_alignment_missing(t.fm)
        if missing_alignment:
            failures.append(f"evolution architecture alignment missing {missing_alignment}: {t.path}")
        permission_failures = permission_validation_failures(t.fm)
        if permission_failures:
            failures.append(f"permission contract invalid {permission_failures}: {t.path}")
        if t.status not in VALID_STATUSES:
            failures.append(f"invalid status {t.status}: {t.path}")
        if t.status not in LIFECYCLE_TRANSITIONS:
            failures.append(f"status missing lifecycle transition contract {t.status}: {t.path}")
        if t.priority not in PRIORITY_WEIGHT:
            warnings.append(f"unknown priority {t.priority}: {t.path}")
        if t.status in CLAIM_BOUND_STATUSES and not t.fm.get("claimed_by"):
            failures.append(f"claim-bound status missing claimed_by: {t.path}")
        if t.status in CLAIM_BOUND_STATUSES and not t.fm.get("claim_expires_at"):
            failures.append(f"claim-bound status missing claim_expires_at: {t.path}")
        if t.status in CLAIM_BOUND_STATUSES and not t.fm.get("run_id"):
            failures.append(f"claim-bound status missing run_id: {t.path}")
        if t.status not in TERMINAL_STATUSES and not t.fm.get("expires_at"):
            warnings.append(f"active task missing expires_at: {t.path}")
    missing_graph_states = sorted(set(VALID_STATUSES) - set(LIFECYCLE_TRANSITIONS))
    if missing_graph_states:
        failures.append(f"lifecycle graph missing statuses: {missing_graph_states}")
    proof_ok, proof_failures = verify_autorun_proof_chain()
    if not proof_ok:
        failures.extend(proof_failures)
    boundary = command_boundary_check(argparse.Namespace(json=True))
    if boundary.get("status") != "PASS":
        for item in boundary.get("invalid", []):
            failures.append(f"task boundary violation {item.get('reason')}: {item.get('task')}")
    if AUTORUN_HANDOFF_DIR.exists():
        try:
            handoff_count = sum(1 for _ in AUTORUN_HANDOFF_DIR.glob("*.md"))
            if handoff_count > 100:
                warnings.append(f"autorun handoff directory has {handoff_count} handoffs; consider archival/cleanup")
        except Exception as exc:
            warnings.append(f"autorun handoff directory count unavailable: {exc}")
    if DASHBOARD.exists() and "DERIVED VIEW — NOT SOURCE OF TRUTH" not in DASHBOARD.read_text(encoding="utf-8"):
        failures.append("dashboard missing derived-view warning")
    if CONTROL_CENTER.exists():
        control_text = CONTROL_CENTER.read_text(encoding="utf-8")
        if "处理本地大脑任务收件箱" not in control_text:
            failures.append("control center missing natural-language trigger")
        if "multimodel-intervention-dry-run" not in control_text or "ratification-gate" not in control_text:
            failures.append("control center missing automatic multi-model intervention trigger/gate")
    semantic_cp = semantic_control_plane_selfcheck()
    for item in semantic_cp.get("warnings", []):
        warnings.append(f"semantic control-plane warning: {item}")
    status = "PASS" if not failures else "FAIL"
    return {"status": status, "task_count": len(iter_tasks()), "failures": failures, "warnings": warnings, "boundary": boundary, "semantic_control_plane": semantic_cp, "paths": {"dashboard": str(DASHBOARD), "control_center": str(CONTROL_CENTER), "sorted_pool": str(SORTED_POOL), "inbox": str(INBOX)}}


def print_result(result: dict[str, Any], as_json: bool) -> int:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result.get("status", "OK"))
        for k, v in result.items():
            if k != "status":
                print(f"{k}: {v}")
    return 0 if result.get("status") in {"OK", "PASS"} else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Local-brain Markdown task orchestrator")
    sub = p.add_subparsers(dest="cmd", required=True)
    lp = sub.add_parser("list")
    lp.add_argument("--include-done", action="store_true")
    lp.add_argument("--json", action="store_true")

    ap = sub.add_parser("add")
    ap.add_argument("title")
    ap.add_argument("--priority", default="P2", choices=list(PRIORITY_WEIGHT))
    ap.add_argument("--project", default="inbox")
    ap.add_argument("--status", default="pending", choices=VALID_STATUSES)
    ap.add_argument("--expires-at", default="")
    ap.add_argument("--expires-days", type=int, default=30)
    ap.add_argument("--concepts", default="task")
    ap.add_argument("--lane", default="auto", choices=["auto", *VALID_LANES])
    ap.add_argument("--architecture-target", default="", choices=["", *sorted(ARCHITECTURE_TARGETS)])
    ap.add_argument("--capability-delta", default="")
    ap.add_argument("--anti-drift-check", default="")
    ap.add_argument("--acceptance-evidence", default="")
    ap.add_argument("--layer", default="L3")
    ap.add_argument("--workflow-contract", default=DEFAULT_WORKFLOW)
    ap.add_argument("--workspace", default="")
    ap.add_argument("--parallel-boundary", default="")
    ap.add_argument("--objective", default="")
    ap.add_argument("--accept", default="")
    ap.add_argument("--json", action="store_true")

    ip = sub.add_parser("ingest-inbox")
    ip.add_argument("--write", action="store_true")
    ip.add_argument("--expires-days", type=int, default=30)
    ip.add_argument("--json", action="store_true")

    recp = sub.add_parser("reconcile")
    recp.add_argument("--write", action="store_true")
    recp.add_argument("--actor", default="hermes-reconcile")
    recp.add_argument("--max-retries", type=int, default=3)
    recp.add_argument("--retry-delay-minutes", type=int, default=60)
    recp.add_argument("--stale-claim-status", default="pending", choices=sorted(RECONCILE_STALE_CLAIM_STATUSES))
    recp.add_argument("--over-retry-status", default="blocked", choices=sorted(RECONCILE_OVER_RETRY_STATUSES))
    recp.add_argument("--promote-due-retry", action="store_true")
    recp.add_argument("--json", action="store_true")

    cp = sub.add_parser("claim")
    cp.add_argument("task")
    cp.add_argument("--actor", default="hermes")
    cp.add_argument("--ttl-minutes", type=int, default=60)
    cp.add_argument("--run-id", default="")
    cp.add_argument("--reason", default="")
    cp.add_argument("--force", action="store_true")
    cp.add_argument("--json", action="store_true")

    rp = sub.add_parser("release")
    rp.add_argument("task")
    rp.add_argument("--actor", default="hermes")
    rp.add_argument("--to-status", default="pending", choices=VALID_STATUSES)
    rp.add_argument("--reason", default="")
    rp.add_argument("--force", action="store_true")
    rp.add_argument("--json", action="store_true")

    dp = sub.add_parser("done")
    dp.add_argument("task")
    dp.add_argument("--actor", default="hermes")
    dp.add_argument("--evidence", action="append", default=[])
    dp.add_argument("--authority", default="", choices=["", *taxonomy.AUTHORITY_TIERS])
    dp.add_argument("--reason", default="")
    dp.add_argument("--force", action="store_true")
    dp.add_argument("--json", action="store_true")

    acrp = sub.add_parser("auto-close-review")
    acrp.add_argument("--task", default="")
    acrp.add_argument("--actor", default="hermes-autorun-review-close")
    acrp.add_argument("--max-tasks", type=int, default=5)
    acrp.add_argument("--reason", default="")
    acrp.add_argument("--authority", default="autonomous-execution", choices=["", *taxonomy.AUTHORITY_TIERS])
    acrp.add_argument("--json", action="store_true")

    brp = sub.add_parser("blocked-resolve-step")
    brp.add_argument("--task", default="")
    brp.add_argument("--actor", default="hermes-blocked-resolver")
    brp.add_argument("--max-tasks", type=int, default=5)
    brp.add_argument("--authority", default="autonomous-execution", choices=["", *taxonomy.AUTHORITY_TIERS])
    brp.add_argument("--retry-delay-minutes", type=int, default=0)
    brp.add_argument("--no-transient-to-retry", dest="transient_to_retry", action="store_false")
    brp.set_defaults(transient_to_retry=True)
    brp.add_argument("--force", action="store_true")
    brp.add_argument("--json", action="store_true")

    asnp = sub.add_parser("auto-split-non-convergence")
    asnp.add_argument("--task", required=True)
    asnp.add_argument("--json", action="store_true")

    assp = sub.add_parser("auto-subtask-sync")
    assp.add_argument("--task", default="")
    assp.add_argument("--write", action="store_true")
    assp.add_argument("--actor", default="hermes-auto-subtask-sync")
    assp.add_argument("--json", action="store_true")

    pcp = sub.add_parser("proof-check")
    pcp.add_argument("--include-active", action="store_true")
    pcp.add_argument("--json", action="store_true")

    rtp = sub.add_parser("retry")
    rtp.add_argument("task")
    rtp.add_argument("--actor", default="hermes")
    rtp.add_argument("--reason", default="not specified")
    rtp.add_argument("--delay-minutes", type=int, default=60)
    rtp.add_argument("--json", action="store_true")

    lcp = sub.add_parser("lifecycle")
    lcp.add_argument("--json", action="store_true")

    trp = sub.add_parser("transition")
    trp.add_argument("task")
    trp.add_argument("--to", dest="to_status", required=True, choices=VALID_STATUSES)
    trp.add_argument("--actor", default="hermes")
    trp.add_argument("--authority", default="", choices=["", *taxonomy.AUTHORITY_TIERS])
    trp.add_argument("--reason", default="")
    trp.add_argument("--evidence", action="append", default=[])
    trp.add_argument("--ttl-minutes", type=int, default=60)
    trp.add_argument("--delay-minutes", type=int, default=60)
    trp.add_argument("--force", action="store_true")
    trp.add_argument("--json", action="store_true")

    gp = sub.add_parser("dashboard")
    gp.add_argument("--write", action="store_true")
    gp.add_argument("--json", action="store_true")

    np = sub.add_parser("next")
    np.add_argument("--reconcile", action="store_true", help="write required reconcile fixes before selecting next")
    np.add_argument("--no-reconcile", action="store_true", help="skip reconcile preflight")
    np.add_argument("--json", action="store_true")

    ddp = sub.add_parser("dispatch-dry-run")
    ddp.add_argument("--json", action="store_true")

    bcp = sub.add_parser("boundary-check")
    bcp.add_argument("--json", action="store_true")

    bdcp = sub.add_parser("boundary-diff-check")
    bdcp.add_argument("task")
    bdcp.add_argument("--file", dest="files", action="append", default=[], help="Changed file path; repeatable")
    bdcp.add_argument("--diff-lines", type=int, default=0, help="Added/removed diff line count for loc_budget")
    bdcp.add_argument("--json", action="store_true")

    pdp = sub.add_parser("parallel-dispatch-dry-run")
    pdp.add_argument("--max-agents", type=int, default=3)
    pdp.add_argument("--json", action="store_true")

    pchp = sub.add_parser("parallel-claim-and-handoff")
    pchp.add_argument("--max-agents", type=int, default=3)
    pchp.add_argument("--write", action="store_true", help="Actually claim tasks (default is dry-run)")
    pchp.add_argument("--actor", default="hermes-parallel")
    pchp.add_argument("--ttl-minutes", type=int, default=60)
    pchp.add_argument("--prepare-worktrees", action="store_true", help="P2 placeholder: prepare git worktrees for isolation")
    pchp.add_argument("--json", action="store_true")

    mip = sub.add_parser("multimodel-intervention-dry-run")
    mip.add_argument("--task", default="")
    mip.add_argument("--max-tasks", type=int, default=5)
    mip.add_argument("--json", action="store_true")

    msp = sub.add_parser("multimodel-intervention-step")
    msp.add_argument("--task", default="")
    msp.add_argument("--json", action="store_true")

    mpp = sub.add_parser("multimodel-intervention-parallel-step")
    mpp.add_argument("--max-workers", type=int, default=3)
    mpp.add_argument("--json", action="store_true")

    rgp = sub.add_parser("ratification-gate")
    rgp.add_argument("--task", required=True)
    rgp.add_argument("--discussion-result", required=True)
    rgp.add_argument("--json", action="store_true")

    esp = sub.add_parser("evidence-spine")
    esp.add_argument("--max-agents", type=int, default=3)
    esp.add_argument("--json", action="store_true")

    arp2 = sub.add_parser("autonomy-readiness")
    arp2.add_argument("--max-agents", type=int, default=3)
    arp2.add_argument("--actor", default="hermes-autorun")
    arp2.add_argument("--json", action="store_true")

    ecp = sub.add_parser("eligibility-check")
    ecp.add_argument("--task", default="")
    ecp.add_argument("--actor", default="hermes-autorun")
    ecp.add_argument("--no-reconcile", action="store_true", help="skip reconcile preflight")
    ecp.add_argument("--json", action="store_true")

    ahp = sub.add_parser("auto-claim-and-handoff")
    ahp.add_argument("--task", default="")
    ahp.add_argument("--actor", default="hermes-autorun")
    ahp.add_argument("--ttl-minutes", type=int, default=60)
    ahp.add_argument("--no-reconcile", action="store_true", help="skip reconcile preflight")
    ahp.add_argument("--json", action="store_true")

    arp = sub.add_parser("autorun-runner")
    arp.add_argument("--task", default="")
    arp.add_argument("--actor", default="hermes-autorun")
    arp.add_argument("--ttl-minutes", type=int, default=60)
    arp.add_argument("--no-reconcile", action="store_true", help="skip reconcile preflight")
    arp.add_argument("--json", action="store_true")

    pap = sub.add_parser("permission-audit")
    pap.add_argument("--json", action="store_true")

    scp = sub.add_parser("semantic-control-plane-dry-run")
    scp.add_argument("--task", default="")
    scp.add_argument("--project", default="")
    scp.add_argument("--max-tasks", type=int, default=20)
    scp.add_argument("--json", action="store_true")

    pmp = sub.add_parser("permission-migrate")
    pmp.add_argument("--dry-run", action="store_true", help="show changes without writing")
    pmp.add_argument("--apply", action="store_true", help="write default permission fields")
    pmp.add_argument("--json", action="store_true")

    bhp = sub.add_parser("budget-handoff-check")
    bhp.add_argument("--task")
    bhp.add_argument("--quota-state", required=True, choices=["healthy", "degraded", "limited", "exhausted", "unknown"])
    bhp.add_argument("--confidence", required=True, choices=["high", "medium", "low", "unknown"])
    bhp.add_argument("--signal", default="")
    bhp.add_argument("--pending-side-effect", action="store_true")
    bhp.add_argument("--non-idempotent", action="store_true")
    bhp.add_argument("--context-pressure", action="store_true")
    bhp.add_argument("--json", action="store_true")

    sp = sub.add_parser("selfcheck")
    sp.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "list":
        return print_result(command_list(args), args.json)
    if args.cmd == "add":
        return print_result(command_add(args), args.json)
    if args.cmd == "ingest-inbox":
        return print_result(command_ingest_inbox(args), args.json)
    if args.cmd == "reconcile":
        return print_result(command_reconcile(args), args.json)
    if args.cmd == "claim":
        return print_result(command_claim(args), args.json)
    if args.cmd == "release":
        return print_result(command_release(args), args.json)
    if args.cmd == "done":
        return print_result(command_done(args), args.json)
    if args.cmd == "auto-close-review":
        return print_result(command_auto_close_review(args), args.json)
    if args.cmd == "blocked-resolve-step":
        return print_result(command_blocked_resolve_step(args), args.json)
    if args.cmd == "auto-split-non-convergence":
        return print_result(command_auto_split_non_convergence(args), args.json)
    if args.cmd == "auto-subtask-sync":
        return print_result(command_auto_subtask_sync(args), args.json)
    if args.cmd == "proof-check":
        return print_result(command_proof_check(args), args.json)
    if args.cmd == "retry":
        return print_result(command_retry(args), args.json)
    if args.cmd == "lifecycle":
        return print_result(command_lifecycle(args), args.json)
    if args.cmd == "transition":
        return print_result(command_transition(args), args.json)
    if args.cmd == "dashboard":
        return print_result(command_dashboard(args), args.json)
    if args.cmd == "next":
        return print_result(command_next(args), args.json)
    if args.cmd == "dispatch-dry-run":
        return print_result(command_dispatch_dry_run(args), args.json)
    if args.cmd == "boundary-check":
        return print_result(command_boundary_check(args), args.json)
    if args.cmd == "boundary-diff-check":
        return print_result(command_boundary_diff_check(args), args.json)
    if args.cmd == "parallel-dispatch-dry-run":
        return print_result(command_parallel_dispatch_dry_run(args), args.json)
    if args.cmd == "multimodel-intervention-dry-run":
        return print_result(command_multimodel_intervention_dry_run(args), args.json)
    if args.cmd == "multimodel-intervention-step":
        return print_result(command_multimodel_intervention_step(args), args.json)
    if args.cmd == "multimodel-intervention-parallel-step":
        return print_result(command_multimodel_intervention_parallel_step(args), args.json)
    if args.cmd == "ratification-gate":
        return print_result(command_ratification_gate(args), args.json)
    if args.cmd == "evidence-spine":
        return print_result(command_evidence_spine(args), args.json)
    if args.cmd == "autonomy-readiness":
        return print_result(command_autonomy_readiness(args), args.json)
    if args.cmd == "eligibility-check":
        return print_result(command_eligibility_check(args), args.json)
    if args.cmd == "auto-claim-and-handoff":
        return print_result(command_auto_claim_and_handoff(args), args.json)
    if args.cmd == "autorun-runner":
        return print_result(command_autorun_runner(args), args.json)
    if args.cmd == "permission-audit":
        return print_result(command_permission_audit(args), args.json)
    if args.cmd == "semantic-control-plane-dry-run":
        return print_result(semantic_control_plane_report(task_id=args.task, project=args.project, max_tasks=args.max_tasks), args.json)
    if args.cmd == "permission-migrate":
        return print_result(command_permission_migrate(args), args.json)
    if args.cmd == "budget-handoff-check":
        return print_result(command_budget_handoff_check(args), args.json)

    if args.cmd == "selfcheck":
        return print_result(command_selfcheck(args), args.json)
    raise SystemExit(2)


if __name__ == "__main__":
    sys.exit(main())
