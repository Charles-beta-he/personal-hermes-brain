#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import sys
import tempfile
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
    a = {"status": "OK", "next_task_id": "a", "dispatchable": True, "multimodel_intervention": {"task_id": "m", "queued_count": 1}, "auto_close_review": {"closed_count": 0, "error_count": 0}}
    b = {"status": "OK", "next_task_id": "b", "dispatchable": True, "multimodel_intervention": {"task_id": "m", "queued_count": 1}, "auto_close_review": {"closed_count": 0, "error_count": 0}}
    c = {"status": "OK", "next_task_id": "b", "dispatchable": True, "multimodel_intervention": {"task_id": "m", "queued_count": 1}, "auto_close_review": {"closed_count": 1, "error_count": 0}}
    assert m.signature(a) != m.signature(b)
    assert m.signature(b) != m.signature(c)


def test_parse_json_tail_empty_is_safe():
    m = load_module()
    assert m.parse_json_tail("") == {}
    assert m.parse_json_tail(json.dumps({"ok": True}))["ok"] is True


def test_run_preserves_full_stdout_for_large_summary_json():
    m = load_module()
    payload = {
        "padding": "x" * 5000,
        "status": "OK",
        "next_task_id": "task-123",
        "dispatchable": True,
        "error_count": 0,
        "reconcile_action_count": 0,
        "ingested_count": 0,
        "multimodel_intervention": {"intervention_required": True, "task_id": "mm-task", "queued_count": 15},
    }
    code = "import json; print(json.dumps(%r))" % payload
    result = m.run([sys.executable, "-c", code], timeout=10)
    parsed = m.parse_json_tail(result["stdout"])
    assert parsed["status"] == "OK"
    assert parsed["next_task_id"] == "task-123"
    assert parsed["multimodel_intervention"]["queued_count"] == 15
    assert len(result["stdout"]) > 5000
    assert result["stdout_tail"].endswith("}\n")


def test_main_parses_large_summary_and_invokes_multimodel_probe_without_silent_nulls():
    m = load_module()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        tick = root / "tick.py"
        mm = root / "mm.py"
        state = root / "state.json"
        log = root / "log.jsonl"
        lock = root / "lock.pid"
        payload = {
            "padding": "x" * 5000,
            "status": "OK",
            "next_task_id": "task-123",
            "dispatchable": True,
            "error_count": 0,
            "reconcile_action_count": 0,
            "ingested_count": 0,
            "multimodel_intervention": {"intervention_required": True, "task_id": "mm-task", "queued_count": 15},
        }
        tick.write_text("import json\nprint(json.dumps(%r))\n" % payload, encoding="utf-8")
        mm.write_text("print('{\"status\":\"OK\",\"action\":\"started_worker\"}')\n", encoding="utf-8")
        m.TICK = tick
        m.MM_DYNAMIC = mm
        m.STATE = state
        m.LOG = log
        m.LOCK = lock
        with contextlib.redirect_stdout(io.StringIO()):
            rc = m.main()
        assert rc == 0
        saved = json.loads(state.read_text(encoding="utf-8"))
        assert saved["last_summary"]["status"] == "OK"
        assert saved["last_summary"]["next_task_id"] == "task-123"
        event = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
        assert event["summary"]["status"] == "OK"
        assert event["summary"]["next_task_id"] == "task-123"
        assert event["multimodel_dynamic"]["returncode"] == 0


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
    print(f"PASS {len(tests)} tests")
