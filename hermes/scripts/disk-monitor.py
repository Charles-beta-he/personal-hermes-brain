#!/usr/bin/env python3
"""Disk Monitor — 精细监控 Hermes 子目录"""
import os

MONITORED = {
    "notes":    (os.path.expanduser("~/.hermes/notes"),       50),
    "skills":   (os.path.expanduser("~/.hermes/skills"),      100),
    "scripts":  (os.path.expanduser("~/.hermes/scripts"),     20),
    "reports":  (os.path.expanduser("~/.hermes/notes/reports"), 30),
    "logs":     (os.path.expanduser("~/.hermes/logs"),         10),
}

def get_size(path):
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total += os.path.getsize(fp)
    return total / (1024 * 1024)

print("=" * 50)
print("Disk Monitor")
print("=" * 50)

alerts = []
for name, (path, limit) in MONITORED.items():
    if os.path.exists(path):
        size = get_size(path)
        status = "✅" if size < limit else "⚠️"
        print(f"  {status} {name:10s}: {size:6.1f} MB (limit: {limit} MB)")
        if size >= limit:
            alerts.append(f"{name}: {size:.1f}MB > {limit}MB")

if alerts:
    print("\n⚠️ 告警:")
    for a in alerts:
        print(f"  - {a}")
else:
    print("\n✅ 所有目录正常")
print("=" * 50)
