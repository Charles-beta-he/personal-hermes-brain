#!/usr/bin/env python3
"""
Critical Config Backup — 冗余备份
每周自动备份核心配置到 git 仓库
"""

import os, shutil, subprocess, datetime, json

BACKUP_DIR = os.path.expanduser("~/.hermes/backups")
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
RUN_DIR = os.path.join(BACKUP_DIR, TIMESTAMP)

CRITICAL_PATHS = [
    "~/.hermes/skills",
    "~/.hermes/notes",
    "~/.hermes/scripts",
    "~/.hermes/config.yaml",
    "~/.claude/mcp.json",
]

EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    ".DS_Store",
    "node_modules",
]

def backup():
    os.makedirs(RUN_DIR, exist_ok=True)
    
    for path in CRITICAL_PATHS:
        src = os.path.expanduser(path)
        if not os.path.exists(src):
            continue
        dst = os.path.join(RUN_DIR, os.path.basename(src))
        
        if os.path.isfile(src):
            shutil.copy2(src, dst)
        else:
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*EXCLUDE_PATTERNS))
    
    # 生成 manifest
    manifest = {
        "timestamp": TIMESTAMP,
        "paths_backed_up": CRITICAL_PATHS,
        "backup_dir": RUN_DIR,
        "size_mb": round(sum(
            os.path.getsize(os.path.join(dp, f)) / 1024 / 1024
            for dp, dn, filenames in os.walk(RUN_DIR)
            for f in filenames
        ), 2)
    }
    
    with open(os.path.join(RUN_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    
    # 清理旧备份（保留最近 10 个）
    backups = sorted([d for d in os.listdir(BACKUP_DIR) if d != TIMESTAMP])
    for old in backups[:-9]:
        old_path = os.path.join(BACKUP_DIR, old)
        if os.path.isdir(old_path):
            shutil.rmtree(old_path)
    
    print(f"✓ 备份完成: {RUN_DIR}")
    print(f"  大小: {manifest['size_mb']} MB")
    print(f"  保留: 最近 10 个备份")
    return manifest

if __name__ == "__main__":
    backup()
