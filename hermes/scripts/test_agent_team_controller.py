#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "agent_team_controller.py"


def load_module():
    spec = importlib.util.spec_from_file_location("agent_team_controller_under_test", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_create_proof_stub_records_book_checkpoint_contract():
    mod = load_module()
    with tempfile.TemporaryDirectory() as td:
        old_dir = mod.PROOF_DIR
        try:
            mod.PROOF_DIR = Path(td)
            task = {"id": "book-1", "title": "Task - 精读书籍：《TCP/IP详解》", "project": "learning"}
            stub = mod.create_worker_proof_stub(task, envelope_id="env-1", run_id="run-1")
            path = Path(stub["proof_stub_path"])
            assert path.exists()
            data = json.loads(path.read_text())
            assert data["schema"] == "taskpool_worker_proof_checkpoint_v1"
            assert data["task_id"] == "book-1"
            assert data["status"] == "started"
            assert data["checkpoints_required"] == ["stub", "structure_map", "concept_cards", "practice_tasks", "final_notes"]
            assert data["acceptance_preserved"] is True
        finally:
            mod.PROOF_DIR = old_dir


def test_record_worker_timeout_updates_stub_instead_of_losing_proof_context():
    mod = load_module()
    with tempfile.TemporaryDirectory() as td:
        old_dir = mod.PROOF_DIR
        try:
            mod.PROOF_DIR = Path(td)
            task = {"id": "book-2", "title": "Task - 精读书籍：《编码》", "project": "learning"}
            stub = mod.create_worker_proof_stub(task, envelope_id="env-2", run_id="run-2")
            result = mod.record_worker_timeout_checkpoint(task, envelope_id="env-2", proof_stub_path=stub["proof_stub_path"], reason="subprocess_timeout")
            data = json.loads(Path(stub["proof_stub_path"]).read_text())
            assert result["status"] == "timeout_with_proof_stub"
            assert data["status"] == "timeout"
            assert data["timeout_reason"] == "subprocess_timeout"
            assert data["partial_proof_available"] is True
            assert data["acceptance_preserved"] is True
        finally:
            mod.PROOF_DIR = old_dir


def test_validate_worker_proof_rejects_checkpoint_stub_as_completion_proof():
    mod = load_module()
    task = {"id": "book-3", "acceptance_criteria": ["结构化学习笔记"]}
    proof = {
        "schema": "taskpool_worker_proof_checkpoint_v1",
        "status": "started",
        "acceptance_preserved": True,
    }
    result = mod.validate_worker_proof_against_task(task, proof)
    assert result["status"] == "FAIL"
    assert "checkpoint_stub_is_not_completion_proof" in result["violations"]


def test_worker_routes_external_evaluation_as_analysis_even_when_hermes_is_mentioned():
    mod = load_module()
    task = {
        "id": "eval-openagents",
        "title": "评估 OpenAgents workspace-network 对 Hermes 多智能体协作与外部工作区集成的参考价值",
        "project": "hermes-agent",
    }
    assert mod._is_advisory_analysis_task(task) is True
    assert mod._worker_needs_codegen(task) is False


def test_worker_routes_explicit_hermes_implementation_as_codegen():
    mod = load_module()
    task = {
        "id": "impl-worker",
        "title": "实现 Hermes agent_team_controller worker timeout fallback 修复",
        "project": "hermes-agent",
    }
    assert mod._worker_needs_codegen(task) is True
