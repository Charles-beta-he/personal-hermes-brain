#!/usr/bin/env python3
"""Evidence-first multi-model loop runner for local-brain tasks.

This is a control-plane orchestrator, not a Markdown executor. Each loop round:
1. runs deterministic gates,
2. writes a claim/evidence state bundle,
3. runs (or evaluates a supplied) consult_models discussion artifact,
4. stops only when ratification says the work is complete.

If models return amend/not_certified, the runner fails closed unless an explicit
bounded --executor-command is provided by a higher-level operator.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TZ = timezone(timedelta(hours=8))
HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(HOME / ".hermes"))).expanduser().resolve()
SCRIPTS = HERMES_HOME / "scripts"
CONSULT = SCRIPTS / "consult_models.py"
DEFAULT_ROUND_DIR = HERMES_HOME / "state" / "brain_task_multimodel_loop"

CERTIFIED_STATUSES = {"certified", "certified_with_minor_risks"}
CLOSED_ISSUE_STATUSES = {"resolved", "accepted_risk", "closed", "noop", "non_blocking", "non-blocking"}
APPROVE_VOTES = {"approve", "approved"}

DEFAULT_TARGET_FILES = [
    "scripts/brain_task_orchestrator.py",
    "scripts/brain_task_dispatch_tick.py",
    "scripts/brain_task_autorun_step.py",
    "scripts/brain_task_idle_runner.py",
    "scripts/brain_task_multimodel_loop_runner.py",
    "scripts/consult_models.py",
    "scripts/test_brain_task_orchestrator.py",
    "scripts/test_brain_task_dispatch_tick.py",
    "scripts/test_brain_task_autorun_step.py",
    "scripts/test_brain_task_idle_runner.py",
    "scripts/test_brain_task_multimodel_loop_runner.py",
]

DEFAULT_MODELS = ["claude-opus-4-7", "gpt-5.5", "deepseek-v4-pro", "mimo-v2.5-pro"]
ALLOWED_MODEL_IDS = {m.lower(): m.lower() for m in DEFAULT_MODELS}
EXPECTED_CERTIFICATION_MODEL_IDS = set(ALLOWED_MODEL_IDS)
MODEL_ID_ALIASES: dict[str, str] = {}

DEFAULT_VERIFY_COMMANDS = [
    "python3 -m py_compile scripts/brain_task_orchestrator.py scripts/brain_task_dispatch_tick.py scripts/brain_task_autorun_step.py scripts/brain_task_idle_runner.py scripts/test_brain_task_orchestrator.py scripts/test_brain_task_dispatch_tick.py scripts/test_brain_task_autorun_step.py scripts/test_brain_task_idle_runner.py scripts/test_brain_task_multimodel_loop_runner.py",
    "python3 scripts/test_brain_task_orchestrator.py",
    "python3 scripts/test_brain_task_dispatch_tick.py",
    "python3 scripts/test_brain_task_autorun_step.py",
    "python3 scripts/test_brain_task_idle_runner.py",
    "python3 scripts/test_brain_task_multimodel_loop_runner.py",
    "python3 scripts/brain_task_orchestrator.py selfcheck --json",
    "python3 scripts/brain_task_orchestrator.py proof-check --json",
    "python3 scripts/brain_task_orchestrator.py boundary-check --json",
    "python3 scripts/brain_task_orchestrator.py parallel-dispatch-dry-run --max-agents 3 --json",
    "python3 scripts/brain_task_idle_runner.py --json",
]


def iso() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_command(cmd: str, timeout: int = 180) -> dict[str, Any]:
    start = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(HERMES_HOME),
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "duration_seconds": round(time.time() - start, 3),
        "stdout_tail": (proc.stdout or "")[-3000:],
        "stderr_tail": (proc.stderr or "")[-3000:],
    }


def collect_model_quota_probe(models: list[str] | None = None) -> dict[str, Any]:
    """Collect read-only quota observability for the intended quorum models.

    This is deliberately a local state probe, not an extra LLM call. The actual
    consult_models fan-out still owns provider calls and quota gating; the loop
    runner records quota visibility as evidence so ratification can inspect why a
    model was or was not usable.
    """
    models = list(models or DEFAULT_MODELS)
    try:
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        import model_quota  # type: ignore

        providers = {model: model_quota.provider_for_model(model) for model in models}
        snapshots = model_quota.snapshot_models(models, providers=providers)
        allowed, skipped = model_quota.gate_models(models, snapshots, providers=providers)
        low_confidence = []
        exhausted = []
        for snap in (snapshots or {}).values():
            if not isinstance(snap, dict):
                continue
            status = str(snap.get("status") or "unknown").strip()
            observability = str(snap.get("observability") or "unknown").strip()
            model = str(snap.get("model") or "")
            if status == "exhausted":
                exhausted.append(model)
            if status in {"unknown", "unavailable", "malformed"} or observability in {"unknown", "unobservable", "malformed"}:
                low_confidence.append(model)
        return {
            "status": "ok",
            "mode": "local_model_quota_state_probe",
            "models": models,
            "providers": providers,
            "allowed_models": allowed,
            "skipped_models": skipped,
            "low_confidence_models": sorted(set(x for x in low_confidence if x)),
            "exhausted_models": sorted(set(x for x in exhausted if x)),
            "snapshot": snapshots,
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "mode": "local_model_quota_state_probe",
            "models": models,
            "reason": f"{type(exc).__name__}: {exc}",
            "allowed_models": [],
            "skipped_models": [],
            "low_confidence_models": list(models),
            "exhausted_models": [],
            "snapshot": {},
        }


def runner_capability_probe() -> dict[str, Any]:
    """Expose self-observable verifier/export capabilities as evidence."""
    return {
        "status": "ok",
        "ratification_artifact_export": callable(globals().get("build_ratification_artifact")),
        "ratification_selfcheck_cli": True,
        "quota_probe_recorded_in_state": callable(globals().get("collect_model_quota_probe")),
        "timeout_fail_closed": True,
    }


def deterministic_gates(skip: bool = False, extra_commands: list[str] | None = None) -> dict[str, Any]:
    commands = list(DEFAULT_VERIFY_COMMANDS)
    commands.extend(extra_commands or [])
    if skip:
        return {"status": "SKIPPED", "commands": [], "failures": []}
    results = [run_command(cmd) for cmd in commands]
    failures = [r for r in results if not r.get("ok")]
    return {"status": "PASS" if not failures else "FAIL", "commands": results, "failures": failures}


def build_state_payload(question: str, gates: dict[str, Any], round_index: int, target_files: list[str] | None = None) -> dict[str, Any]:
    target_files = target_files or DEFAULT_TARGET_FILES
    quota_probe = collect_model_quota_probe(DEFAULT_MODELS)
    capability_probe = runner_capability_probe()
    claims = [
        {
            "id": "C-001",
            "text": "The local-brain automation remains fail-closed: default ticks observe only and do not execute Markdown task bodies or mark tasks done.",
        },
        {
            "id": "C-002",
            "text": "A loop round is complete only when deterministic gates pass and multi-model ratification has no unresolved severity>=3 issues, no amend/reject votes, and sufficient agreement.",
        },
        {
            "id": "C-003",
            "text": "Each multi-model loop round exports an explicit ratification artifact containing discussion_result status, ratification votes, agreement matrix, issue ledger, remaining risks, and best_within_constraints fields.",
        },
        {
            "id": "C-004",
            "text": "The loop runner records read-only model quota/probe observability for intended quorum models before consult_models fan-out so unavailable or exhausted models are visible in evidence.",
        },
    ]
    evidence = [
        {
            "id": f"E-{round_index:03d}-deterministic-gates",
            "type": "command_bundle",
            "supports": ["C-001", "C-002"],
            "status": gates.get("status"),
            "summary": {
                "command_count": len(gates.get("commands") or []),
                "failure_count": len(gates.get("failures") or []),
            },
            "commands": gates.get("commands") or [],
        },
        {
            "id": f"E-{round_index:03d}-runner-capability-probe",
            "type": "runner_capability_probe",
            "supports": ["C-003"],
            "status": capability_probe.get("status"),
            "summary": capability_probe,
        },
        {
            "id": f"E-{round_index:03d}-model-quota-probe",
            "type": "model_quota_probe",
            "supports": ["C-004"],
            "status": quota_probe.get("status"),
            "summary": {
                "mode": quota_probe.get("mode"),
                "allowed_models": quota_probe.get("allowed_models"),
                "skipped_models": quota_probe.get("skipped_models"),
                "low_confidence_models": quota_probe.get("low_confidence_models"),
                "exhausted_models": quota_probe.get("exhausted_models"),
            },
        },
    ]
    return {
        "schema": "brain_task_multimodel_loop_state_v1",
        "question": question,
        "generated_at": iso(),
        "round_index": round_index,
        "context": {
            "hermes_home": str(HERMES_HOME),
            "target_files": target_files,
            "automation_boundary": "control-plane only; no Markdown execution; no automatic done",
        },
        "constraints": [
            "Use evidence-first multi-model certification; model agreement without evidence is not enough.",
            "Default behavior must remain fail-closed and observe-only unless explicit gates pass.",
            "Stop the loop only when ratification says best_within_constraints and no severity>=3 blockers remain.",
        ],
        "acceptance_criteria": [
            "Deterministic gates pass.",
            "consult_models discussion_result status is certified or certified_with_minor_risks.",
            "All ratification votes approve and best_within_constraints=true when votes are present.",
            "No unresolved severity>=3 issue_ledger or remaining_risks entries.",
            "agreement_matrix framing/approach/implementation_order >= 0.85 when present.",
        ],
        "claims": claims,
        "evidence": evidence,
        "verify_commands": DEFAULT_VERIFY_COMMANDS,
        "budget": {
            "model_quota_probe": quota_probe,
        },
    }


def write_state(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def build_consult_run_command(state_file: Path, tier: str = "T3", quorum: int = 4, max_rounds: int = 5, timeout: int = 180) -> list[str]:
    return [
        sys.executable,
        str(CONSULT),
        "run",
        str(state_file),
        "--tier",
        tier,
        "--quorum",
        str(quorum),
        "--discussion",
        "--max-rounds",
        str(max_rounds),
        "--timeout",
        str(timeout),
        "--keep",
    ]


def _finite_float(value: Any) -> float | None:
    """Parse finite JSON numeric fields without accepting bool/NaN/Infinity."""
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except Exception:
        return None
    return parsed if math.isfinite(parsed) else None


def _severity(item: dict[str, Any]) -> int:
    value = _finite_float(item.get("severity") if isinstance(item, dict) else None)
    if value is None:
        return 0
    return int(value)


def _issue_status(item: dict[str, Any]) -> str:
    return str(item.get("status") or item.get("resolution_status") or "").strip().lower()


def open_high_severity(items: Any) -> list[dict[str, Any]]:
    out = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        if _severity(item) >= 3 and _issue_status(item) not in CLOSED_ISSUE_STATUSES:
            out.append(item)
    return out


def _ledger_schema_reasons(items: list[Any], label: str) -> list[str]:
    reasons: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            reasons.append(f"{label}_item_invalid")
            continue
        if "severity" not in item or _finite_float(item.get("severity")) is None:
            reasons.append(f"{label}_severity_invalid")
        if not _issue_status(item):
            reasons.append(f"{label}_status_missing")
    return reasons


def evaluate_discussion(discussion: dict[str, Any]) -> dict[str, Any]:
    passed, reasons = verify_ratification(discussion)
    if not isinstance(discussion, dict):
        discussion = {}
    status = str(discussion.get("status") or "not_certified").strip().lower()
    models = discussion.get("models_consulted") if isinstance(discussion.get("models_consulted"), list) else []
    issue_ledger = discussion.get("issue_ledger") if isinstance(discussion.get("issue_ledger"), list) else []
    remaining_risks = discussion.get("remaining_risks") if isinstance(discussion.get("remaining_risks"), list) else []
    open_issues = open_high_severity(issue_ledger)
    open_risks = open_high_severity(remaining_risks)
    return {
        "done": passed,
        "next_action": "LOOP_DONE" if passed else "continue_loop",
        "blocking_reasons": reasons,
        "status": status,
        "model_count": len(models),
        "open_high_severity_issue_count": len(open_issues),
        "open_high_severity_remaining_risk_count": len(open_risks),
    }


def _canonical_model_id(value: Any) -> str:
    """Map only exact known model IDs to canonical model IDs.

    Certification rejects role/family aliases because a vote must prove the
    exact participant identity/version, not merely a provider family.
    """
    text = str(value or "").strip().lower()
    if not text:
        return ""
    return MODEL_ID_ALIASES.get(text, ALLOWED_MODEL_IDS.get(text, ""))


def _model_family_name(canonical_id: str) -> str:
    if canonical_id == "claude-opus-4-7":
        return "claude"
    if canonical_id == "gpt-5.5":
        return "codex"
    if canonical_id == "deepseek-v4-pro":
        return "deepseek"
    if canonical_id == "mimo-v2.5-pro":
        return "mimo"
    return ""


def verify_ratification(discussion: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return whether a discussion_result satisfies the stop gate.

    Fail closed on missing or malformed certification fields. Deterministic
    gates are evidence; this verifier is the lifecycle transition gate.
    """
    reasons: list[str] = []
    if not isinstance(discussion, dict):
        return False, ["discussion_result_schema_invalid"]

    status = str(discussion.get("status") or "not_certified").strip().lower()
    if status not in CERTIFIED_STATUSES:
        reasons.append("status_not_certified")

    models = discussion.get("models_consulted")
    consulted_ids: set[str] = set()
    consulted_families: set[str] = set()
    if not isinstance(models, list):
        reasons.append("models_consulted_invalid")
        models = []
    else:
        for model in models:
            canonical_id = _canonical_model_id(model)
            if not canonical_id:
                reasons.append("model_consulted_unknown")
                continue
            if canonical_id in consulted_ids:
                reasons.append("duplicate_consulted_model")
            consulted_ids.add(canonical_id)
            family = _model_family_name(canonical_id)
            if not family:
                reasons.append("model_consulted_unknown")
                continue
            if family in consulted_families:
                reasons.append("duplicate_consulted_model_family")
            consulted_families.add(family)
        missing_expected = EXPECTED_CERTIFICATION_MODEL_IDS - consulted_ids
        if missing_expected:
            reasons.append("missing_expected_consulted_model")
        if len(models) < len(EXPECTED_CERTIFICATION_MODEL_IDS) or len(consulted_ids) < len(EXPECTED_CERTIFICATION_MODEL_IDS) or len(consulted_families) < len(EXPECTED_CERTIFICATION_MODEL_IDS):
            reasons.append("insufficient_model_count")

    agreement = discussion.get("agreement_matrix")
    if not isinstance(agreement, dict):
        reasons.append("agreement_matrix_missing")
        agreement = {}
    for axis in ("framing", "approach", "implementation_order"):
        if axis not in agreement:
            reasons.append(f"agreement_missing:{axis}")
            continue
        value = _finite_float(agreement.get(axis))
        if value is None:
            reasons.append(f"agreement_invalid:{axis}")
        elif value < 0.85:
            reasons.append(f"agreement_below_threshold:{axis}")

    issue_ledger = discussion.get("issue_ledger")
    if not isinstance(issue_ledger, list):
        reasons.append("issue_ledger_invalid")
        issue_ledger = []
    reasons.extend(_ledger_schema_reasons(issue_ledger, "issue"))
    open_issues = open_high_severity(issue_ledger)
    if open_issues:
        reasons.append("open_high_severity_issue")

    remaining_risks = discussion.get("remaining_risks")
    if not isinstance(remaining_risks, list):
        reasons.append("remaining_risks_invalid")
        remaining_risks = []
    reasons.extend(_ledger_schema_reasons(remaining_risks, "remaining_risk"))
    open_risks = open_high_severity(remaining_risks)
    if open_risks:
        reasons.append("open_high_severity_remaining_risk")

    votes = discussion.get("ratification_votes")
    if not isinstance(votes, list) or not votes:
        reasons.append("ratification_votes_missing")
        votes = []
    required_approvals = len(EXPECTED_CERTIFICATION_MODEL_IDS)
    approval_models: set[str] = set()
    reject_count = 0
    for idx, vote in enumerate(votes, 1):
        if not isinstance(vote, dict):
            reasons.append("ratification_vote_invalid")
            continue
        vote_model = str(vote.get("model") or "").strip()
        vote_id = _canonical_model_id(vote_model)
        vote_value = str(vote.get("vote") or "").strip().lower()
        if not vote_model:
            reasons.append("ratification_vote_model_missing")
        elif not vote_id:
            reasons.append("ratification_vote_model_unknown")
        elif consulted_ids and vote_id not in consulted_ids:
            reasons.append("ratification_vote_model_not_consulted")
        if vote_value in APPROVE_VOTES:
            if vote_id:
                if vote_id in approval_models:
                    reasons.append("duplicate_approval_vote_model")
                approval_models.add(vote_id)
        elif vote_value in {"reject", "rejected"}:
            reject_count += 1
            reasons.append("reject_vote")
        else:
            reasons.append("non_approve_vote")
        if vote.get("best_within_constraints") is not True:
            reasons.append("best_within_constraints_missing_or_false")
    if votes and len(approval_models) < required_approvals:
        reasons.append("insufficient_approval_votes")
    if reject_count:
        reasons.append("reject_vote_present")

    truth = discussion.get("truth_assessment") or discussion.get("truth_gate")
    if not isinstance(truth, dict) or not truth:
        reasons.append("truth_assessment_missing")
        truth = {}
    truth_can_certify = truth.get("can_certify_truth", truth.get("truth_can_certify"))
    if truth_can_certify is not True:
        reasons.append("truth_not_certified")
    unsupported = truth.get("unsupported_high_severity_claim_ids")
    contradicted = truth.get("contradicted_high_severity_claim_ids")
    if unsupported is None:
        reasons.append("unsupported_claims_missing")
        unsupported = ["__missing__"]
    if contradicted is None:
        reasons.append("contradicted_claims_missing")
        contradicted = ["__missing__"]
    if not isinstance(unsupported, list):
        reasons.append("unsupported_claims_invalid")
        unsupported = [unsupported]
    if not isinstance(contradicted, list):
        reasons.append("contradicted_claims_invalid")
        contradicted = [contradicted]
    if unsupported:
        reasons.append("unsupported_high_severity_claim")
    if contradicted:
        reasons.append("contradicted_high_severity_claim")
    if "evidence_coverage" not in truth:
        reasons.append("evidence_coverage_missing")
    else:
        value = _finite_float(truth.get("evidence_coverage"))
        if value is None:
            reasons.append("evidence_coverage_invalid")
        elif value < 0.85:
            reasons.append("evidence_coverage_below_threshold")

    deduped = sorted(set(reasons))
    return not deduped, deduped

