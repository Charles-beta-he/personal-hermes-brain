#!/usr/bin/env python3
"""Regression tests for taskpool_watch_report.py high-score anti-stall classification."""
from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path.home() / ".hermes" / "scripts" / "taskpool_watch_report.py"


def load_module():
    spec = importlib.util.spec_from_file_location("taskpool_watch_report", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_high_score_review_not_certified_is_closeout_gate_not_stuck():
    m = load_module()
    summary = m.summarize_rows([
        {
            "id": "score445-task",
            "score": 445,
            "status": "review",
            "project": "uvisa-app-2.0-work",
            "multimodel_status": "not_certified",
            "stale_claim": False,
            "dispatchable": False,
        }
    ])
    item = summary["high_score_attention"][0]
    assert item["classification"] == "review_gate_not_closed", item
    assert "target-bound 4/4" in item["next_action"], item


def test_high_score_stale_claim_is_real_deadlock():
    m = load_module()
    summary = m.summarize_rows([
        {
            "id": "stale-claimed-task",
            "score": 500,
            "status": "claimed",
            "project": "demo",
            "multimodel_status": "",
            "stale_claim": True,
            "dispatchable": False,
        }
    ])
    item = summary["high_score_attention"][0]
    assert item["classification"] == "stale_claim_stuck", item
    assert "release" in item["next_action"], item


def test_high_score_pending_dispatchable_is_active_not_done_but_not_review_gate():
    m = load_module()
    summary = m.summarize_rows([
        {
            "id": "pending-task",
            "score": 410,
            "status": "pending",
            "project": "demo",
            "multimodel_status": "",
            "stale_claim": False,
            "dispatchable": True,
        }
    ])
    item = summary["high_score_attention"][0]
    assert item["classification"] == "active_high_score", item


def main() -> int:
    for fn in [
        test_high_score_review_not_certified_is_closeout_gate_not_stuck,
        test_high_score_stale_claim_is_real_deadlock,
        test_high_score_pending_dispatchable_is_active_not_done_but_not_review_gate,
    ]:
        fn()
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
