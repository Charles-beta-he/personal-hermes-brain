#!/usr/bin/env python3
"""Tests for long_evolution_guard.py governance primitives."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("long_evolution_guard.py")


def load_guard():
    spec = importlib.util.spec_from_file_location("long_evolution_guard", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["long_evolution_guard"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class LongEvolutionGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "hermes"
        self.root.mkdir()
        (self.root / "scripts").mkdir()
        (self.root / "skills" / "alpha").mkdir(parents=True)
        (self.root / "scripts" / "brainctl.py").write_text("#!/usr/bin/env python3\ndef main():\n    return 0\n", encoding="utf-8")
        (self.root / "scripts" / "anti_drift_guard.py").write_text("#!/usr/bin/env python3\nclass Guard:\n    pass\n", encoding="utf-8")
        (self.root / "skills" / "alpha" / "SKILL.md").write_text("---\nname: alpha\n---\n# Alpha\n", encoding="utf-8")
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir()
        os.environ["HERMES_HOME"] = str(self.root)
        os.environ["HERMES_EVOLUTION_HOME"] = str(self.home)
        if SCRIPT.exists():
            self.guard = load_guard()

    def tearDown(self):
        os.environ.pop("HERMES_HOME", None)
        os.environ.pop("HERMES_EVOLUTION_HOME", None)
        self.tmp.cleanup()

    def cli(self, *args, check=True):
        proc = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if check and proc.returncode != 0:
            raise AssertionError(f"command failed {proc.returncode}\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}")
        return proc

    def json_cli(self, *args, check=True):
        proc = self.cli(*args, check=check)
        return json.loads(proc.stdout), proc

    def test_inventory_records_scripts_skills_hashes_and_markers(self):
        guard = load_guard()
        inv = guard.build_inventory(self.root)
        self.assertEqual(inv["schema"], "hermes_capability_inventory_v1")
        by_path = {c["path"]: c for c in inv["capabilities"]}
        self.assertIn("scripts/brainctl.py", by_path)
        self.assertIn("skills/alpha/SKILL.md", by_path)
        self.assertEqual(len(by_path["scripts/brainctl.py"]["sha256"]), 64)
        self.assertIn("main", by_path["scripts/brainctl.py"]["markers"])
        self.assertEqual(by_path["skills/alpha/SKILL.md"]["type"], "skill")

    def test_witness_verify_passes_then_detects_tamper(self):
        data, _ = self.json_cli("witness", "--out", str(self.home / "witness.json"))
        self.assertTrue(data["ok"])
        self.assertEqual(data["schema"], "hermes_capability_witness_v1")
        self.assertEqual(len(data["manifest_hash"]), 64)
        self.assertTrue((self.home / "witness.key").exists())
        verify, _ = self.json_cli("verify", "--witness", str(self.home / "witness.json"))
        self.assertTrue(verify["passed"])
        (self.root / "scripts" / "new_tool.py").write_text("#!/usr/bin/env python3\ndef main():\n    return 0\n", encoding="utf-8")
        verify, proc = self.json_cli("verify", "--witness", str(self.home / "witness.json"), "--exit-code", check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(verify["passed"])
        self.assertIn("inventory_drift", {v["type"] for v in verify["violations"]})
        self.assertIn("added_capability", {v["type"] for v in verify["violations"]})
        (self.root / "scripts" / "new_tool.py").unlink()
        (self.root / "scripts" / "brainctl.py").write_text("#!/usr/bin/env python3\ndef main():\n    return 1\n", encoding="utf-8")
        verify, proc = self.json_cli("verify", "--witness", str(self.home / "witness.json"), "--exit-code", check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(verify["passed"])
        self.assertIn("hash_mismatch", {v["type"] for v in verify["violations"]})

    def test_claim_ledger_blocks_duplicate_active_claim_and_allows_release(self):
        first, _ = self.json_cli("claim", "--task", "T-1", "--owner", "agent-a", "--ttl", "60")
        self.assertTrue(first["ok"])
        second, proc = self.json_cli("claim", "--task", "T-1", "--owner", "agent-b", "--ttl", "60", "--exit-code", check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(second["ok"])
        self.assertEqual(second["reason"], "active_claim_exists")
        proc = self.cli("release", "--task", "T-1", check=False)
        self.assertNotEqual(proc.returncode, 0)
        released, _ = self.json_cli("release", "--task", "T-1", "--owner", "agent-a")
        self.assertTrue(released["ok"])
        third, _ = self.json_cli("claim", "--task", "T-1", "--owner", "agent-b", "--ttl", "60")
        self.assertTrue(third["ok"])
        self.assertEqual(third["claim"]["owner"], "agent-b")
        ledger, _ = self.json_cli("ledger-verify")
        self.assertTrue(ledger["passed"])
        self.assertGreaterEqual(ledger["checked_events"], 3)

    def test_handoff_transfers_active_claim_and_records_lineage(self):
        self.json_cli("claim", "--task", "T-2", "--owner", "architect", "--ttl", "60")
        data, _ = self.json_cli("handoff", "--task", "T-2", "--from-owner", "architect", "--to-owner", "coder", "--ttl", "60")
        self.assertTrue(data["ok"])
        status, _ = self.json_cli("claim-status", "--task", "T-2")
        self.assertEqual(status["claim"]["owner"], "coder")
        self.assertEqual(status["claim"]["lineage"][-1]["from"], "architect")

    def test_steal_allows_expired_claim_but_blocks_active_claim(self):
        self.json_cli("claim", "--task", "T-3", "--owner", "agent-a", "--ttl", "1")
        blocked, proc = self.json_cli("steal", "--task", "T-3", "--owner", "agent-b", "--ttl", "60", "--exit-code", check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["reason"], "active_claim_exists")
        # Force expiry by updating the lease directly in the test database.
        db = self.home / "claims.sqlite"
        import sqlite3
        con = sqlite3.connect(db)
        con.execute("update claims set expires_at = 0 where task_id = ?", ("T-3",))
        con.commit(); con.close()
        stolen, _ = self.json_cli("steal", "--task", "T-3", "--owner", "agent-b", "--ttl", "60")
        self.assertTrue(stolen["ok"])
        self.assertEqual(stolen["claim"]["owner"], "agent-b")
        self.assertEqual(stolen["claim"]["lineage"][-1]["event"], "steal")

    def test_budget_check_blocks_hops_tokens_cost_toolcalls_and_walltime(self):
        guard = load_guard()
        envelope = {
            "max_hops": 3, "hop_count": 4,
            "max_tokens": 100, "spent_tokens": 101,
            "max_usd": 0.25, "spent_usd": 0.26,
            "max_tool_calls": 5, "tool_calls": 6,
            "max_wall_seconds": 10, "elapsed_seconds": 11,
        }
        result = guard.check_budget(envelope)
        self.assertFalse(result["passed"])
        self.assertEqual(result["action"], "block")
        types = {v["type"] for v in result["violations"]}
        self.assertTrue({"hop_limit_exceeded", "token_budget_exceeded", "cost_budget_exceeded", "tool_call_budget_exceeded", "walltime_budget_exceeded"} <= types)
        bad, _ = self.json_cli("budget-check", "--envelope", '{"max_hops":3,"hop_count":"NaN"}')
        self.assertFalse(bad["passed"])
        self.assertIn("missing_budget_field", {v["type"] for v in bad["violations"]})
        self.assertIn("invalid_budget_number", {v["type"] for v in bad["violations"]})

    def test_parser_exposes_only_governance_commands(self):
        guard = load_guard()
        parser = guard.build_parser()
        subparsers = next(action for action in parser._actions if action.dest == "cmd")
        commands = set(subparsers.choices)
        self.assertTrue({"inventory", "witness", "verify", "claim", "claim-status", "release", "handoff", "steal", "ledger-verify", "budget-check"} <= commands)
        self.assertFalse({"shell", "eval", "delete", "install"} & commands)


if __name__ == "__main__":
    unittest.main()
