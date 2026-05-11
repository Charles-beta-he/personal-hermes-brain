#!/usr/bin/env python3
"""Tests for multi-model-smoke-safe.py bounded cron wrapper."""

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "multi-model-smoke-safe.py"


def load_module():
    spec = importlib.util.spec_from_file_location("multi_model_smoke_safe", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestMultiModelSmokeSafe(unittest.TestCase):
    def test_partial_fail_is_recorded_but_wrapper_exits_ok(self):
        """A smoke script returning 2 should become auditable JSON, not a cron failure."""
        mod = load_module()
        with tempfile.TemporaryDirectory(prefix="smoke-safe-test-") as td:
            fake = Path(td) / "fake-smoke.py"
            log = Path(td) / "safe.jsonl"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import json, sys\n"
                "print(json.dumps({'model':'gpt-5.5','ok':True}))\n"
                "print(json.dumps({'status':'partial_fail','models':3,'passed':1}))\n"
                "sys.exit(2)\n"
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            result = mod.run_smoke(script=str(fake), script_args=[], timeout_s=5, log_file=str(log))
            self.assertEqual(result["status"], "partial_fail_recorded")
            self.assertEqual(result["returncode"], 2)
            self.assertFalse(result["ok"])
            self.assertEqual(result["summary"].get("passed"), 1)
            self.assertTrue(log.exists())

    def test_timeout_kills_process_tree_and_outputs_json(self):
        """Cron-safe wrapper must not idle beyond its own timeout."""
        with tempfile.TemporaryDirectory(prefix="smoke-safe-test-") as td:
            fake = Path(td) / "slow-smoke.py"
            log = Path(td) / "safe.jsonl"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import subprocess, time\n"
                "subprocess.Popen(['python3','-c','import time; time.sleep(30)'])\n"
                "time.sleep(30)\n"
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            r = subprocess.run(
                [sys.executable, str(SCRIPT), "--script", str(fake), "--timeout", "1", "--log-file", str(log)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            self.assertEqual(r.returncode, 0)
            payload = json.loads(r.stdout)
            self.assertEqual(payload["status"], "timeout_recorded")
            self.assertTrue(r.stdout.strip())

    def test_script_args_are_forwarded(self):
        """Cron script field can pass --skip-claude/--timeout through to smoke script."""
        mod = load_module()
        with tempfile.TemporaryDirectory(prefix="smoke-safe-test-") as td:
            fake = Path(td) / "args-smoke.py"
            log = Path(td) / "safe.jsonl"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import json, sys\n"
                "print(json.dumps({'argv': sys.argv[1:]}))\n"
                "print(json.dumps({'status':'pass','models':1,'passed':1}))\n"
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            result = mod.run_smoke(script=str(fake), script_args=["--skip-claude", "--timeout", "45"], timeout_s=5, log_file=str(log))
            self.assertEqual(result["status"], "ok")
            self.assertIn("--skip-claude", result["records"][0]["argv"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