def should_continue(discussion: dict[str, Any]) -> tuple[bool, str]:
    """Invert verify_ratification() for the driver stop/continue boundary."""
    passed, reasons = verify_ratification(discussion)
    if passed:
        return False, "all_criteria_met"
    return True, ",".join(reasons)


def _state_identity(path: Path | None) -> dict[str, Any]:
    """Return the minimal target identity used to bind consult artifacts.

    Do not select a discussion_result merely because it is the newest file:
    concurrent consult_models runs can finish while this runner is waiting.
    The local-brain runner must only consume artifacts whose tick state belongs
    to the same question/claim set as the state file it launched.
    """
    if not path:
        return {}
    try:
        data = load_json(path)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    claims = data.get("claims") if isinstance(data.get("claims"), list) else []
    claim_texts = [str(c.get("text") or "") for c in claims if isinstance(c, dict)]
    return {
        "question": str(data.get("question") or ""),
        "claim_texts": claim_texts,
    }


def _state_identity_matches(target: dict[str, Any], candidate: dict[str, Any]) -> bool:
    if not target or not candidate:
        return False
    if target.get("question") and target.get("question") != candidate.get("question"):
        return False
    target_claims = [c for c in target.get("claim_texts", []) if c]
    candidate_claims = [c for c in candidate.get("claim_texts", []) if c]
    if target_claims:
        return all(c in candidate_claims for c in target_claims)
    return bool(target.get("question"))


