#!/usr/bin/env python3
"""
Obsidian Vault Watcher — 监控 Vault 变更，触发 Hermes 同步
用法: python3 obsidian-watch.py [--daemon]
"""
import os, sys, json, time, shutil

VAULT = os.path.expanduser("~/Documents/Obsidian Vault")
NOTES = os.path.expanduser("~/.hermes/notes")
STATE_FILE = os.path.expanduser("~/.hermes/.obsidian-watch-state.json")

WATCHED = {
    "Agent Config/User Profile.md": "user-profile.md",
}

def get_mtime(path):
    return os.path.getmtime(path) if os.path.exists(path) else 0

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def check():
    state = load_state()
    changes = []
    for vault_rel, hermes_rel in WATCHED.items():
        vp = os.path.join(VAULT, vault_rel)
        hp = os.path.join(NOTES, hermes_rel)
        mt = get_mtime(vp)
        if mt > state.get(vault_rel, 0):
            if os.path.exists(vp):
                os.makedirs(os.path.dirname(hp), exist_ok=True)
                shutil.copy2(vp, hp)
                changes.append(f"{vault_rel} -> {hermes_rel}")
                state[vault_rel] = mt
    if changes:
        save_state(state)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] Synced:")
        for c in changes:
            print(f"  + {c}")
        return True
    print("No changes")
    return False

def daemon():
    print("Obsidian Watcher daemon started (60s interval)")
    while True:
        check()
        time.sleep(60)

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        daemon()
    else:
        check()
