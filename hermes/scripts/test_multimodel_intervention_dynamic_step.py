#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import sys
import tempfile
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


def test_run_preserves_full_stdout_for_large_dry_run_json():
    m = load_module()
    payload = {
        "padding": "x" * 9000,
        "intervention_required": True,
        "selected_task_id": "mm-task",
        "queued_count": 15,
        "convergence": {"pending_ids": ["a", "b"], "multimodel_passed": 4, "multimodel_triggered": 15},
    }
    code = "import json; print(json.dumps(%r))" % payload
    result = m.run([sys.executable, "-c", code], timeout=10)
    parsed = m.parse_json(result["stdout"])
    assert parsed["intervention_required"] is True
    assert parsed["queued_count"] == 15
    assert parsed["selected_task_id"] == "mm-task"
    assert len(result["stdout"]) > 9000
    assert result["stdout_tail"].endswith("}\n")


def test_main_starts_worker_from_large_dry_run_json_without_truncation():
    m = load_module()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        orch = root / "orch.py"
        state_dir = root / "state"
        log = root / "log.jsonl"
        payload = {
            "padding": "x" * 9000,
            "intervention_required": True,
            "selected_task_id": "mm-task",
            "queued_count": 15,
            "convergence": {"pending_ids": ["a", "b"], "multimodel_passed": 4, "multimodel_triggered": 15},
        }
        orch.write_text("import json\nprint(json.dumps(%r))\n" % payload, encoding="utf-8")
        m.ORCH = orch
        m.STATE_DIR = state_dir
        m.STATE = state_dir / "state.json"
        m.PID = state_dir / "worker.pid"
        m.LOG = log
        m.start_worker = lambda max_workers: 4242
        old_argv = sys.argv[:]
        try:
            sys.argv = ["multimodel_intervention_dynamic_step.py", "--json", "--cooldown-seconds", "0"]
            with contextlib.redirect_stdout(io.StringIO()):
                rc = m.main()
        finally:
            sys.argv = old_argv
        assert rc == 0
        event = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
        assert event["action"] == "started_worker"
        assert event["selected_task_id"] == "mm-task"
        assert event["queued_count"] == 15


def test_main_fails_closed_on_unparseable_dry_run_stdout():
    m = load_module()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        orch = root / "orch.py"
        state_dir = root / "state"
        log = root / "log.jsonl"
        orch.write_text("print('not-json-but-success')\n", encoding="utf-8")
        m.ORCH = orch
        m.STATE_DIR = state_dir
        m.STATE = state_dir / "state.json"
        m.PID = state_dir / "worker.pid"
        m.LOG = log
        old_argv = sys.argv[:]
        try:
            sys.argv = ["multimodel_intervention_dynamic_step.py", "--json"]
            with contextlib.redirect_stdout(io.StringIO()):
                rc = m.main()
        finally:
            sys.argv = old_argv
        assert rc == 2
        event = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
        assert event["status"] == "ERROR"
        assert event["action"] == "dry_run_parse_failed"
        assert event["queued_count"] == -1


def test_worker_summary_preserves_parseable_result_before_log_compaction():
    m = load_module()
    payload = {
        "status": "OK",
        "padding": "x" * 9000,
        "tasks_processed": 1,
        "tasks_passed": 1,
        "tasks_failed": 0,
        "tasks_errors": 0,
        "results": [{"task_id": "task-a", "gate": {"status": "PASS", "decision": "LOOP_DONE"}}],
        "convergence": {"multimodel_passed": 5, "pending_ids": ["task-b"]},
    }
    result = m.with_output_tails({"cmd": ["fake"], "returncode": 0, "stdout": json.dumps(payload), "stderr": ""})
    compact = m.compact_result(result)
    assert m.parse_json(compact["stdout"]) == {}  # compact stdout may be only a tail slice
    summary = m.summarize_worker_result(result)
    assert summary["status"] == "OK"
    assert summary["tasks_passed"] == 1
    assert summary["task_ids"] == ["task-a"]
    assert summary["gate_statuses"] == ["PASS"]
    assert summary["decisions"] == ["LOOP_DONE"]


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
    print(f"PASS {len(tests)} tests")
