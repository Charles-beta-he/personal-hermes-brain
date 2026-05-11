#!/usr/bin/env python3
"""Ratification-first gate for Agent Cognitive Operating System certification.

This gate combines deterministic local evidence with a real multi-model
ratification artifact. It intentionally fails closed when discussion_result.json
is missing, timed out, weak, or contains unresolved high-severity issues.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Optional

APPROVE = {"approve", "approved"}
CERTIFIED = {"certified", "certified_with_minor_risks"}
CERTIFIED_UPPER = {"CERTIFIED", "CERTIFIED_WITH_MINOR_RISKS"}

SCRIPT_DIR = Path(__file__).resolve().parent
SELF_SCRIPT = SCRIPT_DIR / "agent_cos_selfcheck.py"
_spec = importlib.util.spec_from_file_location("agent_cos_selfcheck", SELF_SCRIPT)
selfcheck = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(selfcheck)


def vault_root() -> Path:
    return Path(os.environ.get("HERMES_BRAIN_VAULT") or os.environ.get("OBSIDIAN_VAULT_PATH") or Path.home() / "Documents/brain")


def _is_agent_cos_discussion(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:200000]
    except OSError:
        return False
    needles = [
        "Agent COS",
        "Agent Cognitive Operating System",
        "Agent 认知操作系统",
        "agent-cognitive-operating-system",
    ]
    return any(n in text for n in needles)


def latest_discussion_result() -> Optional[Path]:
    """Return the latest Agent-COS-scoped discussion artifact only.

    Fail closed instead of silently ratifying against an unrelated multi-model tick.
    """
    ticks = sorted((Path.home() / ".hermes").glob("tick-*/discussion_result.json"), key=lambda p: p.stat().st_mtime if p.exists() else 0)
    scoped = [p for p in ticks if _is_agent_cos_discussion(p)]
    return scoped[-1] if scoped else None


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _upper_status(value: str) -> str:
    return str(value or "").strip().upper()


def _open_high_severity_issues(issue_ledger) -> list:
    open_items = []
    for issue in issue_ledger or []:
        if not isinstance(issue, dict):
            continue
        try:
            severity = int(issue.get("severity", 3) or 3)
        except (TypeError, ValueError):
            severity = 3
        status = str(issue.get("status") or "unresolved").lower()
        if severity >= 3 and status not in {"resolved", "accepted_risk"}:
            open_items.append(issue)
    return open_items


def _agreement_failures(agreement_matrix: dict) -> list:
    failures = []
    for axis in ("framing", "approach", "implementation_order"):
        try:
            score = float((agreement_matrix or {}).get(axis, 0.0) or 0.0)
        except (TypeError, ValueError):
            score = 0.0
        if score < 0.85:
            failures.append(axis)
    return failures


def _vote_summary(votes) -> dict:
    votes = votes or []
    approve_count = 0
    reject_count = 0
    best_false = 0
    for vote in votes:
        if not isinstance(vote, dict):
            continue
        raw = str(vote.get("vote") or "").strip().lower()
        if raw in APPROVE:
            approve_count += 1
        if raw == "reject":
            reject_count += 1
        if vote.get("best_within_constraints") is not True:
            best_false += 1
    return {
        "vote_count": len(votes),
        "approval_count": approve_count,
        "reject_count": reject_count,
        "best_within_constraints_false_count": best_false,
    }


def evaluate(root: Optional[Path] = None, discussion_result_path: Optional[Path] = None) -> dict:
    root = Path(root) if root is not None else vault_root()
    deterministic = selfcheck.run_check(root)
    blocking_reasons = []

    if deterministic.get("status") != "PASS":
        blocking_reasons.append("deterministic_gate_failed")

    discussion_path = Path(discussion_result_path) if discussion_result_path else latest_discussion_result()
    discussion = None
    if not discussion_path or not discussion_path.exists():
        blocking_reasons.append("discussion_result_missing")
        return {
            "status": "FAIL",
            "vault": str(root),
            "discussion_result_path": str(discussion_path) if discussion_path else "",
            "deterministic_gate_status": deterministic.get("deterministic_gate_status"),
            "matrix_status": deterministic.get("matrix_status"),
            "ratification_status": "NOT_CERTIFIED_NO_ARTIFACT",
            "final_integration_status": "LOCAL_COMPLETE_UNRATIFIED",
            "blocking_reasons": blocking_reasons,
            "deterministic_selfcheck": deterministic,
        }

    try:
        discussion = load_json(discussion_path)
    except (OSError, json.JSONDecodeError) as exc:
        blocking_reasons.append("discussion_result_unreadable")
        return {
            "status": "FAIL",
            "vault": str(root),
            "discussion_result_path": str(discussion_path),
            "deterministic_gate_status": deterministic.get("deterministic_gate_status"),
            "matrix_status": deterministic.get("matrix_status"),
            "ratification_status": "NOT_CERTIFIED_BAD_ARTIFACT",
            "final_integration_status": "LOCAL_COMPLETE_UNRATIFIED",
            "blocking_reasons": blocking_reasons,
            "error": str(exc),
            "deterministic_selfcheck": deterministic,
        }

    status = str(discussion.get("status") or "not_certified").lower()
    open_high = _open_high_severity_issues(discussion.get("issue_ledger") or [])
    agreement_failures = _agreement_failures(discussion.get("agreement_matrix") or {})
    votes = _vote_summary(discussion.get("ratification_votes") or [])
    truth = discussion.get("truth_assessment") or {}
    remaining_high_risks = _open_high_severity_issues(discussion.get("remaining_risks") or [])

    if status not in CERTIFIED:
        blocking_reasons.append(f"discussion_status_{status}")
    if open_high:
        blocking_reasons.append("unresolved_severity_ge3_issues")
    if remaining_high_risks:
        blocking_reasons.append("remaining_high_severity_risks")
    if agreement_failures:
        blocking_reasons.append("agreement_matrix_below_0_85")
    if votes["approval_count"] < max(1, votes["vote_count"] - 1):
        blocking_reasons.append("insufficient_approval_votes")
    if votes["reject_count"]:
        blocking_reasons.append("reject_votes_present")
    if votes["best_within_constraints_false_count"]:
        blocking_reasons.append("best_within_constraints_false")
    if truth and truth.get("can_certify_truth") is not True:
        blocking_reasons.append("truth_gate_not_certified")
    if truth.get("unsupported_high_severity_claim_ids"):
        blocking_reasons.append("unsupported_high_severity_claims")

    passed = not blocking_reasons
    ratification_status = _upper_status(status) if passed else "NOT_CERTIFIED"
    if status in {"not_certified_timeout", "timeout"}:
        ratification_status = "NOT_CERTIFIED_TIMEOUT"
    final_integration_status = "FULLY_CERTIFIED" if ratification_status == "CERTIFIED" else (
        "CERTIFIED_WITH_MINOR_RISKS" if ratification_status == "CERTIFIED_WITH_MINOR_RISKS" else "LOCAL_COMPLETE_UNRATIFIED"
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "vault": str(root),
        "discussion_result_path": str(discussion_path),
        "deterministic_gate_status": deterministic.get("deterministic_gate_status"),
        "matrix_status": deterministic.get("matrix_status"),
        "ratification_status": ratification_status,
        "final_integration_status": final_integration_status,
        "blocking_reasons": sorted(set(blocking_reasons)),
        "open_severity_ge3_issue_count": len(open_high),
        "remaining_high_severity_risk_count": len(remaining_high_risks),
        "agreement_failures": agreement_failures,
        "vote_summary": votes,
        "truth_assessment": truth,
        "deterministic_selfcheck": deterministic,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--vault", default="")
    ap.add_argument("--discussion-result", default="")
    args = ap.parse_args()
    result = evaluate(
        root=Path(args.vault) if args.vault else None,
        discussion_result_path=Path(args.discussion_result) if args.discussion_result else None,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Agent COS ratification gate: {result['status']}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
