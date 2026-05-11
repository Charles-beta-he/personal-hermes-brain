#!/usr/bin/env python3
"""Regression tests for cross-patch.py real producer/reviewer execution mode."""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("cross-patch.py")
spec = importlib.util.spec_from_file_location("cross_patch", SCRIPT)
cross_patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cross_patch)


class TestCrossPatchRealExecution(unittest.TestCase):
    """All tests in this class redirect logs/DB to tmpdir to avoid polluting
    production ~/.hermes/logs and ~/.hermes/route_outcomes.db."""

    @classmethod
    def setUpClass(cls):
        cls._iso_dir = tempfile.mkdtemp(prefix="cross-patch-real-test-")
        cls._saved_env = {}
        for k, v in {
            "CROSS_PATCH_LOG_FILE": os.path.join(cls._iso_dir, "cross-patch.jsonl"),
            "HERMES_PROTOCOL_DB_PATH": os.path.join(cls._iso_dir, "protocol.db"),
            "HERMES_ROUTE_DB_PATH": os.path.join(cls._iso_dir, "route_outcomes.db"),
        }.items():
            cls._saved_env[k] = os.environ.get(k)
            os.environ[k] = v
        cross_patch.LOG_FILE = os.environ["CROSS_PATCH_LOG_FILE"]

    @classmethod
    def tearDownClass(cls):
        import shutil as _sh
        for k, v in cls._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        _sh.rmtree(cls._iso_dir, ignore_errors=True)

    def test_run_actual_dry_run_calls_two_models_and_does_not_modify_file(self):
        with tempfile.TemporaryDirectory() as td:
            workdir = Path(td)
            target = workdir / "hello.txt"
            target.write_text("hello old world\n")
            calls = []

            def fake_call(model, prompt, *, workdir=None, timeout=120):
                calls.append((model, prompt, workdir, timeout))
                if model == "producer-model":
                    return {
                        "ok": True,
                        "model": model,
                        "provider": "test-provider",
                        "adapter": "fake",
                        "output": json.dumps({
                            "verdict": "pass",
                            "summary": "producer patch",
                            "patches": [{
                                "file": "hello.txt",
                                "original": "old",
                                "suggested": "new",
                                "severity": "major",
                                "confidence": 0.91,
                                "rationale": "replace old"
                            }]
                        })
                    }
                return {
                    "ok": True,
                    "model": model,
                    "provider": "test-provider-2",
                    "adapter": "fake",
                    "output": json.dumps({
                        "verdict": "pass",
                        "summary": "review approved",
                        "approved_patch_ids": ["test-patch-id"],
                        "patches": [{
                            "file": "hello.txt",
                            "original": "old",
                            "suggested": "new",
                            "severity": "major",
                            "confidence": 0.93,
                            "rationale": "approved"
                        }]
                    })
                }

            result = cross_patch.run_cross_patch_actual(
                task="replace old with new",
                workdir=str(workdir),
                producer_model="producer-model",
                reviewer_model="reviewer-model",
                apply=False,
                min_confidence=0.7,
                model_caller=fake_call,
            )

            self.assertEqual(result["execution_mode"], "script_actual")
            self.assertTrue(result["actual_model_calls"])
            self.assertEqual([c[0] for c in calls], ["producer-model", "reviewer-model"])
            self.assertEqual(target.read_text(), "hello old world\n")
            self.assertEqual(result["merge"]["stats"]["applied"], 1)
            self.assertIn("-hello old world", result["merge"]["diff"])
            self.assertIn("+hello new world", result["merge"]["diff"])
            self.assertFalse(result["applied"])

    def test_run_actual_apply_writes_file_after_review_approval(self):
        with tempfile.TemporaryDirectory() as td:
            workdir = Path(td)
            target = workdir / "hello.txt"
            target.write_text("hello old world\n")

            def fake_call(model, prompt, *, workdir=None, timeout=120):
                return {
                    "ok": True,
                    "model": model,
                    "provider": "test-provider",
                    "adapter": "fake",
                    "output": json.dumps({
                        "verdict": "pass",
                        "summary": "ok",
                        "patches": [{
                            "file": "hello.txt",
                            "original": "old",
                            "suggested": "new",
                            "severity": "major",
                            "confidence": 0.95,
                            "rationale": "approved"
                        }]
                    })
                }

            result = cross_patch.run_cross_patch_actual(
                task="replace old with new",
                workdir=str(workdir),
                producer_model="producer-model",
                reviewer_model="reviewer-model",
                apply=True,
                min_confidence=0.7,
                force_no_verify=True,  # test uses fake callers, no real verify
                model_caller=fake_call,
            )

            self.assertTrue(result["applied"])
            self.assertEqual(target.read_text(), "hello new world\n")
            self.assertEqual(result["verdict"], "pass")


if __name__ == "__main__":
    unittest.main(verbosity=2)
