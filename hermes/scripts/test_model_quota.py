#!/usr/bin/env python3
"""Tests for model_quota.py quota snapshot and gating semantics."""

import importlib.util
import json
import math
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock
from pathlib import Path


SCRIPT = Path(__file__).parent / "model_quota.py"


def load_model_quota(temp_home: str):
    old_home = os.environ.get("HERMES_HOME")
    os.environ["HERMES_HOME"] = temp_home
    spec = importlib.util.spec_from_file_location("model_quota_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        if old_home is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = old_home
    return module


class TestModelQuota(unittest.TestCase):
    def test_parse_rate_limit_headers_normalizes_remaining_tokens_and_reset(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            snap = mq.snapshot_from_headers(
                model="claude-opus-4-7",
                provider="anthropic",
                headers={
                    "X-RateLimit-Remaining-Tokens": "12345",
                    "x-ratelimit-remaining-requests": "7",
                    "anthropic-ratelimit-tokens-reset": "2026-04-28T09:00:00Z",
                },
            )
            self.assertEqual(snap["status"], "ok")
            self.assertEqual(snap["observability"], "window_exact")
            self.assertEqual(snap["quota_type"], "rate_limit_window")
            self.assertEqual(snap["remaining_tokens"], 12345)
            self.assertEqual(snap["remaining_requests"], 7)
            self.assertEqual(snap["reset_at"], "2026-04-28T09:00:00Z")
            self.assertEqual(snap["source"], "response_headers")

    def test_snapshot_marks_subscription_providers_unobservable_not_ok(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            snap = mq.default_snapshot("gpt-5.5", "openai-codex")
            self.assertEqual(snap["status"], "unobservable")
            self.assertEqual(snap["observability"], "unobservable")
            self.assertEqual(snap["quota_type"], "subscription_cap")
            self.assertIsNone(snap["remaining_tokens"])

    def test_gate_models_skips_exhausted_but_keeps_unknown_with_risk(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            snapshots = {
                "anthropic::claude-opus-4-7": {"model": "claude-opus-4-7", "provider": "anthropic", "status": "exhausted"},
                "deepseek::deepseek-v4-pro": {"model": "deepseek-v4-pro", "provider": "deepseek", "status": "unknown"},
                "openai-codex::gpt-5.5": {"model": "gpt-5.5", "provider": "openai-codex", "status": "ok"},
            }
            allowed, skipped = mq.gate_models(
                ["claude-opus-4-7", "gpt-5.5", "deepseek-v4-pro"],
                snapshots,
                providers={"claude-opus-4-7": "anthropic", "gpt-5.5": "openai-codex", "deepseek-v4-pro": "deepseek"},
            )
            self.assertEqual(allowed, ["gpt-5.5", "deepseek-v4-pro"])
            self.assertEqual(skipped[0]["model"], "claude-opus-4-7")
            self.assertEqual(skipped[0]["reason"], "quota_exhausted")

    def test_record_call_persists_headers_snapshot_and_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            snap = mq.record_call(
                model="deepseek-v4-pro",
                provider="deepseek",
                ok=True,
                headers={"x-ratelimit-remaining-tokens": "42"},
                usage={"input_tokens": 10, "output_tokens": 5},
            )
            self.assertEqual(snap["remaining_tokens"], 42)
            state_path = Path(td) / "state" / "model_quota_state.json"
            log_path = Path(td) / "logs" / "model-quota.jsonl"
            self.assertTrue(state_path.exists())
            self.assertTrue(log_path.exists())
            state = json.loads(state_path.read_text())
            self.assertIn("deepseek::deepseek-v4-pro", state)
            self.assertEqual(state["deepseek::deepseek-v4-pro"]["remaining_tokens"], 42)

    def test_retry_after_seconds_is_normalized_to_reset_at_iso(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
            reset_at = mq.parse_reset_at("120", now=now)
            self.assertEqual(reset_at, "2026-05-07T12:02:00Z")

            for bad in ("inf", "-inf", "1e309", float("nan"), True):
                self.assertIsNone(mq.parse_reset_at(bad, now=now))

            snap = mq.snapshot_from_error(
                model="deepseek-v4-pro",
                provider="deepseek",
                error="HTTP 429 rate_limit exceeded",
                retry_after="120",
                now=now,
            )
            self.assertEqual(snap["status"], "exhausted")
            self.assertEqual(snap["error_class"], "rate_limit")
            self.assertEqual(snap["reset_at"], "2026-05-07T12:02:00Z")
            self.assertEqual(snap["reset_after_seconds"], 120)

    def test_snapshot_headers_reject_nonfinite_remaining_values(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            for value in ("inf", "-inf", "1e309", float("nan"), True):
                snap = mq.snapshot_from_headers(
                    model="grok-4",
                    provider="xai",
                    headers={"x-ratelimit-remaining-tokens": value},
                )
                self.assertIsNone(snap["remaining_tokens"])
                self.assertNotEqual(snap["status"], "exhausted")

    def test_negative_remaining_headers_are_exhausted_not_low(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            for header in ("x-ratelimit-remaining-tokens", "x-ratelimit-remaining-requests"):
                snap = mq.snapshot_from_headers(
                    model="grok-4",
                    provider="xai",
                    headers={header: "-1"},
                )
                self.assertEqual(snap["status"], "exhausted")
                allowed, skipped = mq.gate_models(["grok-4"], {"xai::grok-4": snap}, providers={"grok-4": "xai"})
                self.assertEqual(allowed, [])
                self.assertEqual(skipped[0]["model"], "grok-4")

    def test_gate_models_sanitizes_malformed_elapsed_reset_confidence(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
            past = (now - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
            for confidence in ("bad", "NaN", "1e309", True):
                snap = {"model": "grok-4", "provider": "xai", "status": "exhausted", "reset_at": past, "confidence": confidence}
                allowed, skipped = mq.gate_models(["grok-4"], {"xai::grok-4": snap}, providers={"grok-4": "xai"}, now=now)
                self.assertEqual(allowed, ["grok-4"])
                self.assertEqual(skipped, [])
                self.assertTrue(math.isfinite(snap["confidence"]))
                self.assertLessEqual(snap["confidence"], 0.55)

    def test_gate_models_skips_malformed_snapshot_values_without_crashing(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            allowed, skipped = mq.gate_models(["grok-4"], {"xai::grok-4": "not-a-dict"}, providers={"grok-4": "xai"})
            self.assertEqual(allowed, [])
            self.assertEqual(skipped[0]["model"], "grok-4")
            self.assertEqual(skipped[0]["reason"], "quota_snapshot_malformed")

    def test_gate_models_allows_stale_transient_exhaustion_without_reset(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
            old = (now - timedelta(seconds=600)).isoformat().replace("+00:00", "Z")
            transient = {"model": "grok-4", "provider": "xai", "status": "exhausted", "quota_type": "rate_limit_window", "last_updated": old, "stale_after_seconds": 300}
            allowed, skipped = mq.gate_models(["grok-4"], {"xai::grok-4": transient}, providers={"grok-4": "xai"}, now=now)
            self.assertEqual(allowed, ["grok-4"])
            self.assertEqual(skipped, [])
            self.assertEqual(transient["status"], "stale_exhausted")

            billing = {"model": "deepseek-v4-pro", "provider": "deepseek", "status": "exhausted", "quota_type": "billing_balance", "last_updated": old, "stale_after_seconds": 300}
            allowed, skipped = mq.gate_models(["deepseek-v4-pro"], {"deepseek::deepseek-v4-pro": billing}, providers={"deepseek-v4-pro": "deepseek"}, now=now)
            self.assertEqual(allowed, [])
            self.assertEqual(skipped[0]["model"], "deepseek-v4-pro")

    def test_malformed_quota_threshold_env_does_not_disable_module_import(self):
        old_token = os.environ.get("HERMES_QUOTA_LOW_TOKEN_THRESHOLD")
        old_request = os.environ.get("HERMES_QUOTA_LOW_REQUEST_THRESHOLD")
        os.environ["HERMES_QUOTA_LOW_TOKEN_THRESHOLD"] = "1e309"
        os.environ["HERMES_QUOTA_LOW_REQUEST_THRESHOLD"] = "NaN"
        try:
            with tempfile.TemporaryDirectory() as td:
                mq = load_model_quota(td)
                snap = mq.snapshot_from_headers(
                    model="claude-opus-4-7",
                    provider="anthropic",
                    headers={"x-ratelimit-remaining-tokens": "1", "x-ratelimit-remaining-requests": "1"},
                )
                self.assertEqual(snap["status"], "low")
        finally:
            if old_token is None:
                os.environ.pop("HERMES_QUOTA_LOW_TOKEN_THRESHOLD", None)
            else:
                os.environ["HERMES_QUOTA_LOW_TOKEN_THRESHOLD"] = old_token
            if old_request is None:
                os.environ.pop("HERMES_QUOTA_LOW_REQUEST_THRESHOLD", None)
            else:
                os.environ["HERMES_QUOTA_LOW_REQUEST_THRESHOLD"] = old_request

    def test_gate_models_rejects_malformed_or_unknown_status_values(self):
        for bad_status in (True, False, None, 3, "", "definitely_ok"):
            with self.subTest(status=bad_status):
                with tempfile.TemporaryDirectory() as td:
                    mq = load_model_quota(td)
                    snapshots = {
                        "openai-codex::gpt-5.5": {
                            "model": "gpt-5.5",
                            "provider": "openai-codex",
                            "status": bad_status,
                        }
                    }
                    allowed, skipped = mq.gate_models(["gpt-5.5"], snapshots, providers={"gpt-5.5": "openai-codex"})
                    self.assertEqual(allowed, [])
                    self.assertEqual(skipped[0]["reason"], "quota_snapshot_malformed_status")

    def test_gate_models_rejects_exact_key_dict_with_missing_or_mismatched_fields(self):
        bad_snapshots = [
            {"status": "ok"},
            {"model": "other-model", "provider": "xai", "status": "ok"},
            {"model": "grok-code", "provider": "other-provider", "status": "ok"},
        ]
        for snap in bad_snapshots:
            with self.subTest(snapshot=snap):
                with tempfile.TemporaryDirectory() as td:
                    mq = load_model_quota(td)
                    allowed, skipped = mq.gate_models(
                        ["grok-code"],
                        {"xai::grok-code": snap},
                        providers={"grok-code": "xai"},
                    )
                    self.assertEqual(allowed, [])
                    self.assertEqual(skipped[0]["reason"], "quota_snapshot_malformed")

    def test_gate_models_skips_all_models_when_snapshot_container_is_malformed(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            for malformed in ([], "not-a-dict"):
                with self.subTest(snapshot=malformed):
                    allowed, skipped = mq.gate_models(["gpt-5.5"], malformed, providers={"gpt-5.5": "openai-codex"})
                    self.assertEqual(allowed, [])
                    self.assertEqual(skipped[0]["reason"], "quota_snapshot_malformed")

    def test_gate_models_reconciles_mismatched_snapshot_key_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            snapshots = {
                "unknown::grok-code": {"model": "grok-code", "provider": "unknown", "status": "exhausted"}
            }
            allowed, skipped = mq.gate_models(["grok-code"], snapshots, providers={"grok-code": "xai"})
            self.assertEqual(allowed, [])
            self.assertEqual(skipped[0]["reason"], "quota_exhausted")
            self.assertEqual(skipped[0]["snapshot"].get("reconciled_from_key"), "unknown::grok-code")

    def test_snapshot_models_reconciles_mismatched_provider_key_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "model_quota_state.json"
            state_path.write_text(json.dumps({
                "unknown::grok-code": {"model": "grok-code", "provider": "unknown", "status": "exhausted"}
            }), encoding="utf-8")
            mq = load_model_quota(td)
            snapshots = mq.snapshot_models(
                ["grok-code"],
                state_path=str(state_path),
                providers={"grok-code": "xai"},
            )
            self.assertIn("xai::grok-code", snapshots)
            self.assertEqual(snapshots["xai::grok-code"]["status"], "exhausted")
            allowed, skipped = mq.gate_models(["grok-code"], snapshots, providers={"grok-code": "xai"})
            self.assertEqual(allowed, [])
            self.assertEqual(skipped[0]["reason"], "quota_exhausted")
            self.assertEqual(skipped[0]["snapshot"].get("reconciled_from_key"), "unknown::grok-code")

    def test_snapshot_models_fails_closed_on_exact_malformed_state_entry(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "model_quota_state.json"
            state_path.write_text(json.dumps({"xai::grok-code": "not-a-dict"}), encoding="utf-8")
            mq = load_model_quota(td)
            snapshots = mq.snapshot_models(
                ["grok-code"],
                state_path=str(state_path),
                providers={"grok-code": "xai"},
            )
            self.assertEqual(snapshots["xai::grok-code"]["status"], "malformed")
            allowed, skipped = mq.gate_models(["grok-code"], snapshots, providers={"grok-code": "xai"})
            self.assertEqual(allowed, [])
            self.assertEqual(skipped[0]["reason"], "quota_snapshot_malformed")

    def test_snapshot_models_fails_closed_on_exact_dict_with_missing_or_mismatched_fields(self):
        bad_entries = [
            {},
            {"model": "grok-code", "provider": "xai"},
            {"model": "other-model", "provider": "xai", "status": "ok"},
            {"model": "grok-code", "provider": "unknown", "status": "ok"},
        ]
        for entry in bad_entries:
            with self.subTest(entry=entry):
                with tempfile.TemporaryDirectory() as td:
                    state_path = Path(td) / "model_quota_state.json"
                    state_path.write_text(json.dumps({"xai::grok-code": entry}), encoding="utf-8")
                    mq = load_model_quota(td)
                    snapshots = mq.snapshot_models(
                        ["grok-code"],
                        state_path=str(state_path),
                        providers={"grok-code": "xai"},
                    )
                    self.assertEqual(snapshots["xai::grok-code"]["status"], "malformed")
                    allowed, skipped = mq.gate_models(["grok-code"], snapshots, providers={"grok-code": "xai"})
                    self.assertEqual(allowed, [])
                    self.assertEqual(skipped[0]["reason"], "quota_snapshot_malformed")

    def test_malformed_quota_state_file_fails_closed_for_snapshot_models(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "model_quota_state.json"
            state_path.write_text("{not-json", encoding="utf-8")
            mq = load_model_quota(td)
            snapshots = mq.snapshot_models(["gpt-5.5"], state_path=str(state_path))
            allowed, skipped = mq.gate_models(["gpt-5.5"], snapshots)
            self.assertEqual(allowed, [])
            self.assertEqual(skipped[0]["model"], "gpt-5.5")
            self.assertEqual(skipped[0]["reason"], "quota_state_malformed")
            self.assertEqual(skipped[0]["snapshot"]["status"], "malformed")

    def test_null_quota_state_file_fails_closed_for_snapshot_models(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "model_quota_state.json"
            state_path.write_text("null", encoding="utf-8")
            mq = load_model_quota(td)
            snapshots = mq.snapshot_models(["gpt-5.5"], state_path=str(state_path))
            allowed, skipped = mq.gate_models(["gpt-5.5"], snapshots)
            self.assertEqual(allowed, [])
            self.assertEqual(skipped[0]["model"], "gpt-5.5")
            self.assertEqual(skipped[0]["reason"], "quota_state_malformed")
            self.assertEqual(skipped[0]["snapshot"].get("state_error", {}).get("reason"), "null_state")

    def test_deepseek_balance_probe_rejects_nonfinite_amounts(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps({"is_available": True, "balance_infos": [{"total_balance": "1e309"}]}).encode("utf-8")

        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            with mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}, clear=False):
                with mock.patch.object(mq.urllib.request, "urlopen", return_value=FakeResponse()):
                    snap = mq.probe_deepseek_balance()
            self.assertEqual(snap["status"], "unknown")
            self.assertEqual(snap["observability"], "unknown")
            self.assertIsNone(snap["remaining_usd"])

    def test_gate_models_allows_elapsed_reset_but_skips_future_reset(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            now = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)
            past = (now - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
            future = (now + timedelta(seconds=300)).isoformat().replace("+00:00", "Z")
            snapshots = {
                "anthropic::claude-opus-4-7": {"model": "claude-opus-4-7", "provider": "anthropic", "status": "exhausted", "reset_at": past},
                "deepseek::deepseek-v4-pro": {"model": "deepseek-v4-pro", "provider": "deepseek", "status": "exhausted", "reset_at": future},
            }
            allowed, skipped = mq.gate_models(
                ["claude-opus-4-7", "deepseek-v4-pro"],
                snapshots,
                providers={"claude-opus-4-7": "anthropic", "deepseek-v4-pro": "deepseek"},
                now=now,
            )
            self.assertEqual(allowed, ["claude-opus-4-7"])
            self.assertEqual(skipped[0]["model"], "deepseek-v4-pro")
            self.assertEqual(skipped[0]["reason"], "quota_exhausted_until_reset")
            self.assertEqual(skipped[0]["seconds_until_reset"], 300)

    def test_quota_confidence_gate_fails_closed_for_unknown_or_unobservable(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            report = mq.assess_quota_confidence(["gpt-5.5", "deepseek-v4-pro"], min_confidence=0.5)
            self.assertFalse(report["ok"])
            self.assertEqual(report["status"], "FAIL_CLOSED")
            self.assertIn("observability_evidence", report)
            evidence = report["observability_evidence"]
            self.assertEqual(evidence["counts"]["total"], 2)
            self.assertEqual(evidence["counts"]["usable"], 0)
            self.assertEqual(evidence["counts"]["unobservable"], 1)
            self.assertEqual(evidence["counts"]["unknown"], 1)
            self.assertIn("manual_budget_confirmation_or_lower_risk_tier", evidence["refresh_actions"])
            self.assertIn("probe_deepseek_balance", evidence["refresh_actions"])
            statuses = {item["model"]: item["status"] for item in report["failures"]}
            self.assertEqual(statuses["gpt-5.5"], "unobservable")
            self.assertEqual(statuses["deepseek-v4-pro"], "unknown")

    def test_quota_confidence_gate_passes_for_exact_confident_ok_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            state_dir = Path(td) / "state"
            state_dir.mkdir(parents=True)
            (state_dir / "model_quota_state.json").write_text(json.dumps({
                "deepseek::deepseek-v4-pro": {
                    "model": "deepseek-v4-pro", "provider": "deepseek", "status": "ok",
                    "observability": "exact", "quota_type": "billing_balance", "confidence": 0.9,
                    "last_updated": datetime.now(timezone.utc).isoformat(), "stale_after_seconds": 300,
                }
            }), encoding="utf-8")
            mq = load_model_quota(td)
            report = mq.assess_quota_confidence(["deepseek-v4-pro"], min_confidence=0.5)
            self.assertTrue(report["ok"])
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["observability_evidence"]["counts"]["total"], 1)
            self.assertEqual(report["observability_evidence"]["counts"]["usable"], 1)

    def test_quota_confidence_gate_fails_closed_for_stale_exact_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            state_dir = Path(td) / "state"
            state_dir.mkdir(parents=True)
            stale = datetime.now(timezone.utc) - timedelta(hours=1)
            (state_dir / "model_quota_state.json").write_text(json.dumps({
                "deepseek::deepseek-v4-pro": {
                    "model": "deepseek-v4-pro", "provider": "deepseek", "status": "ok",
                    "observability": "exact", "quota_type": "billing_balance", "confidence": 0.9,
                    "last_updated": stale.isoformat(), "stale_after_seconds": 300,
                }
            }), encoding="utf-8")
            mq = load_model_quota(td)
            report = mq.assess_quota_confidence(["deepseek-v4-pro"], min_confidence=0.5)
            self.assertFalse(report["ok"])
            self.assertEqual(report["status"], "FAIL_CLOSED")
            self.assertEqual(report["failures"][0]["reasons"], ["stale_quota_evidence"])
            self.assertTrue(report["observability_evidence"]["by_model"]["deepseek::deepseek-v4-pro"]["stale"])

    def test_quota_confidence_gate_fails_closed_for_missing_quota_timestamp(self):
        with tempfile.TemporaryDirectory() as td:
            state_dir = Path(td) / "state"
            state_dir.mkdir(parents=True)
            (state_dir / "model_quota_state.json").write_text(json.dumps({
                "deepseek::deepseek-v4-pro": {
                    "model": "deepseek-v4-pro", "provider": "deepseek", "status": "ok",
                    "observability": "exact", "quota_type": "billing_balance", "confidence": 0.9,
                }
            }), encoding="utf-8")
            mq = load_model_quota(td)
            report = mq.assess_quota_confidence(["deepseek-v4-pro"], min_confidence=0.5)
            self.assertFalse(report["ok"])
            self.assertEqual(report["status"], "FAIL_CLOSED")
            self.assertEqual(report["failures"][0]["reasons"], ["missing_quota_timestamp"])
    def test_record_snapshot_preserves_fresh_exact_balance_from_empty_response_headers(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            state_path = str(Path(td) / "state" / "model_quota_state.json")
            log_path = str(Path(td) / "logs" / "model-quota.jsonl")
            exact = {
                "model": "deepseek-v4-pro",
                "provider": "deepseek",
                "status": "ok",
                "observability": "exact",
                "quota_type": "billing_balance",
                "remaining_usd": 34.98,
                "confidence": 0.85,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "stale_after_seconds": 300,
                "source": "balance_endpoint",
            }
            mq.record_snapshot(exact, state_path=state_path, log_path=log_path)
            preserved = mq.record_call(
                model="deepseek-v4-pro",
                provider="deepseek",
                ok=True,
                headers={"date": "Sat, 09 May 2026 08:52:00 GMT"},
                usage={"prompt_tokens": 28, "completion_tokens": 2},
                state_path=state_path,
                log_path=log_path,
            )
            self.assertEqual(preserved["observability"], "exact")
            self.assertEqual(preserved["remaining_usd"], 34.98)
            self.assertTrue(preserved["preserved_from_lower_confidence_update"])
            state = json.loads(Path(state_path).read_text())
            self.assertEqual(state["deepseek::deepseek-v4-pro"]["observability"], "exact")
            self.assertNotIn("preserved_from_lower_confidence_update", state["deepseek::deepseek-v4-pro"])

    def test_record_snapshot_allows_safety_blocker_to_replace_exact_balance(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            state_path = str(Path(td) / "state" / "model_quota_state.json")
            exact = {
                "model": "deepseek-v4-pro",
                "provider": "deepseek",
                "status": "ok",
                "observability": "exact",
                "quota_type": "billing_balance",
                "remaining_usd": 34.98,
                "confidence": 0.85,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "stale_after_seconds": 300,
                "source": "balance_endpoint",
            }
            mq.record_snapshot(exact, state_path=state_path)
            blocker = mq.record_call(
                model="deepseek-v4-pro",
                provider="deepseek",
                ok=False,
                headers={"retry-after": "60"},
                error="HTTP 429 rate_limit exceeded",
                state_path=state_path,
            )
            self.assertEqual(blocker["status"], "exhausted")
            self.assertEqual(blocker["error_class"], "rate_limit")
            state = json.loads(Path(state_path).read_text())
            self.assertEqual(state["deepseek::deepseek-v4-pro"]["status"], "exhausted")
    def test_unobservable_success_snapshot_is_actionable_but_not_budget_ready(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            snap = mq.snapshot_unobservable_success(
                "mimo-v2.5-pro",
                "xiaomi",
                source="direct_api_no_quota_headers",
                quota_type="provider_api_no_quota_headers",
                header_names=["Date", "X-Mife-Upstream-Status"],
                usage={"prompt_tokens": 10, "completion_tokens": 2},
            )
            self.assertEqual(snap["status"], "unobservable")
            self.assertEqual(snap["observability"], "unobservable")
            self.assertLess(snap["confidence"], 0.5)
            mq.record_snapshot(snap)
            report = mq.assess_quota_confidence(["mimo-v2.5-pro"], providers={"mimo-v2.5-pro": "xiaomi"})
            self.assertFalse(report["ok"])
            self.assertEqual(report["failures"][0]["reasons"], ["status_unobservable", "low_confidence"])
            evidence = mq.quota_observability_evidence({"xiaomi::mimo-v2.5-pro": snap})
            self.assertEqual(
                evidence["by_model"]["xiaomi::mimo-v2.5-pro"]["refresh_action"],
                "provider_unobservable_lower_risk_tier_or_documented_policy",
            )

    def test_unobservable_success_does_not_downgrade_fresh_exact_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            mq = load_model_quota(td)
            state_path = str(Path(td) / "state" / "model_quota_state.json")
            exact = {
                "model": "deepseek-v4-pro",
                "provider": "deepseek",
                "status": "ok",
                "observability": "exact",
                "quota_type": "billing_balance",
                "remaining_usd": 34.98,
                "confidence": 0.85,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "stale_after_seconds": 300,
                "source": "balance_endpoint",
            }
            mq.record_snapshot(exact, state_path=state_path)
            unobservable = mq.snapshot_unobservable_success(
                "deepseek-v4-pro",
                "deepseek",
                source="direct_api_no_quota_headers",
                quota_type="provider_api_no_quota_headers",
            )
            preserved = mq.record_snapshot(unobservable, state_path=state_path)
            self.assertEqual(preserved["observability"], "exact")
            self.assertTrue(preserved["preserved_from_lower_confidence_update"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
