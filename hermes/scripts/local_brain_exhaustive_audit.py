#!/usr/bin/env python3
"""Deterministic local-brain exhaustive audit.

Scans the canonical Obsidian/Hermes local brain for the PUA-loop stop gates:
empty directories, missing top-level indexes, hollow top-level parents, broken
wikilinks, and secret-like patterns. The scanner is intentionally conservative
for secrets: it detects credential-shaped assignments/known token prefixes, not
policy text that merely names credential classes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

DEFAULT_VAULT = Path(os.environ.get("HERMES_BRAIN_VAULT") or os.environ.get("OBSIDIAN_VAULT_PATH") or "~/Documents/brain").expanduser()
IGNORE_DIRS = {".git", ".obsidian", ".trash", "node_modules", "__pycache__"}
INDEX_PATTERNS = ("index", "moc", "索引")
WIKILINK_RE = re.compile(r"!?(?<!\\)\[\[([^\]\n]+)\]\]")
SECRET_PATTERNS = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    (
        "credential_assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|pwd|connection[_-]?string)\b\s*[:=]\s*['\"]?[A-Za-z0-9_./+~!@#$%^&*=-]{16,}['\"]?"
        ),
    ),
]


def visible_dirs(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")]
        yield Path(dirpath)


def visible_md_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")]
        for filename in filenames:
            if filename.startswith("."):
                continue
            if filename.endswith(".md"):
                files.append(Path(dirpath) / filename)
    return sorted(files)


def rel(p: Path, root: Path) -> str:
    return str(p.relative_to(root))


def is_index_file(p: Path) -> bool:
    stem = p.stem.lower()
    return any(pattern in stem for pattern in INDEX_PATTERNS)


def build_note_index(md_files: List[Path], root: Path) -> Tuple[Dict[str, List[str]], set[str]]:
    by_name: Dict[str, List[str]] = {}
    paths: set[str] = set()
    for p in md_files:
        r = rel(p, root)
        no_ext = r[:-3] if r.endswith(".md") else r
        paths.add(no_ext)
        paths.add(r)
        paths.add("/" + no_ext)
        by_name.setdefault(p.stem, []).append(no_ext)
    return by_name, paths


def normalize_wikilink(raw: str) -> str:
    target = raw.split("|", 1)[0].split("#", 1)[0].strip()
    # Obsidian links normally omit .md; tolerate both.
    if target.endswith(".md"):
        target = target[:-3]
    return target


def resolve_wikilink(target: str, by_name: Dict[str, List[str]], paths: set[str]) -> bool:
    if not target:
        return True
    candidates = {target, target.lstrip("/"), target + ".md", "/" + target.lstrip("/")}
    if candidates & paths:
        return True
    stem = Path(target).stem
    return stem in by_name


def scan(vault: Path, sample_limit: int = 30) -> dict:
    vault = vault.expanduser().resolve()
    if not vault.exists():
        raise SystemExit(f"vault does not exist: {vault}")
    dirs = list(visible_dirs(vault))
    md_files = visible_md_files(vault)
    by_name, paths = build_note_index(md_files, vault)

    empty_dirs = []
    for d in dirs:
        if d == vault:
            continue
        entries = [x for x in d.iterdir() if not x.name.startswith(".") and x.name not in IGNORE_DIRS]
        if not entries:
            empty_dirs.append(rel(d, vault))

    top_dirs = [p for p in vault.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name not in IGNORE_DIRS]
    top_level_no_index = []
    parent_no_direct_md_top = []
    for d in sorted(top_dirs):
        direct_md = [p for p in d.iterdir() if p.is_file() and p.suffix == ".md" and not p.name.startswith(".")]
        direct_dirs = [p for p in d.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name not in IGNORE_DIRS]
        if not any(is_index_file(p) for p in direct_md):
            top_level_no_index.append(rel(d, vault))
        if direct_dirs and not direct_md:
            parent_no_direct_md_top.append(rel(d, vault))

    broken = []
    wikilinks_seen = 0
    for p in md_files:
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in WIKILINK_RE.finditer(text):
            raw = m.group(1)
            target = normalize_wikilink(raw)
            wikilinks_seen += 1
            if not resolve_wikilink(target, by_name, paths):
                broken.append({"file": rel(p, vault), "target": target})

    secret_hits = []
    for p in md_files:
        text = p.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            for name, rx in SECRET_PATTERNS:
                if rx.search(line):
                    secret_hits.append({"file": rel(p, vault), "line": i, "pattern": name})

    return {
        "vault": str(vault),
        "visible_dirs_scanned": len(dirs),
        "markdown_files_scanned": len(md_files),
        "empty_dirs": empty_dirs,
        "top_level_no_index": top_level_no_index,
        "parent_no_direct_md_top": parent_no_direct_md_top,
        "broken_wikilinks_count": len(broken),
        "broken_wikilinks_samples": broken[:sample_limit],
        "secret_pattern_hits": len(secret_hits),
        "secret_pattern_hit_samples": secret_hits[:sample_limit],
        "wikilinks_seen": wikilinks_seen,
        "stop_gate_pass": not (empty_dirs or top_level_no_index or parent_no_direct_md_top or broken or secret_hits),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=str(DEFAULT_VAULT))
    ap.add_argument("--sample-limit", type=int, default=30)
    args = ap.parse_args()
    print(json.dumps(scan(Path(args.vault), args.sample_limit), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