def newest_discussion_result(since: float, state_file: Path | None = None) -> Path | None:
    target_identity = _state_identity(state_file)
    candidates = []
    for p in HERMES_HOME.glob("tick-*/discussion_result.json"):
        try:
            if p.stat().st_mtime < since:
                continue
            tick_state = p.parent / "state.json"
            if state_file is not None and not _state_identity_matches(target_identity, _state_identity(tick_state)):
                continue
            candidates.append(p)
        except Exception:
            continue
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def synthetic_certified_discussion() -> dict[str, Any]:
    return {
        "status": "certified",
        "models_consulted": list(DEFAULT_MODELS),
        "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
        "issue_ledger": [{"id": "I-SYNTHETIC", "severity": 3, "status": "resolved"}],
        "remaining_risks": [],
        "ratification_votes": [
            {"model": model, "vote": "approve", "best_within_constraints": True}
            for model in DEFAULT_MODELS
        ],
        "truth_assessment": {
            "can_certify_truth": True,
            "evidence_coverage": 1.0,
            "unsupported_high_severity_claim_ids": [],
            "contradicted_high_severity_claim_ids": [],
        },
        "provenance": ["offline synthetic runtime selfcheck fixture; no provider calls"],
    }


def ratification_summary(discussion: dict[str, Any]) -> dict[str, Any]:
    passed, reasons = verify_ratification(discussion)
    if not isinstance(discussion, dict):
        discussion = {}
    votes = discussion.get("ratification_votes") if isinstance(discussion.get("ratification_votes"), list) else []
    issue_ledger = discussion.get("issue_ledger") if isinstance(discussion.get("issue_ledger"), list) else []
    remaining_risks = discussion.get("remaining_risks") if isinstance(discussion.get("remaining_risks"), list) else []
    agreement = discussion.get("agreement_matrix") if isinstance(discussion.get("agreement_matrix"), dict) else {}
    return {
        "stop_gate": passed,
        "reasons": reasons,
        "status": str(discussion.get("status") or "not_certified"),
        "agreement_matrix": agreement,
        "vote_count": len(votes),
        "open_high_severity_issue_count": len(open_high_severity(issue_ledger)),
        "open_high_severity_remaining_risk_count": len(open_high_severity(remaining_risks)),
    }


