#!/usr/bin/env python3
"""Safety and edge-case tests for cross-patch.py run mode.
Covers: non-unique match, --apply without --verify, cost cap, fuzzy fallback, verify rollback,
and (Phase 4.5) select_producer_reviewer with fake quorum/router."""

import importlib.util
import json
import os
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPT = Path(__file__).parent / "cross-patch.py"
spec = importlib.util.spec_from_file_location("cross_patch", SCRIPT)
cross_patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cross_patch)


class _IsolatedTestEnv(unittest.TestCase):
    """Base class that redirects cross-patch logs and protocol DB to a tmpdir.
    Prevents test runs from polluting production logs/cross-patch.jsonl and
    ~/.hermes/route_outcomes.db.protocol_messages."""

    @classmethod
    def setUpClass(cls):
        cls._iso_dir = tempfile.mkdtemp(prefix="cross-patch-test-")
        cls._saved_env = {}
        for k, v in {
            "CROSS_PATCH_LOG_FILE": os.path.join(cls._iso_dir, "cross-patch.jsonl"),
            "HERMES_PROTOCOL_DB_PATH": os.path.join(cls._iso_dir, "protocol.db"),
            "HERMES_ROUTE_DB_PATH": os.path.join(cls._iso_dir, "route_outcomes.db"),
        }.items():
            cls._saved_env[k] = os.environ.get(k)
            os.environ[k] = v
        # rebind module-level LOG_FILE so the already-imported module sees
        # the test path (env var is read at module import time).
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


class TestCrossPatchSafety(_IsolatedTestEnv):

    def _fake_call_pass(self, model, prompt, *, workdir=None, timeout=120):
        """Fake model caller that returns a passing verdict with approved_patch_ids."""
        return {
            "ok": True, "model": model, "provider": "test", "adapter": "fake",
            "latency_ms": 100,
            "output": json.dumps({
                "verdict": "pass", "summary": "ok",
                "approved_patch_ids": ["test-id"],
                "patches": [{"file": "target.txt", "original": "AAA", "suggested": "BBB",
                             "severity": "major", "confidence": 0.95, "rationale": "test"}],
            }),
        }

    def test_non_unique_match_rejected(self):
        """File with 2 identical 'AAA' blocks -> conflict, not applied."""
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "target.txt").write_text("line1 AAA line2 AAA end\n")
            result = cross_patch.run_cross_patch_actual(
                task="replace AAA", workdir=td,
                producer_model="p", reviewer_model="r",
                apply=True, force_no_verify=True,
                model_caller=self._fake_call_pass,
            )
            # Should have conflicts due to ambiguous match
            conflicts = result["merge"]["stats"]["conflicts"]
            self.assertGreater(conflicts, 0, "Expected conflict for non-unique match")
            self.assertFalse(result["applied"])

    def test_apply_without_verify_rejected(self):
        """--apply without --verify and without --force-no-verify -> rejected."""
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "target.txt").write_text("AAA old\n")
            result = cross_patch.run_cross_patch_actual(
                task="replace", workdir=td,
                producer_model="p", reviewer_model="r",
                apply=True, force_no_verify=False,
                model_caller=self._fake_call_pass,
            )
            self.assertEqual(result["verdict"], "rejected")
            self.assertIn("--verify", result.get("rejection_reason", ""))

    def test_apply_with_verify_pass(self):
        """--apply with --verify (exit 0) -> applied."""
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "target.txt").write_text("AAA old\n")
            result = cross_patch.run_cross_patch_actual(
                task="replace", workdir=td,
                producer_model="p", reviewer_model="r",
                apply=True, verify_cmd="true",  # always succeeds
                model_caller=self._fake_call_pass,
            )
            self.assertTrue(result["applied"])
            self.assertEqual((Path(td) / "target.txt").read_text(), "BBB old\n")

    def test_verify_failure_rollback(self):
        """--apply with --verify (exit 1) -> rollback, original restored."""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "target.txt"
            original = "AAA old\n"
            target.write_text(original)
            result = cross_patch.run_cross_patch_actual(
                task="replace", workdir=td,
                producer_model="p", reviewer_model="r",
                apply=True, verify_cmd="false",  # always fails
                model_caller=self._fake_call_pass,
            )
            self.assertEqual(result["verdict"], "fail")
            self.assertEqual(result["verify"]["rollback"], "applied")
            # File should be rolled back to original
            self.assertEqual(target.read_text(), original)

    def test_cost_tracking_in_result(self):
        """Result should include cost field with latency info."""
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "target.txt").write_text("AAA old\n")
            result = cross_patch.run_cross_patch_actual(
                task="replace", workdir=td,
                producer_model="p", reviewer_model="r",
                model_caller=self._fake_call_pass,
            )
            self.assertIn("cost", result)
            self.assertIn("producer_latency_ms", result["cost"])
            self.assertIn("reviewer_latency_ms", result["cost"])
            self.assertIn("max_cost_usd", result["cost"])


