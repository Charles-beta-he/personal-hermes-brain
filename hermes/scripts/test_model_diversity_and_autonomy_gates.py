#!/usr/bin/env python3
"""Regression tests for model diversity and autonomy fail-closed gates."""

import contextlib
import importlib.util
import io
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).parent


def load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


model_diversity = load_script("model_diversity_monitor", SCRIPTS / "model-diversity-monitor.py")
autonomy = load_script("autonomy_precondition", SCRIPTS / "autonomy-precondition.py")
write_guard = load_script("autonomy_write_guard", SCRIPTS / "autonomy-write-guard.py")


class ModelDiversityGateTests(unittest.TestCase):
    def _db(self, rows):
        td = tempfile.TemporaryDirectory()
        path = Path(td.name) / "route_outcomes.db"
        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE route_outcomes (id INTEGER PRIMARY KEY, ts TEXT, model_chain TEXT, verdict TEXT, route TEXT)"
        )
        conn.executemany(
            "INSERT INTO route_outcomes (ts, model_chain, verdict, route) VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        conn.close()
        self.addCleanup(td.cleanup)
        return path

    def _run_monitor(self, db_path, argv):
        old = model_diversity.DB_PATH
        model_diversity.DB_PATH = str(db_path)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                code = model_diversity.monitor(argv)
        finally:
            model_diversity.DB_PATH = old
        return code, buf.getvalue()

    def test_gate_fails_closed_when_one_model_dominates_window(self):
        rows = [
            (f"2026-05-09T00:{i % 60:02d}:00Z", json.dumps(["gpt-5.5"]), "pass", "probe:smoke")
            for i in range(100)
        ]
        db = self._db(rows)
        code, out = self._run_monitor(db, ["--json", "--gate", "--threshold", "0.8", "--window", "100"])
        data = json.loads(out)
        self.assertEqual(code, 2)
        self.assertTrue(data["dominance_warning"])
        self.assertTrue(data["gate_failed"])
        self.assertEqual(data["dominant_model"], "gpt-5.5")
        self.assertEqual(data["dominant_share"], 1.0)

    def test_gate_passes_for_balanced_multi_model_usage_without_route_convergence(self):
        rows = []
        for model in ["gpt-5.5", "deepseek-v4-pro", "mimo-v2.5-pro", "claude-opus-4-7"]:
            for i in range(25):
                rows.append((f"2026-05-09T01:{i:02d}:00Z", json.dumps([model]), "pass", f"route:{model}"))
        db = self._db(rows)
        code, out = self._run_monitor(db, ["--json", "--gate", "--threshold", "0.8", "--window", "100"])
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertFalse(data["dominance_warning"])
        self.assertFalse(data["gate_failed"])
        self.assertEqual(data["dominant_share"], 0.25)


class AutonomyPreconditionGateTests(unittest.TestCase):
    @staticmethod
    def _ok_check(name):
        return {"name": name, "ok": True}

    @staticmethod
    def _bad_check(name):
        return {"name": name, "ok": False}

    def _run_gate(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = autonomy.main(argv)
        return code, json.loads(buf.getvalue())

    @patch.object(autonomy, "check_p10", return_value={"name": "p10_health", "ok": True})
    def test_dispatch_hint_requires_only_p10_health(self, _p10):
        code, data = self._run_gate(["--mode", "dispatch-hint"])
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["required_checks"], ["p10_health"])

    @patch.object(autonomy, "check_p10", return_value={"name": "p10_health", "ok": True})
    def test_dispatch_hint_accepts_json_gate_flags_for_cli_consistency(self, _p10):
        code, data = self._run_gate(["--mode", "dispatch-hint", "--json", "--gate"])
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["required_checks"], ["p10_health"])

    @patch.object(autonomy, "check_router_readiness", return_value={"name": "router_readiness", "ok": False})
    @patch.object(autonomy, "check_quota", return_value={"name": "quota_confidence", "ok": False})
    @patch.object(autonomy, "check_diversity", return_value={"name": "model_diversity_gate", "ok": False})
    @patch.object(autonomy, "check_p10", return_value={"name": "p10_health", "ok": True})
    def test_budget_handoff_fails_closed_on_diversity_quota_or_router(self, _p10, _div, _quota, _router):
        code, data = self._run_gate(["--mode", "budget-handoff"])
        self.assertEqual(code, 2)
        self.assertEqual(data["status"], "FAIL_CLOSED")
        self.assertEqual(data["failed_required_checks"], ["model_diversity_gate", "quota_confidence", "router_readiness"])

    @patch.object(autonomy, "check_enable_file", return_value={"name": "explicit_autonomy_enable_file", "ok": False})
    @patch.object(autonomy, "check_router_readiness", return_value={"name": "router_readiness", "ok": True})
    @patch.object(autonomy, "check_quota", return_value={"name": "quota_confidence", "ok": True})
    @patch.object(autonomy, "check_diversity", return_value={"name": "model_diversity_gate", "ok": True})
    @patch.object(autonomy, "check_p10", return_value={"name": "p10_health", "ok": True})
    def test_autonomous_execution_requires_explicit_enable_file(self, _p10, _div, _quota, _router, _enable):
        code, data = self._run_gate(["--mode", "autonomous-execution"])
        self.assertEqual(code, 2)
        self.assertEqual(data["status"], "FAIL_CLOSED")
        self.assertEqual(data["failed_required_checks"], ["explicit_autonomy_enable_file"])


