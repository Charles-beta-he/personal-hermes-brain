#!/usr/bin/env python3
"""
Sync Hermes notes ↔ Obsidian Vault (双向)
用法: python3 sync-to-obsidian.py [--push|--pull]
  --push: 将 Hermes notes 同步到 Obsidian (默认)
  --pull: 将 Obsidian 修改读回 Hermes
"""
import os, sys, shutil, json

VAULT = os.path.expanduser("~/Documents/Obsidian Vault")
NOTES = os.path.expanduser("~/.hermes/notes")

SYNC_MAP = {
    "engineering-cybernetics/evolution-dashboard.md": "Agent Reports/Evolution Dashboard.md",
    "engineering-cybernetics/PA-EVOLUTION-GOALS.md": "Agent Reports/PA Evolution Goals.md",
    "reports/cronjob-monitor.md": "Agent Reports/Cronjob Monitor.md",
    "reports/pa-daily-*.md": "Agent Reports/",
    "user-profile.md": "Agent Config/User Profile.md",
    "user-routine-patterns.json": "Agent Config/Routine Patterns.json",
}

def push():
    """Hermes → Obsidian"""
    for src_rel, dst_rel in SYNC_MAP.items():
        src = os.path.join(NOTES, src_rel)
        if "*" in src:
            # glob pattern
            import glob
            for f in glob.glob(src):
                dst = os.path.join(VAULT, dst_rel, os.path.basename(f))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(f, dst)
                print(f"  [PUSH] {f} -> {dst}")
        elif os.path.exists(src):
            dst = os.path.join(VAULT, dst_rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  [PUSH] {src} -> {dst}")
    print("Push complete.")

def pull():
    """Obsidian → Hermes (只读用户手动修改的内容)"""
    # 目前只支持 user-profile.md 的双向
    src = os.path.join(VAULT, "Agent Config/User Profile.md")
    dst = os.path.join(NOTES, "user-profile.md")
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"  [PULL] {src} -> {dst}")
    print("Pull complete.")

if __name__ == "__main__":
    if "--pull" in sys.argv:
        pull()
    else:
        push()
