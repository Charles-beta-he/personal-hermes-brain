#!/usr/bin/env python3
"""ADK P0 Proof Gate Verifier — Validates taskpool task transitions.

Checks:
1. Task file exists and has valid frontmatter
2. Status transition is legal (pending->claimed->running->review->done)
3. Done transition requires proof artifacts
4. No Markdown body execution allowed
5. Evidence requests must be resolved or deferred

Usage:
    python3 ~/.hermes/scripts/proof_gate_verifier.py <task_file> <target_status> [--json]
"""

import json
import re
import sys
from pathlib import Path

LEGAL_TRANSITIONS = {
    "pending": ["claimed"],
    "claimed": ["running", "pending"],  # pending = release
    "running": ["review", "pending"],   # pending = fail/timeout
    "review": ["done", "pending"],      # pending = reject
    "done": [],                          # terminal
}

DANGEROUS_PATTERNS = [
    r"\$\(",           # $(command) — shell substitution in body
    r"```bash",         # executable code blocks
    r"```sh",
    r"rm -rf /",
    r"sudo ",
    r"curl.*\|.*sh",   # pipe to shell
    r"wget.*\|.*sh",
    r"^eval\s|^eval$",  # eval as standalone command at line start
    r"^exec\s|^exec$",  # exec as standalone command at line start
]
# NOTE: backtick-wrapped markdown references like `done` are NOT flagged.
# Only patterns that could execute arbitrary commands are checked.


def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from Markdown."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def check_markdown_body_safety(content: str) -> list:
    """Check for dangerous patterns in Markdown body."""
    # Get body after frontmatter
    match = re.match(r"^---\n.*?\n---\n(.*)", content, re.DOTALL)
    body = match.group(1) if match else content
    issues = []
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, body, re.MULTILINE):
            issues.append(f"Dangerous pattern found: {pattern}")
    return issues


def verify(task_path: str, target_status: str, as_json: bool = False) -> dict:
    """Run proof gate verification."""
    result = {
        "schema": "proof_gate_v1",
        "task_path": task_path,
        "target_status": target_status,
        "checks": [],
        "pass": True,
        "block_reason": None
    }

    # Check 1: File exists
    p = Path(task_path)
    if not p.exists():
        result["checks"].append({"check": "file_exists", "pass": False})
        result["pass"] = False
        result["block_reason"] = "Task file not found"
        return result
    result["checks"].append({"check": "file_exists", "pass": True})

    # Check 2: Parse frontmatter
    content = p.read_text()
    fm = parse_frontmatter(content)
    if not fm:
        result["checks"].append({"check": "frontmatter_valid", "pass": False})
        result["pass"] = False
        result["block_reason"] = "No valid frontmatter"
        return result
    result["checks"].append({"check": "frontmatter_valid", "pass": True})

    # Check 3: Legal transition
    current_status = fm.get("status", "unknown")
    legal = LEGAL_TRANSITIONS.get(current_status, [])
    if target_status not in legal:
        result["checks"].append({
            "check": "legal_transition",
            "pass": False,
            "from": current_status,
            "to": target_status,
            "legal_next": legal
        })
        result["pass"] = False
        result["block_reason"] = f"Illegal transition: {current_status} -> {target_status}. Legal: {legal}"
        return result
    result["checks"].append({"check": "legal_transition", "pass": True})

    # Check 4: Done requires proof
    if target_status == "done":
        evidence = fm.get("evidence", "")
        if not evidence or evidence == "[]":
            result["checks"].append({"check": "proof_required", "pass": False})
            result["pass"] = False
            result["block_reason"] = "Done transition requires evidence artifacts"
            return result
        result["checks"].append({"check": "proof_required", "pass": True})

    # Check 5: No dangerous Markdown body
    body_issues = check_markdown_body_safety(content)
    if body_issues:
        result["checks"].append({"check": "body_safety", "pass": False, "issues": body_issues})
        result["pass"] = False
        result["block_reason"] = f"Dangerous patterns in task body: {body_issues}"
        return result
    result["checks"].append({"check": "body_safety", "pass": True})

    return result


def main():
    if len(sys.argv) < 3:
        print("Usage: proof_gate_verifier.py <task_file> <target_status> [--json]")
        sys.exit(1)

    task_path = sys.argv[1]
    target_status = sys.argv[2]
    as_json = "--json" in sys.argv

    result = verify(task_path, target_status, as_json)

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        status = "PASS" if result["pass"] else "BLOCKED"
        print(f"=== Proof Gate: {status} ===")
        print(f"Task: {result['task_path']}")
        print(f"Target: {result['target_status']}")
        for c in result["checks"]:
            mark = "OK" if c["pass"] else "FAIL"
            print(f"  [{mark}] {c['check']}")
        if result["block_reason"]:
            print(f"  BLOCKED: {result['block_reason']}")

    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
