#!/usr/bin/env python3
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("anti_drift_guard.py")
spec = importlib.util.spec_from_file_location("anti_drift_guard", SCRIPT)
anti = importlib.util.module_from_spec(spec)
sys.modules["anti_drift_guard"] = anti
spec.loader.exec_module(anti)  # type: ignore[union-attr]


class AntiDriftGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.git_run(["git", "init", "-q"])
        self.git_run(["git", "config", "user.email", "test@example.com"])
        self.git_run(["git", "config", "user.name", "Test"])
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("print('v1')\n", encoding="utf-8")
        self.git_run(["git", "add", "."])
        self.git_run(["git", "commit", "-q", "-m", "init"])

    def tearDown(self):
        self.tmp.cleanup()

    def git_run(self, args, check=True):
        return subprocess.run(args, cwd=self.root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)

    def cli(self, *args, check=True):
        proc = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if check and proc.returncode != 0:
            raise AssertionError(f"command failed {proc.returncode}\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}")
        return proc

    def json_cli(self, *args, check=True):
        proc = self.cli(*args, check=check)
        return json.loads(proc.stdout), proc

    def test_init_creates_omc_and_anchor_lock(self):
        data, _ = self.json_cli("init", "--goal", "Ship feature without drift")
        self.assertTrue(data["ok"])
        self.assertTrue((self.root / ".omc" / "anchors" / "goal.md").exists())
        self.assertTrue((self.root / ".omc" / "anchors" / ".lock").exists())
        lock = json.loads((self.root / ".omc" / "anchors" / ".lock").read_text())
        self.assertIn(".omc/anchors/goal.md", lock["hashes"])

    def test_check_anchors_passes_then_detects_modification(self):
        self.json_cli("init", "--goal", "Immutable goal")
        data, _ = self.json_cli("check-anchors")
        self.assertTrue(data["passed"])
        (self.root / ".omc" / "anchors" / "goal.md").write_text("Changed goal\n", encoding="utf-8")
        data, proc = self.json_cli("check-anchors", "--exit-code", check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(data["passed"])
        self.assertEqual(data["violations"][0]["type"], "anchor_modified")

    def test_scope_contract_passes_for_expected_file(self):
        self.json_cli("init", "--goal", "Scope guard")
        (self.root / "src" / "app.py").write_text("print('v2')\n", encoding="utf-8")
        contract = self.root / "contract.json"
        contract.write_text(json.dumps({"expected_files": ["src/app.py"], "loc_budget": 10}), encoding="utf-8")
        data, _ = self.json_cli("scope", "--contract", str(contract))
        self.assertTrue(data["passed"])
        self.assertEqual(data["oracle"], "scope-contract")

    def test_scope_contract_blocks_unexpected_and_forbidden_files(self):
        self.json_cli("init", "--goal", "Scope guard")
        (self.root / "src" / "extra.py").write_text("print('extra')\n", encoding="utf-8")
        contract = self.root / "contract.json"
        contract.write_text(json.dumps({"expected_files": ["src/app.py"], "forbidden_globs": ["src/extra.py"]}), encoding="utf-8")
        data, proc = self.json_cli("scope", "--contract", str(contract), "--exit-code", check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(data["passed"])
        types = {v["type"] for v in data["violations"]}
        self.assertIn("unexpected_file", types)
        self.assertIn("forbidden_file", types)

    def test_scope_contract_blocks_loc_budget(self):
        self.json_cli("init", "--goal", "Scope guard")
        (self.root / "src" / "app.py").write_text("\n".join(["print('x')" for _ in range(20)]) + "\n", encoding="utf-8")
        contract = self.root / "contract.json"
        contract.write_text(json.dumps({"expected_files": ["src/app.py"], "loc_budget": 2}), encoding="utf-8")
        data, _ = self.json_cli("scope", "--contract", str(contract))
        self.assertFalse(data["passed"])
        self.assertIn("loc_budget_exceeded", {v["type"] for v in data["violations"]})

    def test_judge_truth_table_track_a_fail_blocks_even_if_track_b_passes(self):
        a = self.root / "a.json"
        b = self.root / "b.json"
        a.write_text(json.dumps({"passed": False, "severity": 7, "violations": [{"type": "scope"}]}), encoding="utf-8")
        b.write_text(json.dumps({"passed": True, "severity": 0, "violations": []}), encoding="utf-8")
        data, proc = self.json_cli("judge", "--track-a", str(a), "--track-b", str(b), "--exit-code", check=False)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(data["action"], "block")

    def test_judge_truth_table_track_b_fail_asks_user(self):
        a = self.root / "a.json"
        b = self.root / "b.json"
        a.write_text(json.dumps({"passed": True, "severity": 0, "violations": []}), encoding="utf-8")
        b.write_text(json.dumps({"passed": False, "severity": 6, "violations": [{"type": "semantic"}]}), encoding="utf-8")
        data, _ = self.json_cli("judge", "--track-a", str(a), "--track-b", str(b))
        self.assertEqual(data["action"], "ask_user")
        self.assertFalse(data["passed"])

    def test_precondition_reports_missing_anchor_lock(self):
        data, _ = self.json_cli("precondition")
        self.assertFalse(data["passed"])
        self.assertIn("missing_anchor_lock", {v["type"] for v in data["violations"]})

    def test_consult_state_from_track_a_pass_is_parseable(self):
        track = self.root / "track-a.json"
        track.write_text(json.dumps({"oracle": "scope-contract", "passed": True, "severity": 0, "violations": []}), encoding="utf-8")
        out = self.root / "state.json"
        data, _ = self.json_cli("consult-state", "--track-a", str(track), "--question", "review", "--out", str(out))
        self.assertTrue(data["ok"])
        state = json.loads(out.read_text())
        self.assertEqual(state["schema"], "multi_model_state_v1")
        self.assertEqual(state["evidence"][0]["supports"], ["C-001", "C-002"])

    def test_consult_state_from_track_a_fail_contradicts_scope_claim(self):
        track = self.root / "track-a.json"
        track.write_text(json.dumps({"oracle": "scope-contract", "passed": False, "severity": 7, "violations": [{"type": "unexpected_file"}]}), encoding="utf-8")
        data, _ = self.json_cli("consult-state", "--track-a", str(track))
        self.assertEqual(data["schema"], "multi_model_state_v1")
        self.assertEqual(data["evidence"][0]["contradicts"], ["C-002"])
    def test_scope_contract_audited_globs_ignore_existing_repo_noise(self):
        self.json_cli("init", "--goal", "Scope guard")
        (self.root / "ignored.tmp").write_text("noise\n", encoding="utf-8")
        (self.root / "src" / "app.py").write_text("print('v2')\n", encoding="utf-8")
        contract = self.root / "contract.json"
        contract.write_text(json.dumps({
            "expected_files": ["src/app.py"],
            "audited_globs": ["src/**"],
            "loc_budget": 10
        }), encoding="utf-8")
        data, _ = self.json_cli("scope", "--contract", str(contract))
        self.assertTrue(data["passed"])
        self.assertEqual(data["metrics"]["changed_files"], ["src/app.py"])


if __name__ == "__main__":
    unittest.main()
