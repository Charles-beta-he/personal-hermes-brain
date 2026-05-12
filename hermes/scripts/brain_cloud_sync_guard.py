#!/usr/bin/env python3
"""Dynamic no-agent cloud sync guard for the personal Hermes brain repo.

This script is designed for Hermes cron no_agent mode: it stays quiet when there
is no actionable change, and emits compact JSON only on push/change/error.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(HOME / ".hermes"))).expanduser()
REPO = Path(os.environ.get("HERMES_PERSONAL_BRAIN_REPO", str(HOME / "personal-hermes-brain"))).expanduser()
STATE = HERMES_HOME / "state" / "brain_cloud_sync_guard.json"
LOG = HERMES_HOME / "logs" / "brain_cloud_sync_guard.jsonl"
REMOTE = "https://github.com/Charles-beta-he/personal-hermes-brain.git"


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 180, env: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout, env=env)
        return {"cmd": cmd, "returncode": p.returncode, "stdout": (p.stdout or "")[-4000:], "stderr": (p.stderr or "")[-4000:]}
    except subprocess.TimeoutExpired as exc:
        return {"cmd": cmd, "returncode": "timeout", "stdout": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "", "stderr": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "", "reason": "timeout"}


def append(obj: dict[str, Any]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def save_state(obj: dict[str, Any]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    event: dict[str, Any] = {"schema": "brain_cloud_sync_guard_v1", "ts": utc(), "repo": str(REPO)}
    event["local_sync"] = run([sys.executable, str(HERMES_HOME / "scripts" / "brainctl.py"), "--json", "sync"], timeout=180)
    event["reindex"] = run([sys.executable, str(HERMES_HOME / "scripts" / "brainctl.py"), "--json", "reindex"], timeout=180)
    event["export"] = run([sys.executable, str(HERMES_HOME / "scripts" / "personal_hermes_brain_export.py"), "--json"], timeout=300)
    if event["export"]["returncode"] != 0:
        event["status"] = "ERROR"
        append(event); save_state(event)
        print(json.dumps(event, ensure_ascii=False, indent=2))
        return 2
    event["validate"] = run(["bash", "bootstrap/validate_safe_tree.sh"], cwd=REPO, timeout=180)
    event["verify"] = run(["bash", "bootstrap/verify.sh"], cwd=REPO, timeout=180)
    if event["validate"]["returncode"] != 0 or event["verify"]["returncode"] != 0:
        event["status"] = "ERROR"
        append(event); save_state(event)
        print(json.dumps(event, ensure_ascii=False, indent=2))
        return 2
    event["git_status"] = run(["git", "status", "--short"], cwd=REPO, timeout=60)
    changed = bool(event["git_status"].get("stdout", "").strip())
    event["changed"] = changed
    if changed:
        run(["git", "add", "-A"], cwd=REPO, timeout=120)
        msg = "sync: sanitized personal Hermes brain"
        event["commit"] = run(["git", "commit", "-m", msg], cwd=REPO, timeout=180)
        env = os.environ.copy(); env["HERMES_ALLOW_PUSH"] = "1"
        event["push"] = run(["git", "push", "-u", "origin", "HEAD:main"], cwd=REPO, timeout=300, env=env)
        event["status"] = "OK" if event["push"]["returncode"] == 0 else "ERROR"
    else:
        event["status"] = "OK"
        event["action"] = "no_change"
    append(event); save_state(event)
    if changed or event["status"] != "OK":
        print(json.dumps({k: event.get(k) for k in ["schema", "ts", "status", "changed", "repo", "commit", "push", "validate"]}, ensure_ascii=False, indent=2))
    return 0 if event["status"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
