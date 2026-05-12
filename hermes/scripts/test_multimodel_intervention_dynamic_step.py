#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path.home() / ".hermes" / "scripts" / "multimodel_intervention_dynamic_step.py"


def load_module():
    spec = importlib.util.spec_from_file_location("multimodel_intervention_dynamic_step", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_signature_tracks_selected_and_pending_queue():
    m = load_module()
    a = {"selected_task_id": "a", "queued_count": 2, "convergence": {"pending_ids": ["a", "b"], "multimodel_passed": 1, "multimodel_triggered": 3}}
    b = {"selected_task_id": "b", "queued_count": 2, "convergence": {"pending_ids": ["b", "a"], "multimodel_passed": 1, "multimodel_triggered": 3}}
    assert m.signature(a) != m.signature(b)


def test_parse_json_rejects_garbage_safely():
    m = load_module()
    assert m.parse_json("not json") == {}
    assert m.parse_json(json.dumps({"ok": 1}))["ok"] == 1


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
    print(f"PASS {len(tests)} tests")
