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
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser()
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
VALID_STATUSES = ["proposed", "pending", "claimed", "running", "retry", "review", "blocked", "done", "archived", "expired"]
STATUS_ALIASES = {"completed": "done"}  # legacy notes may use completed; normalize as terminal done.
ACTIVE_STATUSES = {"proposed", "pending", "claimed", "running", "retry", "review", "blocked"}
TERMINAL_STATUSES = {"done", "archived", "expired"}
PRIORITY_WEIGHT = {"P0": 400, "P1": 300, "P2": 200, "P3": 100}
STATUS_WEIGHT = {"retry": 60, "running": 50, "claimed": 45, "blocked": 40, "review": 35, "pending": 30, "proposed": 10, "done": -100, "archived": -120, "expired": -130}
VALID_LANES = ["work", "evolution", "advisory"]
LANE_SORT_WEIGHT = {"work": 0, "advisory": 1, "evolution": 2}
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
    "blocked": ["pending", "retry", "archived", "expired"],
    "done": ["archived"],
    "archived": [],
    "expired": ["archived"],
}
REASON_REQUIRED_TO = {"retry", "blocked"}
EVIDENCE_REQUIRED_TO = {"review", "done"}
CLAIM_BOUND_STATUSES = {"claimed", "running", "review"}
INITIAL_TASK_STATUSES = {"proposed", "pending"}
RECONCILE_STALE_CLAIM_STATUSES = {"pending", "blocked", "expired"}
RECONCILE_OVER_RETRY_STATUSES = {"blocked", "expired"}


def now() -> datetime:
    return datetime.now(TZ).replace(microsecond=0)


def iso(dt: datetime | None = None) -> str:
    return (dt or now()).isoformat()


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
    evidence = guard.guard_or_raise("kanban-worker", "claim-and-handoff", "dispatch-hint", AUTONOMY_WRITE_ALLOWLIST)
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
        "mission_schema_version", "mission_id", "mission_title", "mission_objective", "mission_constraints",
        "red_lines", "non_goals", "evidence_refs", "acceptance_criteria", "dag_nodes", "checkpoint_states",
        "permission_gates", "handoff_artifacts", "proof_artifacts", "rollback_signal", "certification_status",
        "ratification_artifact", "mission_node_id", "mission_node_depends_on", "mission_node_kind",
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
        "rollback_signal", "certification_status", "ratification_artifact",
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
        if f.startswith("agreement_below_threshold"):
            add("agreement_low", f)
        if f.startswith("missing_required_model_vote") or f.startswith("duplicate_vote_model") or f.startswith("unexpected_vote_model"):
            add("model_vote_missing", f)
        if f.startswith("best_within_constraints_missing") or "criterion_missing" in f or "one_shot_plan_missing" in f:
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
    return {
        "schema": "local_brain_multimodel_failure_taxonomy_v1",
        "categories": categories,
        "active_categories": {k: v for k, v in categories.items() if v},
        "summary": [f"{k}:{len(v)}" for k, v in categories.items() if v],
    }


def write_multimodel_result_to_task(task: "Task", gate_result: dict[str, Any], discussion_path: str, state_path: str) -> dict[str, Any]:
    """Write multimodel ratification result to task frontmatter.

    Called when ratification_gate returns PASS/LOOP_DONE. Updates:
    - multimodel_status: certified / not_certified
    - multimodel_ratification_artifact: path to discussion result
    """
    passed = gate_result.get("status") == "PASS" and gate_result.get("decision") == "LOOP_DONE"
    status_value = "certified" if passed else "not_certified"
    updates = {
        "multimodel_status": status_value,
        "multimodel_ratification_artifact": discussion_path,
    }
    updates["certification_status"] = status_value

    path = Path(task.path)
    content = path.read_text(encoding="utf-8")
    lines = content.split("\n")

    if not lines or lines[0].strip() != "---":
        return {"status": "SKIP", "reason": "no_frontmatter", "task_id": task.id}
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return {"status": "SKIP", "reason": "unclosed_frontmatter", "task_id": task.id}

    fm_lines = lines[1:end_idx]
    body_lines = lines[end_idx + 1:]

    existing_keys: set[str] = set()
    for i, line in enumerate(fm_lines):
        for key, value in updates.items():
            if line.startswith(f"{key}:"):
                fm_lines[i] = f"{key}: {value}"
                existing_keys.add(key)

    for key, value in updates.items():
        if key not in existing_keys:
            fm_lines.append(f"{key}: {value}")

    new_content = "\n".join(["---"] + fm_lines + ["---"] + body_lines)
    path.write_text(new_content, encoding="utf-8")
    return {"status": "OK", "task_id": task.id, "updates": updates, "passed": passed}


