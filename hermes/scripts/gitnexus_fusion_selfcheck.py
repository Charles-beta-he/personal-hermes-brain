#!/usr/bin/env python3
"""Hermes GitNexus-inspired code-evidence fusion self-check.

Local-first checker for the long-term project that folds GitNexus MCP/code-graph
patterns into Hermes multi-model thinking. It does not invoke GitNexus and does
not require network access. It verifies that the governance artifacts and core
patterns remain present in skills + canonical local brain.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

HOME = Path.home()
HERMES = HOME / ".hermes"
BRAIN = HOME / "Documents" / "brain"

REQUIRED_SKILL = HERMES / "skills" / "software-development" / "multi-model-thinking" / "references" / "gitnexus-code-evidence-mcp-pattern.md"
REQUIRED_BRAIN_FILES = [
    BRAIN / "05-实践与项目" / "projects" / "hermes-code-evidence-mcp" / "Project - Hermes Code Evidence MCP Fusion.md",
    BRAIN / "05-实践与项目" / "projects" / "hermes-code-evidence-mcp" / "P10 - Long-term Strategy.md",
    BRAIN / "05-实践与项目" / "projects" / "hermes-code-evidence-mcp" / "P9 - Implementation Backlog.md",
    BRAIN / "05-实践与项目" / "实践方案" / "04-GitNexus-inspired多模型代码证据门落地方案.md",
    BRAIN / "06-治理与评审" / "reviews" / "2026-05-06-gitnexus-fusion-multimodel-selfcheck.md",
]

PATTERNS = {
    "impact_before_edit": ["impact", "before", "edit"],
    "detect_changes_before_commit": ["detect_changes", "commit"],
    "stale_index_gate": ["Stale index", "stale", "indexed_commit"],
    "tool_shape_contract": ["tool_map", "shape_check"],
    "contract_id_bridge": ["contract_id", "Contract Bridge"],
    "rrf_evidence_only": ["RRF", "truth"],
    "model_agreement_not_evidence": ["Model agreement is not evidence"],
    "no_runtime_import": ["Do not import GitNexus runtime", "PolyForm Noncommercial"],
}

BRAIN_SEARCH_TERMS = [
    "GitNexus-inspired 多模型 代码证据门",
    "impact-before-edit detect_changes stale-index",
    "Contract Bridge contract_id shape_check",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def run(cmd: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, cwd=str(HERMES), text=True, capture_output=True, timeout=timeout)
        return {"ok": p.returncode == 0, "returncode": p.returncode, "stdout": p.stdout[:4000], "stderr": p.stderr[:1000]}
    except Exception as exc:  # checker must report, not crash silently
        return {"ok": False, "error": type(exc).__name__, "message": str(exc)}


def pattern_hits(corpus: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    low = corpus.lower()
    for name, terms in PATTERNS.items():
        hits = []
        for term in terms:
            if term.lower() in low:
                hits.append(term)
        out[name] = {"ok": len(hits) == len(terms), "hits": hits, "missing": [t for t in terms if t not in hits]}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Self-check GitNexus-inspired Hermes fusion artifacts")
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument("--strict", action="store_true", help="exit nonzero on warnings as well as failures")
    args = parser.parse_args()

    files = [REQUIRED_SKILL] + REQUIRED_BRAIN_FILES
    file_status = []
    corpus_parts = []
    for p in files:
        text = read_text(p)
        file_status.append({"path": str(p), "exists": p.exists(), "bytes": len(text.encode("utf-8"))})
        corpus_parts.append(text)
    corpus = "\n".join(corpus_parts)

    patterns = pattern_hits(corpus)
    missing_files = [x for x in file_status if not x["exists"]]
    missing_patterns = [k for k, v in patterns.items() if not v["ok"]]

    brainctl = HERMES / "scripts" / "brainctl.py"
    status = run([sys.executable, str(brainctl), "--json", "status"]) if brainctl.exists() else {"ok": False, "error": "missing_brainctl"}
    search_results = []
    if brainctl.exists():
        for q in BRAIN_SEARCH_TERMS:
            r = run([sys.executable, str(brainctl), "--json", "search", q, "--limit", "5"], timeout=45)
            hit_count = 0
            if r.get("ok"):
                try:
                    parsed = json.loads(r.get("stdout", "[]") or "[]")
                    hit_count = len(parsed) if isinstance(parsed, list) else 0
                except json.JSONDecodeError:
                    hit_count = 0
            search_results.append({"query": q, "ok": bool(hit_count), "hit_count": hit_count})

    p10_health = run(["bash", str(HERMES / "scripts" / "p10-health.sh"), "--json"], timeout=90)
    p10_summary: dict[str, Any] = {"ok": p10_health.get("ok", False)}
    if p10_health.get("ok"):
        try:
            parsed = json.loads(p10_health.get("stdout", "{}"))
            p10_summary = {
                "ok": True,
                "V": parsed.get("V"),
                "grade": parsed.get("grade"),
                "warnings": parsed.get("warnings", []),
            }
        except json.JSONDecodeError:
            p10_summary = {"ok": False, "error": "bad_p10_json"}

    failures = []
    warnings = []
    if missing_files:
        failures.append("missing_required_files")
    if missing_patterns:
        failures.append("missing_required_patterns")
    if not status.get("ok"):
        failures.append("brainctl_status_failed")
    if any(not x["ok"] for x in search_results):
        warnings.append("brain_search_missing_some_terms")
    accepted_risks = []
    p10_warnings = p10_summary.get("warnings") or []
    known_nonblocking_p10 = {"memory file > 2.2KB, may have ghosts"}
    unexpected_p10_warnings = [w for w in p10_warnings if w not in known_nonblocking_p10]
    if p10_warnings and not unexpected_p10_warnings:
        accepted_risks.append("p10_memory_size_warning_existing_nonblocking")
    elif unexpected_p10_warnings:
        warnings.append("p10_health_warnings")

    result = {
        "project": "hermes-code-evidence-mcp-fusion",
        "status": "FAIL" if failures else ("WARN" if warnings else "PASS"),
        "failures": failures,
        "warnings": warnings,
        "accepted_risks": accepted_risks,
        "files": file_status,
        "patterns": patterns,
        "brainctl_status_ok": status.get("ok"),
        "brain_search": search_results,
        "p10_health": p10_summary,
        "caveat": "This checker verifies Hermes-native governance artifacts, not GitNexus runtime adoption or historical multi-model ratification.",
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        if failures:
            print("failures:", ", ".join(failures))
        if warnings:
            print("warnings:", ", ".join(warnings))
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if failures or (args.strict and warnings):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