def dry_run_payload(inject: str = "") -> dict[str, Any]:
    discussion = synthetic_certified_discussion()
    if inject == "amend_vote":
        discussion["ratification_votes"][0]["vote"] = "amend"
    elif inject == "unresolved_issue":
        discussion["issue_ledger"].append({"id": "I-DRY-RUN", "severity": 3, "status": "unresolved"})
    elif inject == "low_agreement":
        discussion["agreement_matrix"] = {"framing": 0.65, "approach": 0.65, "implementation_order": 0.65}
    verdict = evaluate_discussion(discussion)
    return {
        "status": "PASS",
        "mode": "dry_run",
        "inject": inject or "none",
        "ratification": ratification_summary(discussion),
        "verdict": verdict,
        "artifact": build_ratification_artifact(discussion, verdict),
    }


def missing_discussion_result(blocking_reason: str = "discussion_result_missing") -> dict[str, Any]:
    """Synthetic fail-closed discussion shape used when ratification output is absent."""
    return {
        "status": "missing",
        "models_consulted": [],
        "agreement_matrix": {},
        "issue_ledger": [{"id": "I-MISSING-DISCUSSION", "severity": 5, "status": "unresolved", "reason": blocking_reason}],
        "remaining_risks": [{"id": "R-MISSING-DISCUSSION", "severity": 5, "status": "unresolved", "risk": "multi-model ratification artifact is missing; certification must fail closed"}],
        "ratification_votes": [],
        "truth_assessment": {
            "can_certify_truth": False,
            "evidence_coverage": 0.0,
            "unsupported_high_severity_claim_ids": ["C-002", "C-003"],
            "contradicted_high_severity_claim_ids": [],
        },
        "provenance": ["synthetic fail-closed artifact generated by brain_task_multimodel_loop_runner.py"],
    }