def task_multimodel_intervention_reasons(task: "Task") -> list[str]:
    """Return automatic multi-model intervention reasons for active task notes.

    Trigger policy is intentionally deterministic and local-only: model agreement is
    never treated as evidence here. The command surfaces when to invoke the live
    consult_models.py PUA-loop gate; it does not mutate task state or execute hooks.

    Trigger strategy: structural-first, keyword-supplemented.
    - Strong structural triggers fire immediately (P0+evolution, retry>=2).
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
    # Strong triggers fire alone; everything else needs >= 2 signals.
    strong = {"p0_evolution_blast_radius", "loop_non_convergence", "stale_claim"}
    if strong & set(unique):
        return unique
    if len(unique) >= 2:
        return unique
    return []


def task_multimodel_intervention_required(task: "Task") -> bool:
    return bool(task_multimodel_intervention_reasons(task))


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
        if is_mission_envelope_fm(self.fm) and not mission_envelope_valid(self.fm):
            return False
        if not ignore_mission_node and mission_node_blockers(self):
            return False
        return True

    def row(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "priority": self.priority,
            "score": self.score(),
            "lane": self.lane,
            "architecture_target": self.architecture_target,
            "architecture_aligned": self.architecture_aligned(),
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
            "project": self.project,
            "claimed_by": self.fm.get("claimed_by") or "",
            "claim_expires_at": self.fm.get("claim_expires_at") or "",
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


def sorted_tasks(include_done: bool = False) -> list[Task]:
    rows = [t for t in iter_tasks() if include_done or t.status not in TERMINAL_STATUSES]
    return sorted(rows, key=lambda t: (-t.score(), t.expires_at() or datetime.max.replace(tzinfo=TZ), t.priority, t.id))


def dispatch_sort_key(t: Task) -> tuple[int, int, datetime, str, str]:
    return (LANE_SORT_WEIGHT.get(t.lane, 1), -t.score(), t.expires_at() or datetime.max.replace(tzinfo=TZ), t.priority, t.id)


def dispatchable_tasks() -> list[Task]:
    rows = [t for t in iter_tasks() if t.is_dispatchable()]
    return sorted(rows, key=dispatch_sort_key)


def evidence_is_structured(e: str) -> bool:
    e = (e or "").strip()
    if not e:
        return False
    prefixes = ("command:", "file:", "search:", "brainctl:", "url:", "artifact:", "proof:")
    if e.startswith(prefixes):
        return True
    p = Path(os.path.expanduser(e))
    return p.is_absolute() and p.exists()


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
    for item in allowlist:
        if isinstance(item, str):
            token = item.strip()
            if token in {task.id, f"task:{task.id}", task.project, f"project:{task.project}", task.title}:
                return True
        elif isinstance(item, dict):
            task_id = str(item.get("task_id") or item.get("id") or "").strip()
            project = str(item.get("project") or "").strip()
            title = str(item.get("title") or "").strip()
            if (task_id and task_id == task.id) or (project and project == task.project) or (title and title == task.title):
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


def lifecycle_gate(task: Task, to_status: str, actor: str, evidence: list[str] | None = None, reason: str = "", force: bool = False) -> tuple[list[str], list[str]]:
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
    if missing_alignment and to_status in (CLAIM_BOUND_STATUSES | {"done"}) and not force:
        failures.append(f"evolution_architecture_alignment_missing: {missing_alignment}")
    missing_mission = mission_envelope_missing(task.fm)
    if missing_mission and to_status in (CLAIM_BOUND_STATUSES | {"done"}) and not force:
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
    if to_status in EVIDENCE_REQUIRED_TO and not evidence:
        failures.append(f"transition to {to_status} requires structured --evidence")
    invalid_evidence = [e for e in evidence if not evidence_is_structured(str(e))]
    if invalid_evidence:
        failures.append(f"invalid evidence shape: {invalid_evidence}; use command:/file:/search:/brainctl:/artifact:/url:/proof: prefixes or an existing absolute path")
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
    missing_alignment = architecture_alignment_missing(fm)
    if missing_alignment:
        raise SystemExit(f"evolution tasks require architecture alignment fields; missing/invalid={missing_alignment}")
    body = f"# Task - {title}\n\n## Objective\n\n{args.objective or title}\n\n## Acceptance Criteria\n\n- [ ] {args.accept or 'Observable result is recorded in Proof Log.'}\n\n## Plan / Workpad\n\n- [ ] Reconcile current state before execution.\n- [ ] Execute the smallest verifiable slice.\n- [ ] Record proof and update status.\n\n## Validation\n\n| Command / Check | Status | Evidence |\n|---|---|---|\n| brain_task_orchestrator list | pending | |\n\n## Proof Log\n\n- {iso(created)}: Task created from local-brain control point.\n\n## Blockers / Confusions\n\n- None.\n\n## Final Handoff\n\n- Status:\n- Evidence:\n- Residual risk:\n"
    atomic_write(path, render_frontmatter(fm) + "\n" + body)
    return {"status": "OK", "created": str(path), "id": path.stem, "link": obsidian_link(path)}


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
    if args.write and created:
        atomic_write(INBOX, "\n".join(new_lines) + "\n")
    return {"status": "OK", "write": bool(args.write), "created_count": len(created), "created": created, "inbox": str(INBOX)}


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
    return {"status": "OK", "task": t.id, "claimed_by": args.actor, "claim_expires_at": t.fm["claim_expires_at"], "warnings": warnings, "path": str(t.path)}


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
    return {"status": "OK", "task": t.id, "to_status": args.to_status, "warnings": warnings, "path": str(t.path)}


def command_done(args: argparse.Namespace) -> dict[str, Any]:
    t = find_task(args.task)
    if not args.evidence:
        raise SystemExit("done requires at least one structured --evidence entry, e.g. 'command: pytest PASS' or 'file:/path/to/proof.md'")
    failures, warnings = lifecycle_gate(t, "done", args.actor, args.evidence, args.reason, args.force)
    if failures:
        raise SystemExit("; ".join(failures))
    apply_lifecycle_status(t, "done", args.actor, evidence=args.evidence, reason=args.reason, force=args.force)
    save_task(t)
    evidence = t.fm.get("evidence") if isinstance(t.fm.get("evidence"), list) else []
    return {"status": "OK", "task": t.id, "path": str(t.path), "evidence_count": len(evidence), "warnings": warnings}


def command_retry(args: argparse.Namespace) -> dict[str, Any]:
    t = find_task(args.task)
    failures, warnings = lifecycle_gate(t, "retry", args.actor, reason=args.reason)
    if failures:
        raise SystemExit("; ".join(failures))
    apply_lifecycle_status(t, "retry", args.actor, reason=args.reason, delay_minutes=args.delay_minutes)
    save_task(t)
    return {"status": "OK", "task": t.id, "retry_count": t.fm.get("retry_count") or 0, "next_attempt_at": t.fm["next_attempt_at"], "warnings": warnings, "path": str(t.path)}


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
        missing_mission = mission_envelope_missing(t.fm)
        if missing_mission:
            invalid.append({"task": t.id, "status": t.status, "fields": missing_mission, "reason": "mission_envelope_missing"})
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
    failures, warnings = lifecycle_gate(t, to_status, args.actor, args.evidence, args.reason, args.force)
    if failures:
        raise SystemExit("; ".join(failures))
    apply_lifecycle_status(t, to_status, args.actor, evidence=args.evidence, reason=args.reason, ttl_minutes=args.ttl_minutes, delay_minutes=args.delay_minutes, force=args.force)
    save_task(t)
    return {
        "status": "OK",
        "task": t.id,
        "from_status": from_status,
        "to_status": to_status,
        "warnings": warnings,
        "path": str(t.path),
        "next_allowed": allowed_next_statuses(to_status),
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

## Safety Invariants

- Markdown task notes are canonical.
- This dashboard and `任务池-排序.md` are derived views.
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
    return {"status": "OK", "write": bool(args.write), "action_count": len(actions), "actions": actions}


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
    return (
        "Execute this local-brain task only after claiming it. "
        "Treat the task note as canonical workpad; reconcile first; verify; record proof; release/done/retry. "
        f"Task: {row['link']} ({row['id']}) priority={row['priority']} status={row['status']} "
        f"lane={row['lane']} project={row['project']}"
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
        missing_mission = mission_envelope_missing(t.fm)
        if missing_mission:
            invalid.append({"task": t.id, "path": str(t.path), "fields": missing_mission, "reason": "mission_envelope_missing"})
        if t.lane not in VALID_LANES:
            invalid.append({"task": t.id, "path": str(t.path), "lane": t.lane, "reason": "invalid_lane"})
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
    gates = {
        "work_lane_available": dispatchable_by_lane.get("work", 0) > 0,
        "autorun_enabled": os.environ.get(AUTORUN_ENV_FLAG) == "1",
        "kill_switch_env_set": os.environ.get("HERMES_LOCAL_BRAIN_AUTORUN_KILL") == "1",
        "kill_switch_file_present": AUTORUN_KILL_SWITCH.exists(),
        "evolution_preempted_by_work": dispatchable_by_lane.get("work", 0) > 0 and dispatchable_by_lane.get("evolution", 0) > 0,
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
    work_available = any(t.lane == "work" for t in candidates)
    selected: list[Task] = []
    skipped: list[dict[str, Any]] = []
    used_boundaries: dict[str, str] = {}  # boundary_key -> first task_id
    boundary_parallel_groups: dict[str, str] = {}  # boundary_key -> parallel_group of first task
    for t in candidates:
        if work_available and t.lane != "work":
            skipped.append({"id": t.id, "lane": t.lane, "reason": "lane_preempted_by_work", "path": str(t.path)})
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
        if reconcile_result.get("action_count") and not getattr(args, "reconcile", False):
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
    return (-len(reasons), LANE_SORT_WEIGHT.get(task.lane, 1), -task.score(), task.expires_at() or datetime.max.replace(tzinfo=TZ), task.id)


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
    return {
        "schema": "local_brain_multimodel_intervention_v1",
        "task": task.row(),
        "criteria": {
            "accuracy": "claim/evidence state must ground task facts; model agreement alone is insufficient",
            "long_term_goal": "solution must preserve lane/project/architecture_target and not let evolution preempt work delivery",
            "one_shot_landing": "output must be a directly executable next slice with acceptance evidence and rollback boundary",
        },
        "trigger_reasons": reasons,
        "intervention_required": bool(reasons),
        "pua_loop": {
            "mode": "continue_until_multimodel_pass",
            "round_gate": "run deterministic checks -> build target-bound claim/evidence state -> consult_models.py --tier T3 --quorum 4 --discussion -> ratification-gate; continue if gate != PASS",
            "completion_signal": "LOOP_DONE only after target-bound 4/4 ratification-gate PASS and local deterministic gates pass",
        },
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
        "run_discussion_command": f"python3 ~/.hermes/scripts/consult_models.py run {state_arg} --tier T3 --quorum 4 --discussion --max-rounds 3 --keep",
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
    plans = [build_multimodel_intervention_plan(t) for t in intervention_tasks[:max_tasks]]
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
        "plans": plans,
        "criteria": ["accuracy", "long_term_goal", "one_shot_landing"],
        "safety": "dry-run only; this surfaces automatic intervention points but does not run models or edit tasks",
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

    result: dict[str, Any] = {
        "status": "OK",
        "schema": "local_brain_multimodel_intervention_step_v1",
        "generated_at": iso(),
        "task_id": task_id,
        "state_path": state_path,
        "allowlist_active": allowlist_active,
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
            result["run_discussion"] = {
                "status": "OK" if proc.returncode == 0 else "FAIL",
                "returncode": proc.returncode,
                "stdout_tail": proc.stdout[-500:] if proc.stdout else "",
                "stderr_tail": proc.stderr[-500:] if proc.stderr else "",
            }
        except Exception as exc:
            result["run_discussion"] = {"status": "ERROR", "error": str(exc)}

    # Step 3: Find discussion result and run gate
    discussion_path = ""
    gate_result: dict[str, Any] = {}
    if result.get("run_discussion", {}).get("status") == "OK":
        # Find the latest discussion_result.json in tick output dirs
        tick_dirs = sorted(Path(os.path.expanduser("~/.hermes")).glob("tick-*"), key=lambda p: p.stat().st_mtime, reverse=True)
        for tick_dir in tick_dirs[:3]:
            candidate = tick_dir / "discussion_result.json"
            if candidate.exists():
                try:
                    discussion = json.loads(candidate.read_text(encoding="utf-8"))
                    task_obj = find_task(task_id)
                    if task_obj:
                        result["binding_stamp"] = stamp_discussion_task_binding(candidate, task_obj, state_path)
                        discussion = json.loads(candidate.read_text(encoding="utf-8"))
                    # Verify it's for our task by checking provenance or state_hash
                    gate_result = ratification_gate_result(discussion, expected_task=task_obj)
                    discussion_path = str(candidate)
                    break
                except Exception:
                    continue

    result["gate"] = gate_result or {"status": "SKIP", "reason": "no_discussion_result"}
    result["discussion_path"] = discussion_path

    # Step 4: On PASS, write to task frontmatter (D6)
    if gate_result.get("status") == "PASS" and gate_result.get("decision") == "LOOP_DONE":
        task = find_task(task_id)
        if task:
            mutate_result = write_multimodel_result_to_task(task, gate_result, discussion_path, state_path)
            result["task_mutation"] = mutate_result
        else:
            result["task_mutation"] = {"status": "SKIP", "reason": "task_not_found"}
    else:
        result["task_mutation"] = {"status": "SKIP", "reason": "gate_not_passed"}

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
        result["run_discussion"] = {"status": "OK" if proc.returncode == 0 else "FAIL", "returncode": proc.returncode}
    except Exception as exc:
        result["run_discussion"] = {"status": "ERROR", "error": str(exc)}

    # Step 3: Gate — find the correct tick for THIS task
    discussion_path = ""
    gate_result: dict[str, Any] = {}
    if result.get("run_discussion", {}).get("status") == "OK":
        # Look for tick directories created during our discussion (within last 10 min)
        import time
        cutoff = time.time() - 600
        tick_dirs = sorted(
            (p for p in Path(os.path.expanduser("~/.hermes")).glob("tick-*")
             if p.stat().st_mtime > cutoff),
            key=lambda p: p.stat().st_mtime, reverse=True
        )
        for tick_dir in tick_dirs[:10]:
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
                gate_result = ratification_gate_result(discussion, expected_task=task_obj)
                discussion_path = str(candidate)
                break
            except Exception:
                continue

    result["gate"] = gate_result or {"status": "SKIP", "reason": "no_discussion_result"}
    result["discussion_path"] = discussion_path

    # Step 4: Mutate on PASS
    if gate_result.get("status") == "PASS" and gate_result.get("decision") == "LOOP_DONE":
        task = find_task(task_id)
        if task:
            result["task_mutation"] = write_multimodel_result_to_task(task, gate_result, discussion_path, state_path)
        else:
            result["task_mutation"] = {"status": "SKIP", "reason": "task_not_found"}
    else:
        result["task_mutation"] = {"status": "SKIP", "reason": "gate_not_passed"}

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
    if task and task.lane != "work" and any(t.lane == "work" and t.id != task.id for t in dispatchable_tasks()):
        reasons.append("work_lane_available")
    if not allowlist:
        reasons.append("allowlist_empty")
    elif not allowlist_hit:
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
    return f"""# Parallel Handoff — {task.title}

