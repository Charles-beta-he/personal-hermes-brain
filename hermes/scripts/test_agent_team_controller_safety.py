#!/usr/bin/env python3
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path.home() / ".hermes" / "scripts"
sys.path.insert(0, str(SCRIPTS))
SCRIPT = SCRIPTS / "agent_team_controller.py"


def load_module():
    spec = importlib.util.spec_from_file_location("agent_team_controller_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeCompleted:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


class AgentTeamControllerSafetyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ctrl = load_module()
        self.ctrl.PROOF_DIR = Path(self.tmp.name) / "proofs"

    def tearDown(self):
        self.tmp.cleanup()

    def test_verify_with_models_rejects_non_string_worker_output_without_crashing(self):
        result = self.ctrl.verify_with_models(
            "task title",
            {"status": "done", "summary": "dict proof is not worker output text"},
            {"display_name": "Test", "acceptance": []},
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["models_checked"], 0)
        self.assertTrue(any("worker_output" in issue for issue in result["issues"]))

    def test_verify_with_models_accepts_project_name_by_loading_profile(self):
        with patch.object(self.ctrl, "load_project_profile", return_value={"display_name": "Loaded", "acceptance": []}) as load_profile:
            with patch("subprocess.run", return_value=FakeCompleted('{"verified": true, "issues": [], "reasoning": "ok"}')):
                with patch.dict("os.environ", {}, clear=True):
                    result = self.ctrl.verify_with_models("task", "worker output", "some-project")

        load_profile.assert_called_once_with("some-project")
        # Only GPT/Claude were mocked as available; DeepSeek/MiMo missing keys keep
        # the 4-model gate fail-closed rather than certifying with a partial quorum.
        self.assertFalse(result["passed"])
        self.assertEqual(result["models_checked"], 4)
        self.assertTrue(any("XIAOMI_API_KEY missing" in e for e in result.get("model_errors", [])))
        self.assertTrue(any("DEEPSEEK_API_KEY missing" in e for e in result.get("model_errors", [])))

    def test_delegate_worker_invalid_proof_is_not_done(self):
        bad_output = "work happened\nPROOF_JSON: {not json}\n"
        with patch.object(self.ctrl, "can_continue", return_value=(False, 0)):
            with patch("subprocess.run", return_value=FakeCompleted(bad_output)):
                result = self.ctrl.delegate_to_worker(
                    {"title": "task", "id": "task-1", "project": "p", "parallel_boundary": "b"},
                    "group",
                    "envelope-id",
                )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "invalid_proof")

    def test_delegate_worker_without_proof_is_not_done_no_proof(self):
        output = "I think this is complete but forgot the required proof."
        with patch.object(self.ctrl, "can_continue", return_value=(False, 0)):
            with patch("subprocess.run", return_value=FakeCompleted(output)):
                result = self.ctrl.delegate_to_worker(
                    {"title": "task", "id": "task-1", "project": "p", "parallel_boundary": "b"},
                    "group",
                    "envelope-id",
                )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "missing_proof")
        self.assertIn("output", result)


if __name__ == "__main__":
    unittest.main()
