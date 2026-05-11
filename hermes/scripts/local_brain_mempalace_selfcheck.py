#!/usr/bin/env python3
"""Local-first self-check for MemPalace-derived local-brain strategy landing.

No network. No LLM calls. Does not run MemPalace init. The canonical truth source is
~/Documents/brain; MemPalace ideas are checked only as documented derived-layer
contracts.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

VAULT = Path(os.environ.get("HERMES_BRAIN_VAULT", str(Path.home() / "Documents" / "brain"))).expanduser()
PROJECT = VAULT / "20-projects" / "local-brain-mempalace-derived"

REQUIRED_FILES = {
    "project": PROJECT / "Project - MemPalace Derived Local Brain.md",
    "p10": PROJECT / "P10 - Long-term Strategy.md",
    "p9": PROJECT / "P9 - Implementation Backlog.md",
    "playbook": VAULT / "08-实践方案" / "05-MemPalace派生索引落地Playbook.md",
    "review": VAULT / "60-reviews" / "2026-05-06-local-brain-mempalace-multimodel-selfcheck.md",
    "task": VAULT / "30-tasks" / "2026-05-06-local-brain-mempalace-landing-log.md",
    "evolution": VAULT / "05-进化日志" / "2026-05-06-MemPalace派生索引落地.md",
    "atom_evidence": VAULT / "10-atoms" / "evidence-boundary-lossy-summary.md",
    "atom_minority": VAULT / "10-atoms" / "minority-opinion-model-name-is-not-authority.md",
}

REQUIRED_PATTERNS = {
    "p10": [
        "Markdown vault remains the canonical source of truth",
        "MemPalace is a derived retrieval layer, not the brain hierarchy",
        "P10 stop gate",
        "do not run mempalace init on the canonical vault",
        "local-first",
    ],
    "p9": ["P0", "P1", "P2", "Acceptance checks", "brainctl sync", "structural audit"],
    "playbook": ["--palace", "--no-llm", "Drawer", "Closet", "Temporal facts", "Rollback"],
    "review": ["not_certified", "issue_ledger", "DeepSeek", "timeout", "model agreement is not evidence"],
    "task": ["expires_at", "proof ledger", "sync", "reindex", "search"],
    "evolution": ["MemPalace", "derived", "source of truth", "P10"],
    "atom_evidence": ["lossy", "original evidence", "source pointer"],
    "atom_minority": ["model name is not evidence", "minority opinion", "issue ledger"],
}

SENSITIVE_RE = re.compile(
    # Keep this narrow to avoid false positives such as "task-log-template".
    r"(?i)((?:sk-(?:proj|live|test)-[A-Za-z0-9_\-]{20,})|ghp_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9\-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----)"
)

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def run(cmd: list[str], timeout: int = 60) -> dict:
    try:
        p = subprocess.run(cmd, cwd=str(VAULT), text=True, capture_output=True, timeout=timeout)
        return {"cmd": cmd, "exit_code": p.returncode, "stdout": p.stdout[:4000], "stderr": p.stderr[:2000]}
    except Exception as e:  # self-check reports exception as FAIL evidence
        return {"cmd": cmd, "exit_code": 999, "stdout": "", "stderr": repr(e)}


def structural_audit() -> dict:
    ignored = {".obsidian", ".git", ".trash", ".DS_Store"}
    dirs = [p for p in VAULT.rglob("*") if p.is_dir() and not any(part in ignored or part.startswith(".") for part in p.relative_to(VAULT).parts)]
    empty_dirs = []
    for d in dirs:
        children = [c for c in d.iterdir() if c.name not in ignored and not c.name.startswith(".")]
        if not children:
            empty_dirs.append(str(d.relative_to(VAULT)))

    top_level_no_index = []
    parent_no_direct_md_top = []
    for d in sorted([p for p in VAULT.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name not in ignored]):
        direct_md = list(d.glob("*.md"))
        has_index = any((f.name.startswith("00-") and ("索引" in f.name or "index" in f.name.lower())) for f in direct_md)
        if not has_index:
            top_level_no_index.append(d.name)
        has_child_md = any(x.is_file() and x.suffix.lower() == ".md" for x in d.rglob("*.md"))
        if has_child_md and not direct_md:
            parent_no_direct_md_top.append(d.name)

    md_files = [p for p in VAULT.rglob("*.md") if not any(part.startswith(".") for part in p.relative_to(VAULT).parts)]
    basenames = {p.stem for p in md_files}
    rel_no_ext = {str(p.relative_to(VAULT).with_suffix("")) for p in md_files}
    broken = []
    for p in md_files:
        text = read(p)
        for m in WIKILINK_RE.finditer(text):
            target = m.group(1).split("|", 1)[0].split("#", 1)[0].strip()
            if not target or target in basenames or target in rel_no_ext:
                continue
            # Obsidian allows basename resolution with path prefix omitted.
            if Path(target).name in basenames:
                continue
            broken.append({"file": str(p.relative_to(VAULT)), "target": target})

    secret_hits = []
    for p in md_files:
        text = read(p)
        if SENSITIVE_RE.search(text):
            secret_hits.append(str(p.relative_to(VAULT)))

    return {
        "empty_dirs": sorted(empty_dirs),
        "top_level_no_index": sorted(top_level_no_index),
        "parent_no_direct_md_top": sorted(parent_no_direct_md_top),
        "broken_wikilinks_count": len(broken),
        "broken_wikilinks_sample": broken[:20],
        "secret_pattern_hits": len(secret_hits),
        "secret_pattern_files": secret_hits[:20],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--skip-brainctl", action="store_true")
    args = ap.parse_args()

    checks = []
    ok = True

    for name, path in REQUIRED_FILES.items():
        exists = path.exists()
        checks.append({"name": f"file:{name}", "ok": exists, "path": str(path)})
        ok = ok and exists
        if exists and name in REQUIRED_PATTERNS:
            text = read(path)
            for pattern in REQUIRED_PATTERNS[name]:
                hit = pattern in text
                checks.append({"name": f"pattern:{name}:{pattern}", "ok": hit, "path": str(path)})
                ok = ok and hit

    structure = structural_audit() if VAULT.exists() else {"error": "vault_missing"}
    for key in ["empty_dirs", "top_level_no_index", "parent_no_direct_md_top"]:
        good = structure.get(key) == []
        checks.append({"name": f"structure:{key}", "ok": good, "value": structure.get(key)})
        ok = ok and good
    for key in ["broken_wikilinks_count", "secret_pattern_hits"]:
        good = structure.get(key) == 0
        checks.append({"name": f"structure:{key}", "ok": good, "value": structure.get(key)})
        ok = ok and good

    brainctl = {}
    if not args.skip_brainctl:
        script = str(Path.home() / ".hermes" / "scripts" / "brainctl.py")
        brainctl["status"] = run([sys.executable, script, "--json", "status"])
        brainctl["search_project"] = run([sys.executable, script, "--json", "search", "MemPalace派生索引 P10 source of truth", "--limit", "8"])
        for k, r in brainctl.items():
            good = r["exit_code"] == 0 and (k != "search_project" or "local-brain-mempalace" in r.get("stdout", ""))
            checks.append({"name": f"brainctl:{k}", "ok": good, "exit_code": r["exit_code"]})
            ok = ok and good

    report = {"status": "PASS" if ok else "FAIL", "vault": str(VAULT), "checks": checks, "structure": structure, "brainctl": brainctl}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(report["status"])
        for c in checks:
            print(("OK" if c["ok"] else "FAIL"), c["name"], c.get("value", c.get("path", "")))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
