#!/usr/bin/env python3
"""local_brain_mempalace_benchmark.py — isolated derived-index benchmark.

This is a MemPalace-inspired benchmark harness, not MemPalace runtime adoption.
It copies a tiny non-sensitive Markdown sample to /tmp, performs deterministic
local comparisons, and writes reports only when explicitly requested.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence


def tokenize(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z0-9_\u4e00-\u9fff]+", text)}


def note_excerpt(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8", errors="replace")).strip()[:240]


def copy_sample(source_vault: Path, sample_limit: int) -> Path:
    sample_dir = Path(tempfile.mkdtemp(prefix="hermes-mempalace-sample-"))
    for md in sorted(source_vault.rglob("*.md"))[:sample_limit]:
        rel = md.relative_to(source_vault)
        target = sample_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(md, target)
    return sample_dir


def score_query(files: Sequence[Path], query: str) -> dict[str, Any]:
    q_tokens = tokenize(query)
    brainctl_like = []
    derived = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        low = text.lower()
        phrase_score = 1 if query.lower() in low else 0
        overlap = len(q_tokens & tokenize(text))
        item = {"path": path.as_posix(), "phrase_score": phrase_score, "token_overlap": overlap, "excerpt": note_excerpt(path)}
        if phrase_score or overlap:
            brainctl_like.append(item)
            derived.append(item)
    brainctl_like.sort(key=lambda x: (-x["phrase_score"], -x["token_overlap"], x["path"]))
    derived.sort(key=lambda x: (-x["token_overlap"], -x["phrase_score"], x["path"]))
    return {"query": query, "brainctl_like": brainctl_like[:5], "derived_token_overlap": derived[:5]}


def run_benchmark(source_vault: str | Path, *, queries: Sequence[str], sample_limit: int = 20, no_llm: bool = True) -> dict[str, Any]:
    source = Path(source_vault).expanduser().resolve()
    sample = copy_sample(source, sample_limit)
    files = sorted(sample.rglob("*.md"))
    query_reports = [score_query(files, q) for q in queries]
    return {
        "schema": "local_brain_mempalace_derived_benchmark_v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_vault": str(source),
        "sample_dir": str(sample),
        "sample_file_count": len(files),
        "derived_only": True,
        "no_llm": bool(no_llm),
        "writes_to_source_vault": False,
        "queries": list(query_reports),
        "promotion_gate": "no_promotion_without_precision_gain_and_no_recall_loss",
    }


def write_review(report: dict[str, Any], out: str | Path) -> Path:
    target = Path(out).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        "type: review",
        "layer: L6",
        "status: completed",
        f"created: {report['generated_at']}",
        "source: local_brain_mempalace_benchmark.py --no-llm",
        "---",
        "",
        "# MemPalace derived-index benchmark report",
        "",
        "## Evidence Boundary",
        "",
        "This report compares deterministic local search signals on an isolated sample. It does not adopt MemPalace runtime and does not write derived facts into the canonical vault.",
        "",
        "## Result JSON",
        "",
        "```json",
        json.dumps(report, ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run isolated local-brain derived-index benchmark")
    parser.add_argument("--source", default=str(Path.home() / "Documents" / "brain"))
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--sample-limit", type=int, default=20)
    parser.add_argument("--no-llm", action="store_true", default=True)
    parser.add_argument("--write-review", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    queries = args.query or ["MemPalace派生索引 P10 source of truth", "temporal facts bilingual query benchmark"]
    report = run_benchmark(args.source, queries=queries, sample_limit=args.sample_limit, no_llm=args.no_llm)
    if args.write_review:
        report["review_written"] = str(write_review(report, args.write_review))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
