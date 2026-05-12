#!/usr/bin/env python3
"""Shared permission / authority taxonomy for Hermes autonomy surfaces.

This module is intentionally dependency-light and side-effect free. It defines
what a caller is allowed to ask for; lifecycle-specific proof gates remain in
the owning system (for example brain_task_orchestrator.py review -> done).
"""
from __future__ import annotations

from typing import Any, Iterable

WRITE_SURFACES = {
    "taskpool",
    "goal",
    "kanban-worker",
    "watcher",
    "teams",
    "google-workspace",
    "gateway-fanout",
    "cron-no-agent",
}

AUTHORITY_TIERS = [
    "read",
    "dry-run",
    "dispatch-hint",
    "claim-and-handoff",
    "budget-handoff",
    "autonomous-execution",
    "yolo-execution",
]
AUTHORITY_RANK = {name: idx for idx, name in enumerate(AUTHORITY_TIERS)}

OPERATION_CLASSES = {
    "read",
    "dry-run",
    "dispatch-hint",
    "claim",
    "claim-and-handoff",
    "handoff",
    "write",
    "external-write",
    "execute",
    "complete",
}

READONLY_OPERATIONS = {"read", "dry-run", "dispatch-hint"}
CONTROL_PLANE_OPERATIONS = {"claim", "claim-and-handoff", "handoff"}
EXECUTION_OPERATIONS = {"write", "external-write", "execute"}
LIFECYCLE_GATED_OPERATIONS = {"complete"}

MODE_ALIASES = {
    "readonly": "read",
    "read-only": "read",
    "control-plane": "claim-and-handoff",
    "autonomous_execution": "autonomous-execution",
    "yolo": "yolo-execution",
    "--yolo": "yolo-execution",
}

LANE_AUTHORITY_DEFAULTS: dict[str, dict[str, Any]] = {
    "work": {
        "required_authority": "autonomous-execution",
        "max_authority": "yolo-execution",
        "write_surfaces": ["taskpool", "codebase"],
        "completion_gate": "project-evidence-review-done",
        "lane_semantics": "work/product delivery: project evidence, tests/build, scoped commit, report/push policy as required",
    },
    "evolution": {
        "required_authority": "budget-handoff",
        "max_authority": "autonomous-execution",
        "write_surfaces": ["taskpool", "hermes-scripts", "brain"],
        "completion_gate": "ratification-or-selfcheck-review-done",
        "lane_semantics": "self-evolution: deterministic gates plus ratification/proof before review->done",
    },
    "advisory": {
        "required_authority": "dispatch-hint",
        "max_authority": "budget-handoff",
        "write_surfaces": ["taskpool", "brain"],
        "completion_gate": "advisory-evidence-review-done",
        "lane_semantics": "research/advisory: evidence deposition; no execution closeout without promotion",
    },
}


def normalize_authority(authority: str | None) -> str:
    text = str(authority or "").strip()
    if not text:
        return "dispatch-hint"
    return MODE_ALIASES.get(text, text)


def authority_rank(authority: str | None) -> int:
    name = normalize_authority(authority)
    return AUTHORITY_RANK.get(name, -1)


def known_authority(authority: str | None) -> bool:
    return normalize_authority(authority) in AUTHORITY_RANK


def known_surface(surface: str | None) -> bool:
    return str(surface or "").strip() in WRITE_SURFACES


def unknown_allowlisted_surfaces(allowlist: Iterable[str] | None) -> list[str]:
    return sorted({str(x).strip() for x in (allowlist or []) if str(x).strip() and str(x).strip() not in WRITE_SURFACES})


def describe_authority(authority: str | None) -> dict[str, Any]:
    name = normalize_authority(authority)
    return {
        "authority_tier": name,
        "known": name in AUTHORITY_RANK,
        "rank": AUTHORITY_RANK.get(name, -1),
        "approval_bypass": name == "yolo-execution",
        "lifecycle_proof_required": True,
        "may_complete_task": False,
        "required_lifecycle_gate": "review_to_done",
        "required_evidence_prefixes": ["command:", "file:", "search:", "brainctl:", "artifact:", "url:", "proof:"],
        "proof_hash_required_for_autorun": True,
        "policy": "authority grants execution approval only; completion remains lifecycle/proof gated",
    }


