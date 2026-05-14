#!/usr/bin/env python3
"""Bounded local-brain autorun step.

This is a safer self-execution bridge for the local-brain task pool. It combines
hint/summary scheduling with bounded execution, but it is deliberately *not* a
Markdown executor:
- it never parses task-note bodies for commands;
- it only runs static command IDs from this file's registry;
- a policy file must explicitly allow task/profile/commands/workspace;
- success stops at review, never done.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(HOME / ".hermes"))).expanduser().resolve()
SCRIPT_DIR = HERMES_HOME / "scripts"
ORCH = SCRIPT_DIR / "brain_task_orchestrator.py"
AUTORUN_STATE_DIR = Path(os.environ.get("HERMES_BRAIN_AUTORUN_STATE_DIR", str(HERMES_HOME / "state"))).expanduser()
AUTORUN_POLICY = AUTORUN_STATE_DIR / "auto_run_policy.json"

COMMAND_REGISTRY: dict[str, list[str]] = {
    "noop": [sys.executable, "-c", "print('noop PASS')"],
    "fail": [sys.executable, "-c", "raise SystemExit(7)"],
    "py_compile_taskpool": [
        sys.executable,
        "-m",
        "py_compile",
        "scripts/brain_task_orchestrator.py",
        "scripts/brain_task_dispatch_tick.py",
        "scripts/brain_task_autorun_step.py",
    ],
    "test_brain_task_dispatch_tick": [sys.executable, "scripts/test_brain_task_dispatch_tick.py"],
}


def load_orchestrator():
    spec = importlib.util.spec_from_file_location("brain_task_orchestrator", ORCH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"orchestrator unavailable: {ORCH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def print_result(result: dict[str, Any], as_json: bool) -> int:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(result.get("status", "OK"))
        for k, v in result.items():
            if k != "status":
                print(f"{k}: {v}")
    return 0 if result.get("status") in {"OK", "PASS"} else 2


def run_json(cmd: list[str], timeout: int = 120) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(HERMES_HOME), capture_output=True, text=True, timeout=timeout, check=False)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return {"status": "ERROR", "cmd": cmd, "returncode": proc.returncode, "stdout": out[-4000:], "stderr": err[-4000:]}
    try:
        data = json.loads(out) if out else {"status": "OK"}
    except Exception as exc:
        return {"status": "ERROR", "cmd": cmd, "returncode": proc.returncode, "stdout": out[-4000:], "stderr": err[-4000:], "parse_error": type(exc).__name__}
    data.setdefault("cmd", cmd)
    data.setdefault("returncode", proc.returncode)
    return data


def list_rows() -> list[dict[str, Any]]:
    data = run_json([sys.executable, str(ORCH), "list", "--json"])
    return data.get("rows", []) if isinstance(data.get("rows"), list) else []


def find_row(task_id: str) -> dict[str, Any] | None:
    for row in list_rows():
        if row.get("id") == task_id:
            return row
    return None


def load_policy(profile: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        raw = json.loads(AUTORUN_POLICY.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, ["policy_missing"]
    except Exception as exc:
        return None, ["policy_invalid_json", type(exc).__name__]
    profiles = raw.get("profiles") if isinstance(raw, dict) else None
    if not isinstance(profiles, dict):
        return None, ["policy_profiles_missing"]
    policy = profiles.get(profile)
    if not isinstance(policy, dict):
        return None, ["policy_profile_missing"]
    return policy, []


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if value in (None, ""):
        return []
    return [str(value)]


def workspace_allowed(workspace: Path, roots: list[str]) -> bool:
    try:
        ws = workspace.expanduser().resolve()
        for root in roots:
            rp = Path(root).expanduser().resolve()
            if os.path.commonpath([str(ws), str(rp)]) == str(rp):
                return True
    except Exception:
        return False
    return False


def validate_policy_for_task(policy: dict[str, Any], row: dict[str, Any]) -> tuple[bool, list[str], Path, list[str], int]:
    reasons: list[str] = []
    task_id = str(row.get("id") or "")
    lane = str(row.get("lane") or "")
    project = str(row.get("project") or "")
    policy_task_ids = as_list(policy.get("task_ids"))
    policy_projects = as_list(policy.get("projects"))
    project_keys = [project, f"project:{project}" if project else ""]
    task_allowed = "*" in policy_task_ids or task_id in policy_task_ids or any(k and k in policy_projects for k in project_keys)
    if not task_allowed:
        reasons.append("policy_task_miss")
    allowed_lanes = as_list(policy.get("lanes"))
    if allowed_lanes and lane not in allowed_lanes:
        reasons.append("policy_lane_miss")
    command_ids = as_list(policy.get("command_ids"))
    if not command_ids:
        reasons.append("policy_commands_empty")
    unknown = [cid for cid in command_ids if cid not in COMMAND_REGISTRY]
    if unknown:
        reasons.append("policy_unknown_command_id:" + ",".join(unknown))
    if str(policy.get("close_mode") or "review_only") != "review_only":
        reasons.append("policy_close_mode_not_review_only")
    workspace = Path(str(policy.get("workspace") or HERMES_HOME))
    roots = as_list(policy.get("workspace_roots"))
    if not roots:
        reasons.append("policy_workspace_roots_empty")
    elif not workspace_allowed(workspace, roots):
        reasons.append("policy_workspace_not_allowed")
    try:
        max_seconds = int(policy.get("max_seconds") or 300)
    except Exception:
        max_seconds = 300
    if max_seconds < 1 or max_seconds > 900:
        reasons.append("policy_max_seconds_out_of_range")
    return not reasons, reasons, workspace.expanduser().resolve(), command_ids, max_seconds


def transition(task_id: str, to_status: str, actor: str, *, evidence: list[str] | None = None, reason: str = "", delay_minutes: int = 60) -> dict[str, Any]:
    cmd = [sys.executable, str(ORCH), "transition", task_id, "--to", to_status, "--actor", actor, "--json"]
    for e in evidence or []:
        cmd.extend(["--evidence", e])
    if reason:
        cmd.extend(["--reason", reason])
    if delay_minutes != 60:
        cmd.extend(["--delay-minutes", str(delay_minutes)])
    return run_json(cmd)


def command_autorun_step(args: argparse.Namespace) -> dict[str, Any]:
    orch = load_orchestrator()
    actor = args.actor
    eligibility_cmd = [sys.executable, str(ORCH), "eligibility-check", "--actor", actor, "--json"]
    if args.task:
        eligibility_cmd.extend(["--task", args.task])
    eligibility = run_json(eligibility_cmd)
    if not eligibility.get("eligible"):
        return {
            "status": "PASS",
            "claimed": False,
            "advanced": False,
            "eligible": False,
            "task_id": eligibility.get("task_id", ""),
            "reasons": eligibility.get("reasons", []) or ["not_eligible"],
            "warnings": eligibility.get("warnings", []),
            "safety": "fail-closed; no claim and no execution",
        }
    task_id = str(eligibility.get("task_id") or "")
    row = find_row(task_id)
    if not row:
        return {"status": "PASS", "claimed": False, "advanced": False, "eligible": False, "task_id": task_id, "reasons": ["task_row_unavailable"], "safety": "fail-closed; no claim and no execution"}
    policy, policy_reasons = load_policy(args.profile)
    if policy is None:
        return {"status": "PASS", "claimed": False, "advanced": False, "eligible": True, "task_id": task_id, "reasons": policy_reasons, "policy": str(AUTORUN_POLICY), "safety": "fail-closed; policy required before claim"}
    ok, policy_reasons, workspace, command_ids, max_seconds = validate_policy_for_task(policy, row)
    if not ok:
        return {"status": "PASS", "claimed": False, "advanced": False, "eligible": True, "task_id": task_id, "reasons": policy_reasons, "policy": str(AUTORUN_POLICY), "safety": "fail-closed; policy denied before claim"}

    claim_cmd = [sys.executable, str(ORCH), "auto-claim-and-handoff", "--task", task_id, "--actor", actor, "--ttl-minutes", str(args.ttl_minutes), "--json"]
    claim = run_json(claim_cmd)
    if not claim.get("claimed"):
        return {"status": "PASS", "claimed": False, "advanced": False, "eligible": bool(claim.get("eligible")), "task_id": task_id, "reasons": claim.get("reasons", []) or ["claim_denied"], "warnings": claim.get("warnings", []), "claim": claim, "safety": "fail-closed; no execution"}

    row_after_claim = find_row(task_id) or {}
    readback_failures = []
    if row_after_claim.get("status") != "claimed":
        readback_failures.append("claim_readback_status_mismatch")
    if row_after_claim.get("claimed_by") != actor:
        readback_failures.append("claim_readback_actor_mismatch")
    if not row_after_claim.get("claim_expires_at"):
        readback_failures.append("claim_readback_lease_missing")
    if readback_failures:
        run_json([sys.executable, str(ORCH), "release", task_id, "--actor", actor, "--to-status", "pending", "--reason", "autorun-step claim readback mismatch", "--force", "--json"])
        return {"status": "ERROR", "claimed": False, "advanced": False, "task_id": task_id, "reasons": ["claim_readback_mismatch"], "warnings": readback_failures, "safety": "fail-closed; released if possible; no command executed"}

    started_hash = orch.append_autorun_proof_event({"event": "runner_started", "task": task_id, "actor": actor, "profile": args.profile, "command_ids": command_ids, "workspace": str(workspace), "safety": "static-command-registry-only; markdown-body-inert"})
    running = transition(task_id, "running", actor)
    if running.get("status") != "OK":
        run_json([sys.executable, str(ORCH), "release", task_id, "--actor", actor, "--to-status", "pending", "--reason", "autorun-step could not enter running", "--force", "--json"])
        return {"status": "ERROR", "claimed": False, "advanced": False, "task_id": task_id, "proof_hash": started_hash, "reasons": ["transition_to_running_failed"], "transition": running}

    command_results: list[dict[str, Any]] = []
    failed: dict[str, Any] | None = None
    for cid in command_ids:
        argv = COMMAND_REGISTRY[cid]
        orch.append_autorun_proof_event({"event": "command_started", "task": task_id, "actor": actor, "run_id": claim.get("run_id", ""), "command_id": cid, "argv": argv})
        proc = subprocess.run(argv, cwd=str(workspace), capture_output=True, text=True, timeout=max_seconds, check=False)
        result = {"command_id": cid, "returncode": proc.returncode, "stdout_tail": (proc.stdout or "")[-1000:], "stderr_tail": (proc.stderr or "")[-1000:]}
        command_results.append(result)
        orch.append_autorun_proof_event({"event": "command_finished", "task": task_id, "actor": actor, "run_id": claim.get("run_id", ""), **result})
        if proc.returncode != 0:
            failed = result
            break

    if failed:
        proof_hash = orch.append_autorun_proof_event({"event": "runner_finished", "task": task_id, "actor": actor, "run_id": claim.get("run_id", ""), "result": "failed", "failed_command_id": failed.get("command_id"), "safety": "moved-to-retry; no done"})
        retry = transition(task_id, "retry", actor, reason=f"autorun-step command failed: {failed.get('command_id')}", delay_minutes=args.retry_delay_minutes)
        return {"status": "OK", "claimed": True, "advanced": False, "eligible": True, "task_id": task_id, "from_status": "running", "to_status": "retry", "proof_hash": proof_hash, "command_results": command_results, "transition": retry, "safety": "failed closed to retry; no markdown body execution; no done"}

    proof_hash = orch.append_autorun_proof_event({"event": "runner_finished", "task": task_id, "actor": actor, "run_id": claim.get("run_id", ""), "result": "passed", "command_ids": command_ids, "safety": "review_only; no done"})
    evidence = [f"proof:{proof_hash}"] + [f"command:{cid} PASS" for cid in command_ids]
    review = transition(task_id, "review", actor, evidence=evidence)
    return {"status": "OK", "claimed": True, "advanced": review.get("status") == "OK", "eligible": True, "task_id": task_id, "from_status": "running", "to_status": "review" if review.get("status") == "OK" else "running", "proof_hash": proof_hash, "handoff": claim.get("handoff", ""), "command_results": command_results, "transition": review, "safety": "bounded static commands only; markdown body inert; review_only"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Bounded local-brain autorun step")
    p.add_argument("--task", default="")
    p.add_argument("--profile", default="default")
    p.add_argument("--actor", default="hermes-autorun-step")
    p.add_argument("--ttl-minutes", type=int, default=60)
    p.add_argument("--retry-delay-minutes", type=int, default=60)
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return print_result(command_autorun_step(args), args.json)


if __name__ == "__main__":
    raise SystemExit(main())
