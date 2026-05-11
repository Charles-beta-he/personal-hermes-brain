#!/usr/bin/env python3
"""Taskpool Proof Gate — Verify structured proof before allowing done transition.

This script enforces the fail-closed proof requirement:
  - done transitions MUST have at least one proof artifact
  - proof artifacts MUST exist on disk
  - no Markdown body execution allowed
  - files_changed in PROOF_JSON must comply with allowed/forbidden globs
  - loc_budget must not be exceeded by changed file count

Usage:
    python3 ~/.hermes/scripts/taskpool_proof_gate.py verify <task_md_path> [--json]
    python3 ~/.hermes/scripts/taskpool_proof_gate.py verify-boundary <task_md_path> --proof-json <json_str> [--json]

Exit codes:
    0 = proof valid, transition allowed
    1 = proof insufficient, transition blocked
"""
import fnmatch
import hashlib
import json
import os
import re
import sys
from pathlib import Path


def extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from task markdown."""
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).split('\n'):
        if ':' in line and not line.strip().startswith('-'):
            key, _, val = line.partition(':')
            fm[key.strip()] = val.strip()
    # Parse evidence list
    evidence = []
    in_evidence = False
    for line in match.group(1).split('\n'):
        if line.strip().startswith('evidence:'):
            in_evidence = True
            continue
        if in_evidence and line.strip().startswith('- artifact:'):
            evidence.append(line.strip().replace('- artifact:', '').strip())
        elif in_evidence and not line.strip().startswith('-') and line.strip():
            in_evidence = False
    fm['_evidence'] = evidence
    return fm


def verify_proof(task_path: str) -> dict:
    """Verify a task's proof artifacts are sufficient for done transition."""
    path = Path(task_path)
    if not path.exists():
        return {"status": "BLOCKED", "reason": "Task file not found", "code": 1}

    content = path.read_text(encoding='utf-8')
    fm = extract_frontmatter(content)

    issues = []
    evidence_valid = []

    # Check 1: Must have evidence
    evidence = fm.get('_evidence', [])
    if not evidence:
        issues.append("No evidence artifacts declared in frontmatter")

    # Check 2: Evidence files must exist
    for ev_path in evidence:
        ev = Path(ev_path)
        if ev.exists():
            # Compute hash for proof chain
            try:
                data = ev.read_bytes()
                h = hashlib.sha256(data).hexdigest()[:16]
                evidence_valid.append({"path": str(ev), "hash": h, "exists": True})
            except Exception as e:
                evidence_valid.append({"path": str(ev), "exists": False, "error": str(e)})
                issues.append(f"Evidence unreadable: {ev_path}")
        else:
            evidence_valid.append({"path": str(ev), "exists": False})
            issues.append(f"Evidence missing: {ev_path}")

    # Check 3: No markdown body execution (reject if task body has shell commands)
    body = content.split('---', 2)[-1] if content.count('---') >= 2 else ''
    dangerous_patterns = [r'```bash', r'```sh', r'```shell', r'`rm ', r'`sudo ']
    for pat in dangerous_patterns:
        if re.search(pat, body):
            issues.append(f"Dangerous pattern in task body: {pat}")

    # Check 4: Status must be explicitly set to done (not auto-settable)
    status = fm.get('status', '')
    if status == 'done':
        issues.append("Status already 'done' — must transition through proof gate")

    result = {
        "task": str(path),
        "evidence_count": len(evidence),
        "evidence_valid": [e for e in evidence_valid if e.get("exists")],
        "evidence_missing": [e for e in evidence_valid if not e.get("exists")],
        "issues": issues,
        "status": "PASS" if not issues else "BLOCKED",
        "code": 0 if not issues else 1
    }
    return result


