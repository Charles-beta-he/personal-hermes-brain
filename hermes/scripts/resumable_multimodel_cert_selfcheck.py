#!/usr/bin/env python3
"""Local-first self-check for the Resumable Multi-Model Certification System landing.

This verifies deterministic project/brain artifacts and the explicit deferred status of
TaskCreate -> next-round ralph. It does not certify implementation readiness.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

PROJECT = "resumable-multimodel-certification"
DEFER_MARKER = "TASKCREATE_RALPH_DEFERRED_UNTIL_RESUMABLE_CERT_READY"

REQUIRED_FILES = [
    "05-实践与项目/projects/resumable-multimodel-certification/Project - Resumable Multi-Model Certification.md",
    "05-实践与项目/projects/resumable-multimodel-certification/P10 - Long-term Strategy.md",
    "05-实践与项目/projects/resumable-multimodel-certification/P9 - Implementation Backlog.md",
    "05-实践与项目/实践方案/10-可恢复多模型认证系统Playbook.md",
    "06-治理与评审/reviews/2026-05-07-resumable-multimodel-certification-multimodel-selfcheck.md",
    "05-实践与项目/tasks/2026-05-07-resumable-multimodel-certification-landing-log.md",
    "06-治理与评审/进化日志/2026-05-07-可恢复多模型认证系统长期目标落地.md",
    "99-hermes-notes/evolution/2026-05-07-resumable-multimodel-certification.md",
]

REQUIRED_INDEXES = [
    "05-实践与项目/projects/00-projects索引.md",
    "05-实践与项目/实践方案/00-实践方案索引.md",
    "05-实践与项目/tasks/00-tasks索引.md",
    "06-治理与评审/reviews/00-reviews索引.md",
    "06-治理与评审/进化日志/00-进化日志索引.md",
]

REQUIRED_TERMS = {
    "project": [
        "Resumable Multi-Model Certification",
        "discussion_result.json",
        "certification_manifest.json",
        DEFER_MARKER,
    ],
    "p10": [
        "Discussion is a resumable state machine",
        "audit-certification",
        "resume-discussion",
        "TaskCreate -> ralph",
    ],
    "p9": [
        "RMCS-P0-001",
        "RMCS-P1-003",
        "DEFERRED-TASKCREATE-RALPH",
    ],
    "playbook": [
        "Certification Rule",
        "Fail-closed Rule",
        "TaskCreate -> ralph Policy",
    ],
    "review": [
        "consensus verdict: dissent",
        "not full certification",
        "TaskCreate -> ralph before RMCS",
    ],
}

FILE_BY_KEY = {
    "project": REQUIRED_FILES[0],
    "p10": REQUIRED_FILES[1],
    "p9": REQUIRED_FILES[2],
    "playbook": REQUIRED_FILES[3],
    "review": REQUIRED_FILES[4],
}


def vault_root() -> Path:
    return Path(os.environ.get("HERMES_BRAIN_VAULT") or os.environ.get("OBSIDIAN_VAULT_PATH") or Path.home() / "Documents/brain")


def _strict_true(value) -> bool:
    """Return True only for a real JSON boolean true; truthy strings fail closed."""
    return value is True


def _safe_int(value, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
        return parsed if math.isfinite(float(parsed)) else default
    except (TypeError, ValueError, OverflowError):
        return default


def _safe_float(value, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError, OverflowError):
        return default


def _strict_int(value):
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _is_conditional_advisory_patch(patch: dict) -> bool:
    """Mirror runtime handling for conditional verifier suggestions.

    Conditional `add_verifier` planner entries are evidence-request/advisory
    notes, not concrete implementation deltas. Standalone selfcheck must not
    turn those advisories into false dropped-work failures for no-action ticks.
    """
    if not isinstance(patch, dict):
        return False
    op = str(patch.get("op", "")).strip().casefold()
    if op != "add_verifier":
        return False
    rationale = str(patch.get("rationale", "")).strip().casefold()
    conditional_markers = (
        "only if",
        "conditional",
        "if absent",
        "if missing",
        "if fresh",
        "if direct inspection",
        "if verification",
        "if tests",
        "if the named test",
        "if the verifier",
        "verify whether",
    )
    return any(marker in rationale for marker in conditional_markers)


def _planner_patch_summary(plans: list[dict]) -> dict:
    summary = {
        "planner_count": 0,
        "total_patch_count": 0,
        "noop_patch_count": 0,
        "conditional_advisory_patch_count": 0,
        "concrete_patch_count": 0,
        "malformed_plan_count": 0,
        "plans_missing_patches_count": 0,
        "plans_non_list_patches_count": 0,
        "non_dict_patch_count": 0,
        "certification_intent": "unknown",
    }
    for plan in plans:
        if not isinstance(plan, dict):
            summary["malformed_plan_count"] += 1
            continue
        summary["planner_count"] += 1
        if "patches" not in plan:
            summary["plans_missing_patches_count"] += 1
            continue
        patches = plan.get("patches")
        if not isinstance(patches, list):
            summary["plans_non_list_patches_count"] += 1
            continue
        for patch in patches:
            if not isinstance(patch, dict):
                summary["non_dict_patch_count"] += 1
                continue
            summary["total_patch_count"] += 1
            if str(patch.get("op", "")).strip().casefold() == "noop":
                summary["noop_patch_count"] += 1
            elif _is_conditional_advisory_patch(patch):
                summary["conditional_advisory_patch_count"] += 1
            else:
                summary["concrete_patch_count"] += 1
    malformed_count = (
        summary["malformed_plan_count"]
        + summary["plans_missing_patches_count"]
        + summary["plans_non_list_patches_count"]
        + summary["non_dict_patch_count"]
    )
    if malformed_count:
        summary["certification_intent"] = "malformed_patch_data"
    elif summary["concrete_patch_count"] == 0 and summary["planner_count"] > 0:
        summary["certification_intent"] = "no_action_certification"
    elif summary["concrete_patch_count"] > 0:
        summary["certification_intent"] = "implementation_required"
    else:
        summary["certification_intent"] = "no_planner_patch_data"
    return summary


def audit_certification_tick(tick_dir: Path | str | None) -> dict:
    """Deterministically verify a specific RMCS certification tick artifact chain.

    This is intentionally stricter than trusting a manifest claim. A tick can
    claim complete certification only when discussion, fanout, truth, votes,
    agreement, and issue-ledger gates all independently pass.
    """
    if tick_dir is None:
        return {"provided": False, "can_claim_complete_certification": False, "reasons": ["certification_tick_not_provided"]}
    tick = Path(tick_dir).expanduser()
    discussion_path = tick / "discussion_result.json"
    manifest_path = tick / "final" / "certification_manifest.json"
    merged_path = tick / "merged_plan.json"
    plans_dir = tick / "plans"
    reasons = []
    discussion = {}
    manifest = {}
    merged = {}
    discussion_malformed = False
    manifest_malformed = False
    plan_files = sorted(plans_dir.glob("*.json")) if plans_dir.exists() else []
    plan_count = len(plan_files)
    plan_models = []
    audit_plans = []
    for idx, plan_file in enumerate(plan_files):
        try:
            plan = json.loads(plan_file.read_text(encoding="utf-8"))
            if isinstance(plan, dict):
                audit_plans.append(plan)
                plan_models.append(str(plan.get("meta", {}).get("planner_model") or plan.get("model") or plan_file.stem or f"model_{idx}"))
            else:
                reasons.append(f"plan_artifact_malformed:{plan_file.name}")
                plan_models.append(plan_file.stem or f"model_{idx}")
        except Exception as e:
            reasons.append(f"plan_artifact_unreadable:{plan_file.name}:{e}")
            plan_models.append(plan_file.stem or f"model_{idx}")
    if not tick.exists():
        reasons.append("tick_dir_missing")
    if not merged_path.exists():
        reasons.append("merged_plan_missing")
    else:
        try:
            loaded_merged = json.loads(merged_path.read_text(encoding="utf-8"))
            if isinstance(loaded_merged, dict):
                merged = loaded_merged
            else:
                reasons.append("merged_plan_malformed")
        except Exception as e:  # noqa: BLE001
            reasons.append(f"merged_plan_unreadable:{e}")
    if not discussion_path.exists():
        reasons.append("discussion_result_missing")
    else:
        try:
            loaded_discussion = json.loads(discussion_path.read_text(encoding="utf-8"))
            if isinstance(loaded_discussion, dict):
                discussion = loaded_discussion
            else:
                discussion_malformed = True
                reasons.append("discussion_result_malformed")
        except Exception as e:  # noqa: BLE001 - selfcheck returns machine-readable failure
            reasons.append(f"discussion_result_unreadable:{e}")
    if not manifest_path.exists():
        reasons.append("certification_manifest_missing")
    else:
        try:
            loaded_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(loaded_manifest, dict):
                manifest = loaded_manifest
            else:
                manifest_malformed = True
                reasons.append("certification_manifest_malformed")
        except Exception as e:  # noqa: BLE001
            reasons.append(f"certification_manifest_unreadable:{e}")

    discussion_status = discussion.get("status")
    if discussion and discussion_status not in {"certified", "certified_with_minor_risks"}:
        reasons.append(f"discussion_status_not_certified:{discussion_status}")

    raw_fanout = discussion.get("fanout_certification")
    fanout = raw_fanout if isinstance(raw_fanout, dict) else {}
    merged_raw_fanout = merged.get("fanout_certification") if isinstance(merged, dict) else None
    merged_fanout = merged_raw_fanout if isinstance(merged_raw_fanout, dict) else {}
    if merged_raw_fanout is not None and not isinstance(merged_raw_fanout, dict):
        reasons.append("merged_fanout_certification_malformed")
    if raw_fanout is not None and not isinstance(raw_fanout, dict):
        reasons.append("fanout_certification_malformed")
    fanout_certified = _strict_true(fanout.get("certified"))
    multi_model_certified = _strict_true(fanout.get("multi_model_certified"))
    planner_count = _strict_int(fanout.get("planner_count"))
    success_count = _strict_int(fanout.get("success_count"))
    merged_planner_count = _strict_int(merged_fanout.get("planner_count")) if merged_fanout else None
    merged_success_count = _strict_int(merged_fanout.get("success_count")) if merged_fanout else None
    expected_vote_count = planner_count if planner_count is not None else plan_count
    if not fanout:
        reasons.append("fanout_certification_missing")
    elif not fanout_certified:
        reasons.append("fanout_not_certified")
    if not fanout or not multi_model_certified:
        reasons.append("fanout_not_multi_model_certified")
    if not merged_fanout:
        reasons.append("merged_fanout_certification_missing")
    else:
        if not _strict_true(merged_fanout.get("certified")):
            reasons.append("merged_fanout_not_certified")
        if not _strict_true(merged_fanout.get("multi_model_certified")):
            reasons.append("merged_fanout_not_multi_model_certified")
    if planner_count is None or success_count is None:
        reasons.append("fanout_counts_not_strict_integers")
    elif planner_count < 2 or success_count < 2:
        reasons.append("expected_vote_count_below_2")
    elif planner_count != plan_count or success_count != plan_count:
        reasons.append("fanout_counts_inconsistent_with_plans")
    if merged_fanout:
        if merged_planner_count is None or merged_success_count is None:
            reasons.append("merged_fanout_counts_not_strict_integers")
        elif merged_planner_count < 2 or merged_success_count < 2:
            reasons.append("merged_expected_vote_count_below_2")
        elif merged_planner_count != plan_count or merged_success_count != plan_count:
            reasons.append("merged_fanout_counts_inconsistent_with_plans")

    raw_issue_ledger = discussion.get("issue_ledger")
    issue_ledger = raw_issue_ledger if isinstance(raw_issue_ledger, list) else []
    if not isinstance(raw_issue_ledger, list):
        reasons.append("issue_ledger_missing_or_malformed")
    if any(not isinstance(i, dict) for i in issue_ledger):
        reasons.append("issue_ledger_contains_malformed_entries")
    unresolved_high = [
        i for i in issue_ledger
        if isinstance(i, dict) and i.get("status") == "unresolved" and _safe_int(i.get("severity"), 3) >= 3
    ]
    if unresolved_high:
        reasons.append("unresolved_severity_ge_3_issues")

    raw_votes = discussion.get("ratification_votes")
    votes = [v for v in raw_votes if isinstance(v, dict)] if isinstance(raw_votes, list) else []
    non_dict_vote_count = len(raw_votes) - len(votes) if isinstance(raw_votes, list) else 0
    vote_models = [str(v.get("model", "")) for v in votes]
    vote_model_set = set(vote_models)
    expected_model_set = set(plan_models)
    duplicate_vote_models = sorted({m for m in vote_models if m and vote_models.count(m) > 1})
    anonymous_vote_count = sum(1 for m in vote_models if not m)
    unexpected_vote_models = sorted(vote_model_set - expected_model_set) if expected_model_set else []
    approvals = [v for v in votes if str(v.get("vote", "")).lower() == "approve" and _strict_true(v.get("best_within_constraints"))]
    approving_model_set = {str(v.get("model", "")) for v in approvals if v.get("model")}
    rejects = [v for v in votes if str(v.get("vote", "")).lower() == "reject"]
    unsigned = [v for v in votes if not _strict_true(v.get("best_within_constraints"))]
    required_approvals = max(2, expected_vote_count - 1)
    if not isinstance(raw_votes, list):
        reasons.append("ratification_votes_missing_or_malformed")
    if non_dict_vote_count:
        reasons.append("ratification_votes_contains_malformed_entries")
    if not votes:
        reasons.append("ratification_votes_missing")
    if len(votes) < required_approvals or len(approving_model_set) < required_approvals:
        reasons.append("insufficient_approval_votes")
    if anonymous_vote_count:
        reasons.append("ratification_vote_missing_model_identity")
    if duplicate_vote_models:
        reasons.append("duplicate_ratification_vote_models")
    if unexpected_vote_models:
        reasons.append("unexpected_ratification_vote_models")
    if unsigned:
        reasons.append("best_within_constraints_not_strict_true")
    if rejects:
        reasons.append("reject_votes_present")

    raw_agreement = discussion.get("agreement_matrix")
    agreement = raw_agreement if isinstance(raw_agreement, dict) else {}
    if raw_agreement is not None and not isinstance(raw_agreement, dict):
        reasons.append("agreement_matrix_malformed")
    for axis in ("framing", "approach", "implementation_order"):
        if axis not in agreement:
            reasons.append(f"agreement_{axis}_missing")
        elif _safe_float(agreement.get(axis)) < 0.85:
            reasons.append(f"agreement_{axis}_below_0_85")

    raw_truth = discussion.get("truth_assessment")
    truth = raw_truth if isinstance(raw_truth, dict) else {}
    merged_raw_truth = merged.get("truth_assessment") if isinstance(merged.get("truth_assessment"), dict) else merged.get("truth_gate") if isinstance(merged.get("truth_gate"), dict) else None
    merged_truth = merged_raw_truth if isinstance(merged_raw_truth, dict) else {}
    if "truth_assessment" in merged and not isinstance(merged.get("truth_assessment"), dict):
        reasons.append("merged_truth_gate_malformed")
    elif "truth_gate" in merged and not isinstance(merged.get("truth_gate"), dict):
        reasons.append("merged_truth_gate_malformed")
    if raw_truth is not None and not isinstance(raw_truth, dict):
        reasons.append("truth_gate_malformed")
    if not truth:
        reasons.append("truth_gate_missing")
    elif not _strict_true(truth.get("can_certify_truth")):
        reasons.append("truth_gate_not_certifiable")
    if not merged_truth:
        reasons.append("merged_truth_gate_missing")
    elif not _strict_true(merged_truth.get("can_certify_truth")):
        reasons.append("merged_truth_gate_not_certifiable")

    manifest_claim = _strict_true(manifest.get("can_claim_complete_certification"))
    if manifest and not manifest_claim:
        reasons.append("manifest_can_claim_false")
    if manifest and manifest.get("status") not in {"certified", "certified_with_minor_risks"}:
        reasons.append(f"manifest_status_not_certified:{manifest.get('status')}")

    merged_patches = merged.get("patches") if isinstance(merged, dict) else None
    recomputed_patch_summary = _planner_patch_summary(audit_plans)
    if any(
        _strict_int(recomputed_patch_summary.get(key)) or 0
        for key in (
            "malformed_plan_count",
            "plans_missing_patches_count",
            "plans_non_list_patches_count",
            "non_dict_patch_count",
        )
    ):
        reasons.append("plan_patches_missing_or_malformed")
    if not isinstance(merged_patches, list):
        reasons.append("merged_plan_patches_missing_or_malformed")
    elif len(merged_patches) == 0:
        patch_summary = merged.get("planner_patch_summary") if isinstance(merged.get("planner_patch_summary"), dict) else {}
        stored_no_action = (
            _strict_int(patch_summary.get("concrete_patch_count")) == 0
            and str(patch_summary.get("certification_intent", "")).strip().casefold() == "no_action_certification"
        )
        recomputed_no_action = (
            _strict_int(recomputed_patch_summary.get("concrete_patch_count")) == 0
            and str(recomputed_patch_summary.get("certification_intent", "")).strip().casefold() == "no_action_certification"
        )
        if not (stored_no_action and recomputed_no_action):
            reasons.append("empty_merged_patches_require_no_action_certification")

    can_claim = bool(tick.exists() and discussion_path.exists() and manifest_path.exists() and manifest_claim and not reasons)
    return {
        "provided": True,
        "tick_dir": str(tick),
        "discussion_result_present": discussion_path.exists(),
        "certification_manifest_present": manifest_path.exists(),
        "discussion_status": discussion_status,
        "manifest_status": manifest.get("status"),
        "fanout_certified": fanout_certified,
        "multi_model_certified": multi_model_certified,
        "expected_vote_count": expected_vote_count,
        "approval_count": len(approvals),
        "unique_approval_count": len(approving_model_set),
        "reject_count": len(rejects),
        "unresolved_severity_ge_3_count": len(unresolved_high),
        "can_claim_complete_certification": can_claim,
        "reasons": sorted(set(reasons)),
    }


def run_check(root: Path | None = None, certification_tick: Path | str | None = None) -> dict:
    root = root or vault_root()
    missing_files = [f for f in REQUIRED_FILES if not (root / f).exists()]
    missing_indexes = [f for f in REQUIRED_INDEXES if not (root / f).exists()]

    missing_terms: dict[str, list[str]] = {}
    for key, terms in REQUIRED_TERMS.items():
        rel = FILE_BY_KEY[key]
        p = root / rel
        text = p.read_text(encoding="utf-8") if p.exists() else ""
        misses = [t for t in terms if t not in text]
        if misses:
            missing_terms[rel] = misses

    index_missing_links: dict[str, str] = {}
    for rel in REQUIRED_INDEXES:
        p = root / rel
        text = p.read_text(encoding="utf-8") if p.exists() else ""
        if PROJECT not in text and "可恢复多模型认证系统" not in text:
            index_missing_links[rel] = "project link missing"

    secret_patterns = ["api_key", "password", "Authorization: Bearer", "connection string", "BEGIN PRIVATE KEY"]
    allowed_policy_phrases = ["不记录", "不保存", "如出现", "统一写", "Non-goals"]
    secret_hits = []
    for rel in REQUIRED_FILES:
        p = root / rel
        lines = (p.read_text(encoding="utf-8") if p.exists() else "").splitlines()
        for line_no, line in enumerate(lines, start=1):
            if any(policy in line for policy in allowed_policy_phrases):
                continue
            for pat in secret_patterns:
                if pat in line and "[REDACTED]" not in line:
                    secret_hits.append({"file": rel, "line": line_no, "pattern": pat})

    project_text = (root / REQUIRED_FILES[0]).read_text(encoding="utf-8") if (root / REQUIRED_FILES[0]).exists() else ""
    deferred_ok = DEFER_MARKER in project_text and "TaskCreate -> 下一轮 ralph" in project_text

    tick = Path.home() / ".hermes/tick-20260507-031812/merged_plan.json"
    tick_exists = tick.exists()
    tick_summary = {}
    if tick_exists:
        try:
            merged = json.loads(tick.read_text(encoding="utf-8"))
            tick_summary = {
                "consensus_verdict": merged.get("merge_info", {}).get("consensus_verdict"),
                "consensus_score": merged.get("merge_info", {}).get("consensus_score"),
                "source_plans": merged.get("meta", {}).get("source_plans"),
            }
        except Exception as e:  # noqa: BLE001 - selfcheck reports deterministic error text
            tick_summary = {"error": str(e)}

    fail_reasons = []
    if missing_files:
        fail_reasons.append("missing_files")
    if missing_indexes:
        fail_reasons.append("missing_indexes")
    if missing_terms:
        fail_reasons.append("missing_terms")
    if index_missing_links:
        fail_reasons.append("index_missing_links")
    if secret_hits:
        fail_reasons.append("secret_hits")
    if not deferred_ok:
        fail_reasons.append("taskcreate_deferred_marker")

    certification_tick_gate = audit_certification_tick(certification_tick)
    if certification_tick is not None and not certification_tick_gate.get("can_claim_complete_certification"):
        fail_reasons.append("certification_tick_gate")

    result = {
        "status": "FAIL" if fail_reasons else "PASS",
        "project": PROJECT,
        "vault": str(root),
        "required_files_count": len(REQUIRED_FILES),
        "missing_files": missing_files,
        "missing_indexes": missing_indexes,
        "missing_terms": missing_terms,
        "index_missing_links": index_missing_links,
        "taskcreate_ralph_deferred": deferred_ok,
        "defer_marker": DEFER_MARKER,
        "source_tick_exists": tick_exists,
        "source_tick_summary": tick_summary,
        "certification_tick_gate": certification_tick_gate,
        "secret_hits": secret_hits,
        "fail_reasons": fail_reasons,
        "certification_note": "This self-check verifies local-brain landing only; no discussion_result means the prior fanout remains not fully certified.",
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--certification-tick", help="Optional RMCS tick dir whose discussion_result.json and final/certification_manifest.json must support a fully-certified runtime claim")
    args = ap.parse_args()
    result = run_check(certification_tick=args.certification_tick)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"RMCS self-check: {result['status']}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