# ── Phase 4.5: select_producer_reviewer test fixtures ───────────────────────
# These tests mock _model_available_check and subprocess.run (for model-router)
# to exercise the 3-stage selector without touching real quorum.yaml or router.


class _FakeQuorumTempDirMixin:
    """Mixin that creates a temp quorum.yaml for the test method."""

    def setUp(self):
        super().setUp()
        self._quorum_tmpdir = tempfile.mkdtemp(prefix="fake-quorum-")
        self._orig_quorum = getattr(cross_patch, "QUORUM_FILE", None)
        self._fake_quorum_path = os.path.join(self._quorum_tmpdir, "quorum.yaml")
        cross_patch.QUORUM_FILE = self._fake_quorum_path

    def tearDown(self):
        cross_patch.QUORUM_FILE = self._orig_quorum
        import shutil as _sh
        _sh.rmtree(self._quorum_tmpdir, ignore_errors=True)
        super().tearDown()

    def _write_quorum(self, content: str):
        with open(self._fake_quorum_path, "w") as f:
            f.write(content)


class TestSelectorExplicitOnly(_FakeQuorumTempDirMixin, unittest.TestCase):
    """Step 1 only — both requested_producer and requested_reviewer provided and available."""

    @patch.object(cross_patch, '_model_available_check', return_value=True)
    def test_explicit_both_available(self, mock_check):
        p, r = cross_patch.select_producer_reviewer(
            requested_producer="gpt-5.5", requested_reviewer="deepseek-v4-pro",
        )
        self.assertEqual(p, "gpt-5.5")
        self.assertEqual(r, "deepseek-v4-pro")
        self.assertEqual(mock_check.call_count, 2)

    @patch.object(cross_patch.subprocess, 'run')
    @patch.object(cross_patch, '_model_available_check', side_effect=lambda m: m != "gpt-5.5")
    def test_explicit_producer_unavailable_falls_through(self, mock_check, mock_run):
        """Producer unavailable -> falls to step 2/3. With no router/quorum, raises."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="router unavailable")
        with self.assertRaises(cross_patch.CrossPatchUnavailable) as ctx:
            cross_patch.select_producer_reviewer(
                requested_producer="gpt-5.5", requested_reviewer="deepseek-v4-pro",
            )
        self.assertIn("No available", str(ctx.exception))


class TestSelectorRouterStep(_FakeQuorumTempDirMixin, unittest.TestCase):
    """Step 2 — model-router select-pair subprocess is called."""

    def _fake_router_result(self, producer, reviewer):
        cp = MagicMock()
        cp.returncode = 0
        cp.stdout = json.dumps({
            "producer": {"model": producer, "reason": "mock"},
            "reviewer": {"model": reviewer, "reason": "mock"},
            "diversity_rule": "provider_or_savings",
            "same_provider": False,
        })
        return cp

    @patch.object(cross_patch, '_model_available_check', return_value=True)
    @patch.object(cross_patch.subprocess, 'run')
    def test_router_provides_pair_when_no_explicit(self, mock_run, mock_check):
        """No explicit models -> router picks pair."""
        mock_run.return_value = self._fake_router_result("gpt-5.5", "deepseek-v4-pro")
        p, r = cross_patch.select_producer_reviewer()
        self.assertEqual(p, "gpt-5.5")
        self.assertEqual(r, "deepseek-v4-pro")
        # router called with --task-tier codegen
        args, kwargs = mock_run.call_args
        self.assertIn("select-pair", args[0])
        self.assertIn("--task-tier", args[0])
        self.assertIn("codegen", args[0])

    @patch.object(cross_patch, '_model_available_check', return_value=True)
    @patch.object(cross_patch.subprocess, 'run')
    def test_router_pair_unavailable_then_falls_to_quorum(self, mock_run, mock_check):
        """Router returns a pair that fails availability check -> falls to quorum.yaml."""
        self._write_quorum("""\
tiers:
  T2:
    planners: [mimo-v2.5-pro, claude-opus-4-7]
