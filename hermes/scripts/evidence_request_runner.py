#!/usr/bin/env python3
"""evidence_request_runner.py — allowlisted evidence-request hydrator.

Models may ask for evidence; this runner executes only local/read-only actions
and returns telemetry/budget data. It does not grant shell access to models and
it does not make truth claims beyond the collected tool evidence.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Sequence

BUDGET_DEFAULT = {"max_requests": 8, "max_chars": 20000}
ALLOWLIST = {"brainctl_search", "brainctl_evidence", "read_note"}


def load_brainctl():
    script = Path(__file__).parent / "brainctl.py"
    spec = importlib.util.spec_from_file_location("brainctl", script)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("brainctl", module)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def compact_json_size(data: Any) -> int:
    return len(json.dumps(data, ensure_ascii=False, sort_keys=True))


def execute_request(brainctl, request: dict[str, Any]) -> dict[str, Any]:
    rid = str(request.get("id") or "request")
    action = request.get("action")
    if action not in ALLOWLIST:
        return {"id": rid, "status": "blocked", "reason": "action_not_allowlisted", "action": action}
    if action in {"brainctl_search", "brainctl_evidence"}:
        query = str(request.get("query") or "")
        limit = int(request.get("limit") or 5)
        hits = brainctl.search(query, limit=limit, json_mode=True)
        return {"id": rid, "status": "ok", "action": action, "query_hash": brainctl.sha256_text(query), "hit_count": len(hits), "hits": hits}
    if action == "read_note":
        rel = Path(str(request.get("path") or "")).as_posix().lstrip("/")
        paths = brainctl.resolve_paths()
        target = (paths.vault / rel).resolve()
        vault = paths.vault.resolve()
        if vault not in target.parents and target != vault:
            return {"id": rid, "status": "blocked", "reason": "path_outside_vault", "path": rel}
        if not target.exists() or target.suffix != ".md":
            return {"id": rid, "status": "blocked", "reason": "note_not_found", "path": rel}
        text = target.read_text(encoding="utf-8", errors="replace")
        return {"id": rid, "status": "ok", "action": action, "path": rel, "chars": len(text), "excerpt": text[:1200]}
    return {"id": rid, "status": "blocked", "reason": "unhandled_action", "action": action}


def run_requests(requests: Sequence[dict[str, Any]], budget: dict[str, Any] | None = None) -> dict[str, Any]:
    budget = {**BUDGET_DEFAULT, **(budget or {})}
    max_requests = int(budget.get("max_requests", BUDGET_DEFAULT["max_requests"]))
    max_chars = int(budget.get("max_chars", BUDGET_DEFAULT["max_chars"]))
    violations: list[dict[str, Any]] = []
    if len(requests) > max_requests:
        violations.append({"type": "request_budget_exceeded", "requested": len(requests), "limit": max_requests})
    brainctl = load_brainctl()
    results: list[dict[str, Any]] = []
    total_chars = 0
    for idx, request in enumerate(requests):
        if idx >= max_requests:
            results.append({"id": str(request.get("id") or idx), "status": "blocked", "reason": "request_budget_exceeded"})
            continue
        result = execute_request(brainctl, request)
        size = compact_json_size(result)
        total_chars += size
        if total_chars > max_chars:
            result = {"id": str(request.get("id") or idx), "status": "blocked", "reason": "char_budget_exceeded", "size": size}
            violations.append({"type": "char_budget_exceeded", "limit": max_chars})
        if result.get("status") == "blocked":
            reason = result.get("reason", "blocked")
            if reason != "request_budget_exceeded":
                violations.append({"type": reason, "id": result.get("id")})
        results.append(result)
    telemetry = {"requests_received": len(requests), "requests_executed": sum(1 for r in results if r.get("status") == "ok"), "result_chars": total_chars}
    return {"schema": "evidence_request_runner_v1", "passed": not violations, "budget": budget, "telemetry": telemetry, "violations": violations, "results": results}


def load_requests(value: str) -> list[dict[str, Any]]:
    path = Path(value).expanduser()
    data = json.loads(path.read_text(encoding="utf-8") if path.exists() else value)
    if isinstance(data, dict) and "requests" in data:
        data = data["requests"]
    if not isinstance(data, list):
        raise ValueError("requests must be a JSON list or object with requests")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run allowlisted evidence requests")
    parser.add_argument("--requests", required=True, help="JSON list or path")
    parser.add_argument("--budget", default="{}", help="JSON object or path")
    return parser


def parse_json_arg(value: str) -> dict[str, Any]:
    path = Path(value).expanduser()
    data = json.loads(path.read_text(encoding="utf-8") if path.exists() else value)
    if not isinstance(data, dict):
        raise ValueError("budget must be JSON object")
    return data


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_requests(load_requests(args.requests), parse_json_arg(args.budget))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
