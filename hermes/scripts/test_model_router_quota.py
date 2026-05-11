#!/usr/bin/env python3
"""Tests for model-router quota-aware candidate gating."""

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parent / "model-router.py"


def load_router(temp_home: str):
    old_home = os.environ.get("HERMES_HOME")
    old_model_quota = sys.modules.pop("model_quota", None)
    os.environ["HERMES_HOME"] = temp_home
    spec = importlib.util.spec_from_file_location("model_router_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        if old_model_quota is not None:
            sys.modules["model_quota"] = old_model_quota
        if old_home is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = old_home
    return module


def quota_pass_payload(models=None):
    models = models or ["gpt-5.5", "deepseek-v4-pro"]
    timestamp = "2026-05-09T00:00:00Z"
    snapshots = {
        model: {"model": model, "status": "ok", "confidence": 1.0, "last_updated": timestamp}
        for model in models
    }
    return {
        "schema_version": 1,
        "ok": True,
        "status": "PASS",
        "models_checked": list(models),
        "min_confidence": 0.5,
        "blocking_statuses": ["exhausted", "low", "unknown", "unobservable"],
        "pass_count": len(models),
        "failure_count": 0,
        "passes": [{"model": model, "status": "ok", "confidence": 1.0, "last_updated": timestamp} for model in models],
        "failures": [],
        "snapshots": snapshots,
        "observability_evidence": {
            "schema_version": 1,
            "counts": {"usable": len(models), "total": len(models)},
            "by_model": {model: {"model": model, "status": "ok", "confidence": 1.0, "last_updated": timestamp, "evidence_state": "usable"} for model in models},
        },
    }


class TestModelRouterQuota(unittest.TestCase):
    def test_select_model_excludes_exhausted_quota_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            state_dir = Path(td) / "state"
            state_dir.mkdir(parents=True)
            (state_dir / "model_quota_state.json").write_text(json.dumps({
                "anthropic::claude-opus-4-7": {"model": "claude-opus-4-7", "provider": "anthropic", "status": "exhausted"},
                "openai-codex::gpt-5.5": {"model": "gpt-5.5", "provider": "openai-codex", "status": "ok"},
            }))
            router = load_router(td)
            router._model_available = lambda model, config=None: True
            router._get_pricing = lambda: None
            router.get_model_stats = lambda task_class=None: [
                {"model": "claude-opus-4-7", "count": 100, "pass_rate": 1.0, "score": 1.0, "avg_dur": 1},
                {"model": "gpt-5.5", "count": 100, "pass_rate": 0.5, "score": 0.5, "avg_dur": 1},
            ]
            decision = router.select_model(
                config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["claude-opus-4-7", "gpt-5.5"], "min_traces_per_model": 1, "epsilon": 0.0},
                candidate_override=["claude-opus-4-7", "gpt-5.5"],
                epsilon=0.0,
            )
            self.assertEqual(decision["model"], "gpt-5.5")
            self.assertIn("claude-opus-4-7", decision["quota_exhausted_candidates"])

    def test_log_decision_writes_auditable_routing_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            decision = {
                "model": "gpt-5.5",
                "reason": "exploit(score=0.9)",
                "task_tier": "codegen",
                "epsilon_used": 0.0,
                "candidates": ["claude-opus-4-7", "gpt-5.5"],
                "unavailable_candidates": [],
                "quota_exhausted_candidates": ["claude-opus-4-7"],
                "quota_snapshot": {
                    "anthropic::claude-opus-4-7": {"model": "claude-opus-4-7", "provider": "anthropic", "status": "exhausted", "confidence": 0.9, "reset_at": "2026-05-07T12:02:00Z"},
                    "openai-codex::gpt-5.5": {"model": "gpt-5.5", "provider": "openai-codex", "status": "unobservable", "confidence": 0.2},
                },
                "schedule_label": "free",
                "effective_cost_est": 0,
            }
            router.log_decision(decision, task_class="bugfix")
            log_path = Path(td) / "logs" / "model-routing.jsonl"
            entry = json.loads(log_path.read_text().strip())
            self.assertEqual(entry["event"], "routing_decision")
            self.assertEqual(entry["selected_model"], "gpt-5.5")
            self.assertEqual(entry["selected_provider"], "openai-codex")
            self.assertEqual(entry["candidate_models"], ["claude-opus-4-7", "gpt-5.5"])
            self.assertEqual(entry["skipped_models"][0]["model"], "claude-opus-4-7")
            self.assertEqual(entry["skipped_models"][0]["skip_reason"], "quota_exhausted")
            self.assertEqual(entry["quota_status"]["openai-codex::gpt-5.5"]["status"], "unobservable")
            self.assertEqual(entry["quota_status"]["anthropic::claude-opus-4-7"]["reset_at"], "2026-05-07T12:02:00Z")

    def test_select_model_prefers_capability_compatible_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._model_available = lambda model, config=None: True
            router._get_pricing = lambda: None
            router.get_model_stats = lambda task_class=None: [
                {"model": "chat-only", "count": 100, "pass_rate": 1.0, "score": 1.0, "avg_dur": 1},
                {"model": "code-model", "count": 100, "pass_rate": 0.5, "score": 0.5, "avg_dur": 1},
            ]
            decision = router.select_model(
                config={
                    "enabled": True,
                    "default_model": "code-model",
                    "candidate_models": ["chat-only", "code-model"],
                    "min_traces_per_model": 1,
                    "epsilon": 0.0,
                    "pricing": {"models": {
                        "chat-only": {"provider": "cheap", "capabilities": ["chat"]},
                        "code-model": {"provider": "code", "capabilities": ["code", "reasoning"]},
                    }},
                },
                task_class="bugfix",
                task_tier="codegen",
                candidate_override=["chat-only", "code-model"],
                epsilon=0.0,
            )
            self.assertEqual(decision["model"], "code-model")
            self.assertIn("chat-only", decision["capability_skipped_candidates"])

    def test_select_model_fails_closed_when_all_candidates_explicitly_lack_required_capability(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._model_available = lambda model, config=None: True
            router._get_pricing = lambda: None
            router.get_model_stats = lambda task_class=None: [
                {"model": "chat-only", "count": 100, "pass_rate": 1.0, "score": 1.0, "avg_dur": 1},
            ]
            decision = router.select_model(
                config={
                    "enabled": True,
                    "default_model": "chat-only",
                    "candidate_models": ["chat-only"],
                    "min_traces_per_model": 1,
                    "epsilon": 0.0,
                    "pricing": {"models": {"chat-only": {"provider": "cheap", "capabilities": ["chat"]}}},
                },
                task_class="bugfix",
                task_tier="codegen",
                candidate_override=["chat-only"],
                epsilon=0.0,
            )
            self.assertIsNone(decision["model"])
            self.assertEqual(decision["reason"], "no_capability_candidates")
            self.assertEqual(decision["capability_skipped_candidates"], ["chat-only"])

    def test_select_model_fails_closed_when_no_candidates(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            decision = router.select_model(
                config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": [], "min_traces_per_model": 1, "epsilon": 0.0},
                candidate_override=[],
                epsilon=0.0,
            )
            self.assertIsNone(decision["model"])
            self.assertEqual(decision["reason"], "no_candidates")

    def test_select_pair_fails_closed_without_diverse_reviewer_when_same_provider_not_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._model_available = lambda model, config=None: True
            router._get_pricing = lambda: None
            router.get_model_stats = lambda task_class=None: [
                {"model": "producer", "count": 100, "pass_rate": 1.0, "score": 1.0, "avg_dur": 1},
                {"model": "reviewer", "count": 100, "pass_rate": 1.0, "score": 0.9, "avg_dur": 1},
            ]
            config = {
                "enabled": True,
                "default_model": "producer",
                "candidate_models": ["producer", "reviewer"],
                "min_traces_per_model": 1,
                "epsilon": 0.0,
                "pricing": {"models": {
                    "producer": {"provider": "same", "capabilities": ["code"]},
                    "reviewer": {"provider": "same", "capabilities": ["code"]},
                }},
            }
            pair = router.select_pair(config=config, task_class="bugfix", task_tier="codegen")
            self.assertEqual(pair["producer"]["model"], "producer")
            self.assertIsNone(pair["reviewer"]["model"])
            self.assertEqual(pair["reviewer"]["reason"], "no_diverse_reviewer")
            self.assertFalse(pair["same_provider"])

    def test_load_config_preserves_pricing_provider_metadata_when_pricing_table_unavailable(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td, "config.yaml").write_text(
                "model:\n  default: grok-code\n"
                "smart_model_routing:\n  enabled: true\n  candidate_models:\n    - grok-code\n"
                "pricing:\n  models:\n    grok-code:\n      provider: xai\n",
                encoding="utf-8",
            )
            router = load_router(td)
            router._get_pricing = lambda: None
            old_xai = os.environ.pop("XAI_API_KEY", None)
            try:
                config = router.load_config()
                self.assertEqual(router._provider_for_model("grok-code", config=config), "xai")
                self.assertFalse(router._model_available("grok-code", config=config))
            finally:
                if old_xai is not None:
                    os.environ["XAI_API_KEY"] = old_xai

    def test_select_model_reuses_sticky_affinity_when_still_eligible(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._model_available = lambda model, config=None: True
            router._get_pricing = lambda: None
            stats = [
                {"model": "model-a", "count": 100, "pass_rate": 0.9, "score": 0.9, "avg_dur": 1},
                {"model": "model-b", "count": 100, "pass_rate": 0.5, "score": 0.5, "avg_dur": 1},
            ]
            router.get_model_stats = lambda task_class=None: stats
            config = {"enabled": True, "default_model": "model-b", "candidate_models": ["model-a", "model-b"], "min_traces_per_model": 1, "epsilon": 0.0}
            first = router.select_model(config=config, candidate_override=["model-a", "model-b"], epsilon=0.0, sticky_key="session-1")
            self.assertEqual(first["model"], "model-a")

            stats[:] = [
                {"model": "model-a", "count": 100, "pass_rate": 0.1, "score": 0.1, "avg_dur": 1},
                {"model": "model-b", "count": 100, "pass_rate": 1.0, "score": 1.0, "avg_dur": 1},
            ]
            second = router.select_model(config=config, candidate_override=["model-a", "model-b"], epsilon=0.0, sticky_key="session-1")
            self.assertEqual(second["model"], "model-a")
            self.assertEqual(second["reason"], "sticky_affinity")

    def test_select_model_fails_closed_when_all_quota_candidates_exhausted(self):
        with tempfile.TemporaryDirectory() as td:
            state_dir = Path(td) / "state"
            state_dir.mkdir(parents=True)
            (state_dir / "model_quota_state.json").write_text(json.dumps({
                "anthropic::claude-opus-4-7": {"model": "claude-opus-4-7", "provider": "anthropic", "status": "exhausted"},
                "openai-codex::gpt-5.5": {"model": "gpt-5.5", "provider": "openai-codex", "status": "exhausted"},
            }))
            router = load_router(td)
            router._model_available = lambda model, config=None: True
            router._get_pricing = lambda: None
            decision = router.select_model(
                config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["claude-opus-4-7", "gpt-5.5"], "min_traces_per_model": 1, "epsilon": 0.0},
                candidate_override=["claude-opus-4-7", "gpt-5.5"],
                epsilon=0.0,
            )
            self.assertIsNone(decision["model"])
            self.assertEqual(decision["reason"], "no_quota_candidates")
            self.assertEqual(set(decision["quota_exhausted_candidates"]), {"claude-opus-4-7", "gpt-5.5"})

    def test_select_model_fails_closed_when_all_providers_unavailable(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._model_available = lambda model, config=None: False
            router._get_pricing = lambda: None
            decision = router.select_model(
                config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["claude-opus-4-7", "gpt-5.5"], "min_traces_per_model": 1, "epsilon": 0.0},
                candidate_override=["claude-opus-4-7", "gpt-5.5"],
                epsilon=0.0,
            )
            self.assertIsNone(decision["model"])
            self.assertEqual(decision["reason"], "no_available_providers")
            self.assertEqual(set(decision["unavailable_candidates"]), {"claude-opus-4-7", "gpt-5.5"})

    def test_select_model_fails_closed_when_quota_gate_unavailable(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._model_available = lambda model, config=None: True
            router._get_pricing = lambda: None
            router.model_quota = None
            decision = router.select_model(
                config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5"], "min_traces_per_model": 1, "epsilon": 0.0},
                candidate_override=["gpt-5.5"],
                epsilon=0.0,
            )
            self.assertIsNone(decision["model"])
            self.assertEqual(decision["reason"], "no_quota_candidates")
            self.assertEqual(decision["quota_exhausted_candidates"], ["gpt-5.5"])

    def test_select_model_uses_config_provider_mapping_for_quota_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            state_dir = Path(td) / "state"
            state_dir.mkdir(parents=True)
            (state_dir / "model_quota_state.json").write_text(json.dumps({
                "xai::grok-code": {"model": "grok-code", "provider": "xai", "status": "exhausted"},
                "openai-codex::gpt-5.5": {"model": "gpt-5.5", "provider": "openai-codex", "status": "ok"},
            }))
            router = load_router(td)
            router._model_available = lambda model, config=None: True
            router._get_pricing = lambda: None
            router.get_model_stats = lambda task_class=None: [
                {"model": "grok-code", "count": 100, "pass_rate": 1.0, "score": 1.0, "avg_dur": 1},
                {"model": "gpt-5.5", "count": 100, "pass_rate": 0.5, "score": 0.5, "avg_dur": 1},
            ]
            decision = router.select_model(
                config={
                    "enabled": True,
                    "default_model": "gpt-5.5",
                    "candidate_models": ["grok-code", "gpt-5.5"],
                    "min_traces_per_model": 1,
                    "epsilon": 0.0,
                    "pricing": {"models": {
                        "grok-code": {"provider": "xai", "capabilities": ["code"]},
                        "gpt-5.5": {"provider": "openai-codex", "capabilities": ["code"]},
                    }},
                },
                candidate_override=["grok-code", "gpt-5.5"],
                epsilon=0.0,
            )
            self.assertEqual(decision["model"], "gpt-5.5")
            self.assertIn("grok-code", decision["quota_exhausted_candidates"])

    def test_select_model_uses_pricing_provider_mapping_for_quota_snapshot(self):
        class PricingStub:
            def get_provider(self, model):
                return "xai" if model == "grok-code" else "openai-codex"

            def estimate_cost(self, model, input_tokens, output_tokens, now_utc):
                return 0.0

            def effective_rate(self, model, now_utc):
                return (0.0, 0.0, "free")

        with tempfile.TemporaryDirectory() as td:
            state_dir = Path(td) / "state"
            state_dir.mkdir(parents=True)
            (state_dir / "model_quota_state.json").write_text(json.dumps({
                "xai::grok-code": {"model": "grok-code", "provider": "xai", "status": "exhausted"},
                "openai-codex::gpt-5.5": {"model": "gpt-5.5", "provider": "openai-codex", "status": "ok"},
            }))
            router = load_router(td)
            router._model_available = lambda model, config=None: True
            router._get_pricing = lambda: PricingStub()
            router.get_model_stats = lambda task_class=None: [
                {"model": "grok-code", "count": 100, "pass_rate": 1.0, "score": 1.0, "avg_dur": 1},
                {"model": "gpt-5.5", "count": 100, "pass_rate": 0.5, "score": 0.5, "avg_dur": 1},
            ]
            decision = router.select_model(
                config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["grok-code", "gpt-5.5"], "min_traces_per_model": 1, "epsilon": 0.0},
                candidate_override=["grok-code", "gpt-5.5"],
                epsilon=0.0,
            )
            self.assertEqual(decision["model"], "gpt-5.5")
            self.assertIn("grok-code", decision["quota_exhausted_candidates"])
            self.assertIn("xai::grok-code", decision["quota_snapshot"])

    def test_select_model_uses_config_provider_mapping_for_availability(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router._PROVIDER_ENV = dict(router._PROVIDER_ENV, custom_missing="CUSTOM_MISSING_ROUTER_KEY")
            os.environ.pop("CUSTOM_MISSING_ROUTER_KEY", None)
            decision = router.select_model(
                config={
                    "enabled": True,
                    "default_model": "custom-model",
                    "candidate_models": ["custom-model"],
                    "min_traces_per_model": 1,
                    "epsilon": 0.0,
                    "pricing": {"models": {
                        "custom-model": {"provider": "custom_missing", "capabilities": ["code", "reasoning"]},
                    }},
                },
                candidate_override=["custom-model"],
                epsilon=0.0,
            )
            self.assertIsNone(decision["model"])
            self.assertEqual(decision["reason"], "no_available_providers")
            self.assertEqual(decision["unavailable_candidates"], ["custom-model"])

    def test_select_pair_does_not_bypass_quota_for_same_provider_reviewer(self):
        class PricingStub:
            def get_candidate_models(self, tier):
                return ["producer-model"] if tier == "codegen" else ["reviewer-model"]

            def get_provider(self, model):
                return "same-provider"

            def is_off_peak(self, model, now_utc):
                return True

            def estimate_cost(self, model, input_tokens, output_tokens, now_utc):
                return 0.0

            def effective_rate(self, model, now_utc):
                return (0.0, 0.0, "free")

        with tempfile.TemporaryDirectory() as td:
            state_dir = Path(td) / "state"
            state_dir.mkdir(parents=True)
            (state_dir / "model_quota_state.json").write_text(json.dumps({
                "same-provider::reviewer-model": {"model": "reviewer-model", "provider": "same-provider", "status": "exhausted"},
            }))
            router = load_router(td)
            router._model_available = lambda model, config=None: True
            router._get_pricing = lambda: PricingStub()
            router.get_model_stats = lambda task_class=None: [
                {"model": "producer-model", "count": 100, "pass_rate": 1.0, "score": 1.0, "avg_dur": 1},
                {"model": "reviewer-model", "count": 100, "pass_rate": 1.0, "score": 1.0, "avg_dur": 1},
            ]
            pair = router.select_pair(
                task_tier="codegen",
                config={
                    "enabled": True,
                    "default_model": "producer-model",
                    "candidate_models": ["producer-model", "reviewer-model"],
                    "min_traces_per_model": 1,
                    "epsilon": 0.0,
                    "pricing": {"models": {
                        "producer-model": {"provider": "same-provider", "capabilities": ["code", "review", "reasoning"]},
                        "reviewer-model": {"provider": "same-provider", "capabilities": ["code", "review", "reasoning"]},
                    }},
                },
            )
            self.assertEqual(pair["producer"]["model"], "producer-model")
            self.assertIsNone(pair["reviewer"]["model"])
            self.assertEqual(pair["reviewer"]["reason"], "no_quota_candidates")
            self.assertIn("reviewer-model", pair["reviewer"].get("quota_exhausted_candidates", []))

    def test_cli_select_fails_closed_when_no_model_selected(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            old_argv = sys.argv[:]
            router.load_config = lambda: {"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5"], "epsilon": 0.0, "min_traces_per_model": 1}
            router.select_model = lambda **kwargs: {"model": None, "reason": "no_quota_candidates"}
            router.log_decision = lambda decision, task_class=None: None
            sys.argv = ["model-router.py", "select"]
            stderr = io.StringIO()
            try:
                with contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as cm:
                        router.cli()
                self.assertNotEqual(cm.exception.code, 0)
                self.assertIn("no_quota_candidates", stderr.getvalue())
            finally:
                sys.argv = old_argv

    def test_cli_select_fails_closed_when_config_load_fails(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            old_argv = sys.argv[:]
            router.load_config = lambda: None
            router.log_decision = lambda decision, task_class=None: None
            sys.argv = ["model-router.py", "select"]
            stdout = io.StringIO()
            stderr = io.StringIO()
            try:
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as cm:
                        router.cli()
                self.assertNotEqual(cm.exception.code, 0)
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn("config_load_failed", stderr.getvalue())
            finally:
                sys.argv = old_argv

    def test_cli_select_pair_fails_closed_when_pair_contains_no_model(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            old_argv = sys.argv[:]
            router.load_config = lambda: {"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5"], "epsilon": 0.0, "min_traces_per_model": 1}
            router.select_pair = lambda **kwargs: {
                "producer": {"model": None, "reason": "no_quota_candidates"},
                "reviewer": {"model": "gpt-5.5", "reason": "ok"},
                "diversity_rule": "provider_or_savings",
                "same_provider": False,
            }
            sys.argv = ["model-router.py", "select-pair"]
            stderr = io.StringIO()
            try:
                with contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as cm:
                        router.cli()
                self.assertNotEqual(cm.exception.code, 0)
                self.assertIn("no_quota_candidates", stderr.getvalue())
            finally:
                sys.argv = old_argv

    def test_router_readiness_fails_closed_on_dominance_or_quota(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router.load_config = lambda: {"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5", "deepseek-v4-pro"], "epsilon": 0.0, "min_traces_per_model": 1}
            router._model_available = lambda model, config=None: True
            router._quota_filter_candidates = lambda candidates, config=None: ([m for m in candidates if m != "gpt-5.5"], [], {})
            def fake_run_json(cmd, timeout=30):
                joined = " ".join(cmd)
                if "model-diversity-monitor.py" in joined:
                    return {
                        "dominance_warning": True,
                        "gate_failed": False,
                        "diversity_warnings": 0,
                        "route_diversity_signals": {},
                        "dominant_model": "gpt-5.5",
                        "dominant_share": 1.0,
                        "total_calls": 4,
                        "model_stats": {"gpt-5.5": {"total": 4}},
                    }, {"returncode": 0}
                if "model_quota.py" in joined:
                    return {"ok": False, "status": "FAIL_CLOSED", "failure_count": 1}, {"returncode": 2}
                return {}, {"returncode": 0}
            router._run_json_command = fake_run_json
            report = router.router_readiness(config=router.load_config())
            self.assertFalse(report["ok"])
            self.assertIn("dominance_warning", report["failed_checks"])
            self.assertIn("quota_confidence_unavailable", report["failed_checks"])
            self.assertEqual(report["eligible_non_dominant_alternates"], ["deepseek-v4-pro"])
            self.assertEqual(report["rebalance_plan"]["action"], "warm_up_non_dominant_alternates")
            self.assertEqual(report["rebalance_plan"]["per_model_targets"], {"deepseek-v4-pro": 1})
            self.assertEqual(report["rebalance_plan"]["rerun_gate_after"], "model-router.py readiness --json --gate")
            self.assertFalse(report["certification_gate"]["can_certify_autonomy"])
            self.assertFalse(report["certification_gate"]["can_promote_budget_handoff"])
            self.assertFalse(report["certification_gate"]["automatic_rebalance_performed"])
            self.assertIn("warm_up_eligible_non_dominant_alternates", report["certification_gate"]["recommended_next_actions"])

    def test_router_readiness_fails_closed_when_diversity_command_fails(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router._model_available = lambda model, config=None: True
            router._quota_filter_candidates = lambda candidates, config=None: (list(candidates), [], {})
            def fake_run_json(cmd, timeout=30):
                joined = " ".join(cmd)
                if "model-diversity-monitor.py" in joined:
                    return {}, {"returncode": 1, "stderr": "boom", "stdout_tail": ""}
                if "model_quota.py" in joined:
                    return quota_pass_payload(), {"returncode": 0}
                return {}, {"returncode": 0}
            router._run_json_command = fake_run_json
            report = router.router_readiness(config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5", "deepseek-v4-pro"], "epsilon": 0.0, "min_traces_per_model": 1})
            self.assertFalse(report["ok"], report)
            self.assertEqual(report["status"], "FAIL_CLOSED")
            self.assertIn("diversity_report_unavailable", report["failed_checks"])
            self.assertFalse(report["certification_gate"]["can_certify_autonomy"])

    def test_router_readiness_preserves_parseable_diversity_gate_output_on_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router._model_available = lambda model, config=None: True
            router._quota_filter_candidates = lambda candidates, config=None: (list(candidates), [], {})
            def fake_run_json(cmd, timeout=30):
                joined = " ".join(cmd)
                if "model-diversity-monitor.py" in joined:
                    return {
                        "dominance_warning": True,
                        "gate_failed": True,
                        "diversity_warnings": 0,
                        "route_diversity_signals": {},
                        "dominant_model": "gpt-5.5",
                        "dominant_share": 1.0,
                        "total_calls": 500,
                        "model_stats": {"gpt-5.5": {"total": 500}},
                    }, {"returncode": 2}
                if "model_quota.py" in joined:
                    return quota_pass_payload(), {"returncode": 0}
                return {}, {"returncode": 0}
            router._run_json_command = fake_run_json
            report = router.router_readiness(config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5", "deepseek-v4-pro"], "epsilon": 0.0, "min_traces_per_model": 1})
            self.assertFalse(report["ok"], report)
            self.assertIn("dominance_warning", report["failed_checks"])
            self.assertIn("diversity_gate_failed", report["failed_checks"])
            self.assertIn("diversity_monitor_nonzero_exit", report["failed_checks"])
            self.assertNotIn("diversity_report_unavailable", report["failed_checks"])
            self.assertEqual(report["rebalance_plan"]["action"], "warm_up_non_dominant_alternates")
            self.assertIn("warm_up_eligible_non_dominant_alternates", report["certification_gate"]["recommended_next_actions"])
            self.assertIn("inspect_preserved_diversity_gate_artifact", report["certification_gate"]["recommended_next_actions"])

    def test_router_readiness_fails_closed_on_diversity_gate_failed_without_dominance(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router._model_available = lambda model, config=None: True
            router._quota_filter_candidates = lambda candidates, config=None: (list(candidates), [], {})
            def fake_run_json(cmd, timeout=30):
                joined = " ".join(cmd)
                if "model-diversity-monitor.py" in joined:
                    return {
                        "dominance_warning": False,
                        "gate_failed": True,
                        "diversity_warnings": 1,
                        "route_diversity_signals": {"reviewer": {"status": "low_diversity"}},
                        "dominant_model": "gpt-5.5",
                        "dominant_share": 0.25,
                    }, {"returncode": 0}
                if "model_quota.py" in joined:
                    return quota_pass_payload(), {"returncode": 0}
                return {}, {"returncode": 0}
            router._run_json_command = fake_run_json
            report = router.router_readiness(config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5", "deepseek-v4-pro"], "epsilon": 0.0, "min_traces_per_model": 1})
            self.assertFalse(report["ok"], report)
            self.assertIn("diversity_gate_failed", report["failed_checks"])
            self.assertIn("resolve_diversity_gate_failures", report["certification_gate"]["recommended_next_actions"])

    def test_router_readiness_accepts_route_diversity_signals_list_shape(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router._model_available = lambda model, config=None: True
            router._quota_filter_candidates = lambda candidates, config=None: (list(candidates), [], {})
            def fake_run_json(cmd, timeout=30):
                joined = " ".join(cmd)
                if "model-diversity-monitor.py" in joined:
                    return {"dominance_warning": False, "gate_failed": False, "diversity_warnings": 0, "route_diversity_signals": [], "dominant_model": "gpt-5.5", "dominant_share": 0.25}, {"returncode": 0}
                if "model_quota.py" in joined:
                    return quota_pass_payload(), {"returncode": 0}
                return {}, {"returncode": 0}
            router._run_json_command = fake_run_json
            report = router.router_readiness(config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5", "deepseek-v4-pro"], "epsilon": 0.0, "min_traces_per_model": 1})
            self.assertTrue(report["ok"], report)
            self.assertNotIn("diversity_report_unavailable", report["failed_checks"])

    def test_router_readiness_fails_closed_on_malformed_parseable_diversity_json(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router._model_available = lambda model, config=None: True
            router._quota_filter_candidates = lambda candidates, config=None: (list(candidates), [], {})
            def fake_run_json(cmd, timeout=30):
                joined = " ".join(cmd)
                if "model-diversity-monitor.py" in joined:
                    return {"dominance_warning": False}, {"returncode": 0}
                if "model_quota.py" in joined:
                    return quota_pass_payload(), {"returncode": 0}
                return {}, {"returncode": 0}
            router._run_json_command = fake_run_json
            report = router.router_readiness(config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5", "deepseek-v4-pro"], "epsilon": 0.0, "min_traces_per_model": 1})
            self.assertFalse(report["ok"], report)
            self.assertEqual(report["status"], "FAIL_CLOSED")
            self.assertIn("diversity_report_unavailable", report["failed_checks"])
            self.assertIn("rerun_diversity_monitor_and_preserve_artifact", report["certification_gate"]["recommended_next_actions"])
            self.assertNotIn("certification_gate_clear", report["certification_gate"]["recommended_next_actions"])

    def test_router_readiness_requires_strict_true_quota_ok_and_returncode_clear(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router._model_available = lambda model, config=None: True
            router._quota_filter_candidates = lambda candidates, config=None: (list(candidates), [], {})
            def fake_run_json(cmd, timeout=30):
                joined = " ".join(cmd)
                if "model-diversity-monitor.py" in joined:
                    return {"dominance_warning": False, "gate_failed": False, "diversity_warnings": 0, "route_diversity_signals": {}, "dominant_model": "gpt-5.5", "dominant_share": 0.25}, {"returncode": 0}
                if "model_quota.py" in joined:
                    return {"ok": "false", "status": "PASS", "failure_count": 0}, {"returncode": 1}
                return {}, {"returncode": 0}
            router._run_json_command = fake_run_json
            report = router.router_readiness(config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5", "deepseek-v4-pro"], "epsilon": 0.0, "min_traces_per_model": 1})
            self.assertFalse(report["ok"], report)
            self.assertEqual(report["status"], "FAIL_CLOSED")
            self.assertIn("quota_confidence_unavailable", report["failed_checks"])
            self.assertIn("refresh_quota_confidence_or_lower_risk_tier", report["certification_gate"]["recommended_next_actions"])
            self.assertNotIn("certification_gate_clear", report["certification_gate"]["recommended_next_actions"])


    def test_router_readiness_fails_closed_when_rebalance_plan_fields_are_malformed(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router._model_available = lambda model, config=None: True
            router._quota_filter_candidates = lambda candidates, config=None: (list(candidates), [], {})
            def fake_run_json(cmd, timeout=30):
                joined = " ".join(cmd)
                if "model-diversity-monitor.py" in joined:
                    return {
                        "dominance_warning": True,
                        "gate_failed": False,
                        "diversity_warnings": 0,
                        "route_diversity_signals": {},
                        "dominant_model": "gpt-5.5",
                        "dominant_share": "not-a-number",
                        "total_calls": "not-an-int",
                        "model_stats": {"gpt-5.5": {"total": "not-an-int"}},
                    }, {"returncode": 0}
                if "model_quota.py" in joined:
                    return quota_pass_payload(), {"returncode": 0}
                return {}, {"returncode": 0}
            router._run_json_command = fake_run_json
            report = router.router_readiness(config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5", "deepseek-v4-pro"], "epsilon": 0.0, "min_traces_per_model": 1})
            self.assertFalse(report["ok"], report)
            self.assertIn("diversity_report_unavailable", report["failed_checks"])
            self.assertEqual(report["rebalance_plan"]["action"], "no_rebalance_needed")
            self.assertFalse(report["certification_gate"]["can_certify_autonomy"])

    def test_router_readiness_fails_closed_on_minimal_quota_success_shell(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router._model_available = lambda model, config=None, log_unavailable=True: True
            router._quota_filter_candidates = lambda candidates, config=None: (list(candidates), [], {})
            def fake_run_json(cmd, timeout=30):
                joined = " ".join(cmd)
                if "model-diversity-monitor.py" in joined:
                    return {"dominance_warning": False, "gate_failed": False, "diversity_warnings": 0, "route_diversity_signals": {}, "dominant_model": "gpt-5.5", "dominant_share": 0.25}, {"returncode": 0}
                if "model_quota.py" in joined:
                    return {"ok": True}, {"returncode": 0}
                return {}, {"returncode": 0}
            router._run_json_command = fake_run_json
            report = router.router_readiness(config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5", "deepseek-v4-pro"], "epsilon": 0.0, "min_traces_per_model": 1})
            self.assertFalse(report["ok"], report)
            self.assertIn("quota_confidence_failed", report["failed_checks"])
            self.assertFalse(report["certification_gate"]["can_certify_autonomy"], report)




    def test_router_readiness_fails_closed_when_quota_min_confidence_too_low(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router._model_available = lambda model, config=None, log_unavailable=True: True
            router.get_model_stats = lambda task_class=None: [
                {"model": "gpt-5.5", "count": 50, "pass_rate": 0.9, "score": 0.9, "avg_dur": 1},
                {"model": "deepseek-v4-pro", "count": 50, "pass_rate": 0.8, "score": 0.8, "avg_dur": 1},
            ]
            quota = quota_pass_payload()
            quota["min_confidence"] = 0.0
            for entry in quota["passes"]:
                entry["confidence"] = 0.0
            for snap in quota["snapshots"].values():
                snap["confidence"] = 0.0
            for entry in quota["observability_evidence"]["by_model"].values():
                entry["confidence"] = 0.0
            def fake_run_json(cmd, timeout=30):
                joined = " ".join(cmd)
                if "model-diversity-monitor.py" in joined:
                    return {"dominance_warning": False, "gate_failed": False, "diversity_warnings": 0, "route_diversity_signals": [], "dominant_model": "gpt-5.5", "dominant_share": 0.25}, {"returncode": 0}
                if "model_quota.py" in joined:
                    return quota, {"returncode": 0}
                return {}, {"returncode": 0}
            router._run_json_command = fake_run_json
            report = router.router_readiness(config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5", "deepseek-v4-pro"], "epsilon": 0.0, "min_traces_per_model": 1})
            self.assertFalse(report["ok"], report)
            self.assertIn("quota_confidence_failed", report["failed_checks"])

    def test_router_readiness_fails_closed_when_quota_min_confidence_missing(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router._model_available = lambda model, config=None, log_unavailable=True: True
            router.get_model_stats = lambda task_class=None: [
                {"model": "gpt-5.5", "count": 50, "pass_rate": 0.9, "score": 0.9, "avg_dur": 1},
                {"model": "deepseek-v4-pro", "count": 50, "pass_rate": 0.8, "score": 0.8, "avg_dur": 1},
            ]
            quota = quota_pass_payload()
            quota.pop("min_confidence")
            def fake_run_json(cmd, timeout=30):
                joined = " ".join(cmd)
                if "model-diversity-monitor.py" in joined:
                    return {"dominance_warning": False, "gate_failed": False, "diversity_warnings": 0, "route_diversity_signals": [], "dominant_model": "gpt-5.5", "dominant_share": 0.25}, {"returncode": 0}
                if "model_quota.py" in joined:
                    return quota, {"returncode": 0}
                return {}, {"returncode": 0}
            router._run_json_command = fake_run_json
            report = router.router_readiness(config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5", "deepseek-v4-pro"], "epsilon": 0.0, "min_traces_per_model": 1})
            self.assertFalse(report["ok"], report)
            self.assertIn("quota_confidence_failed", report["failed_checks"])

    def test_router_readiness_fails_closed_on_hollow_quota_success_shell(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router._model_available = lambda model, config=None, log_unavailable=True: True
            router.get_model_stats = lambda task_class=None: [
                {"model": "gpt-5.5", "count": 50, "pass_rate": 0.9, "score": 0.9, "avg_dur": 1},
                {"model": "deepseek-v4-pro", "count": 50, "pass_rate": 0.8, "score": 0.8, "avg_dur": 1},
            ]
            def fake_run_json(cmd, timeout=30):
                joined = " ".join(cmd)
                if "model-diversity-monitor.py" in joined:
                    return {"dominance_warning": False, "gate_failed": False, "diversity_warnings": 0, "route_diversity_signals": [], "dominant_model": "gpt-5.5", "dominant_share": 0.25}, {"returncode": 0}
                if "model_quota.py" in joined:
                    return {
                        "schema_version": 1,
                        "ok": True,
                        "status": "PASS",
                        "models_checked": ["gpt-5.5", "deepseek-v4-pro"],
                        "min_confidence": 0.5,
                        "pass_count": 2,
                        "failure_count": 0,
                        "passes": [{"model": "gpt-5.5"}, {"model": "deepseek-v4-pro"}],
                        "failures": [],
                        "snapshots": {"hollow": {"status": "ok"}},
                        "observability_evidence": {"counts": {"total": 2, "usable": 2}, "by_model": {"gpt-5.5": {"model": "gpt-5.5", "evidence_state": "usable"}, "deepseek-v4-pro": {"model": "deepseek-v4-pro", "evidence_state": "usable"}}},
                    }, {"returncode": 0}
                return {}, {"returncode": 0}
            router._run_json_command = fake_run_json
            report = router.router_readiness(config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5", "deepseek-v4-pro"], "epsilon": 0.0, "min_traces_per_model": 1})
            self.assertFalse(report["ok"], report)
            self.assertIn("quota_confidence_failed", report["failed_checks"])
            self.assertFalse(report["certification_gate"]["can_certify_autonomy"], report)

    def test_router_readiness_fails_closed_on_inconsistent_quota_success_shell(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router._model_available = lambda model, config=None, log_unavailable=True: True
            router._quota_filter_candidates = lambda candidates, config=None: (list(candidates), [], {})
            def fake_run_json(cmd, timeout=30):
                joined = " ".join(cmd)
                if "model-diversity-monitor.py" in joined:
                    return {"dominance_warning": False, "gate_failed": False, "diversity_warnings": 0, "route_diversity_signals": {}, "dominant_model": "gpt-5.5", "dominant_share": 0.25}, {"returncode": 0}
                if "model_quota.py" in joined:
                    return {"ok": True, "status": "FAIL_CLOSED", "failure_count": 1, "failures": [{"model": "gpt-5.5"}]}, {"returncode": 0}
                return {}, {"returncode": 0}
            router._run_json_command = fake_run_json
            report = router.router_readiness(config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5", "deepseek-v4-pro"], "epsilon": 0.0, "min_traces_per_model": 1})
            self.assertFalse(report["ok"], report)
            self.assertIn("quota_confidence_failed", report["failed_checks"])
            self.assertNotIn("certification_gate_clear", report["certification_gate"]["recommended_next_actions"])

    def test_router_readiness_fails_closed_on_malformed_diversity_numeric_fields(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router._model_available = lambda model, config=None, log_unavailable=True: True
            router._quota_filter_candidates = lambda candidates, config=None: (list(candidates), [], {})
            def fake_run_json(cmd, timeout=30):
                joined = " ".join(cmd)
                if "model-diversity-monitor.py" in joined:
                    return {"dominance_warning": False, "gate_failed": False, "diversity_warnings": -1, "route_diversity_signals": {}, "dominant_model": "gpt-5.5", "dominant_share": "NaN"}, {"returncode": 0}
                if "model_quota.py" in joined:
                    return quota_pass_payload(), {"returncode": 0}
                return {}, {"returncode": 0}
            router._run_json_command = fake_run_json
            report = router.router_readiness(config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5", "deepseek-v4-pro"], "epsilon": 0.0, "min_traces_per_model": 1})
            self.assertFalse(report["ok"], report)
            self.assertIn("diversity_report_unavailable", report["failed_checks"])

    def test_router_readiness_eligible_alternates_do_not_log_provider_availability(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router.model_quota = None
            def forbidden_log(*args, **kwargs):
                raise AssertionError("readiness alternate computation must be read-only")
            router._log_unavailable_provider = forbidden_log
            cfg = {
                "pricing": {"models": {"alt-model": {"provider": "anthropic"}}},
                "candidate_models": ["alt-model"],
            }
            old_env = os.environ.pop("ANTHROPIC_API_KEY", None)
            try:
                alternates, meta = router._eligible_alternates(["alt-model"], "dominant-model", config=cfg)
            finally:
                if old_env is not None:
                    os.environ["ANTHROPIC_API_KEY"] = old_env
            self.assertEqual(alternates, [])
            self.assertTrue(meta.get("read_only"), meta)
            self.assertFalse((Path(td) / "state" / "provider_availability.json").exists())



    def test_router_readiness_passes_when_diversity_and_quota_pass(self):
        with tempfile.TemporaryDirectory() as td:
            router = load_router(td)
            router._get_pricing = lambda: None
            router._model_available = lambda model, config=None: True
            router._quota_filter_candidates = lambda candidates, config=None: (list(candidates), [], {})
            def fake_run_json(cmd, timeout=30):
                joined = " ".join(cmd)
                if "model-diversity-monitor.py" in joined:
                    return {"dominance_warning": False, "gate_failed": False, "diversity_warnings": 0, "route_diversity_signals": {}, "dominant_model": "gpt-5.5", "dominant_share": 0.25}, {"returncode": 0}
                if "model_quota.py" in joined:
                    return quota_pass_payload(), {"returncode": 0}
                return {}, {"returncode": 0}
            router._run_json_command = fake_run_json
            report = router.router_readiness(config={"enabled": True, "default_model": "gpt-5.5", "candidate_models": ["gpt-5.5", "deepseek-v4-pro"], "epsilon": 0.0, "min_traces_per_model": 1})
            self.assertTrue(report["ok"])
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["rebalance_plan"]["action"], "no_rebalance_needed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