def build_ratification_artifact(
    discussion: dict[str, Any],
    verdict: dict[str, Any],
    discussion_result_path: Path | None = None,
    issue_ledger_path: Path | None = None,
    state_path: Path | None = None,
) -> dict[str, Any]:
    if not isinstance(discussion, dict):
        discussion = missing_discussion_result("discussion_result_schema_invalid")
        discussion["status"] = "malformed"
    votes = [vote for vote in (discussion.get("ratification_votes") or []) if isinstance(vote, dict)]
    best_by_model = {
        str(vote.get("model") or f"vote-{idx}"): vote.get("best_within_constraints")
        for idx, vote in enumerate(votes, 1)
    }
    return {
        "schema": "brain_task_multimodel_ratification_artifact_v1",
        "created_at": iso(),
        "paths": {
            "discussion_result_path": str(discussion_result_path) if discussion_result_path else "",
            "issue_ledger_path": str(issue_ledger_path) if issue_ledger_path else "",
            "state_path": str(state_path) if state_path else "",
        },
        "consult_models": {
            "discussion_result_status": discussion.get("status"),
            "models_consulted": discussion.get("models_consulted") or [],
            "agreement_matrix": discussion.get("agreement_matrix") or {},
            "ratification_votes": votes,
            "best_within_constraints_by_model": best_by_model,
            "best_within_constraints_all": bool(votes) and all(v is True for v in best_by_model.values()),
            "issue_ledger": discussion.get("issue_ledger") or [],
            "remaining_risks": discussion.get("remaining_risks") or [],
            "truth_assessment": discussion.get("truth_assessment") or discussion.get("truth_gate") or {},
            "evidence_coverage": (discussion.get("truth_assessment") or discussion.get("truth_gate") or {}).get("evidence_coverage"),
        },
        "verifier": verdict,
    }


