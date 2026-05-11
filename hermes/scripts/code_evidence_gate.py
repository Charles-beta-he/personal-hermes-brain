#!/usr/bin/env python3
"""code_evidence_gate.py — dry-run GitNexus-inspired code evidence gate.

Hermes-native, local-first primitives only. This script does not import or call
GitNexus. It emits evidence objects for orchestrator truth gates and keeps RRF as
ranking/provenance, never as a truth verdict.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

SCHEMA = "code_evidence_v1"


def run_git(root: str | Path, args: Sequence[str]) -> tuple[int, str, str]:
    proc = subprocess.run(["git", *args], cwd=Path(root), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=20)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def git_head(root: str | Path) -> str | None:
    code, out, _ = run_git(root, ["rev-parse", "HEAD"])
    return out if code == 0 and out else None


def git_status_paths(root: str | Path) -> list[str]:
    code, out, _ = run_git(root, ["status", "--porcelain"])
    if code != 0 or not out:
        return []
    paths = []
    for line in out.splitlines():
        if len(line) >= 4:
            paths.append(line[3:].strip())
    return sorted(paths)


def infer_target_type(target_id: str) -> str:
    if target_id.startswith("cli::"):
        return "cli"
    if target_id.startswith("mcp::"):
        return "mcp_tool"
    if target_id.startswith("cron::"):
        return "cron"
    if Path(target_id).suffix:
        return "file"
    return "symbol"


def build_code_evidence(root: str | Path, target_id: str, *, indexed_commit: str | None = None) -> dict[str, Any]:
    root_path = Path(root).expanduser().resolve()
    current_head = git_head(root_path)
    indexed = indexed_commit or current_head
    stale = bool(indexed and current_head and indexed != current_head)
    changed_paths = git_status_paths(root_path)
    evidence = {
        "schema": SCHEMA,
        "target_type": infer_target_type(target_id),
        "target_id": target_id,
        "indexed_commit": indexed,
        "current_head": current_head,
        "stale": stale,
        "risk": "unknown" if stale else "low_dry_run",
        "direct_breakage_d1": [],
        "likely_affected_d2": changed_paths,
        "test_needed_d3": [],
        "affected_processes": [],
        "affected_contracts": [],
        "evidence_sources": [
            {"type": "git_head", "value": current_head},
            {"type": "git_status", "changed_paths": changed_paths},
        ],
        "unsupported_claims": [],
        "truth_gate": "not_certified_needs_reindex" if stale else "certified_dry_run",
    }
    return evidence


def detect_changes_before_commit(root: str | Path, expected: Sequence[str] | None = None) -> dict[str, Any]:
    expected_set = set(expected or [])
    actual = set(git_status_paths(root))
    unexpected = sorted(actual - expected_set) if expected_set else []
    missing = sorted(expected_set - actual) if expected_set else []
    return {
        "schema": "detect_changes_before_commit_v1",
        "changed_files": sorted(actual),
        "expected_files": sorted(expected_set),
        "unexpected_changes": unexpected,
        "missing_expected_changes": missing,
        "action": "block_completion_claim" if unexpected else "proceed",
    }


def shape_check(obj: dict[str, Any], *, required: Sequence[str]) -> dict[str, Any]:
    missing = [key for key in required if key not in obj]
    return {"schema": "shape_check_v1", "ok": not missing, "missing": missing, "observed_keys": sorted(obj.keys())}


def contract_id(kind: str, *parts: str) -> str:
    safe = [str(kind).strip()]
    safe.extend(str(part).strip() for part in parts if str(part).strip())
    return "::".join(safe)


def rrf_merge(rankings: Sequence[Sequence[str]], *, k: int = 60) -> list[dict[str, Any]]:
    scores: dict[str, float] = {}
    appearances: dict[str, int] = {}
    for ranking in rankings:
        for idx, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + idx)
            appearances[item] = appearances.get(item, 0) + 1
    return [
        {"id": item, "rrf_score": score, "ranker_count": appearances[item]}
        for item, score in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def emit(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run code evidence gate")
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("evidence")
    p.add_argument("--target", required=True)
    p.add_argument("--indexed-commit", default=None)

    p = sub.add_parser("detect-changes")
    p.add_argument("--expected", action="append", default=[])

    p = sub.add_parser("shape-check")
    p.add_argument("--object", required=True, help="JSON object or path")
    p.add_argument("--required", action="append", default=[])

    p = sub.add_parser("contract-id")
    p.add_argument("kind")
    p.add_argument("parts", nargs="*")

    p = sub.add_parser("rrf")
    p.add_argument("rankings", nargs="+", help="comma separated ranked ids")
    p.add_argument("--k", type=int, default=60)
    return parser


def parse_json_arg(value: str) -> dict[str, Any]:
    path = Path(value).expanduser()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "evidence":
        data = build_code_evidence(args.root, args.target, indexed_commit=args.indexed_commit)
    elif args.cmd == "detect-changes":
        data = detect_changes_before_commit(args.root, expected=args.expected)
    elif args.cmd == "shape-check":
        data = shape_check(parse_json_arg(args.object), required=args.required)
    elif args.cmd == "contract-id":
        data = {"schema": "contract_id_v1", "contract_id": contract_id(args.kind, *args.parts)}
    elif args.cmd == "rrf":
        data = {"schema": "evidence_rrf_v1", "verdict": "ranking_only_not_truth", "items": rrf_merge([r.split(",") for r in args.rankings], k=args.k)}
    else:
        raise AssertionError(args.cmd)
    emit(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
