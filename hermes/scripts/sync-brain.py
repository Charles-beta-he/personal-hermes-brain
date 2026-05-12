#!/usr/bin/env python3
"""
sync-brain.py — 双向同步 Hermes notes ↔ Obsidian vault (brain)

方向:
  Push: ~/.hermes/notes/  →  ~/Documents/brain/99-hermes-notes/
  Pull: ~/Documents/brain/  →  ~/.hermes/notes/brain/

用法:
  python3 ~/.hermes/scripts/sync-brain.py          # 默认: push + pull
  python3 ~/.hermes/scripts/sync-brain.py --push     # 只推送
  python3 ~/.hermes/scripts/sync-brain.py --pull     # 只拉取
  python3 ~/.hermes/scripts/sync-brain.py --status   # 只检查差异
"""

import os
import shutil
import sys
import filecmp
from pathlib import Path

HERMES_NOTES = Path(os.path.expanduser("~/.hermes/notes"))
BRAIN = Path(os.path.expanduser("~/Documents/brain"))
BRAIN_HERMES_SYNC = BRAIN / "99-hermes-notes"
HERMES_BRAIN_SYNC = HERMES_NOTES / "brain"

def push():
    """Hermes notes → Obsidian vault"""
    HERMES_BRAIN_SYNC.mkdir(parents=True, exist_ok=True)
    count = 0
    for src_path in HERMES_NOTES.rglob("*.md"):
        # Skip only the pull-mirror subtree ~/.hermes/notes/brain/.
        # Do not skip ordinary notes whose filename contains "brain".
        try:
            rel_parts = src_path.relative_to(HERMES_NOTES).parts
        except ValueError:
            rel_parts = src_path.parts
        if rel_parts and rel_parts[0] == "brain":
            continue
        if ".git" in str(src_path):
            continue
        rel = src_path.relative_to(HERMES_NOTES)
        dst = BRAIN_HERMES_SYNC / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists() or not filecmp.cmp(src_path, dst, shallow=False):
            shutil.copy2(src_path, dst)
            count += 1
    return count

def pull():
    """Obsidian vault → Hermes notes (read-only mirror for search)"""
    HERMES_BRAIN_SYNC.mkdir(parents=True, exist_ok=True)
    count = 0
    for src_path in BRAIN.rglob("*.md"):
        if "99-hermes-notes" in str(src_path):
            continue
        if ".obsidian" in str(src_path):
            continue
        rel = src_path.relative_to(BRAIN)
        dst = HERMES_BRAIN_SYNC / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists() or not filecmp.cmp(src_path, dst, shallow=False):
            shutil.copy2(src_path, dst)
            count += 1
    return count

def status():
    """Show sync diff"""
    print("=== Push (Hermes → Brain) ===")
    push_count = 0
    for src_path in HERMES_NOTES.rglob("*.md"):
        # Skip only the pull-mirror subtree ~/.hermes/notes/brain/.
        # Do not skip ordinary notes whose filename contains "brain".
        try:
            rel_parts = src_path.relative_to(HERMES_NOTES).parts
        except ValueError:
            rel_parts = src_path.parts
        if rel_parts and rel_parts[0] == "brain":
            continue
        if ".git" in str(src_path):
            continue
        rel = src_path.relative_to(HERMES_NOTES)
        dst = BRAIN_HERMES_SYNC / rel
        if not dst.exists():
            print(f"  NEW push:  {rel}")
            push_count += 1
        elif not filecmp.cmp(src_path, dst, shallow=False):
            print(f"  CHANGED:   {rel}")
            push_count += 1
    
    print(f"\n  {push_count} files to push")
    
    print("\n=== Pull (Brain → Hermes) ===")
    pull_count = 0
    for src_path in BRAIN.rglob("*.md"):
        if "99-hermes-notes" in str(src_path):
            continue
        if ".obsidian" in str(src_path):
            continue
        rel = src_path.relative_to(BRAIN)
        dst = HERMES_BRAIN_SYNC / rel
        if not dst.exists():
            print(f"  NEW pull:  {rel}")
            pull_count += 1
        elif not filecmp.cmp(src_path, dst, shallow=False):
            print(f"  CHANGED:   {rel}")
            pull_count += 1
    
    print(f"\n  {pull_count} files to pull")
    return push_count + pull_count

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "sync"
    
    if mode == "--push":
        c = push()
        print(f"Pushed {c} files to brain/99-hermes-notes/")
    elif mode == "--pull":
        c = pull()
        print(f"Pulled {c} files to ~/.hermes/notes/brain/")
    elif mode == "--status":
        status()
    else:  # sync = push + pull
        pc = push()
        pl = pull()
        print(f"Sync complete: {pc} pushed, {pl} pulled")