def verify_proof_boundary(task_path: str, proof_json: dict) -> dict:
    """Verify that files_changed in PROOF_JSON comply with task boundary constraints.

    Fail-closed enforcement:
    - If allowed_globs is set, every file in files_changed must match at least one pattern.
    - If forbidden_globs is set, no file in files_changed may match any pattern.
    - If loc_budget is set, len(files_changed) must not exceed it.
    - If no boundary constraints are set, returns SKIP (legacy task).

    Args:
        task_path: Path to the task markdown file.
        proof_json: The parsed PROOF_JSON dict from worker output.

    Returns:
        dict with status (PASS/FAIL/SKIP), violations list, and constraint details.
    """
    path = Path(task_path)
    if not path.exists():
        return {"status": "FAIL", "reason": "Task file not found", "code": 1}

    content = path.read_text(encoding='utf-8')
    fm = extract_frontmatter(content)

    # Extract boundary constraints from frontmatter
    allowed_raw = fm.get('allowed_globs', '')
    forbidden_raw = fm.get('forbidden_globs', '')
    loc_budget_raw = fm.get('loc_budget', '')

    # Parse allowed_globs (comma-separated or single value)
    allowed_globs = [g.strip() for g in str(allowed_raw).split(',') if g.strip()] if allowed_raw else []
    forbidden_globs = [g.strip() for g in str(forbidden_raw).split(',') if g.strip()] if forbidden_raw else []

    loc_budget = 0
    if loc_budget_raw:
        try:
            loc_budget = int(loc_budget_raw)
        except (ValueError, TypeError):
            pass

    # If no boundary constraints, skip
    if not allowed_globs and not forbidden_globs and loc_budget <= 0:
        return {
            "status": "SKIP",
            "task": str(path),
            "reason": "no_boundary_constraints_set",
            "code": 0,
        }

    files_changed = proof_json.get('files_changed', [])
    if not isinstance(files_changed, list):
        files_changed = []

    violations = []

    # Check forbidden_globs (dominates allowed_globs)
    for fpath in files_changed:
        fpath = str(fpath).strip()
        if not fpath:
            continue
        for pattern in forbidden_globs:
            if fnmatch.fnmatch(fpath, pattern):
                violations.append(f"forbidden_match:{fpath}:{pattern}")
                break

    # Check allowed_globs (if set, every file must match at least one)
    if allowed_globs:
        for fpath in files_changed:
            fpath = str(fpath).strip()
            if not fpath:
                continue
            # Skip if already flagged as forbidden
            if any(v.startswith(f"forbidden_match:{fpath}:") for v in violations):
                continue
            if not any(fnmatch.fnmatch(fpath, p) for p in allowed_globs):
                violations.append(f"not_in_allowed_globs:{fpath}")

    # Check loc_budget
    if loc_budget > 0 and len(files_changed) > loc_budget:
        violations.append(f"loc_budget_exceeded:{len(files_changed)}>{loc_budget}")

    status = "PASS" if not violations else "FAIL"
    return {
        "status": status,
        "task": str(path),
        "files_changed_count": len(files_changed),
        "allowed_globs": allowed_globs,
        "forbidden_globs": forbidden_globs,
        "loc_budget": loc_budget,
        "violations": violations,
        "code": 0 if not violations else 1,
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: taskpool_proof_gate.py verify <task_md_path> [--json]")
        print("       taskpool_proof_gate.py verify-boundary <task_md_path> --proof-json <json_str> [--json]")
        sys.exit(2)

    cmd = sys.argv[1]
    as_json = "--json" in sys.argv

    if cmd == 'verify':
        task_path = sys.argv[2]
        result = verify_proof(task_path)
    elif cmd == 'verify-boundary':
        task_path = sys.argv[2]
        # Find --proof-json argument
        proof_json_str = None
        for i, arg in enumerate(sys.argv):
            if arg == '--proof-json' and i + 1 < len(sys.argv):
                proof_json_str = sys.argv[i + 1]
                break
        if not proof_json_str:
            print("Error: --proof-json <json_str> is required for verify-boundary")
            sys.exit(2)
        try:
            proof_json = json.loads(proof_json_str)
        except json.JSONDecodeError as e:
            print(f"Error: invalid JSON in --proof-json: {e}")
            sys.exit(2)
        result = verify_proof_boundary(task_path, proof_json)
    else:
        print("Usage: taskpool_proof_gate.py verify <task_md_path> [--json]")
        print("       taskpool_proof_gate.py verify-boundary <task_md_path> --proof-json <json_str> [--json]")
        sys.exit(2)

    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Task: {result.get('task', 'unknown')}")
        print(f"Status: {result.get('status', 'unknown')}")
        if 'evidence_count' in result:
            print(f"Evidence: {result['evidence_count']} declared, {len(result.get('evidence_valid', []))} valid, {len(result.get('evidence_missing', []))} missing")
        if 'violations' in result and result.get('violations'):
            print("Violations:")
            for v in result['violations']:
                print(f"  - {v}")
        if 'issues' in result and result.get('issues'):
            print("Issues:")
            for i in result['issues']:
                print(f"  - {i}")

    sys.exit(result.get('code', 1))


if __name__ == "__main__":
    main()
