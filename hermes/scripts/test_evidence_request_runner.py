#!/usr/bin/env python3
"""Tests for evidence_request_runner.py allowlisted evidence hydration."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "evidence_request_runner.py"
spec = importlib.util.spec_from_file_location("evidence_request_runner", SCRIPT)
evidence_request_runner = importlib.util.module_from_spec(spec)
import sys
sys.modules["evidence_request_runner"] = evidence_request_runner
spec.loader.exec_module(evidence_request_runner)


class EvidenceRequestRunnerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name) / "brain"
        self.vault.mkdir()
        (self.vault / "Note.md").write_text("# Note\n\nLocal brain evidence request runner.\n", encoding="utf-8")
        self.old_vault = os.environ.get("HERMES_BRAIN_VAULT")
        self.old_memory = os.environ.get("HERMES_MEMORY_HOME")
        os.environ["HERMES_BRAIN_VAULT"] = str(self.vault)
        os.environ["HERMES_MEMORY_HOME"] = str(Path(self.tmp.name) / "memory")

    def tearDown(self):
        if self.old_vault is None:
            os.environ.pop("HERMES_BRAIN_VAULT", None)
        else:
            os.environ["HERMES_BRAIN_VAULT"] = self.old_vault
        if self.old_memory is None:
            os.environ.pop("HERMES_MEMORY_HOME", None)
        else:
            os.environ["HERMES_MEMORY_HOME"] = self.old_memory
        self.tmp.cleanup()

    def test_runner_executes_allowlisted_search_with_budget(self):
        request = {"id": "r1", "action": "brainctl_search", "query": "Local brain", "limit": 3}
        result = evidence_request_runner.run_requests([request], budget={"max_requests": 2, "max_chars": 4000})
        self.assertTrue(result["passed"])
        self.assertEqual(result["results"][0]["status"], "ok")
        self.assertGreaterEqual(result["telemetry"]["requests_executed"], 1)
        self.assertIn("budget", result)

    def test_runner_blocks_non_allowlisted_actions_and_budget_overflow(self):
        result = evidence_request_runner.run_requests(
            [{"id": "bad", "action": "shell", "command": "date"}, {"id": "too_many", "action": "brainctl_search", "query": "x"}],
            budget={"max_requests": 1, "max_chars": 1000},
        )
        statuses = {item["status"] for item in result["results"]}
        self.assertIn("blocked", statuses)
        self.assertFalse(result["passed"])
        violation_types = {v["type"] for v in result["violations"]}
        self.assertIn("request_budget_exceeded", violation_types)
        self.assertIn("action_not_allowlisted", violation_types)


if __name__ == "__main__":
    unittest.main()
