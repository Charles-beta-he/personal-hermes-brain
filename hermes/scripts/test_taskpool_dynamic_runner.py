#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path.home() / ".hermes" / "scripts" / "taskpool_dynamic_runner.py"


def load_module():
    spec = importlib.util.spec_from_file_location("taskpool_dynamic_runner", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_signature_changes_on_next_task():
    m = load_module()
    a = {"status": "OK", "next_task_id": "a", "dispatchable": True, "multimodel_intervention": {"task_id": "m", "queued_count": 1}}
    b = {"status": "OK", "next_task_id": "b", "dispatchable": True, "multimodel_intervention": {"task_id": "m", "queued_count": 1}}
    assert m.signature(a) != m.signature(b)


def test_parse_json_tail_empty_is_safe():
    m = load_module()
    assert m.parse_json_tail("") == {}
    assert m.parse_json_tail(json.dumps({"ok": True}))["ok"] is True


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
    print(f"PASS {len(tests)} tests")