def required_authority_for_operation(operation: str | None) -> str:
    op = str(operation or "write").strip()
    if op in READONLY_OPERATIONS:
        return "dispatch-hint"
    if op in CONTROL_PLANE_OPERATIONS:
        return "dispatch-hint"
    if op in EXECUTION_OPERATIONS:
        return "budget-handoff"
    if op in LIFECYCLE_GATED_OPERATIONS:
        return "__lifecycle_gate__"
    return "budget-handoff"


def evaluate_authority(surface: str, operation: str, authority: str, allowlist: Iterable[str] | None = None) -> dict[str, Any]:
    surface = str(surface or "").strip()
    operation = str(operation or "write").strip()
    authority = normalize_authority(authority)
    allow = {str(x).strip() for x in (allowlist or []) if str(x).strip()}
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, **extra: Any) -> None:
        checks.append({"name": name, "ok": bool(ok), **extra})

    unknown_allow = unknown_allowlisted_surfaces(allow)
    add("known_write_surface", surface in WRITE_SURFACES, surface=surface, known=sorted(WRITE_SURFACES))
    add("known_authority_tier", authority in AUTHORITY_RANK, authority=authority, known=AUTHORITY_TIERS)
    add("unknown_allowlisted_surface", not unknown_allow, unknown=unknown_allow)

    if operation in LIFECYCLE_GATED_OPERATIONS:
        add("requires_lifecycle_gate", False, operation=operation, required_lifecycle_gate="review_to_done")
    elif operation not in READONLY_OPERATIONS:
        add("surface_allowlisted", surface in allow, allowlist=sorted(allow))
        required = required_authority_for_operation(operation)
        rank_ok = authority_rank(authority) >= authority_rank(required)
        add("authority_rank_sufficient", rank_ok, required_authority=required, authority=authority)

    failed = [c["name"] for c in checks if not c.get("ok")]
    return {
        "schema_version": 1,
        "surface": surface,
        "operation": operation,
        "authority_tier": authority,
        "ok": not failed,
        "status": "PASS" if not failed else "FAIL_CLOSED",
        "failed_required_checks": failed,
        "checks": checks,
        "authority": describe_authority(authority),
    }


def lane_defaults(lane: str | None) -> dict[str, Any]:
    lane = str(lane or "work").strip().lower()
    defaults = LANE_AUTHORITY_DEFAULTS.get(lane, LANE_AUTHORITY_DEFAULTS["work"])
    return {k: (list(v) if isinstance(v, list) else v) for k, v in defaults.items()}


def validate_task_permission_fields(fields: dict[str, Any], lane: str | None = None) -> list[str]:
    failures: list[str] = []
    defaults = lane_defaults(lane)
    required = str(fields.get("required_authority") or defaults["required_authority"]).strip()
    maximum = str(fields.get("max_authority") or defaults["max_authority"]).strip()
    completion_gate = str(fields.get("completion_gate") or defaults["completion_gate"]).strip()
    surfaces_raw = fields.get("write_surfaces") or defaults["write_surfaces"]
    surfaces = [str(x).strip() for x in surfaces_raw] if isinstance(surfaces_raw, list) else [x.strip() for x in str(surfaces_raw).split(",") if x.strip()]
    if not known_authority(required):
        failures.append(f"required_authority:unknown:{required}")
    if not known_authority(maximum):
        failures.append(f"max_authority:unknown:{maximum}")
    if known_authority(required) and known_authority(maximum) and authority_rank(maximum) < authority_rank(required):
        failures.append(f"max_authority_below_required:{maximum}<{required}")
    unknown_surfaces = [s for s in surfaces if s not in WRITE_SURFACES and s not in {"codebase", "hermes-scripts", "brain", "github", "lark", "browser", "shell"}]
    if unknown_surfaces:
        failures.append(f"write_surfaces:unknown:{sorted(unknown_surfaces)}")
    if not completion_gate:
        failures.append("completion_gate:missing")
    return failures


def task_permission_contract(fields: dict[str, Any], lane: str | None = None) -> dict[str, Any]:
    defaults = lane_defaults(lane)
    contract = dict(defaults)
    for key in ("required_authority", "max_authority", "write_surfaces", "completion_gate", "lane_semantics", "permission_tier"):
        value = fields.get(key)
        if value not in (None, "", []):
            contract[key] = value
    contract.setdefault("permission_tier", contract.get("required_authority"))
    contract["validation_failures"] = validate_task_permission_fields(contract, lane)
    return contract
