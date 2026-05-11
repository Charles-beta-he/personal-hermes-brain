#!/usr/bin/env python3
"""Regression tests for structured post-session tool failure aggregation."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "post-session-autopsy.py"


def load_module():
    spec = importlib.util.spec_from_file_location("post_session_autopsy", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestPostSessionAutopsy(unittest.TestCase):
    def test_detect_tool_failures_extracts_structured_signature(self):
        mod = load_module()
        messages = [
            {"role": "assistant", "tool_calls": [{"function": {"name": "terminal"}}]},
            {"role": "tool", "content": json.dumps({"exit_code": 124, "error": "Command timed out after 600s", "output": "partial"})},
        ]
        failures = mod.detect_tool_failures(messages)
        self.assertEqual(len(failures), 1)
        failure = failures[0]
        self.assertEqual(failure["tool_name"], "terminal")
        self.assertEqual(failure["tool"], "terminal")
        self.assertEqual(failure["exit_code"], 124)
        self.assertEqual(failure["error_signature"], "timeout")
        self.assertIn("stderr_tail", failure)

    def test_detect_tool_failures_extracts_module_not_found_signature(self):
        mod = load_module()
        messages = [
            {"role": "assistant", "tool_calls": [{"function": {"name": "terminal"}}]},
            {"role": "tool", "content": json.dumps({"exit_code": 1, "error": "ModuleNotFoundError: No module named 'yaml'"})},
        ]
        failures = mod.detect_tool_failures(messages)
        self.assertEqual(failures[0]["error_signature"], "module_not_found")

    def test_analyze_session_emits_failure_groups_for_tool_failures_signal(self):
        mod = load_module()
        session = {
            "session_id": "s1",
            "session_start": "2026-05-06T00:00:00",
            "messages": [
                {"role": "assistant", "tool_calls": [{"function": {"name": "terminal"}}]},
                {"role": "tool", "content": json.dumps({"exit_code": 124, "error": "Command timed out after 600s"})},
                {"role": "assistant", "tool_calls": [{"function": {"name": "terminal"}}]},
                {"role": "tool", "content": json.dumps({"exit_code": 124, "error": "Command timed out after 600s"})},
                {"role": "assistant", "tool_calls": [{"function": {"name": "read_file"}}]},
                {"role": "tool", "content": json.dumps({"exit_code": 1, "error": "File not found"})},
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "session_test.json"
            path.write_text(json.dumps(session))
            result = mod.analyze_session(str(path), path.name)
        signal = next(s for s in result["signals"] if s["type"] == "tool_failures")
        self.assertIn("failure_groups", signal)
        self.assertEqual(signal["failure_groups"][0]["tool_name"], "terminal")
        self.assertEqual(signal["failure_groups"][0]["error_signature"], "timeout")
        self.assertEqual(signal["failure_groups"][0]["count"], 2)
        self.assertIn("terminal/timeout", signal["detail"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
