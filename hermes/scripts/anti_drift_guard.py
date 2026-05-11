#!/usr/bin/env python3
"""Hermes-native dual-track anti-drift guard.

This is the small landing slice from the dual-track anti-drift design:
Track A is deterministic and LLM-free; Track B is prepared as evidence-first
state for consult_models.py rather than embedded as an always-on hook runtime.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

VERSION = 1
OMC_DIR = ".omc"
ANCHORS_DIR = "anchors"
LOCK_FILE = ".lock"


class GuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class OracleResult:
    oracle: str
    passed: bool
    severity: int
    violations: list[dict[str, Any]]
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": VERSION,
            "oracle": self.oracle,
            "passed": self.passed,
            "severity": self.severity,
            "violations": self.violations,
            "metrics": self.metrics,
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit(data: dict[str, Any], exit_on_fail: bool = False) -> int:
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    if exit_on_fail and data.get("passed") is False:
        return 2
    if exit_on_fail and data.get("action") == "block":
        return 2
    return 0


def root_path(root: str | Path) -> Path:
    return Path(root).expanduser().resolve()


def omc(root: Path) -> Path:
    return root / OMC_DIR


def anchor_root(root: Path) -> Path:
    return omc(root) / ANCHORS_DIR


def rel_to_root(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_anchor_files(root: Path) -> Iterable[Path]:
    base = anchor_root(root)
    if not base.exists():
        return []
    return sorted(
        p
        for p in base.rglob("*")
        if p.is_file() and p.name != LOCK_FILE and not p.name.startswith(".")
    )


def build_lock(root: Path) -> dict[str, Any]:
    hashes = {rel_to_root(p, root): sha256_file(p) for p in iter_anchor_files(root)}
    root_hash = hashlib.sha256(
        "\n".join(f"{k}:{v}" for k, v in sorted(hashes.items())).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": VERSION,
        "created_at": now_iso(),
        "root": str(root),
        "hashes": hashes,
        "root_hash": root_hash,
    }


def read_json(path: Path) -> Any:
    with path.expanduser().open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_git(root: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise GuardError(proc.stderr.strip() or proc.stdout.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def is_git_repo(root: Path) -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def cmd_init(args: argparse.Namespace) -> int:
    root = root_path(args.root)
    (anchor_root(root) / "contracts").mkdir(parents=True, exist_ok=True)
    (anchor_root(root) / "screenshots").mkdir(parents=True, exist_ok=True)
    (omc(root) / "state" / "tasks").mkdir(parents=True, exist_ok=True)
    (omc(root) / "oracles" / "track-a").mkdir(parents=True, exist_ok=True)
    (omc(root) / "oracles" / "track-b").mkdir(parents=True, exist_ok=True)

    goal_file = anchor_root(root) / "goal.md"
    if args.goal and not goal_file.exists():
        goal_file.write_text(args.goal.rstrip() + "\n", encoding="utf-8")
    elif not goal_file.exists():
        goal_file.write_text("# Goal\n\nTODO: write immutable goal anchor.\n", encoding="utf-8")

    lock = build_lock(root)
    write_json(anchor_root(root) / LOCK_FILE, lock)
    return emit({"ok": True, "root": str(root), "omc": str(omc(root)), "lock": lock})


def cmd_lock(args: argparse.Namespace) -> int:
    root = root_path(args.root)
    if not anchor_root(root).exists():
        raise GuardError(f"missing anchors directory: {anchor_root(root)}")
    lock = build_lock(root)
    write_json(anchor_root(root) / LOCK_FILE, lock)
    return emit({"ok": True, "root": str(root), "lock": lock})


def cmd_check_anchors(args: argparse.Namespace) -> int:
    root = root_path(args.root)
    lock_path = anchor_root(root) / LOCK_FILE
    if not lock_path.exists():
        result = OracleResult(
            oracle="anchor-lock",
            passed=False,
            severity=8,
            violations=[{"type": "missing_lock", "path": rel_to_root(lock_path, root) if lock_path.exists() else str(lock_path)}],
            metrics={"root": str(root), "checked_at": now_iso()},
        )
        return emit(result.to_dict(), exit_on_fail=args.exit_code)

    expected = read_json(lock_path)
    actual = build_lock(root)
    expected_hashes = expected.get("hashes", {})
    actual_hashes = actual.get("hashes", {})
    violations: list[dict[str, Any]] = []
    for path in sorted(set(expected_hashes) | set(actual_hashes)):
        old = expected_hashes.get(path)
        new = actual_hashes.get(path)
        if old is None:
            violations.append({"type": "anchor_added", "path": path, "actual_sha256": new})
        elif new is None:
            violations.append({"type": "anchor_removed", "path": path, "expected_sha256": old})
        elif old != new:
            violations.append({"type": "anchor_modified", "path": path, "expected_sha256": old, "actual_sha256": new})

    result = OracleResult(
        oracle="anchor-lock",
        passed=not violations,
        severity=9 if violations else 0,
        violations=violations,
        metrics={
            "root": str(root),
            "expected_root_hash": expected.get("root_hash"),
            "actual_root_hash": actual.get("root_hash"),
            "anchor_count": len(actual_hashes),
            "checked_at": now_iso(),
        },
    )
    return emit(result.to_dict(), exit_on_fail=args.exit_code)


def changed_files(root: Path, base: str, include_untracked: bool) -> tuple[list[str], dict[str, dict[str, int]]]:
    diff = run_git(root, ["diff", "--name-only", base, "--"])
    files = [line.strip() for line in diff.splitlines() if line.strip()]
    numstat_out = run_git(root, ["diff", "--numstat", base, "--"])
    numstat: dict[str, dict[str, int]] = {}
    for line in numstat_out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            added = 0 if parts[0] == "-" else int(parts[0])
            deleted = 0 if parts[1] == "-" else int(parts[1])
            numstat[parts[2]] = {"added": added, "deleted": deleted, "delta": added + deleted}
    if include_untracked:
        untracked = run_git(root, ["ls-files", "--others", "--exclude-standard"])
        for line in untracked.splitlines():
            if line.strip() and line.strip() not in files:
                files.append(line.strip())
                numstat.setdefault(line.strip(), {"added": 0, "deleted": 0, "delta": 0})
    return sorted(files), numstat


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)


def load_contract(path: Path) -> dict[str, Any]:
    data = read_json(path)
    if not isinstance(data, dict):
        raise GuardError("contract must be a JSON object")
    return data


def cmd_scope(args: argparse.Namespace) -> int:
    root = root_path(args.root)
    if not is_git_repo(root):
        raise GuardError(f"not a git repo: {root}")
    contract_path = Path(args.contract).expanduser().resolve()
    contract = load_contract(contract_path)
    include_untracked = bool(contract.get("include_untracked", True))
    files, numstat = changed_files(root, args.base, include_untracked)

    expected_files = set(contract.get("expected_files") or [])
    allowed_globs = list(contract.get("allowed_globs") or [])
    forbidden_files = set(contract.get("forbidden_files") or [])
    forbidden_globs = list(contract.get("forbidden_globs") or [])
    loc_budget = contract.get("loc_budget")
    allow_omc = bool(contract.get("allow_omc", True))
    audited_globs = list(contract.get("audited_globs") or [])
    if audited_globs:
        files = [f for f in files if matches_any(f, audited_globs)]
        numstat = {k: v for k, v in numstat.items() if k in files}

    violations: list[dict[str, Any]] = []
    contract_rel = None
    try:
        contract_rel = rel_to_root(contract_path, root)
    except ValueError:
        contract_rel = None

    for f in files:
        allowed = f in expected_files or matches_any(f, allowed_globs)
        if f == contract_rel:
            allowed = True
        if allow_omc and (f.startswith(f"{OMC_DIR}/") or f == OMC_DIR):
            allowed = True
        if not allowed:
            violations.append({"type": "unexpected_file", "path": f})
        if f in forbidden_files or matches_any(f, forbidden_globs):
            violations.append({"type": "forbidden_file", "path": f})

    total_delta = sum(v.get("delta", 0) for v in numstat.values())
    if isinstance(loc_budget, int) and total_delta > loc_budget:
        violations.append({"type": "loc_budget_exceeded", "budget": loc_budget, "actual_delta": total_delta})

    result = OracleResult(
        oracle="scope-contract",
        passed=not violations,
        severity=max([7 if v["type"] != "loc_budget_exceeded" else 5 for v in violations], default=0),
        violations=violations,
        metrics={
            "root": str(root),
            "base": args.base,
            "contract": str(contract_path),
            "changed_files": files,
            "changed_file_count": len(files),
            "loc_delta": total_delta,
            "checked_at": now_iso(),
        },
    )
    return emit(result.to_dict(), exit_on_fail=args.exit_code)


def load_oracle_payload(value: str) -> dict[str, Any]:
    path = Path(value).expanduser()
    if path.exists():
        data = read_json(path)
    else:
        data = json.loads(value)
    if isinstance(data, list):
        return aggregate_results(data)
    if not isinstance(data, dict):
        raise GuardError("oracle payload must be object or list")
    return data


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    severity = 0
    for r in results:
        if not r.get("passed", False):
            violations.extend(r.get("violations") or [])
            severity = max(severity, int(r.get("severity") or 0))
    return {
        "schema_version": VERSION,
        "oracle": "aggregate",
        "passed": not violations,
        "severity": severity,
        "violations": violations,
        "metrics": {"oracle_count": len(results), "checked_at": now_iso()},
    }


def verdict(payload: dict[str, Any]) -> str:
    if payload.get("passed") is True:
        return "pass"
    severity = int(payload.get("severity") or 0)
    return "fail" if severity >= 5 else "warn"


def cmd_judge(args: argparse.Namespace) -> int:
    track_a = load_oracle_payload(args.track_a)
    track_b = load_oracle_payload(args.track_b) if args.track_b else {"passed": True, "severity": 0, "violations": []}
    a = verdict(track_a)
    b = verdict(track_b)
    if a == "fail":
        action = "block"
    elif b == "fail":
        action = "ask_user"
    elif a == "warn" or b == "warn":
        action = "proceed_log"
    else:
        action = "proceed"
    out = {
        "schema_version": VERSION,
        "oracle": "dual-track-judge",
        "action": action,
        "passed": action in {"proceed", "proceed_log"},
        "track_a_verdict": a,
        "track_b_verdict": b,
        "track_a": track_a,
        "track_b": track_b,
        "checked_at": now_iso(),
        "truth_table": "Track A fail blocks; Track B fail asks user; warnings proceed with log.",
    }
    return emit(out, exit_on_fail=args.exit_code)


def cmd_precondition(args: argparse.Namespace) -> int:
    root = root_path(args.root)
    violations: list[dict[str, Any]] = []
    if not is_git_repo(root):
        violations.append({"type": "not_git_repo", "path": str(root)})
    if not (anchor_root(root) / LOCK_FILE).exists():
        violations.append({"type": "missing_anchor_lock", "path": str(anchor_root(root) / LOCK_FILE)})
    for cmd in args.require_command or []:
        found = subprocess.run(["/bin/sh", "-c", f"command -v {cmd}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if not found:
            violations.append({"type": "missing_command", "command": cmd})
    if args.require_ax:
        proc = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to UI elements enabled'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if proc.returncode != 0 or proc.stdout.strip().lower() != "true":
            violations.append({"type": "accessibility_permission_missing", "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()})
    result = OracleResult(
        oracle="precondition",
        passed=not violations,
        severity=8 if violations else 0,
        violations=violations,
        metrics={"root": str(root), "checked_at": now_iso()},
    )
    return emit(result.to_dict(), exit_on_fail=args.exit_code)


def cmd_consult_state(args: argparse.Namespace) -> int:
    root = root_path(args.root)
    track_a = load_oracle_payload(args.track_a)
    claims = [
        {"id": "C-001", "text": "Deterministic Track A anti-drift guard ran and emitted machine-readable JSON.", "severity": 3},
        {"id": "C-002", "text": "The current project changes respect immutable anchors and task scope constraints unless Track A evidence says otherwise.", "severity": 4},
    ]
    if track_a.get("passed") is False:
        supports = ["C-001"]
        contradicts = ["C-002"]
    else:
        supports = ["C-001", "C-002"]
        contradicts = []
    evidence = [
        {
            "id": "E-track-a-001",
            "type": "oracle_result",
            "summary": f"Track A oracle {track_a.get('oracle')} returned passed={track_a.get('passed')} severity={track_a.get('severity')}.",
            "supports": supports,
            "contradicts": contradicts,
            "payload": track_a,
        }
    ]
    state = {
        "schema": "multi_model_state_v1",
        "created_at": now_iso(),
        "question": args.question,
        "context": {"repo": str(root), "source": "anti_drift_guard.py consult-state"},
        "constraints": [
            "Evidence-first: model agreement is not evidence; cite evidence_bundle.grounding.",
            "Do not request destructive actions unless Track A has a deterministic blocker.",
            "Track A deterministic failures cannot be overruled by Track B agreement.",
        ],
        "acceptance_criteria": [
            "No unsupported severity>=3 claims.",
            "No unresolved severity>=3 blocker remains.",
            "Track A blocker leads to amend/reject rather than approve.",
        ],
        "claims": claims,
        "evidence": evidence,
        "implementation_target": {"files": [], "verify_commands": []},
        "is_candidate_solution": False,
        "state_owner": "anti_drift_guard",
    }
    if args.out:
        write_json(Path(args.out).expanduser(), state)
        return emit({"ok": True, "out": str(Path(args.out).expanduser()), "state": state})
    return emit(state)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Hermes dual-track anti-drift guard")
    p.add_argument("--root", default=".", help="Project root")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="Create .omc skeleton and anchor lock")
    s.add_argument("--goal")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("lock", help="Write immutable anchor hash lock")
    s.set_defaults(func=cmd_lock)

    s = sub.add_parser("check-anchors", help="Verify anchors against .lock")
    s.add_argument("--exit-code", action="store_true")
    s.set_defaults(func=cmd_check_anchors)

    s = sub.add_parser("scope", help="Check git diff against a task contract JSON")
    s.add_argument("--contract", required=True)
    s.add_argument("--base", default="HEAD")
    s.add_argument("--exit-code", action="store_true")
    s.set_defaults(func=cmd_scope)

    s = sub.add_parser("judge", help="Merge Track A and Track B oracle JSON via truth table")
    s.add_argument("--track-a", required=True)
    s.add_argument("--track-b")
    s.add_argument("--exit-code", action="store_true")
    s.set_defaults(func=cmd_judge)

    s = sub.add_parser("precondition", help="Autorun precondition oracle")
    s.add_argument("--require-command", action="append")
    s.add_argument("--require-ax", action="store_true")
    s.add_argument("--exit-code", action="store_true")
    s.set_defaults(func=cmd_precondition)

    s = sub.add_parser("consult-state", help="Build consult_models-compatible evidence-first state from Track A output")
    s.add_argument("--track-a", required=True)
    s.add_argument("--question", default="Review anti-drift oracle output and identify semantic drift risks.")
    s.add_argument("--out")
    s.set_defaults(func=cmd_consult_state)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except GuardError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