class AutonomyWriteGuardTests(unittest.TestCase):
    @patch.object(write_guard, "run_precondition", return_value={"ok": True, "data": {"status": "PASS"}, "returncode": 0})
    def test_dry_run_known_surface_allows_dispatch_hint_only(self, _pre):
        with tempfile.TemporaryDirectory() as td:
            result = write_guard.evaluate("goal", "dry-run", "dispatch-hint", Path(td) / "missing.json")
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "PASS")

    @patch.object(write_guard, "run_precondition", return_value={"ok": True, "data": {"status": "PASS"}, "returncode": 0})
    def test_write_requires_explicit_allowlist_even_when_precondition_passes(self, _pre):
        with tempfile.TemporaryDirectory() as td:
            result = write_guard.evaluate("teams", "write", "budget-handoff", Path(td) / "missing.json")
        self.assertFalse(result["ok"])
        self.assertIn("surface_allowlisted", result["failed_required_checks"])

    @patch.object(write_guard, "run_precondition", return_value={"ok": False, "data": {"status": "FAIL_CLOSED"}, "returncode": 2})
    def test_write_fails_closed_when_autonomy_precondition_fails(self, _pre):
        with tempfile.TemporaryDirectory() as td:
            allow = Path(td) / "allow.json"
            allow.write_text(json.dumps(["google-workspace"]), encoding="utf-8")
            result = write_guard.evaluate("google-workspace", "write", "budget-handoff", allow)
        self.assertFalse(result["ok"])
        self.assertIn("autonomy_precondition", result["failed_required_checks"])

    @patch.object(write_guard, "run_precondition", return_value={"ok": False, "data": {"status": "FAIL_CLOSED"}, "returncode": 2})
    def test_guard_or_raise_exposes_fail_closed_evidence_to_callers(self, _pre):
        with tempfile.TemporaryDirectory() as td:
            allow = Path(td) / "allow.json"
            allow.write_text(json.dumps(["goal"]), encoding="utf-8")
            with self.assertRaises(PermissionError) as cm:
                write_guard.guard_or_raise("goal", "write", "budget-handoff", allow)
        data = json.loads(str(cm.exception))
        self.assertEqual(data["status"], "FAIL_CLOSED")
        self.assertIn("autonomy_precondition", data["failed_required_checks"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
