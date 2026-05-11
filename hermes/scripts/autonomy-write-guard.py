#!/usr/bin/env python3
"""Write-surface guard for Hermes autonomy-capable integrations.

This is the small, reusable enforcement wrapper for /goal, Kanban, watchers,
Teams/Google Workspace writes, gateway fanout, or any future side-effecting
surface. It does not perform the write itself; callers must call this first and
proceed only when ok=true.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", HOME / ".hermes")).expanduser()
SCRIPTS = HERMES_HOME / "scripts"
DEFAULT_ALLOWLIST = Path(
    os.environ.get("HERMES_AUTONOMY_WRITE_ALLOWLIST", str(HERMES_HOME / "config" / "autonomy-write-allowlist.json"))
).expanduser()
WRITE_SURFACES = {
    "goal",
    "kanban-worker",
    "watcher",
    "teams",
    "google-workspace",
    "gateway-fanout",
    "cron-no-agent",
}
READONLY_MODES = {"read", "dry-run", "dispatch-hint"}
WRITE_MODES = {"budget-handoff", "autonomous-execution"}
CONTROL_PLANE_OPERATIONS = {"claim-and-handoff"}


def load_allowlist(path: Path) -> set[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    if isinstance(data, list):
        return {str(x) for x in data if x}
    if isinstance(data, dict):
        values = data.get("allow") or data.get("surfaces") or []
        if isinstance(values, list):
            return {str(x) for x in values if x}
    return set()


def run_precondition(mode: str) -> dict[str, Any]:
    cmd = [sys.executable, str(SCRIPTS / "autonomy-precondition.py"), "--mode", mode]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
    try:
        data = json.loads(proc.stdout or "{}")
    except Exception:
        data = {"parse_error": (proc.stdout or "")[-1000:]}
    return {"ok": proc.returncode == 0 and bool(data.get("ok")), "returncode": proc.returncode, "data": data, "stderr": (proc.stderr or "")[-1000:]}


def evaluate(surface: str, operation: str, mode: str, allowlist_path: Path) -> dict[str, Any]:
    allowlist = load_allowlist(allowlist_path)
    checks = []
    def add(name: str, ok: bool, **extra: Any) -> None:
        checks.append({"name": name, "ok": bool(ok), **extra})

    known_surface = surface in WRITE_SURFACES
    add("known_write_surface", known_surface, surface=surface, known=sorted(WRITE_SURFACES))

    if operation in READONLY_MODES:
        pre = run_precondition("dispatch-hint")
        add("dispatch_hint_precondition", pre["ok"], precondition=pre)
        failed = [c["name"] for c in checks if not c.get("ok")]
        return {
            "schema_version": 1,
            "surface": surface,
            "operation": operation,
            "mode": mode,
            "status": "PASS" if not failed else "FAIL_CLOSED",
            "ok": not failed,
            "failed_required_checks": failed,
            "checks": checks,
            "policy": "read/dry-run surfaces may pass with dispatch-hint only; no external write authorized",
        }

    if operation in CONTROL_PLANE_OPERATIONS:
        allowlisted = surface in allowlist
        add("surface_allowlisted", allowlisted, allowlist_path=str(allowlist_path), allowlist=sorted(allowlist))
        control_plane_mode_ok = mode == "dispatch-hint"
        add("control_plane_mode_is_dispatch_hint", control_plane_mode_ok, allowed_modes=["dispatch-hint"])
        pre = run_precondition("dispatch-hint")
        add("dispatch_hint_precondition", pre["ok"], precondition=pre)
        failed = [c["name"] for c in checks if not c.get("ok")]
        return {
            "schema_version": 1,
            "surface": surface,
            "operation": operation,
            "mode": mode,
            "status": "PASS" if not failed else "FAIL_CLOSED",
            "ok": not failed,
            "failed_required_checks": failed,
            "checks": checks,
            "policy": "bounded control-plane handoffs may mutate local task state only after surface allowlist and dispatch-hint precondition PASS; no task execution or external write authorized",
        }

    allowlisted = surface in allowlist
    add("surface_allowlisted", allowlisted, allowlist_path=str(allowlist_path), allowlist=sorted(allowlist))
    requested_mode_ok = mode in WRITE_MODES
    add("write_mode_is_explicit", requested_mode_ok, allowed_modes=sorted(WRITE_MODES))
    pre = run_precondition(mode if mode in WRITE_MODES else "budget-handoff")
    add("autonomy_precondition", pre["ok"], precondition=pre)
    failed = [c["name"] for c in checks if not c.get("ok")]
    return {
        "schema_version": 1,
        "surface": surface,
        "operation": operation,
        "mode": mode,
        "status": "PASS" if not failed else "FAIL_CLOSED",
        "ok": not failed,
        "failed_required_checks": failed,
        "checks": checks,
        "policy": "side-effecting writes require known surface, explicit allowlist, explicit mode, and autonomy-precondition PASS",
    }


def guard_or_raise(surface: str, operation: str, mode: str, allowlist_path: Path | None = None) -> dict[str, Any]:
    """Reusable caller-side guard.

    Side-effecting integrations should call this immediately before performing
    writes. It returns the full evidence object on PASS and raises
    PermissionError with the same evidence JSON on FAIL_CLOSED.
    """
    result = evaluate(surface, operation, mode, allowlist_path or DEFAULT_ALLOWLIST)
    if not result.get("ok"):
        raise PermissionError(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail-closed guard before Hermes write-capable surfaces")
    parser.add_argument("--surface", required=True)
    parser.add_argument("--operation", default="write")
    parser.add_argument("--mode", choices=["dispatch-hint", "budget-handoff", "autonomous-execution"], default="dispatch-hint")
    parser.add_argument("--allowlist", default=str(DEFAULT_ALLOWLIST))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--gate", action="store_true")
    args = parser.parse_args(argv)
    result = evaluate(args.surface, args.operation, args.mode, Path(args.allowlist).expanduser())
    if args.json or args.gate:
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(f"autonomy_write_guard: {result['status']} failed={result['failed_required_checks']}")
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
