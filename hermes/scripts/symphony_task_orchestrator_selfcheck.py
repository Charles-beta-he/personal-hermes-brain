#!/usr/bin/env python3
"""Self-check for Symphony-inspired local-brain task orchestrator landing.

Local-only, deterministic, no network, no LLM. Verifies that the landing package
exists and preserves the canonical Markdown source-of-truth boundary.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

VAULT = Path(os.environ.get("HERMES_BRAIN_VAULT", os.environ.get("OBSIDIAN_VAULT_PATH", str(Path.home() / "Documents" / "brain")))).expanduser()

REQUIRED_FILES = {
    "project": "05-实践与项目/projects/symphony-inspired-local-task-orchestrator/Project - Symphony-inspired Local Task Orchestrator.md",
    "p10": "05-实践与项目/projects/symphony-inspired-local-task-orchestrator/P10 - Long-term Strategy.md",
    "p9": "05-实践与项目/projects/symphony-inspired-local-task-orchestrator/P9 - Implementation Backlog.md",
    "playbook": "05-实践与项目/实践方案/11-Symphony-inspired本地任务编排Playbook.md",
    "task_template": "08-模板/local-brain-task-note-template.md",
    "workflow_template": "08-模板/task-workflow-contract-template.md",
    "control_center": "07-仪表盘/待完成任务控制台.md",
    "sorted_pool": "05-实践与项目/tasks/任务池-排序.md",
    "task_inbox": "05-实践与项目/tasks/任务收件箱.md",
    "dashboard": "07-仪表盘/待完成任务运行态.md",
    "review": "06-治理与评审/reviews/2026-05-08-symphony-inspired-task-orchestrator-multimodel-selfcheck.md",
    "final_cert": "06-治理与评审/reviews/2026-05-08-symphony-inspired-task-orchestrator-final-certification.json",
    "task_log": "05-实践与项目/tasks/2026-05-08-symphony-inspired-task-orchestrator-landing-log.md",
    "evolution": "06-治理与评审/进化日志/2026-05-08-Symphony-inspired本地任务编排落地.md",
    "atom": "04-知识原子/atoms/task-queue-is-derived-from-canonical-markdown.md",
    "ai_system": "04-知识原子/ai-systems/OpenAI Symphony - Codex Orchestration.md",
}

REQUIRED_PHRASES = {
    "project": [
        "selective extraction, not runtime adoption",
        "Markdown canonical",
        "Derived queue",
        "Success Criteria",
    ],
    "p10": [
        "Markdown canonical",
        "Lease before work",
        "Reconcile before dispatch",
        "Hooks are allowlisted",
    ],
    "p9": [
        "P1 — Read-only indexer",
        "P2 — Safe claim/release/add/done/retry mutator",
        "P3 — Safe autonomous execution dry-run boundary",
        "Scope status: all in-scope P0/P1/P2/P3-dry-run deliverables are complete",
    ],
    "playbook": [
        "observe -> reconcile -> select -> claim -> execute -> verify -> record proof -> release/archive -> dashboard",
        "Reconcile before dispatch",
        "claim_expires_at",
        "severity >=3 model issues",
    ],
    "task_template": [
        "status: pending",
        "claimed_by:",
        "claim_expires_at:",
        "retry_count: 0",
        "next_attempt_at:",
        "expires_at:",
    ],
    "workflow_template": [
        "max_concurrent",
        "base_delay_seconds",
        "allowed_paths",
        "evidence_gates",
        "Hooks are inert unless allowlisted",
    ],
    "dashboard": [
        "DERIVED VIEW — NOT SOURCE OF TRUTH",
        "must_reconcile_before_dispatch",
        "待完成任务运行态",
        "处理本地大脑任务收件箱",
    ],
    "control_center": [
        "待完成任务控制台",
        "处理本地大脑任务收件箱",
        "多模型分解本地大脑任务池并排序",
        "dispatch-dry-run",
    ],
    "sorted_pool": [
        "DERIVED VIEW — NOT SOURCE OF TRUTH",
        "任务池-排序",
    ],
    "task_inbox": [
        "任务收件箱",
        "Inbox Drafts",
        "priority:P1",
    ],
    "review": [
        "Final status: certified",
        "truth_status`: grounded",
        "unresolved_severity_ge_3_count`: 0",
        "No remaining next step or caveat",
    ],
    "final_cert": [
        '"status": "certified"',
        '"truth_status": "grounded"',
        '"unresolved_severity_ge_3_count": 0',
        '"caveats": []',
    ],
    "task_log": [
        "status: done",
        "expires_at:",
        "Acceptance Criteria",
    ],
    "atom": [
        "派生视图",
        "不能反过来成为事实源",
        "Operational Rule",
    ],
    "ai_system": [
        "Selective extraction only",
        "Linear/Codex runtime lock-in",
    ],
}

MOC_MARKERS = {
    "05-实践与项目/projects/00-projects索引.md": "Symphony-inspired 本地任务编排",
    "05-实践与项目/tasks/00-tasks索引.md": "symphony-inspired-task-orchestrator-landing-log",
    "05-实践与项目/实践方案/00-实践方案索引.md": "11-Symphony-inspired本地任务编排Playbook",
    "06-治理与评审/reviews/00-reviews索引.md": "symphony-inspired-task-orchestrator-multimodel-selfcheck",
    "06-治理与评审/进化日志/00-进化日志索引.md": "Symphony-inspired本地任务编排落地",
    "08-模板/00-模板索引.md": "task-workflow-contract-template",
    "04-知识原子/atoms/00-atoms索引.md": "task-queue-is-derived-from-canonical-markdown",
    "04-知识原子/ai-systems/00-ai-systems索引.md": "OpenAI Symphony - Codex Orchestration",
    "07-仪表盘/00-仪表盘索引.md": "待完成任务运行态",
}

SECRET_PATTERNS = [
    re.compile(r"sk-proj-[A-Za-z0-9_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


def read_rel(rel: str) -> str:
    return (VAULT / rel).read_text(encoding="utf-8")


def check() -> dict:
    failures: list[str] = []
    warnings: list[str] = []
    files: dict[str, dict] = {}

    if not VAULT.exists():
        failures.append(f"vault missing: {VAULT}")
        return {"status": "FAIL", "vault": str(VAULT), "failures": failures, "warnings": warnings}

    for key, rel in REQUIRED_FILES.items():
        path = VAULT / rel
        exists = path.exists()
        files[key] = {"path": str(path), "exists": exists}
        if not exists:
            failures.append(f"missing required file: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".md" and not text.startswith("---\n"):
            failures.append(f"missing yaml frontmatter: {rel}")
        for phrase in REQUIRED_PHRASES.get(key, []):
            if phrase not in text:
                failures.append(f"missing phrase in {rel}: {phrase}")
        for pat in SECRET_PATTERNS:
            if pat.search(text):
                failures.append(f"possible secret pattern in {rel}: {pat.pattern}")

    for rel, marker in MOC_MARKERS.items():
        path = VAULT / rel
        if not path.exists():
            failures.append(f"missing MOC: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        if marker not in text:
            failures.append(f"MOC missing marker {marker}: {rel}")

    # Narrow wikilink check for links introduced by this landing package.
    for key, rel in REQUIRED_FILES.items():
        path = VAULT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        links = re.findall(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]", text)
        for link in links:
            # Obsidian links may omit .md; only check links with explicit top-level folders.
            if not re.match(r"^(00-|01-|02-|03-|04-|05-|06-|07-|08-|99-)", link):
                continue
            candidate = VAULT / f"{link}.md"
            if not candidate.exists():
                warnings.append(f"wikilink target not found from {rel}: {link}")

    status = "PASS" if not failures else "FAIL"
    return {
        "status": status,
        "vault": str(VAULT),
        "required_file_count": len(REQUIRED_FILES),
        "files": files,
        "failures": failures,
        "warnings": warnings,
        "accepted_risks": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = check()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["status"])
        for failure in result.get("failures", []):
            print(f"FAIL: {failure}")
        for warning in result.get("warnings", []):
            print(f"WARN: {warning}")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