def required_ratification_artifact_fields_present(artifact: dict[str, Any]) -> tuple[bool, list[str]]:
    consult = artifact.get("consult_models") if isinstance(artifact, dict) else {}
    missing = []
    for key in (
        "discussion_result_status",
        "ratification_votes",
        "agreement_matrix",
        "issue_ledger",
        "remaining_risks",
        "best_within_constraints_by_model",
    ):
        if not isinstance(consult, dict) or key not in consult:
            missing.append(key)
    return not missing, missing


def ratification_selfcheck_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dump explicit ratification artifact from a consult_models discussion_result.json")
    parser.add_argument("--discussion-result", required=True)
    parser.add_argument("--issue-ledger", default="")
    parser.add_argument("--state", default="")
    parser.add_argument("--out", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    discussion_path_raw = str(args.discussion_result or "")
    discussion_path = Path(discussion_path_raw).expanduser() if discussion_path_raw else Path("")
    load_error = ""
    try:
        if not discussion_path_raw or not discussion_path.is_file():
            raise FileNotFoundError(discussion_path_raw or "<empty discussion-result>")
        discussion = load_json(discussion_path)
        if not isinstance(discussion, dict):
            load_error = "discussion_result_schema_invalid"
            discussion = missing_discussion_result(load_error)
            discussion["status"] = "malformed"
    except Exception as exc:
        load_error = load_error or "discussion_result_malformed"
        discussion = missing_discussion_result(load_error)
        discussion["status"] = "malformed"
        discussion["load_error"] = f"{type(exc).__name__}: {exc}"
    verdict = evaluate_discussion(discussion)
    if load_error and load_error not in verdict.get("blocking_reasons", []):
        verdict["blocking_reasons"] = sorted(set(list(verdict.get("blocking_reasons") or []) + [load_error]))
        verdict["done"] = False
        verdict["next_action"] = "continue_loop"
    artifact = build_ratification_artifact(
        discussion,
        verdict,
        discussion_result_path=discussion_path if discussion_path_raw else None,
        issue_ledger_path=Path(args.issue_ledger).expanduser() if args.issue_ledger else None,
        state_path=Path(args.state).expanduser() if args.state else None,
    )
    fields_ok, missing = required_ratification_artifact_fields_present(artifact)
    gate_ok = fields_ok and bool(verdict.get("done"))
    payload = {
        "status": "PASS" if gate_ok else "FAIL",
        "missing_fields": missing,
        "ratification": ratification_summary(discussion),
        "artifact": artifact,
    }
    if args.out:
        write_state(Path(args.out).expanduser(), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if gate_ok else 2


def run_consult(state_file: Path, tier: str, quorum: int, max_rounds: int, timeout: int) -> dict[str, Any]:
    cmd = build_consult_run_command(state_file, tier=tier, quorum=quorum, max_rounds=max_rounds, timeout=timeout)
    start = time.time()
    outer_timeout = max(timeout * quorum + 120, timeout + 120)
    try:
        proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=outer_timeout, check=False)
        returncode: int | str = proc.returncode
        stdout_tail = (proc.stdout or "")[-3000:]
        stderr_tail = (proc.stderr or "")[-3000:]
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        returncode = "timeout"
        stdout_tail = ((exc.output or "") if isinstance(exc.output, str) else "")[-3000:]
        stderr_tail = ((exc.stderr or "") if isinstance(exc.stderr, str) else "")[-3000:]
        timed_out = True
    discussion_path = newest_discussion_result(start, state_file)
    return {
        "cmd": cmd,
        "returncode": returncode,
        "timed_out": timed_out,
        "timeout_seconds": outer_timeout,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "discussion_result_path": str(discussion_path) if discussion_path else "",
    }


def run_executor(command: str, issue_ledger_path: Path, state_path: Path, timeout: int) -> dict[str, Any]:
    argv = shlex.split(command)
    env = os.environ.copy()
    env["HERMES_MM_LOOP_ISSUE_LEDGER"] = str(issue_ledger_path)
    env["HERMES_MM_LOOP_STATE"] = str(state_path)
    proc = subprocess.run(argv, cwd=str(HERMES_HOME), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
    return {
        "cmd": argv,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout_tail": (proc.stdout or "")[-3000:],
        "stderr_tail": (proc.stderr or "")[-3000:],
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "ratification-selfcheck":
        return ratification_selfcheck_main(argv[1:])

    parser = argparse.ArgumentParser(description="Run deterministic + multi-model certification loop for local-brain automation")
    parser.add_argument("--question", default="完善本地大脑任务池自动化流程：每轮 loop 推进后由多模型验证，直到多模型认为结束")
    parser.add_argument("--round-dir", default=str(DEFAULT_ROUND_DIR))
    parser.add_argument("--state-out", default="")
    parser.add_argument("--max-loop-rounds", type=int, default=3)
    parser.add_argument("--discussion-max-rounds", type=int, default=5)
    parser.add_argument("--tier", default="T3")
    parser.add_argument("--quorum", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--discussion-result", default="", help="Use existing discussion_result.json instead of calling models (test/replay mode)")
    parser.add_argument("--skip-deterministic", action="store_true")
    parser.add_argument("--executor-command", default="", help="Explicit bounded command to apply unresolved issue ledger between rounds")
    parser.add_argument("--executor-timeout", type=int, default=300)
    parser.add_argument("--probe-quota", action="store_true", help="Read-only model quota probe; no provider calls")
    parser.add_argument("--dry-run", action="store_true", help="Run synthetic ratification verifier without model calls")
    parser.add_argument("--inject", choices=["amend_vote", "unresolved_issue", "low_agreement"], default="")
    parser.add_argument("--selfcheck-runtime", action="store_true", help="Write/read a synthetic ratification artifact to prove runtime export path")
    parser.add_argument("--artifact-out", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.probe_quota:
        probe = collect_model_quota_probe(DEFAULT_MODELS)
        print(json.dumps({"status": probe.get("status", "unknown"), "model_quota_probe": probe}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if args.dry_run:
        print(json.dumps(dry_run_payload(args.inject), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if args.selfcheck_runtime:
        discussion = synthetic_certified_discussion()
        verdict = evaluate_discussion(discussion)
        artifact = build_ratification_artifact(discussion, verdict)
        out = Path(args.artifact_out).expanduser() if args.artifact_out else HERMES_HOME / "state" / "brain_task_multimodel_loop_runtime_selfcheck_artifact.json"
        write_state(out, artifact)
        payload = {
            "status": "PASS",
            "mode": "offline_synthetic_runtime_selfcheck",
            "artifact_path": str(out),
            "ratification": ratification_summary(discussion),
            "artifact": artifact,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    round_dir = Path(args.round_dir).expanduser()
    round_dir.mkdir(parents=True, exist_ok=True)
    rounds: list[dict[str, Any]] = []

    for i in range(1, max(args.max_loop_rounds, 1) + 1):
        gates = deterministic_gates(skip=args.skip_deterministic)
        state_path = Path(args.state_out).expanduser() if args.state_out else round_dir / f"round-{i:02d}-state.json"
        state = build_state_payload(args.question, gates, i)
        write_state(state_path, state)

        if gates.get("status") == "FAIL":
            payload = {"status": "DETERMINISTIC_GATES_FAILED", "rounds_used": i, "state_path": str(state_path), "rounds": rounds + [{"round": i, "gates": gates}]}
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            return 2

        if args.discussion_result:
            discussion_path_raw = str(args.discussion_result)
            discussion_path = Path(discussion_path_raw).expanduser()
            consult_result = {"mode": "fixture", "discussion_result_path": str(discussion_path)}
        else:
            consult_result = run_consult(state_path, tier=args.tier, quorum=args.quorum, max_rounds=args.discussion_max_rounds, timeout=args.timeout)
            discussion_path_raw = str(consult_result.get("discussion_result_path") or "")
            discussion_path = Path(discussion_path_raw).expanduser() if discussion_path_raw else None

        if not discussion_path or not discussion_path.is_file():
            verdict = {
                "done": False,
                "status": "missing",
                "model_count": 0,
                "open_high_severity_issue_count": 1,
                "open_high_severity_remaining_risk_count": 1,
                "blocking_reasons": ["discussion_result_missing"],
                "next_action": "continue_loop",
            }
            synthetic_discussion = missing_discussion_result("discussion_result_missing")
            issue_path = round_dir / f"round-{i:02d}-issue-ledger.json"
            write_state(issue_path, {
                "issue_ledger": synthetic_discussion.get("issue_ledger") or [],
                "remaining_risks": synthetic_discussion.get("remaining_risks") or [],
                "verdict": verdict,
                "consult": consult_result,
            })
            artifact_path = round_dir / f"round-{i:02d}-ratification-artifact.json"
            artifact = build_ratification_artifact(
                synthetic_discussion,
                verdict,
                discussion_result_path=discussion_path if discussion_path else None,
                issue_ledger_path=issue_path,
                state_path=state_path,
            )
            write_state(artifact_path, artifact)
            round_record = {
                "round": i,
                "gates": {"status": gates.get("status")},
                "state_path": str(state_path),
                "consult": consult_result,
                "issue_ledger_path": str(issue_path),
                "ratification_artifact_path": str(artifact_path),
                "verdict": verdict,
            }
            rounds.append(round_record)
        else:
            malformed_reason = ""
            try:
                discussion = load_json(discussion_path)
                if not isinstance(discussion, dict):
                    malformed_reason = "discussion_result_schema_invalid"
                    discussion = missing_discussion_result(malformed_reason)
                    discussion["status"] = "malformed"
                else:
                    status = str(discussion.get("status") or "not_certified").strip().lower()
                    passed, schema_reasons = verify_ratification(discussion)
                    # Keep normal certified/not-certified discussions intact, but
                    # convert structurally incomplete certification shells into an
                    # explicit fail-closed artifact so they cannot look like LOOP_DONE.
                    if not passed and status in CERTIFIED_STATUSES and any(reason in schema_reasons for reason in (
                        "models_consulted_invalid",
                        "agreement_matrix_missing",
                        "agreement_missing:framing",
                        "agreement_missing:approach",
                        "agreement_missing:implementation_order",
                        "issue_ledger_invalid",
                        "remaining_risks_invalid",
                        "ratification_votes_missing",
                        "truth_assessment_missing",
                        "evidence_coverage_missing",
                    )):
                        malformed_reason = "discussion_result_schema_invalid"
                        discussion = missing_discussion_result(malformed_reason)
                        discussion["status"] = "malformed"
            except Exception:
                malformed_reason = "discussion_result_malformed"
                discussion = missing_discussion_result(malformed_reason)
                discussion["status"] = "malformed"
            verdict = evaluate_discussion(discussion)
            if malformed_reason and malformed_reason not in verdict.get("blocking_reasons", []):
                verdict["blocking_reasons"] = sorted(set(list(verdict.get("blocking_reasons") or []) + [malformed_reason]))
                verdict["done"] = False
                verdict["next_action"] = "continue_loop"
            issue_path = round_dir / f"round-{i:02d}-issue-ledger.json"
            issue_ledger = discussion.get("issue_ledger") if isinstance(discussion, dict) and isinstance(discussion.get("issue_ledger"), list) else []
            remaining_risks = discussion.get("remaining_risks") if isinstance(discussion, dict) and isinstance(discussion.get("remaining_risks"), list) else []
            write_state(issue_path, {"issue_ledger": issue_ledger, "remaining_risks": remaining_risks, "verdict": verdict})
            artifact_path = round_dir / f"round-{i:02d}-ratification-artifact.json"
            artifact = build_ratification_artifact(
                discussion,
                verdict,
                discussion_result_path=discussion_path,
                issue_ledger_path=issue_path,
                state_path=state_path,
            )
            write_state(artifact_path, artifact)
            round_record = {"round": i, "gates": {"status": gates.get("status")}, "state_path": str(state_path), "discussion_result_path": str(discussion_path), "issue_ledger_path": str(issue_path), "ratification_artifact_path": str(artifact_path), "verdict": verdict}
            rounds.append(round_record)
            if verdict.get("done"):
                payload = {"status": "LOOP_DONE", "rounds_used": i, "rounds": rounds, "final_discussion_result": str(discussion_path)}
                print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
                return 0

            if args.executor_command and i < args.max_loop_rounds:
                executor = run_executor(args.executor_command, Path(round_record.get("issue_ledger_path", round_dir)), state_path, args.executor_timeout)
                round_record["executor"] = executor
                if not executor.get("ok"):
                    payload = {"status": "EXECUTOR_FAILED", "rounds_used": i, "rounds": rounds}
                    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
                    return 4

        if not args.executor_command:
            break

    payload = {"status": "NOT_CERTIFIED_MAX_ROUNDS", "rounds_used": len(rounds), "rounds": rounds, "safety": "fail-closed; no Markdown execution and no automatic done"}
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