""")
        # Router returns a model that's marked unavailable
        def fake_available(m):
            return m == "mimo-v2.5-pro" or m == "claude-opus-4-7"

        mock_check.side_effect = fake_available
        mock_run.return_value = self._fake_router_result("mimo-v2.5-pro", "gpt-5.5")
        p, r = cross_patch.select_producer_reviewer()
        # Router gives mimo-v2.5-pro (available) + gpt-5.5 (unavailable) ->
        # producer stays mimo-v2.5-pro, reviewer falls to quorum -> claude-opus-4-7
        self.assertEqual(p, "mimo-v2.5-pro")
        self.assertEqual(r, "claude-opus-4-7")

    @patch.object(cross_patch, '_model_available_check', return_value=True)
    @patch.object(cross_patch.subprocess, 'run')
    def test_router_timeout_falls_to_quorum(self, mock_run, mock_check):
        """Router subprocess times out -> gracefully falls to quorum.yaml."""
        self._write_quorum("""\
tiers:
  T2:
    planners: [mimo-v2.5-pro, deepseek-v4-pro]
""")
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="model-router.py select-pair", timeout=10, output=""
        )
        p, r = cross_patch.select_producer_reviewer()
        self.assertEqual(p, "mimo-v2.5-pro")
        self.assertEqual(r, "deepseek-v4-pro")

    @patch.object(cross_patch, '_model_available_check', return_value=True)
    @patch.object(cross_patch.subprocess, 'run')
    def test_router_json_malformed_falls_to_quorum(self, mock_run, mock_check):
        """Router returns non-JSON -> gracefully falls to quorum.yaml."""
        self._write_quorum("""\
tiers:
  T2:
    planners: [gpt-5.5, deepseek-v4-pro]
""")
        cp = MagicMock()
        cp.returncode = 0
        cp.stdout = "NOT JSON AT ALL"
        mock_run.return_value = cp
        p, r = cross_patch.select_producer_reviewer()
        self.assertEqual(p, "gpt-5.5")
        self.assertEqual(r, "deepseek-v4-pro")


class TestSelectorQuorumStep(_FakeQuorumTempDirMixin, unittest.TestCase):
    """Step 3 — quorum.yaml tiers.planners fallback."""

    def setUp(self):
        super().setUp()
        self._write_quorum("""\
tiers:
  T2:
    planners: [gpt-5.5, mimo-v2.5-pro, deepseek-v4-pro]
  T1:
    planners: [mimo-v2.5-pro]
""")

    @patch.object(cross_patch, '_model_available_check', return_value=True)
    @patch.object(cross_patch.subprocess, 'run')
    def test_quorum_picks_first_two_available(self, mock_run, mock_check):
        """Router fails (exit 1) -> quorum provides first 2 planners."""
        cp = MagicMock()
        cp.returncode = 1
        cp.stdout = ""
        mock_run.return_value = cp
        p, r = cross_patch.select_producer_reviewer()
        self.assertEqual(p, "gpt-5.5")
        self.assertEqual(r, "mimo-v2.5-pro")

    @patch.object(cross_patch, '_model_available_check', side_effect=lambda m: m != "gpt-5.5")
    @patch.object(cross_patch.subprocess, 'run')
    def test_quorum_skips_unavailable(self, mock_run, mock_check):
        """First planner unavailable -> pick second as producer, third as reviewer."""
        cp = MagicMock()
        cp.returncode = 1
        cp.stdout = ""
        mock_run.return_value = cp
        p, r = cross_patch.select_producer_reviewer()
        self.assertEqual(p, "mimo-v2.5-pro")
        self.assertEqual(r, "deepseek-v4-pro")

    @patch.object(cross_patch, '_model_available_check', side_effect=lambda m: False)
    @patch.object(cross_patch.subprocess, 'run')
    def test_quorum_all_unavailable_raises(self, mock_run, mock_check):
        """All planners unavailable -> CrossPatchUnavailable raised."""
        cp = MagicMock()
        cp.returncode = 1
        cp.stdout = ""
        mock_run.return_value = cp
        with self.assertRaises(cross_patch.CrossPatchUnavailable) as ctx:
            cross_patch.select_producer_reviewer()
        self.assertIn("No available", str(ctx.exception))

    @patch.object(cross_patch, '_model_available_check', return_value=True)
    @patch.object(cross_patch.subprocess, 'run')
    def test_quorum_single_planner_raises(self, mock_run, mock_check):
        """Only 1 planner in tier -> not enough for a pair -> raises."""
        cp = MagicMock()
        cp.returncode = 1
        cp.stdout = ""
        mock_run.return_value = cp
        # Overwrite to tier with only 1 planner
        self._write_quorum("""\
tiers:
  T2:
    planners: [gpt-5.5]
""")
        with self.assertRaises(cross_patch.CrossPatchUnavailable):
            cross_patch.select_producer_reviewer(tier="T2")


class TestSelectorTierParameter(_FakeQuorumTempDirMixin, unittest.TestCase):
    """select_producer_reviewer(tier=...) routes to correct tier in quorum."""

    def setUp(self):
        super().setUp()
        self._write_quorum("""\