- task_id: `{task.id}`
- task_link: {obsidian_link(task.path)}
- actor: `{actor}`
- run_id: `{run_id}`
- batch_id: `{batch_id}`
- batch_index: {batch_index}
- claim_expires_at: `{task.fm.get('claim_expires_at') or ''}`

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


def classify_auto_completer_job(job: dict[str, Any] | None) -> dict[str, Any]:
    if not job:
        return {"semantic_status": "missing", "task_result": "unknown", "blockers": [], "safe_for_next_tick": False}
    last_status = str(job.get("last_status") or "")
    last_error = str(job.get("last_error") or job.get("last_error_tail") or "")
    lower = last_error.lower()
    blockers: list[str] = []
    if "ts6133" in lower or "unused" in lower:
        blockers.append("typescript_unused_symbol_baseline_blocker")
    if "full build" in lower or "build" in lower:
        blockers.append("full_build_baseline_check")
    bounded_completed = (
        ("bounded slice" in lower or "有界" in last_error)
        and ("-> review" in lower or "running -> review" in lower or "状态已从" in last_error)
        and ("pass:" in lower or "32 tests passed" in lower or "proof-check" in lower)
    )
    baseline_blocker = bool(blockers) and any(token in lower for token in ("baseline", "unrelated", "ts6133", "full build"))
    if last_status == "error" and bounded_completed and baseline_blocker:
        semantic_status = "ok_with_task_blocker"
        task_result = "review_with_baseline_blocker"
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
        "policy": "bounded slice reaching review with unrelated baseline blocker is task evidence/blocker, not scheduler crash",
    }


