#!/usr/bin/env python3
"""Tests for code_evidence_gate.py dry-run GitNexus-inspired evidence primitives."""

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "code_evidence_gate.py"
spec = importlib.util.spec_from_file_location("code_evidence_gate", SCRIPT)
code_evidence_gate = importlib.util.module_from_spec(spec)
import sys
sys.modules["code_evidence_gate"] = code_evidence_gate
spec.loader.exec_module(code_evidence_gate)


class CodeEvidenceGateTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.run(["git", "init"], cwd=self.root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        (self.root / "app.py").write_text("def hello():\n    return 'hi'\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.indexed_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()

    def tearDown(self):
        self.tmp.cleanup()

    def test_code_evidence_schema_reports_freshness_and_target(self):
        data = code_evidence_gate.build_code_evidence(self.root, "app.py", indexed_commit=self.indexed_commit)
        self.assertEqual(data["schema"], "code_evidence_v1")
        self.assertEqual(data["target_type"], "file")
        self.assertEqual(data["target_id"], "app.py")
        self.assertFalse(data["stale"])
        self.assertEqual(data["truth_gate"], "certified_dry_run")

    def test_stale_index_gate_marks_needs_reindex_after_head_changes(self):
        (self.root / "app.py").write_text("def hello():\n    return 'bye'\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-m", "change"], cwd=self.root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = code_evidence_gate.build_code_evidence(self.root, "app.py", indexed_commit=self.indexed_commit)
        self.assertTrue(data["stale"])
        self.assertEqual(data["truth_gate"], "not_certified_needs_reindex")

    def test_detect_changes_before_commit_reports_unexpected_changes(self):
        (self.root / "extra.txt").write_text("unexpected\n", encoding="utf-8")
        result = code_evidence_gate.detect_changes_before_commit(self.root, expected=["app.py"])
        self.assertIn("extra.txt", result["unexpected_changes"])
        self.assertEqual(result["action"], "block_completion_claim")

    def test_shape_check_contract_ledger_and_rrf_merge(self):
        shape = code_evidence_gate.shape_check({"name": "brainctl", "schema": {"type": "object"}}, required=["name", "schema"])
        self.assertTrue(shape["ok"])
        contract = code_evidence_gate.contract_id("cli", "brainctl.py", "validate")
        self.assertEqual(contract, "cli::brainctl.py::validate")
        fused = code_evidence_gate.rrf_merge([["a", "b"], ["b", "c"]], k=60)
        self.assertEqual(fused[0]["id"], "b")
        self.assertNotIn("truth", fused[0])


if __name__ == "__main__":
    unittest.main()