tiers:
  T0:
    planners: [mimo-v2.5-pro]
  T2:
    planners: [gpt-5.5, claude-opus-4-7, deepseek-v4-pro]
""")

    @patch.object(cross_patch, '_model_available_check', return_value=True)
    @patch.object(cross_patch.subprocess, 'run')
    def test_tier_t0_single_planner_fails(self, mock_run, mock_check):
        """T0 has only 1 planner -> not enough, raises."""
        cp = MagicMock()
        cp.returncode = 1
        cp.stdout = ""
        mock_run.return_value = cp
        with self.assertRaises(cross_patch.CrossPatchUnavailable):
            cross_patch.select_producer_reviewer(tier="T0")

    @patch.object(cross_patch, '_model_available_check', return_value=True)
    @patch.object(cross_patch.subprocess, 'run')
    def test_tier_t2_uses_correct_planner_set(self, mock_run, mock_check):
        """T2 uses its own planner list, not T0's."""
        cp = MagicMock()
        cp.returncode = 1
        cp.stdout = ""
        mock_run.return_value = cp
        p, r = cross_patch.select_producer_reviewer(tier="T2")
        self.assertEqual(p, "gpt-5.5")
        self.assertEqual(r, "claude-opus-4-7")


# ── Integration: selector + run_cross_patch_actual ─────────────────────────
class TestSelectorIntegration(_FakeQuorumTempDirMixin, _IsolatedTestEnv):
    """select_producer_reviewer is called inside run_cross_patch_actual.
    These tests verify the full call chain when producer_model/reviewer_model are None."""

    def setUp(self):
        _FakeQuorumTempDirMixin.setUp(self)
        # _IsolatedTestEnv.setUpClass is @classmethod, so only call our parent setUp
        self._iso_dir = tempfile.mkdtemp(prefix="cross-patch-test-")
        self._saved_env = {}
        for k, v in {
            "CROSS_PATCH_LOG_FILE": os.path.join(self._iso_dir, "cross-patch.jsonl"),
            "HERMES_PROTOCOL_DB_PATH": os.path.join(self._iso_dir, "protocol.db"),
            "HERMES_ROUTE_DB_PATH": os.path.join(self._iso_dir, "route_outcomes.db"),
        }.items():
            self._saved_env[k] = os.environ.get(k)
            os.environ[k] = v
        cross_patch.LOG_FILE = os.environ["CROSS_PATCH_LOG_FILE"]
        self._write_quorum("""\
tiers:
  T2:
    planners: [gpt-5.5, deepseek-v4-pro]
""")

    def tearDown(self):
        import shutil as _sh
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        _sh.rmtree(self._iso_dir, ignore_errors=True)
        _FakeQuorumTempDirMixin.tearDown(self)

    @patch.object(cross_patch, '_model_available_check', return_value=True)
    @patch.object(cross_patch.subprocess, 'run')
    def test_run_actual_with_selector_resolution(self, mock_run, mock_check):
        """run_cross_patch_actual without explicit models -> selector resolves pair."""
        cp = MagicMock()
        cp.returncode = 1
        cp.stdout = ""
        mock_run.return_value = cp

        def fake_call(model, prompt, *, workdir=None, timeout=120):
            return {
                "ok": True, "model": model, "provider": "test", "adapter": "fake",
                "output": json.dumps({
                    "verdict": "pass", "summary": "auto",
                    "patches": [{"file": "target.txt", "original": "old", "suggested": "new",
                                 "severity": "major", "confidence": 0.95, "rationale": "test"}],
                }),
            }

        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "target.txt").write_text("hello old world\n")
            result = cross_patch.run_cross_patch_actual(
                task="replace old with new",
                workdir=str(td),
                apply=True, force_no_verify=True,
                model_caller=fake_call,
            )
            # Selector should have picked gpt-5.5 (producer) / deepseek-v4-pro (reviewer)
            self.assertTrue(result["applied"])
            self.assertIn("hello new world", (Path(td) / "target.txt").read_text())

    @patch.object(cross_patch, '_model_available_check', side_effect=lambda m: False)
    @patch.object(cross_patch.subprocess, 'run')
    def test_run_actual_selector_all_unavailable(self, mock_run, mock_check):
        """All resolvers fail -> CrossPatchUnavailable propagated."""
        cp = MagicMock()
        cp.returncode = 1
        cp.stdout = ""
        mock_run.return_value = cp
        with self.assertRaises(cross_patch.CrossPatchUnavailable):
            cross_patch.run_cross_patch_actual(
                task="replace", workdir=tempfile.mkdtemp(),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
