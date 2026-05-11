#!/usr/bin/env python3
"""Skill Stale Alert — 检测长期未审计的 skill"""
import os, json, datetime

DB = os.path.expanduser("~/.hermes/skills/bayesian-agent/confidence-db.json")
with open(DB) as f:
    db = json.load(f)

now = datetime.datetime.now()
stale = []
for name, data in db["skills"].items():
    last = data.get("last_audit", "")
    if last:
        try:
            dt = datetime.datetime.fromisoformat(last)
            days = (now - dt).days
            if days > 7:
                stale.append((name, days))
        except:
            pass

if stale:
    print("⚠️ 长期未审计的 skill:")
    for name, days in sorted(stale, key=lambda x: -x[1]):
        print(f"  {name}: {days} 天")
else:
    print("✅ 所有 skill 近期都有审计")
