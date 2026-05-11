#!/usr/bin/env python3
"""Tests for p10-health-safe.py bounded health wrapper."""

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "p10-health-safe.py"


def load_module():
    spec = importlib.util.spec_from_file_location("p10_health_safe", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestP10HealthSafe(unittest.TestCase):
    def test_slow_health_script_records_timeout_and_exits_zero(self):
        """A stuck p10-health.sh should be converted into auditable timeout JSON."""
        mod = load_module()
        with tempfile.TemporaryDirectory(prefix="p10-safe-test-") as td:
            slow = Path(td) / "slow-health.sh"
            log = Path(td) / "safe.jsonl"
            slow.write_text("#!/usr/bin/env bash\nsleep 3\necho '{\"V\":1}'\n")
            slow.chmod(slow.stat().st_mode | stat.S_IXUSR)
            result = mod.run_health(script=str(slow), timeout_s=1, log_file=str(log))
            self.assertEqual(result["status"], "timeout_recorded")
            self.assertEqual(result["timeout_s"], 1)
            self.assertFalse(result["ok"])
            self.assertTrue(log.exists())
            logged = json.loads(log.read_text().strip().splitlines()[-1])
            self.assertEqual(logged["status"], "timeout_recorded")

    def test_valid_json_health_script_passes_through_payload(self):
        """Valid p10-health JSON should be preserved and annotated."""
        mod = load_module()
        with tempfile.TemporaryDirectory(prefix="p10-safe-test-") as td:
            fast = Path(td) / "fast-health.sh"
            log = Path(td) / "safe.jsonl"
            fast.write_text("#!/usr/bin/env bash\nprintf '{\"V\":0.95,\"grade\":\"A\"}'\n")
            fast.chmod(fast.stat().st_mode | stat.S_IXUSR)
            result = mod.run_health(script=str(fast), timeout_s=5, log_file=str(log))
            self.assertEqual(result["status"], "ok")
            self.assertTrue(result["ok"])
            self.assertEqual(result["health"].get("V"), 0.95)
            self.assertEqual(result["health"].get("grade"), "A")

    def test_cli_always_outputs_json_even_on_timeout(self):
        """Cron callers should always receive non-empty JSON output."""
        with tempfile.TemporaryDirectory(prefix="p10-safe-test-") as td:
            slow = Path(td) / "slow-health.sh"
            log = Path(td) / "safe.jsonl"
            slow.write_text("#!/usr/bin/env bash\nsleep 3\n")
            slow.chmod(slow.stat().st_mode | stat.S_IXUSR)
            r = subprocess.run(
                [sys.executable, str(SCRIPT), "--script", str(slow), "--timeout", "1", "--log-file", str(log)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            self.assertEqual(r.returncode, 0)
            payload = json.loads(r.stdout)
            self.assertEqual(payload["status"], "timeout_recorded")
            self.assertTrue(r.stdout.strip())
    def test_cli_kills_process_tree_on_timeout(self):
        """Timeout must kill child processes too; otherwise real p10-health can hold pipes open."""
        with tempfile.TemporaryDirectory(prefix="p10-safe-test-") as td:
            slow_tree = Path(td) / "slow-tree-health.sh"
            log = Path(td) / "safe.jsonl"
            slow_tree.write_text("#!/usr/bin/env bash\npython3 -c 'import time; time.sleep(30)' &\nwait\n")
            slow_tree.chmod(slow_tree.stat().st_mode | stat.S_IXUSR)
            r = subprocess.run(
                [sys.executable, str(SCRIPT), "--script", str(slow_tree), "--timeout", "1", "--log-file", str(log)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            self.assertEqual(r.returncode, 0)
            payload = json.loads(r.stdout)
            self.assertEqual(payload["status"], "timeout_recorded")


if __name__ == "__main__":
    unittest.main(verbosity=2)
