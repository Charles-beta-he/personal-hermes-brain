#!/usr/bin/env python3
"""Deterministic file-only recovery validator for Planning with Files.

No external imports. Reads a single Markdown plan/workpad file and verifies that
state needed after context compaction is recoverable from that file alone.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = [
    "## Recovery Header",
    "## Objective",
    "## Acceptance Criteria",
    "## State Ledger",
    "## Current Step Marker",
    "## Decisions Preserved",
    "## Files Changed",
    "## Resume Protocol",
]

REQUIRED_PATTERNS = {
    "absolute_plan_path": r"Plan path: `/Users/charles/.+\.md`",
    "canonical_task_path": r"Canonical task path: `/Users/charles/.+planning-with-files.+\.md`",
    "completed_steps": r"\| \d+\. .+ \| done \|",
    "current_step_row": r"\| \d+\. .+ \| current \|",
    "current_step_marker": r"Current step id:\s*\d+",
    "next_atomic_action": r"Next atomic action:\s*\S",
    "blocker_status": r"Blockers:\s*.+",
    "changed_files": r"\| `/Users/charles/.+` \| (create|modify) \|",
    "resume_instruction": r"After context compaction|After compaction/restart/handoff",
}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate-planning-with-files-recovery.py <plan.md>", file=sys.stderr)
        return 2

    plan_path = Path(sys.argv[1]).expanduser().resolve()
    text = plan_path.read_text(encoding="utf-8")

    section_results = {section: (section in text) for section in REQUIRED_SECTIONS}
    pattern_results = {
        name: bool(re.search(pattern, text, flags=re.MULTILINE))
        for name, pattern in REQUIRED_PATTERNS.items()
    }

    recovered = {
        "current_step_id": None,
        "next_atomic_action": None,
        "blockers": None,
        "completed_step_count": len(re.findall(r"\| \d+\. .+ \| done \|", text)),
        "current_step_count": len(re.findall(r"\| \d+\. .+ \| current \|", text)),
    }

    match = re.search(r"Current step id:\s*(\d+)", text)
    if match:
        recovered["current_step_id"] = match.group(1)
    match = re.search(r"Next atomic action:\s*(.+)", text)
    if match:
        recovered["next_atomic_action"] = match.group(1).strip()
    match = re.search(r"Blockers:\s*(.+)", text)
    if match:
        recovered["blockers"] = match.group(1).strip()

    passed = all(section_results.values()) and all(pattern_results.values())
    output = {
        "overall_status": "PASS" if passed else "FAIL",
        "validated_file": str(plan_path),
        "method": "file-only read after simulated context compaction",
        "section_results": section_results,
        "pattern_results": pattern_results,
        "recovered_state": recovered,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
