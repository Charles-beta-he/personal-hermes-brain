#!/usr/bin/env python3
"""Tests for claim_guard_wrapper.py cron/subagent governance wrapper."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "claim_guard_wrapper.py"
spec = importlib.util.spec_from_file_location("claim_guard_wrapper", SCRIPT)
wrapper = importlib.util.module_from_spec(spec)
import sys
sys.modules["claim_guard_wrapper"] = wrapper
spec.loader.exec_module(wrapper)


class ClaimGuardWrapperTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_home = os.environ.get("HERMES_EVOLUTION_HOME")
        os.environ["HERMES_EVOLUTION_HOME"] = str(Path(self.tmp.name) / "evolution")

    def tearDown(self):
        if self.old_home is None:
            os.environ.pop("HERMES_EVOLUTION_HOME", None)
        else:
            os.environ["HERMES_EVOLUTION_HOME"] = self.old_home
        self.tmp.cleanup()

    def test_wrapper_claims_task_and_validates_budget_envelope(self):
        result = wrapper.prepare_guarded_run("cron:brain-hourly-sync", "cron", {"hop_count": 0, "max_hops": 1, "spent_tokens": 10, "max_tokens": 100, "spent_usd": 0, "max_usd": 1, "tool_calls": 1, "max_tool_calls": 5, "elapsed_seconds": 1, "max_wall_seconds": 60})
        self.assertTrue(result["ok"])
        self.assertEqual(result["mailbox_envelope"]["schema"], "hermes_typed_mailbox_envelope_v1")
        self.assertEqual(result["budget"]["action"], "proceed")

    def test_wrapper_blocks_duplicate_active_claim(self):
        envelope = {"hop_count": 0, "max_hops": 1, "spent_tokens": 10, "max_tokens": 100, "spent_usd": 0, "max_usd": 1, "tool_calls": 1, "max_tool_calls": 5, "elapsed_seconds": 1, "max_wall_seconds": 60}
        first = wrapper.prepare_guarded_run("subagent:task", "agent-a", envelope)
        second = wrapper.prepare_guarded_run("subagent:task", "agent-b", envelope)
        self.assertTrue(first["ok"])
        self.assertFalse(second["ok"])
        self.assertEqual(second["reason"], "claim_blocked")


if __name__ == "__main__":
    unittest.main()
