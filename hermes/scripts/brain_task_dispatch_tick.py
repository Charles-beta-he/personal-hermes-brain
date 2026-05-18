#!/usr/bin/env python3
"""Safe local-brain task dispatch tick.

This is normally a control-plane tick, not an autonomous executor:
- ingests Obsidian inbox drafts into canonical task notes;
- reconciles stale leases/expired tasks/due retries;
- regenerates derived dashboards;
- emits a dispatch hint for the next dispatchable task;
- records a JSONL proof log.

It never executes task Markdown or arbitrary hooks.  With explicit --autorun-step,
it may run the bounded static runner and proof-gated review->done closer.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TZ = timezone(timedelta(hours=8))
HOME = Path.home()
SCRIPT = HOME / ".hermes" / "scripts" / "brain_task_orchestrator.py"
AUTORUN_STEP_SCRIPT = HOME / ".hermes" / "scripts" / "brain_task_autorun_step.py"
STATE_DIR = Path(os.environ.get("HERMES_BRAIN_DISPATCH_TICK_STATE_DIR", str(HOME / ".hermes" / "state"))).expanduser()
LOG_DIR = Path(os.environ.get("HERMES_BRAIN_DISPATCH_TICK_LOG_DIR", str(HOME / ".hermes" / "logs"))).expanduser()
STATE_FILE = STATE_DIR / "brain_task_dispatch_tick_state.json"
LOG_FILE = LOG_DIR / "brain_task_dispatch_tick.jsonl"
DEFAULT_COMMAND_TIMEOUT_SECONDS = 120.0
DEFAULT_TERMINATE_GRACE_SECONDS = 5.0


def positive_float_env(name: str, default: float) -> float:
    raw = os.environ.get(name, "")
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def command_timeout_seconds() -> float:
    return positive_float_env("HERMES_BRAIN_DISPATCH_TICK_COMMAND_TIMEOUT_SECONDS", DEFAULT_COMMAND_TIMEOUT_SECONDS)


def terminate_grace_seconds() -> float:
    return positive_float_env("HERMES_BRAIN_DISPATCH_TICK_TERMINATE_GRACE_SECONDS", DEFAULT_TERMINATE_GRACE_SECONDS)


def _timeout_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _signal_process_group(proc: subprocess.Popen[Any], sig: int) -> bool:
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, sig)
        return True
    except ProcessLookupError:
        return True
    except Exception:
        return False


def _terminate_process_tree(proc: subprocess.Popen[Any]) -> bool:
    """Terminate a timed-out command and its process group.

    Multi-model steps can spawn long-running child model calls. Killing only the
    immediate process leaves orphan consult_models.py children running. Starting
    commands in a new session and killing the process group keeps timeout
    handling fail-closed and resource-safe.
    """
    if _signal_process_group(proc, signal.SIGTERM):
        return True
    try:
        proc.terminate()
    except Exception:
        try:
            proc.kill()
        except Exception:
            return False
    return False


def _kill_process_tree(proc: subprocess.Popen[Any]) -> bool:
    if _signal_process_group(proc, signal.SIGKILL):
        return True
    try:
        proc.kill()
        return False
    except Exception:
        return False


def iso() -> str:
    return datetime.now(TZ).replace(microsecond=0).isoformat()


def run_json(args: list[str]) -> dict[str, Any]:
    cmd = [sys.executable, str(SCRIPT), *args]
    return run_cmd_json(cmd)


def run_cmd_json(cmd: list[str], env_overlay: dict[str, str] | None = None) -> dict[str, Any]:
    timeout = command_timeout_seconds()
    env = os.environ.copy()
    if env_overlay:
        env.update(env_overlay)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        env=env,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process_group_terminated = _terminate_process_tree(proc)
        process_group_killed = False
        try:
            out, err = proc.communicate(timeout=terminate_grace_seconds())
        except subprocess.TimeoutExpired:
            process_group_killed = _kill_process_tree(proc)
            out, err = proc.communicate()
        return {
            "status": "ERROR",
            "cmd": cmd,
            "returncode": "timeout",
            "timeout_seconds": timeout,
            "terminate_grace_seconds": terminate_grace_seconds(),
            "stdout": _timeout_output(out)[-4000:],
            "stderr": _timeout_output(err)[-4000:],
            "reason": "subprocess_timeout",
            "process_group_terminated": process_group_terminated,
            "process_group_killed": process_group_killed,
        }
    out = (out or "").strip()
    err = (err or "").strip()
    try:
        data = json.loads(out) if out else {"status": "OK"}
    except Exception as exc:
        data = {"status": "ERROR", "cmd": cmd, "returncode": proc.returncode, "stdout": out, "stderr": err, "parse_error": str(exc)}
    if not isinstance(data, dict):
        data = {"status": "ERROR", "cmd": cmd, "returncode": proc.returncode, "stdout": out, "stderr": err, "parse_error": "json payload is not an object"}
    data.setdefault("cmd", cmd)
    data.setdefault("returncode", proc.returncode)
    if proc.returncode != 0:
        data.setdefault("reported_status", data.get("status"))
        data["status"] = "ERROR"
        data.setdefault("stdout", out)
        data.setdefault("stderr", err)
    return data


def load_state() -> dict[str, Any]:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_log(event: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe local-brain task dispatch tick")
    parser.add_argument("--print-always", action="store_true", help="Always print the event JSON")
    parser.add_argument("--summary", action="store_true", help="Always print a compact JSON summary suitable for cron no_agent heartbeat delivery")
    parser.add_argument("--no-state", action="store_true", help="Do not suppress repeated notifications")
    parser.add_argument("--autorun", action="store_true", help="Opt-in bridge: run auto-claim-and-handoff after all safe tick gates pass")
    parser.add_argument("--autorun-step", action="store_true", help="Opt-in bounded runner: claim, run static allowlisted command IDs, and stop at review")
    parser.add_argument("--multimodel-step", action="store_true", help="Opt-in expensive multi-model step; still requires HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1")
    parser.add_argument("--multimodel-task", default="", help="Limit --multimodel-step to one task id when event-hook smart routing enables it")
    parser.add_argument("--no-blocked-resolve-step", dest="blocked_resolve_step", action="store_false", help="Disable bounded blocked-task resolver for this tick")
    parser.set_defaults(blocked_resolve_step=True)
    args = parser.parse_args()

    event: dict[str, Any] = {"status": "OK", "generated_at": iso(), "script": str(Path(__file__).expanduser())}
    event["ingest"] = run_json(["ingest-inbox", "--write", "--json"])
    event["reconcile"] = run_json(["reconcile", "--write", "--promote-due-retry", "--json"])
    event["dashboard"] = run_json(["dashboard", "--write", "--json"])
    event["proof_check"] = run_json(["proof-check", "--json"])
    event["evidence_spine"] = run_json(["evidence-spine", "--json"])
    event["multimodel_intervention"] = run_json(["multimodel-intervention-dry-run", "--json"])

    errors = []
    errored_steps: set[str] = set()
    allowed_statuses = {"OK", "PASS", "SKIP"}  # SKIP for multimodel_step when env var not set
    if (event.get("evidence_spine") or {}).get("gate_status") not in {None, "PASS"}:
        errors.append({
            "step": "evidence_spine",
            "status": (event.get("evidence_spine") or {}).get("status"),
            "gate_status": (event.get("evidence_spine") or {}).get("gate_status"),
            "summary": (event.get("evidence_spine") or {}).get("summary", {}),
        })
        errored_steps.add("evidence_spine")

    # D2: expensive multi-model auto-step is double-gated: explicit CLI flag + env var.
    # Ambient HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1 must not turn safe summary
    # cron ticks into long-running model calls.
    if args.multimodel_step and os.environ.get("HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL") == "1" and not errors:
        multimodel_args = ["multimodel-intervention-step", "--json"]
        if args.multimodel_task:
            multimodel_args.extend(["--task", args.multimodel_task])
            event["multimodel_task"] = args.multimodel_task
        event["multimodel_step"] = run_json(multimodel_args)
        if event["multimodel_step"].get("status") not in allowed_statuses:
            errors.append({"step": "multimodel_step", "status": event["multimodel_step"].get("status"), "stderr": event["multimodel_step"].get("stderr"), "stdout": event["multimodel_step"].get("stdout"), "reason": event["multimodel_step"].get("reason")})
    elif args.multimodel_step and not errors:
        event["multimodel_step"] = {
            "status": "SKIP",
            "reason": "autorun_multimodel_disabled",
            "env_flag": "HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL",
            "safety": "set HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1 to enable",
        }
    event["dispatch"] = run_json(["dispatch-dry-run", "--json"])

    for key in ["ingest", "reconcile", "dashboard", "proof_check", "evidence_spine", "multimodel_intervention", "multimodel_step", "dispatch"]:
        if key in errored_steps:
            continue
        item = event.get(key, {})
        if item and item.get("status") not in allowed_statuses:
            errors.append({"step": key, "status": item.get("status"), "stderr": item.get("stderr"), "stdout": item.get("stdout")})
            errored_steps.add(key)
    # Flow tolerance: historical proof debt in already-done tasks must be visible,
    # but it should not block dispatch/autorun for the current active task pool.
    # Keep fail-closed for active-task proof errors, invalid proof hashes, selfcheck
    # failures, boundary failures, and any unknown step error.
    def _historical_proof_debt_only() -> bool:
        proof = event.get("proof_check") or {}
        failures = proof.get("failures") if isinstance(proof.get("failures"), list) else []
        warnings = proof.get("warnings") if isinstance(proof.get("warnings"), list) else []
        if not failures and not warnings:
            return False
        tolerated_failure_prefixes = (
            "done task missing evidence: ",
            "autorun done task missing proof evidence: ",
            "unstructured evidence in ",
        )
        tolerated_warning_prefixes = (
            "missing Final Handoff section: ",
            "legacy body-only evidence accepted: ",
        )
        return all(str(f).startswith(tolerated_failure_prefixes) for f in failures) and all(
            str(w).startswith(tolerated_warning_prefixes) for w in warnings
        )

    tolerated_errors: list[dict[str, Any]] = []
    fatal_errors: list[dict[str, Any]] = []
    historical_proof_debt_only = _historical_proof_debt_only()
    for err in errors:
        step = str(err.get("step") or "")
        if step == "proof_check" and historical_proof_debt_only:
            tolerated_errors.append({**err, "tolerance": "historical_done_task_proof_debt"})
            continue
        if step == "evidence_spine" and historical_proof_debt_only:
            summary = err.get("summary") if isinstance(err.get("summary"), dict) else {}
            if summary.get("proof_check") == "FAIL" and summary.get("selfcheck") == "PASS" and summary.get("boundary_check") == "PASS":
                tolerated_errors.append({**err, "tolerance": "historical_done_task_proof_debt"})
                continue
        fatal_errors.append(err)
    if tolerated_errors:
        event["flow_tolerated_errors"] = tolerated_errors
    errors = fatal_errors
    event["errors"] = errors
    if errors:
        event["status"] = "ERROR"

    if args.blocked_resolve_step and not errors:
        event["blocked_resolve"] = run_json(["blocked-resolve-step", "--max-tasks", "5", "--json"])
        blocked_resolve = event["blocked_resolve"]
        if blocked_resolve.get("status") == "ERROR":
            errors.append({"step": "blocked_resolve", "result": blocked_resolve})
            errored_steps.add("blocked_resolve")
            event["status"] = "ERROR"
            event["errors"] = errors

    if args.autorun_step and not errors:
        event["autorun"] = run_cmd_json([sys.executable, str(AUTORUN_STEP_SCRIPT), "--json"])
        if event["autorun"].get("status") not in {"OK", "PASS"}:
            errors.append({"step": "autorun_step", "status": event["autorun"].get("status"), "stderr": event["autorun"].get("stderr"), "stdout": event["autorun"].get("stdout")})
            event["status"] = "ERROR"
            event["errors"] = errors
        if not errors:
            event["auto_close_review"] = run_cmd_json([sys.executable, str(SCRIPT), "auto-close-review", "--json"], env_overlay={"HERMES_AUTO_CLOSE_REVIEW_TRIGGER_CERT": "0"})
            if event["auto_close_review"].get("status") not in {"OK", "PASS"}:
                errors.append({"step": "auto_close_review", "status": event["auto_close_review"].get("status"), "stderr": event["auto_close_review"].get("stderr"), "stdout": event["auto_close_review"].get("stdout")})
                event["status"] = "ERROR"
                event["errors"] = errors
        event["post_autorun_dispatch"] = run_json(["dispatch-dry-run", "--json"])
    elif args.autorun and not errors:
        event["autorun"] = run_json(["auto-claim-and-handoff", "--json"])
        if event["autorun"].get("status") not in {"OK", "PASS"}:
            errors.append({"step": "autorun", "status": event["autorun"].get("status"), "stderr": event["autorun"].get("stderr"), "stdout": event["autorun"].get("stdout")})
            event["status"] = "ERROR"
            event["errors"] = errors

    next_task = (event.get("dispatch") or {}).get("next") or {}
    next_id = next_task.get("id") or ""
    event["next_task_id"] = next_id
    event["dispatchable"] = bool((event.get("dispatch") or {}).get("dispatchable"))
    event["reconcile_action_count"] = int((event.get("reconcile") or {}).get("action_count") or 0)
    event["ingested_count"] = int((event.get("ingest") or {}).get("created_count") or 0)
    mm_selected_id = str((event.get("multimodel_intervention") or {}).get("selected_task_id") or "")
    event["multimodel_intervention_required"] = bool((event.get("multimodel_intervention") or {}).get("intervention_required"))
    event["multimodel_intervention_task_id"] = mm_selected_id
    event["log_file"] = str(LOG_FILE)
    event["state_file"] = str(STATE_FILE)

    previous = load_state() if not args.no_state else {}
    changed = next_id and next_id != previous.get("last_notified_task_id")
    mm_changed = mm_selected_id and mm_selected_id != previous.get("last_multimodel_intervention_task_id")
    noteworthy = bool(errors or event["reconcile_action_count"] or event["ingested_count"] or changed or mm_changed)
    stdout_policy = "summary" if args.summary else ("print_always" if args.print_always else "noteworthy_only")
    will_print = bool(args.summary or args.print_always or noteworthy)
    print_reason = "summary" if args.summary else ("print_always" if args.print_always else ("noteworthy" if noteworthy else "suppressed_no_change"))
    recovery_command = f"python3 {Path(__file__).expanduser()} --print-always --no-state"
    dispatch_hint = {
        "task_id": next_id,
        "title": next_task.get("title", ""),
        "lane": next_task.get("lane", ""),
        "priority": next_task.get("priority", ""),
        "project": next_task.get("project", ""),
        "claim_command": (event.get("dispatch") or {}).get("claim_command", ""),
        "safety": "hint_only",
    }
    autorun_raw = event.get("autorun") if isinstance(event.get("autorun"), dict) else {}
    auto_close_raw = event.get("auto_close_review") if isinstance(event.get("auto_close_review"), dict) else {}
    mm_raw = event.get("multimodel_intervention") if isinstance(event.get("multimodel_intervention"), dict) else {}
    evidence_spine_raw = event.get("evidence_spine") if isinstance(event.get("evidence_spine"), dict) else {}
    mm_selected = mm_raw.get("selected") if isinstance(mm_raw.get("selected"), dict) else {}
    trigger_reasons = mm_selected.get("trigger_reasons", [])
    advisory_reasons = mm_selected.get("advisory_reasons", [])
    cert_reasons = mm_selected.get("certification_reasons", [])
    if not advisory_reasons and not cert_reasons and trigger_reasons:
        strong = {"p0_evolution_blast_radius", "loop_non_convergence", "stale_claim"}
        advisory_reasons = [r for r in trigger_reasons if r not in strong]
        cert_reasons = [r for r in trigger_reasons if r in strong]
    recommended_tier = "T3_certification" if cert_reasons else ("T2_advisory" if len(trigger_reasons) >= 3 else "T1_advisory")
    multimodel_summary = {
        "intervention_required": bool(mm_raw.get("intervention_required")),
        "task_id": str(mm_raw.get("selected_task_id") or ""),
        "queued_count": int(mm_raw.get("queued_count") or 0),
        "criteria": mm_raw.get("criteria", []),
        "trigger_reasons": trigger_reasons,
        "advisory_reasons": advisory_reasons,
        "certification_reasons": cert_reasons,
        "recommended_tier": recommended_tier,
        "advisory_only": bool(advisory_reasons) and not bool(cert_reasons),
        "gate_command_template": mm_selected.get("gate_command_template", ""),
        "convergence": mm_raw.get("convergence", {}),
        "safety": mm_raw.get("safety", ""),
    }
    autorun_summary = {
        "requested": bool(args.autorun or args.autorun_step),
        "step_mode": "bounded_step" if args.autorun_step else ("claim_and_handoff" if args.autorun else "none"),
        "present": "autorun" in event,
        "status": autorun_raw.get("status"),
        "eligible": bool(autorun_raw.get("eligible")),
        "claimed": bool(autorun_raw.get("claimed")),
        "advanced": bool(autorun_raw.get("advanced")),
        "task_id": autorun_raw.get("task_id") or autorun_raw.get("task") or "",
        "to_status": autorun_raw.get("to_status", ""),
        "reasons": autorun_raw.get("reasons", []),
        "proof_hash": autorun_raw.get("proof_hash", ""),
        "handoff": autorun_raw.get("handoff", ""),
        "claim_expires_at": autorun_raw.get("claim_expires_at", ""),
        "safety": autorun_raw.get("safety", ""),
    }
    summary_payload = {
        "schema": "brain_task_dispatch_tick_summary_v1",
        "generated_at": event["generated_at"],
        "status": event["status"],
        "dispatchable": event["dispatchable"],
        "next_task_id": event["next_task_id"],
        "reconcile_action_count": event["reconcile_action_count"],
        "ingested_count": event["ingested_count"],
        "error_count": len(errors),
        "evidence_spine": {
            "status": evidence_spine_raw.get("status"),
            "gate_status": evidence_spine_raw.get("gate_status"),
            "summary": evidence_spine_raw.get("summary", {}),
            "safety": evidence_spine_raw.get("safety", ""),
        },
        "multimodel_intervention": multimodel_summary,
        "multimodel_step": (event.get("multimodel_step") or {}) if isinstance(event.get("multimodel_step"), dict) else {},
        "auto_close_review": {
            "status": auto_close_raw.get("status"),
            "closed_count": int(auto_close_raw.get("closed_count") or 0),
            "skipped_count": int(auto_close_raw.get("skipped_count") or 0),
            "error_count": int(auto_close_raw.get("error_count") or 0),
            "closed": auto_close_raw.get("closed", []),
            "skipped": auto_close_raw.get("skipped", []),
            "safety": auto_close_raw.get("safety", ""),
        },
        "stdout_policy": "summary",
        "log_file": str(LOG_FILE),
        "state_file": str(STATE_FILE),
        "dispatch_hint": dispatch_hint,
        "recovery_command": recovery_command,
    }
    if args.autorun or args.autorun_step:
        summary_payload["autorun"] = autorun_summary
    event["observability"] = {
        "schema": "brain_task_dispatch_tick_observability_v1",
        "stdout_policy": stdout_policy,
        "printed": will_print,
        "print_reason": print_reason,
        "noteworthy": noteworthy,
        "summary_available": True,
        "log_file": str(LOG_FILE),
        "state_file": str(STATE_FILE),
        "recovery_command": recovery_command,
        "no_agent_note": "Default no-change ticks may intentionally emit empty stdout; use --summary for heartbeat or --print-always for full JSON.",
    }

    append_log(event)
    save_state({
        "updated_at": event["generated_at"],
        "last_notified_task_id": next_id,
        "last_status": event["status"],
        "last_dispatchable": event["dispatchable"],
        "last_multimodel_intervention_task_id": mm_selected_id,
        "last_multimodel_intervention_required": event["multimodel_intervention_required"],
        "last_log_file": str(LOG_FILE),
        "last_stdout_policy": stdout_policy,
        "last_print_reason": print_reason,
    })

    if args.summary:
        print(json.dumps(summary_payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif args.print_always or noteworthy:
        print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0 if event["status"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