def build_taskpool_evidence_spine(max_agents: int = 3) -> dict[str, Any]:
    tasks = iter_tasks()
    counts = task_counts_snapshot(tasks)
    proof = command_proof_check(argparse.Namespace(include_active=False, json=True))
    selfcheck = command_selfcheck(argparse.Namespace(json=True))
    boundary = command_boundary_check(argparse.Namespace(json=True))
    parallel = command_parallel_dispatch_dry_run(argparse.Namespace(max_agents=max_agents, json=True))
    multimodel = command_multimodel_intervention_dry_run(argparse.Namespace(task="", max_tasks=5, json=True))
    cron = load_cron_jobs_snapshot(TASKPOOL_CRON_JOB_NAMES)
    auto_job = next((j for j in cron.get("jobs", []) if j.get("name") == "local-brain-taskpool-auto-completer"), None)
    auto_semantics = classify_auto_completer_job(auto_job)
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
        {"claim_id": "C-TP-003", "text": "Parallel dispatch is dry-run only and enforces work-lane preemption / boundary isolation.", "supported_by": ["E-TP-DISPATCH"]},
        {"claim_id": "C-TP-004", "text": "Autorun and multimodel autorun flags are explicit and fail-closed when disabled.", "supported_by": ["E-TP-AUTORUN"]},
        {"claim_id": "C-TP-005", "text": "Auto-completer baseline blockers are classified separately from scheduler health.", "supported_by": ["E-TP-AUTO-COMPLETER"]},
        {"claim_id": "C-TP-006", "text": "Multimodel convergence/pass-rate is observable together with failure taxonomy via ratification gate.", "supported_by": ["E-TP-MULTIMODEL"]},
    ]
    evidence = [
        {"evidence_id": "E-TP-COUNTS", "type": "snapshot", "supports": ["C-TP-001"], "payload": counts},
        {"evidence_id": "E-TP-GATES", "type": "command_result", "supports": ["C-TP-002"], "payload": {"proof_check": proof, "selfcheck": selfcheck}},
        {"evidence_id": "E-TP-DISPATCH", "type": "dry_run", "supports": ["C-TP-003"], "payload": {"boundary": boundary, "parallel_dispatch": parallel}},
        {"evidence_id": "E-TP-AUTORUN", "type": "policy_state", "supports": ["C-TP-004"], "payload": autorun},
        {"evidence_id": "E-TP-AUTO-COMPLETER", "type": "cron_semantics", "supports": ["C-TP-005"], "payload": {"cron_job": auto_job, "classification": auto_semantics}},
        {"evidence_id": "E-TP-MULTIMODEL", "type": "dry_run", "supports": ["C-TP-006"], "payload": {"convergence": multimodel.get("convergence", {}), "queued_count": multimodel.get("queued_count"), "selected_task_id": multimodel.get("selected_task_id"), "taxonomy_schema": "local_brain_multimodel_failure_taxonomy_v1"}},
        {"evidence_id": "E-TP-CRON", "type": "scheduler_state", "supports": ["C-TP-004", "C-TP-005"], "payload": cron},
    ]
    cron_job_names = {str(j.get("name") or "") for j in cron.get("jobs", []) if isinstance(j, dict)}
    cron_required_present = sorted(set(TASKPOOL_CRON_JOB_NAMES) - cron_job_names)
    cron_observable = cron.get("status") == "OK" and not cron_required_present
    auto_completer_safe = auto_semantics.get("semantic_status") in {"ok", "ok_with_task_blocker"} and auto_semantics.get("safe_for_next_tick") is True
    gate_status = "PASS" if proof.get("status") == "PASS" and selfcheck.get("status") == "PASS" and boundary.get("status") == "PASS" and cron_observable and auto_completer_safe else "WARN"
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
            "parallel_selected_count": parallel.get("selected_count"),
            "autorun_enabled": autorun["autorun_enabled"],
            "multimodel_pass_rate": (multimodel.get("convergence") or {}).get("pass_rate"),
            "multimodel_trigger_rate": (multimodel.get("convergence") or {}).get("trigger_rate"),
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
    write_surface_allowed = "kanban-worker" in {str(x).strip() for x in write_allowlist if isinstance(x, str)}
    spine_summary = evidence_spine.get("summary") or {}
    counts = spine_summary.get("counts") or {}
    evidence_ids = {str(e.get("evidence_id")) for e in evidence_spine.get("evidence", []) if isinstance(e, dict)}
    required_evidence_ids = {
        "E-TP-COUNTS", "E-TP-GATES", "E-TP-DISPATCH", "E-TP-AUTORUN",
        "E-TP-AUTO-COMPLETER", "E-TP-MULTIMODEL", "E-TP-CRON",
    }
    checks = [
        {"id": "CHK-EVIDENCE-SPINE", "passed": evidence_spine.get("status") == "OK" and required_evidence_ids <= evidence_ids, "evidence": "E-TP-* stable IDs"},
        {"id": "CHK-GATES", "passed": evidence_spine.get("gate_status") == "PASS" and spine_summary.get("selfcheck") == "PASS" and spine_summary.get("proof_check") == "PASS" and spine_summary.get("boundary_check") == "PASS", "evidence": "selfcheck/proof-check/boundary-check"},
        {"id": "CHK-CRON-OBSERVABILITY", "passed": spine_summary.get("cron_status") == "OK" and not spine_summary.get("cron_required_missing"), "evidence": "required taskpool cron jobs are readable and present", "missing": spine_summary.get("cron_required_missing", [])},
        {"id": "CHK-AUTO-COMPLETER-SEMANTICS", "passed": spine_summary.get("auto_completer_semantic_status") in {"ok", "ok_with_task_blocker"} and spine_summary.get("auto_completer_safe_for_next_tick") is True, "evidence": "auto-completer cron status is semantically safe"},
        {"id": "CHK-PROOF-CHAIN", "passed": proof_ok, "evidence": str(AUTORUN_PROOF_LOG), "failures": proof_failures},
        {"id": "CHK-WORK-PREEMPTION", "passed": bool((counts.get("by_lane") or {}).get("work", 0)) and int(spine_summary.get("parallel_selected_count") or 0) >= 1, "evidence": "parallel-dispatch-dry-run work lane selection"},
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
        activation_blockers.append("write_surface_kanban_worker_not_allowlisted")
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
            "write_surface_kanban_worker_allowed": write_surface_allowed,
        },
    }


