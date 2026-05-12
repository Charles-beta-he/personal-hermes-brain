#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path.home() / ".hermes" / "scripts" / "post-session-autopsy.py"


def load_module():
    spec = importlib.util.spec_from_file_location("post_session_autopsy", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PostSessionAutopsyBudgetTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()

    def test_detects_iteration_budget_saturation_message(self):
        messages = [
            {"role": "assistant", "content": "working..."},
            {
                "role": "user",
                "content": "You've reached the maximum number of tool-calling iterations allowed. Please provide a final response.",
            },
        ]
        events = self.mod.detect_iteration_budget_events(messages)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["classification"], "control_system_saturation")
        self.assertEqual(events[0]["recommended_loop"], "bounded_tick_handoff_then_resume")

    def test_analyze_session_emits_high_priority_budget_signal(self):
        session = {
            "session_id": "budget-fixture",
            "session_start": "2026-05-12T00:00:00Z",
            "model": "gpt-5.5",
            "platform": "cli",
            "messages": [
                {"role": "user", "content": "继续完成工具上限导致的问题"},
                {"role": "assistant", "content": "Iteration budget reached (60/60) — response may be incomplete"},
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "session.json"
            path.write_text(json.dumps(session), encoding="utf-8")
            result = self.mod.analyze_session(str(path), "session.json")
        self.assertEqual(result["iteration_budget_count"], 2)
        signals = {s["type"]: s for s in result["signals"]}
        self.assertIn("iteration_budget_saturation", signals)
        self.assertEqual(signals["iteration_budget_saturation"]["severity"], "high")
        self.assertIn("control_system_saturation", signals["iteration_budget_saturation"]["classification"])

    def test_user_correction_language_includes_jie_chu_and_self_correction(self):
        messages = [
            {"role": "assistant", "content": "已完成。"},
            {"role": "user", "content": "这种我揪出来的问题是否会触发错误分类与复盘循环？双环学习与自我修正是否正确触发？"},
        ]
        corrections = self.mod.detect_corrections(messages)
        self.assertEqual(len(corrections), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
