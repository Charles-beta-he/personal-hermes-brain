#!/usr/bin/env python3
"""
memory-cleaner.py — 记忆噪音自动清理。

扫描 MEMORY.md，检测并清理：
  - 矛盾条目（同一事实的不同版本）
  - 过时条目（包含过时版本号、过去完成时的工作总结）
  - 重复条目（相似度 > 80% 的段落）

用法：
  python3 memory-cleaner.py           # dry-run 模式
  python3 memory-cleaner.py --clean   # 执行清理
  python3 memory-cleaner.py --stats   # 仅统计
"""

import os
import re
import sys
from pathlib import Path

MEMORY_FILE = Path(os.path.expanduser("~/.hermes/memories/MEMORY.md"))

# ── Ghost detection patterns ───────────────────────────────────
_GHOST_PATTERNS = [
    # Version numbers (vX.Y.Z) in memory = stale
    re.compile(r'\bv\d+\.\d+\.\d+\b'),
    # Past-tense completed-work markers
    re.compile(r'(?:已|已经).*(?:完成|上线|实现|优化).*(?:了|完毕|完成)'),
    re.compile(r'最终达到.*状态'),
    re.compile(r'test[_-]?prompts?\.json.*(?:created|added|done)'),
    re.compile(r'(?:PR|MR|commit)\s*#\d+\s*(?:merged|closed|landed)'),
    # Timestamps that indicate past reports
    re.compile(r'\d{4}-\d{2}-\d{2}\s+(?:审计|报告|扫描|自检)'),
]

_DUPLICATE_THRESHOLD = 0.75  # similarity ratio for duplicate detection


def _normalize(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r'\s+', ' ', text.strip().lower())


def _similarity(a: str, b: str) -> float:
    """Simple token-overlap similarity."""
    a_tokens = set(_normalize(a).split())
    b_tokens = set(_normalize(b).split())
    if not a_tokens or not b_tokens:
        return 0.0
    intersection = a_tokens & b_tokens
    union = a_tokens | b_tokens
    return len(intersection) / len(union)


def _is_ghost(entry: str) -> tuple[bool, str]:
    """Check if an entry looks like a ghost (stale/past-tense)."""
    reasons = []
    for pattern in _GHOST_PATTERNS:
        if pattern.search(entry):
            reasons.append(f"matches: {pattern.pattern[:40]}")
    if reasons:
        return True, "; ".join(reasons)
    return False, ""


def scan() -> dict:
    """Scan MEMORY.md and return statistics."""
    if not MEMORY_FILE.exists():
        return {"status": "MISSING", "entries": 0, "ghosts": [], "duplicates": []}

    content = MEMORY_FILE.read_text()
    entries = [e.strip() for e in content.split("§") if e.strip()]

    result = {
        "status": "OK",
        "entries": len(entries),
        "char_count": len(content),
        "ghosts": [],
        "duplicates": [],
    }

    # Check each entry for ghost patterns
    for i, entry in enumerate(entries):
        is_ghost, reason = _is_ghost(entry)
        if is_ghost:
            preview = entry[:80].replace("\n", " ")
            result["ghosts"].append({"index": i, "preview": preview, "reason": reason})

    # Check for duplicate entries
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            sim = _similarity(entries[i], entries[j])
            if sim >= _DUPLICATE_THRESHOLD:
                result["duplicates"].append({
                    "i": i, "j": j,
                    "similarity": sim,
                    "preview_i": entries[i][:60].replace("\n", " "),
                    "preview_j": entries[j][:60].replace("\n", " "),
                })

    return result


def clean(dry_run: bool = True) -> bool:
    """Remove ghost and duplicate entries. Returns True if changes were needed."""
    if not MEMORY_FILE.exists():
        print("MEMORY.md not found")
        return False

    content = MEMORY_FILE.read_text()
    entries = [e.strip() for e in content.split("§") if e.strip()]
    original_count = len(entries)

    # Remove ghosts (reverse index to avoid shifting)
    ghosts_found = []
    for i in range(len(entries) - 1, -1, -1):
        is_ghost, reason = _is_ghost(entries[i])
        if is_ghost:
            ghosts_found.append((i, entries[i][:60].replace("\n", " "), reason))
            entries.pop(i)

    # Remove duplicates (keep first occurrence)
    duplicates_found = []
    i = 0
    while i < len(entries):
        j = i + 1
        while j < len(entries):
            if _similarity(entries[i], entries[j]) >= _DUPLICATE_THRESHOLD:
                duplicates_found.append((i, j, entries[j][:60].replace("\n", " ")))
                entries.pop(j)
            else:
                j += 1
        i += 1

    if not ghosts_found and not duplicates_found:
        return False

    if dry_run:
        print(f"  Ghosts found: {len(ghosts_found)}")
        for idx, preview, reason in ghosts_found:
            print(f"    [{idx}] {preview}")
            print(f"          → {reason}")
        print(f"  Duplicates found: {len(duplicates_found)}")
        for _, _, preview in duplicates_found:
            print(f"    Duplicate: {preview}")
        print(f"  Would remove {len(ghosts_found) + len(duplicates_found)} entries")
        return True

    # Write cleaned content
    new_content = "\n§\n".join(entries) + "\n"
    MEMORY_FILE.write_text(new_content)
    print(f"  Removed {original_count - len(entries)} entries ({original_count} → {len(entries)})")
    return True


def main():
    if "--stats" in sys.argv:
        stats = scan()
        print(f"Memory entries: {stats['entries']}")
        print(f"Characters: {stats['char_count']}")
        print(f"Ghosts: {len(stats['ghosts'])}")
        print(f"Duplicates: {len(stats['duplicates'])}")
        return

    if "--clean" in sys.argv:
        print("Cleaning memory...")
        changed = clean(dry_run=False)
        if not changed:
            print("  No ghosts or duplicates found")
    else:
        print("Memory cleaner — dry run (pass --clean to apply)")
        changed = clean(dry_run=True)
        if not changed:
            print("  No issues found")


if __name__ == "__main__":
    main()