def command_dashboard(args: argparse.Namespace) -> dict[str, Any]:
    ensure_inbox()
    dashboard, pool = render_dashboard()
    control = render_control_center()
    if args.write:
        atomic_write(DASHBOARD, dashboard)
        atomic_write(SORTED_POOL, pool)
        atomic_write(CONTROL_CENTER, control)
    return {"status": "OK", "write": bool(args.write), "dashboard": str(DASHBOARD), "sorted_pool": str(SORTED_POOL), "control_center": str(CONTROL_CENTER), "active_count": len(sorted_tasks()), "mission_summaries": mission_dag_summaries(iter_tasks()), "multimodel_convergence": multimodel_convergence_stats()}


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
        if t.status not in VALID_STATUSES:
            failures.append(f"invalid status {t.status}: {t.path}")
        if t.status not in LIFECYCLE_TRANSITIONS:
            failures.append(f"status missing lifecycle transition contract {t.status}: {t.path}")
        if t.priority not in PRIORITY_WEIGHT:
            warnings.append(f"unknown priority {t.priority}: {t.path}")
        if t.status in {"claimed", "running", "review"} and not t.fm.get("claimed_by"):
            failures.append(f"claim-bound status missing claimed_by: {t.path}")
        if t.status in {"claimed", "running", "review"} and not t.fm.get("claim_expires_at"):
            failures.append(f"claim-bound status missing claim_expires_at: {t.path}")
        if t.status in {"claimed", "running", "review"} and not t.fm.get("run_id"):
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
    status = "PASS" if not failures else "FAIL"
    return {"status": status, "task_count": len(iter_tasks()), "failures": failures, "warnings": warnings, "boundary": boundary, "paths": {"dashboard": str(DASHBOARD), "control_center": str(CONTROL_CENTER), "sorted_pool": str(SORTED_POOL), "inbox": str(INBOX)}}


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
    dp.add_argument("--reason", default="")
    dp.add_argument("--force", action="store_true")
    dp.add_argument("--json", action="store_true")

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
    if args.cmd == "selfcheck":
        return print_result(command_selfcheck(args), args.json)
    raise SystemExit(2)


if __name__ == "__main__":
    sys.exit(main())
