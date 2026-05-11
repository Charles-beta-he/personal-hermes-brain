#!/usr/bin/env python3
"""Tests for iteration budget doctor and bounded tick helpers."""
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


doctor = load_module("iteration_budget_doctor", ROOT / "iteration_budget_doctor.py")
budget_tick = load_module("brain_task_budget_tick", ROOT / "brain_task_budget_tick.py")


class IterationBudgetGuardTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "hermes"
        self.vault = Path(self.tmp.name) / "brain"
        (self.home / "logs").mkdir(parents=True)
        (self.home / "cron").mkdir(parents=True)
        (self.vault / "05-实践与项目" / "tasks").mkdir(parents=True)
        (self.home / "config.yaml").write_text(
            "agent:\n  max_turns: 60\ndelegation:\n  max_iterations: 50\ncompression:\n  enabled: true\n  threshold: 0.6\n",
            encoding="utf-8",
        )
        (self.home / ".env").write_text("HERMES_MAX_ITERATIONS=999\nOPENAI_API_KEY=SECRET_SHOULD_NOT_APPEAR\n", encoding="utf-8")
        (self.home / "logs" / "run.log").write_text("Iteration budget reached (60/60) — response may be incomplete\n", encoding="utf-8")
        (self.home / "cron" / "jobs.json").write_text(
            json.dumps(
                {
                    "jobs": [
                        {"id": "a", "name": "agent job", "enabled": True, "state": "scheduled", "prompt": "summarize", "script": "x.py"},
                        {"id": "b", "name": "safe tick", "enabled": True, "state": "scheduled", "script": "tick.py", "no_agent": True},
                    ]
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_doctor_redacts_env_values_and_counts_hits(self):
        config = doctor.load_yamlish_config(self.home / "config.yaml")
        warnings = doctor.scan_warning_hits(self.home, max_files=10, max_hits=5)
        cron = doctor.cron_summary(self.home)
        env = doctor.env_presence(self.home)
        self.assertEqual(config["agent"]["max_turns"], 60)
        self.assertEqual(warnings["hit_count"], 1)
        self.assertEqual(cron["job_count"], 2)
        self.assertEqual(cron["no_agent_count"], 1)
        rendered = json.dumps(env)
        self.assertIn("OPENAI_API_KEY", rendered)
        self.assertNotIn("SECRET_SHOULD_NOT_APPEAR", rendered)

    def test_budget_tick_classification_and_budget_stop(self):
        row = {"id": "task-a", "title": "删除生产凭证", "priority": "P0", "status": "pending", "project": "danger"}
        cls = budget_tick.classify_mode(row, "auto")
        self.assertEqual(cls["risk"], "high")
        self.assertFalse(cls["allowed_for_auto_claim"])
        b = budget_tick.compute_budget({"budget": {"agent_max_turns": 60}}, spent_tool_calls=50, max_tool_calls=60, safety_margin=12)
        self.assertEqual(b["action"], "stop_and_handoff")
        self.assertLessEqual(b["remaining_before_handoff"], 0)

    def test_budget_tick_proceed_for_low_risk(self):
        row = {"id": "task-b", "title": "read-only audit", "priority": "P2", "status": "pending", "project": "audit"}
        cls = budget_tick.classify_mode(row, "auto")
        b = budget_tick.compute_budget({"budget": {"agent_max_turns": 60}}, spent_tool_calls=5, max_tool_calls=45, safety_margin=12)
        self.assertEqual(cls["risk"], "low")
        self.assertTrue(cls["allowed_for_auto_claim"])
        self.assertEqual(b["action"], "proceed_bounded")


if __name__ == "__main__":
    unittest.main()
