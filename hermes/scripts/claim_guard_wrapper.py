#!/usr/bin/env python3
"""claim_guard_wrapper.py — cron/subagent claim + budget typed-envelope wrapper.

Thin wrapper around long_evolution_guard primitives. It prepares a low-risk
local lease, typed mailbox envelope, and provider/budget accounting boundary
before a cron/subagent task claims completion.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Sequence


def load_guard():
    script = Path(__file__).parent / "long_evolution_guard.py"
    spec = importlib.util.spec_from_file_location("long_evolution_guard", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("long_evolution_guard", module)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def prepare_guarded_run(task_id: str, owner: str, budget_envelope: dict[str, Any], *, ttl: int = 3600, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    guard = load_guard()
    budget = guard.check_budget(budget_envelope)
    if not budget.get("passed"):
        return {"ok": False, "reason": "budget_blocked", "budget": budget}
    claim = guard.claim_task(task_id, owner, ttl=ttl, metadata={"wrapper": "claim_guard_wrapper", **(metadata or {})})
    if not claim.get("ok"):
        return {"ok": False, "reason": "claim_blocked", "claim": claim, "budget": budget}
    mailbox = {
        "schema": "hermes_typed_mailbox_envelope_v1",
        "task_id": task_id,
        "owner": owner,
        "claim": claim.get("claim"),
        "budget_hash": budget.get("envelope_hash"),
        "provider_accounting": {
            "spent_tokens": budget_envelope.get("spent_tokens"),
            "max_tokens": budget_envelope.get("max_tokens"),
            "spent_usd": budget_envelope.get("spent_usd"),
            "max_usd": budget_envelope.get("max_usd"),
        },
        "truth_boundary": "claim and budget guard only; task result still needs tool evidence",
    }
    return {"ok": True, "claim": claim, "budget": budget, "mailbox_envelope": mailbox}


def parse_json_arg(value: str) -> dict[str, Any]:
    path = Path(value).expanduser()
    data = json.loads(path.read_text(encoding="utf-8") if path.exists() else value)
    if not isinstance(data, dict):
        raise ValueError("expected JSON object")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare claim/budget guarded run")
    parser.add_argument("--task", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--budget", required=True, help="JSON object or path")
    parser.add_argument("--ttl", type=int, default=3600)
    parser.add_argument("--metadata", default="{}", help="JSON object or path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = prepare_guarded_run(args.task, args.owner, parse_json_arg(args.budget), ttl=args.ttl, metadata=parse_json_arg(args.metadata))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
