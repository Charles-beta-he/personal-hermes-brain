#!/usr/bin/env python3
"""Integration tests for consult_models.py planner dispatch logic."""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

SCRIPT = Path(__file__).parent / "consult_models.py"
spec = importlib.util.spec_from_file_location("consult_models", SCRIPT)
consult = importlib.util.module_from_spec(spec)
spec.loader.exec_module(consult)


class TestConsultModelsIntegration(unittest.TestCase):
    def test_env_int_falls_back_on_invalid_value(self):
        """Invalid env integer values should not crash import-time config helpers."""
        self.assertEqual(consult._env_int("__HERMES_TEST_MISSING_INT__", "123"), 123)
        os.environ["__HERMES_TEST_BAD_INT__"] = "not-an-int"
        try:
            self.assertEqual(consult._env_int("__HERMES_TEST_BAD_INT__", "456"), 456)
        finally:
            os.environ.pop("__HERMES_TEST_BAD_INT__", None)

    def test_truth_gate_summary_handles_non_dict_inputs(self):
        """Communication packet truth gate summaries should defensively handle malformed values."""
        self.assertEqual(consult._summarize_truth_gate("bad"), {})

    def test_safe_numeric_parsers_reject_bool_and_nonfinite_values(self):
        """Certification-critical numeric parsing must fail closed on bool/NaN/Infinity."""
        self.assertEqual(consult._safe_int(True, 3), 3)
        self.assertEqual(consult._safe_int(False, 3), 3)
        self.assertEqual(consult._safe_int(float("inf"), 3), 3)
        self.assertEqual(consult._safe_float(True, 0.0), 0.0)
        self.assertEqual(consult._safe_float(False, 0.0), 0.0)
        self.assertEqual(consult._safe_float(float("nan"), 0.0), 0.0)
        self.assertEqual(consult._safe_float(float("inf"), 0.0), 0.0)
        self.assertEqual(consult._safe_float(float("-inf"), 0.0), 0.0)

    def test_evidence_verification_canonicalizes_kind_and_type_independently(self):
        self.assertFalse(consult._evidence_counts_as_verification({"kind": "   ", "type": " gate_requirement "}))
        self.assertFalse(consult._evidence_counts_as_verification({"kind": " policy ", "type": "command_output"}))
        self.assertFalse(consult._evidence_counts_as_verification({"kind": " provenance ", "type": "command_output"}))
        self.assertFalse(consult._evidence_counts_as_verification({"kind": "command_output", "type": " provenance_only "}))
        self.assertFalse(consult._evidence_counts_as_verification({"kind": " POLICY_ONLY ", "type": "artifact"}))
        self.assertTrue(consult._evidence_counts_as_verification({"kind": " command_output ", "type": "artifact"}))

    def test_model_provider_resolves_gpt55(self):
        """model_provider() should resolve gpt-5.5 to openai-codex"""
        config = {"pricing": {"models": {"gpt-5.5": {"provider": "openai-codex"}}}}
        result = consult.model_provider(config, "gpt-5.5")
        self.assertEqual(result, "openai-codex")

    def test_model_provider_resolves_mimo(self):
        """model_provider() should resolve mimo-v2.5-pro to xiaomi"""
        config = {"pricing": {"models": {"mimo-v2.5-pro": {"provider": "xiaomi"}}}}
        result = consult.model_provider(config, "mimo-v2.5-pro")
        self.assertEqual(result, "xiaomi")

    def test_model_provider_unknown_returns_empty(self):
        """model_provider() returns '' for unknown model"""
        config = {"pricing": {"models": {}}}
        result = consult.model_provider(config, "unknown-model")
        self.assertEqual(result, "")

    def test_quorum_config_loads(self):
        """quorum.yaml should load with multi_brain enabled"""
        quorum_path = Path(os.path.expanduser("~/.hermes/config/quorum.yaml"))
        if not quorum_path.exists():
            self.skipTest("quorum.yaml not found")
        import yaml
        with open(quorum_path) as f:
            q = yaml.safe_load(f)
        self.assertIn("multi_brain", q)
        self.assertTrue(q["multi_brain"].get("enabled", False))
        self.assertIn("T1", q.get("tiers", {}))

    def _analysis_selfcheck_fixture(self):
        quorum = {
            "multi_brain": {"enabled": True, "shadow_mode": False, "default_arbiter": "claude-opus-4-7"},
            "tiers": {
                "T0": {"quorum": 1, "min_quorum": 1, "planners": ["mimo-v2.5-pro"], "diversity": "none"},
                "T1": {"quorum": 3, "min_quorum": 2, "planners": ["gpt-5.5", "mimo-v2.5-pro", "deepseek-v4-pro"], "diversity": "provider"},
                "T2": {"quorum": 4, "min_quorum": 2, "planners": ["gpt-5.5", "mimo-v2.5-pro", "claude-opus-4-7", "deepseek-v4-pro"], "diversity": "provider"},
                "T3": {"quorum": 4, "min_quorum": 2, "planners": ["claude-opus-4-7", "gpt-5.5", "deepseek-v4-pro", "mimo-v2.5-pro"], "diversity": "provider"},
            },
        }
        config = {"pricing": {"models": {
            "gpt-5.5": {"provider": "openai-codex"},
            "mimo-v2.5-pro": {"provider": "xiaomi"},
            "deepseek-v4-pro": {"provider": "deepseek"},
            "claude-opus-4-7": {"provider": "anthropic"},
        }}}
        return quorum, config

    def test_analysis_selfcheck_passes_with_valid_fixture(self):
        quorum, config = self._analysis_selfcheck_fixture()
        report = consult.run_analysis_selfcheck(quorum=quorum, config=config, include_temp_audit=True)

        self.assertEqual(report["schema_version"], "multi_model_analysis_selfcheck_v1")
        self.assertEqual(report["status"], "PASS", [c for c in report["checks"] if not c["ok"]])
        self.assertEqual(report["summary"]["failed"], 0)
        self.assertEqual(report["fanout_matrix"]["below_min"]["status"], "degraded_not_certified")
        self.assertEqual(report["truth_gate_matrix"]["needs_link_review"]["truth_status"], "needs_link_review")
        self.assertEqual(report.get("temp_audit_manifest_status"), "certified")

    def test_analysis_selfcheck_fails_closed_for_solo_t1_and_duplicate_provider(self):
        quorum, config = self._analysis_selfcheck_fixture()
        quorum["tiers"]["T1"]["min_quorum"] = 1
        config["pricing"]["models"]["deepseek-v4-pro"]["provider"] = "xiaomi"

        report = consult.run_analysis_selfcheck(quorum=quorum, config=config, include_temp_audit=False)

        self.assertEqual(report["status"], "FAIL")
        failed_names = {check["name"] for check in report["checks"] if not check["ok"]}
        self.assertIn("T1_not_solo_certifiable", failed_names)
        self.assertIn("T1_provider_diversity", failed_names)

    def test_fanout_certification_handles_bad_numeric_inputs_fail_closed(self):
        status = consult.fanout_certification_status("bad", "bad", "bad", "bad")
        ok, errors = consult.validate_fanout_certification_status(status)

        self.assertTrue(ok, errors)
        self.assertEqual(status["status"], "degraded_not_certified")
        self.assertFalse(status["certified"])
        self.assertFalse(status["multi_model_certified"])

    def test_fanout_certification_rejects_impossible_count_relationships(self):
        impossible_cases = [
            consult.fanout_certification_status(3, 2, 2, 0),
            consult.fanout_certification_status(2, 0, 1, 0),
            consult.fanout_certification_status(1, 2, 1, 2),
        ]
        for status in impossible_cases:
            with self.subTest(status=status):
                ok, errors = consult.validate_fanout_certification_status(status)
                self.assertFalse(status["certified"])
                self.assertFalse(status["multi_model_certified"])
                self.assertEqual(status["status"], "degraded_not_certified")
                self.assertFalse(ok)
                self.assertTrue(errors)

    def test_fanout_validator_rejects_handcrafted_false_certification_counts(self):
        status = consult.fanout_certification_status(2, 2, 2, 0)
        status["planner_count"] = 0
        status["certified"] = True
        status["multi_model_certified"] = True

        ok, errors = consult.validate_fanout_certification_status(status)

        self.assertFalse(ok)
        self.assertIn("success_count cannot exceed planner_count", errors)
        self.assertIn("certified fanout requires planner_count >= 1", errors)

    def test_fanout_validator_rejects_malformed_counts_without_crashing(self):
        status = consult.fanout_certification_status(2, 2, 2, 0)
        status["success_count"] = "2"
        status["multi_model_certified"] = True

        ok, errors = consult.validate_fanout_certification_status(status)

        self.assertFalse(ok)
        self.assertIn("success_count must be non-negative integer", errors)

    def test_fanout_validator_rejects_handcrafted_cross_field_inconsistencies(self):
        base = consult.fanout_certification_status(2, 2, 2, 0)
        cases = []
        mutated = dict(base)
        mutated["certified"] = False
        mutated["multi_model_certified"] = True
        cases.append((mutated, "multi_model_certified requires certified=true"))
        mutated = dict(base)
        mutated["status"] = "single_model_quorum_met"
        mutated["multi_model_certified"] = True
        cases.append((mutated, "single_model_quorum_met cannot be multi_model_certified"))
        mutated = dict(base)
        mutated["status"] = "fanout_quorum_met"
        mutated["certified"] = False
        cases.append((mutated, "fanout_quorum_met requires certified=true"))

        for status, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                ok, errors = consult.validate_fanout_certification_status(status)
                self.assertFalse(ok)
                self.assertIn(expected_error, errors)

    def test_quorum_t1_has_two_planners(self):
        """T1 should have at least 2 planners for diversity"""
        quorum_path = Path(os.path.expanduser("~/.hermes/config/quorum.yaml"))
        if not quorum_path.exists():
            self.skipTest("quorum.yaml not found")
        import yaml
        with open(quorum_path) as f:
            q = yaml.safe_load(f)
        t1_planners = q.get("tiers", {}).get("T1", {}).get("planners", [])
        self.assertGreaterEqual(len(t1_planners), 2, f"T1 planners={t1_planners}, need >= 2")

    def test_quorum_t1_min_quorum_requires_two_models(self):
        """T1 should not certify with only one successful planner"""
        quorum_path = Path(os.path.expanduser("~/.hermes/config/quorum.yaml"))
        if not quorum_path.exists():
            self.skipTest("quorum.yaml not found")
        import yaml
        with open(quorum_path) as f:
            q = yaml.safe_load(f)
        t1 = q.get("tiers", {}).get("T1", {})
        self.assertGreaterEqual(t1.get("min_quorum", 0), 2, f"T1 min_quorum={t1.get('min_quorum')}, need >= 2")

    def test_fanout_below_min_quorum_is_degraded_not_certified(self):
        """A fan-out below min_quorum should be auditable as degraded_not_certified."""
        status = consult.fanout_certification_status(success_count=1, planner_count=3, min_quorum=2, fail_count=2)
        self.assertEqual(status["status"], "degraded_not_certified")
        self.assertFalse(status["certified"])
        self.assertTrue(status["below_min_quorum"])
        self.assertIn("reason", status)
        self.assertIn("below min_quorum", status["reason"])

    def test_fanout_single_planner_is_not_multi_model_certified(self):
        """T0/single-planner fan-out can be useful, but must not claim multi-model certification."""
        status = consult.fanout_certification_status(success_count=1, planner_count=1, min_quorum=1, fail_count=0)
        self.assertEqual(status["status"], "single_model_quorum_met")
        self.assertTrue(status["certified"])
        self.assertFalse(status["multi_model_certified"])
        self.assertEqual(status["certification_scope"], "single_model")
        self.assertIn("single planner", status["reason"])

    def test_fanout_certification_status_has_schema_required_fields(self):
        """Fan-out certification objects should be schema-checkable before artifact write."""
        status = consult.fanout_certification_status(success_count=2, planner_count=3, min_quorum=2, fail_count=1)
        ok, errors = consult.validate_fanout_certification_status(status)
        self.assertTrue(ok, errors)
        for key in (
            "schema_version", "status", "certified", "multi_model_certified",
            "certification_scope", "below_min_quorum", "success_count", "fail_count",
            "planner_count", "min_quorum", "reason",
        ):
            self.assertIn(key, status)

    def test_fanout_certification_schema_file_is_parseable(self):
        """The operational JSON schema for fanout_certification should exist and match code constants."""
        schema_path = Path(os.path.expanduser("~/.hermes/schemas/fanout-certification.schema.json"))
        self.assertTrue(schema_path.exists(), f"missing schema file: {schema_path}")
        schema = json.loads(schema_path.read_text())
        self.assertEqual(schema["properties"]["schema_version"]["const"], consult.FANOUT_CERTIFICATION_SCHEMA_VERSION)
        for key in consult.FANOUT_CERTIFICATION_REQUIRED_FIELDS:
            self.assertIn(key, schema["required"])

    def test_quota_observability_summary_flags_unknown_and_unobservable(self):
        """Unknown/unobservable quota should be surfaced as low-confidence, not silently healthy."""
        attached = {
            "openai-codex::gpt-5.5": {"model": "gpt-5.5", "status": "unobservable", "observability": "unobservable"},
            "deepseek::deepseek-v4-pro": {"model": "deepseek-v4-pro", "status": "unknown", "observability": "unknown"},
            "anthropic::claude-opus-4-7": {"model": "claude-opus-4-7", "status": "ok", "observability": "exact"},
        }
        summary = consult.quota_observability_summary(attached)
        self.assertEqual(summary["unknown_count"], 1)
        self.assertEqual(summary["unobservable_count"], 1)
        self.assertEqual(summary["exact_count"], 1)
        self.assertTrue(summary["has_low_confidence_quota"])
        self.assertIn("gpt-5.5", summary["low_confidence_models"])
        self.assertIn("deepseek-v4-pro", summary["low_confidence_models"])

    def test_quorum_t1_diversity_is_provider(self):
        """T1 diversity rule should be 'provider'"""
        quorum_path = Path(os.path.expanduser("~/.hermes/config/quorum.yaml"))
        if not quorum_path.exists():
            self.skipTest("quorum.yaml not found")
        import yaml
        with open(quorum_path) as f:
            q = yaml.safe_load(f)
        diversity = q.get("tiers", {}).get("T1", {}).get("diversity", "")
        self.assertEqual(diversity, "provider")

    def test_build_state_marks_state_as_facts_not_solution(self):
        """Main orchestrator state.json should define facts/bounds, not final candidate solution."""
        state = consult.build_state(
            question="Implement true multi-model discussion",
            context={"repo": "~/.hermes/scripts"},
            constraints=["use four models"],
            acceptance_criteria=["ratification gates pass"],
            implementation_target={"files": ["consult_models.py"], "verify_commands": ["python3 -m unittest"]},
        )
        self.assertEqual(state["schema"], "multi_model_state_v1")
        self.assertEqual(state["question"], "Implement true multi-model discussion")
        self.assertIn("implementation_target", state)
        self.assertFalse(state.get("is_candidate_solution"))
        self.assertIn("verify_commands", state["implementation_target"])

    def test_issue_ledger_detects_conflicting_patch_ids(self):
        """Discussion should start from an explicit disagreement ledger across model plans."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": [{"id": "A", "target_file": "x.py", "op": "add_verifier", "rationale": "r1"}]},
            {"meta": {"planner_model": "codex"}, "patches": [{"id": "B", "target_file": "x.py", "op": "modify_router_weight", "rationale": "r2"}]},
        ]
        issues = consult.build_issue_ledger(plans)
        self.assertGreaterEqual(len(issues), 1)
        self.assertEqual(issues[0]["status"], "unresolved")
        self.assertGreaterEqual(issues[0]["severity"], 3)
        self.assertIn("claude", issues[0]["models"])
        self.assertIn("codex", issues[0]["models"])

    def test_issue_ledger_ignores_noop_patch_disagreements(self):
        """No-op certification patches are not implementation disagreements or blockers."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": [{"id": "noop-a", "target_file": "x.py", "op": "noop", "rationale": "already verified"}]},
            {"meta": {"planner_model": "codex"}, "patches": [{"id": "noop-b", "target_file": "x.py", "op": "noop", "rationale": "no source change"}]},
            {"meta": {"planner_model": "deepseek"}, "patches": []},
            {"meta": {"planner_model": "mimo"}, "patches": [{"id": "noop-c", "target_file": "x.py", "op": "noop", "rationale": "certify"}]},
        ]
        self.assertEqual(consult.build_issue_ledger(plans), [])

    def test_issue_ledger_flags_noop_vs_real_change_disagreement(self):
        """A balanced noop/change split remains a real disagreement."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": [{"id": "noop-a", "op": "noop", "rationale": "already verified"}]},
            {"meta": {"planner_model": "codex"}, "patches": [{"id": "A", "target_file": "x.py", "op": "add_verifier", "rationale": "needed"}]},
        ]
        issues = consult.build_issue_ledger(plans)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["target_file"], "<mixed-noop-vs-change>")
        self.assertIn("claude", issues[0]["missing_models"])

    def test_issue_ledger_does_not_block_on_conditional_advisory_under_noop_supermajority(self):
        """N-1 noop/no-change votes make a minority conditional advisory non-blocking."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": [{"id": "noop-a", "op": "noop", "rationale": "already verified"}]},
            {"meta": {"planner_model": "gpt"}, "patches": [{"id": "A", "target_file": "x.py", "op": "add_verifier", "rationale": "optional follow-up only if missing"}]},
            {"meta": {"planner_model": "deepseek"}, "patches": [{"id": "noop-b", "op": "noop", "rationale": "no source change"}]},
            {"meta": {"planner_model": "mimo"}, "patches": [{"id": "noop-c", "op": "noop", "rationale": "certify"}]},
        ]
        self.assertEqual(consult.build_issue_ledger(plans), [])

    def test_issue_ledger_blocks_unconditional_minority_patch_under_noop_supermajority(self):
        """N-1 noop/no-change votes must not hide a concrete minority implementation patch."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": [{"id": "noop-a", "op": "noop", "rationale": "already verified"}]},
            {"meta": {"planner_model": "gpt"}, "patches": [{"id": "A", "target_file": "x.py", "op": "add_verifier", "rationale": "missing regression test must be added"}]},
            {"meta": {"planner_model": "deepseek"}, "patches": [{"id": "noop-b", "op": "noop", "rationale": "no source change"}]},
            {"meta": {"planner_model": "mimo"}, "patches": [{"id": "noop-c", "op": "noop", "rationale": "certify"}]},
        ]
        issues = consult.build_issue_ledger(plans)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["target_file"], "<mixed-noop-vs-change>")
        self.assertIn("claude", issues[0]["missing_models"])

    def test_issue_ledger_treats_conditional_verifier_suggestions_as_advisory(self):
        """Conditional add_verifier proposals are evidence requests, not patch blockers."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": [{"id": "noop-a", "target_file": "x.py", "op": "noop", "rationale": "tests already prove it"}]},
            {"meta": {"planner_model": "codex"}, "patches": [{"id": "maybe-test", "target_file": "x.py", "op": "add_verifier", "rationale": "add verifier only if direct inspection shows the named test is missing"}]},
            {"meta": {"planner_model": "deepseek"}, "patches": [{"id": "maybe-test-2", "target_file": "x.py", "op": "add_verifier", "rationale": "conditional follow-up if fresh tick fails"}]},
            {"meta": {"planner_model": "mimo"}, "patches": []},
        ]
        self.assertEqual(consult.build_issue_ledger(plans), [])

    def test_issue_ledger_flags_unconditional_verifier_patch_vs_noop(self):
        """Concrete verifier additions still block a balanced noop/change split."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": [{"id": "noop-a", "target_file": "x.py", "op": "noop", "rationale": "certify"}]},
            {"meta": {"planner_model": "codex"}, "patches": [{"id": "add-test", "target_file": "x.py", "op": "add_verifier", "rationale": "missing regression test must be added"}]},
        ]
        issues = consult.build_issue_ledger(plans)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["target_file"], "<mixed-noop-vs-change>")

    def test_issue_ledger_flags_unconditional_verifier_patch_with_nonconditional_if_word(self):
        """The bare word 'if' in a concrete rationale must not make it advisory."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": [{"id": "noop-a", "target_file": "x.py", "op": "noop", "rationale": "certify"}]},
            {"meta": {"planner_model": "codex"}, "patches": [{"id": "add-test", "target_file": "x.py", "op": "add_verifier", "rationale": "add regression for if statement parsing"}]},
            {"meta": {"planner_model": "deepseek"}, "patches": [{"id": "noop-b", "target_file": "x.py", "op": "noop", "rationale": "already verified"}]},
            {"meta": {"planner_model": "mimo"}, "patches": []},
        ]
        issues = consult.build_issue_ledger(plans)
        self.assertTrue(any(issue.get("target_file") == "<mixed-noop-vs-change>" for issue in issues))

    def test_issue_ledger_flags_unconditional_verifier_patch_with_before_deciding_phrase(self):
        """Process phrases without explicit conditional wording must not make concrete verifier work advisory."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": [{"id": "noop-a", "target_file": "x.py", "op": "noop", "rationale": "certify"}]},
            {"meta": {"planner_model": "codex"}, "patches": [{"id": "add-test", "target_file": "x.py", "op": "add_verifier", "rationale": "add the regression verifier before deciding certification"}]},
            {"meta": {"planner_model": "deepseek"}, "patches": [{"id": "noop-b", "target_file": "x.py", "op": "noop", "rationale": "already verified"}]},
            {"meta": {"planner_model": "mimo"}, "patches": []},
        ]
        issues = consult.build_issue_ledger(plans)
        self.assertTrue(any(issue.get("target_file") == "<mixed-noop-vs-change>" for issue in issues))
        summary = consult._planner_patch_summary(plans)
        self.assertEqual(summary["concrete_patch_count"], 1)
        self.assertEqual(summary["conditional_advisory_patch_count"], 0)

    def test_planner_patch_summary_marks_no_action_certification_without_concrete_patches(self):
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": [{"op": "noop", "rationale": "certify"}]},
            {"meta": {"planner_model": "codex"}, "patches": [{"op": "add_verifier", "rationale": "add only if missing"}]},
        ]
        summary = consult._planner_patch_summary(plans)
        self.assertEqual(summary["certification_intent"], "no_action_certification")
        self.assertEqual(summary["concrete_patch_count"], 0)
        self.assertEqual(summary["noop_patch_count"], 1)
        self.assertEqual(summary["conditional_advisory_patch_count"], 1)

    def test_discussion_packet_explains_empty_patches_for_no_action_certification(self):
        current_best = {
            "patches": [],
            "planner_patch_summary": {"certification_intent": "no_action_certification", "concrete_patch_count": 0},
        }
        packet = consult.build_discussion_comm_packet(current_best, [], consult.build_evidence_bundle({}), {}, 1)
        self.assertEqual(packet["current_best_summary"]["planner_patch_summary"]["certification_intent"], "no_action_certification")
        self.assertTrue(any("empty current_best_summary.patches" in instruction for instruction in packet["instructions"]))

    def test_discussion_retries_unparseable_response_with_strict_json_prompt(self):
        """Transient empty/non-JSON discussion outputs should get one strict JSON retry before failing closed."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": []},
            {"meta": {"planner_model": "codex"}, "patches": []},
        ]
        calls = {"claude": 0, "codex": 0}

        def flaky_call(model, prompt):
            calls[model] += 1
            if calls[model] == 1:
                return ""
            self.assertIn("Return ONLY a JSON object", prompt)
            return '{"vote":"approve","best_within_constraints":true,"reasoning":"strict retry ok","critiques":[],"evidence_requests":[]}'

        result = consult.run_discussion_rounds(plans, current_best={"patches": []}, models=["claude", "codex"], max_rounds=1, call_model_fn=flaky_call)
        self.assertEqual(result["status"], "certified")
        self.assertEqual(calls, {"claude": 2, "codex": 2})

    def test_ratification_requires_no_rejects_and_no_unresolved_blockers(self):
        """Certification requires multi-party approval plus clean issue ledger."""
        votes = [
            {"model": "claude", "vote": "approve", "best_within_constraints": True},
            {"model": "codex", "vote": "approve", "best_within_constraints": True},
            {"model": "deepseek", "vote": "reject", "best_within_constraints": False},
            {"model": "mimo", "vote": "approve", "best_within_constraints": True},
        ]
        status = consult.evaluate_ratification(
            votes=votes,
            agreement_matrix={"framing": 0.9, "approach": 0.9, "implementation_order": 0.9},
            issue_ledger=[{"id": "I-1", "severity": 4, "status": "unresolved"}],
            revised_this_round=False,
            novel_redteam_blocker=False,
        )
        self.assertEqual(status["status"], "not_certified")
        self.assertIn("reject", " ".join(status["reasons"]))

    def test_run_discussion_offline_certifies_when_all_gates_clean(self):
        """Offline discussion runner should produce auditable ratification output without model calls."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": [{"id": "A", "target_file": "x.py", "op": "add_verifier"}]},
            {"meta": {"planner_model": "codex"}, "patches": [{"id": "A", "target_file": "x.py", "op": "add_verifier"}]},
            {"meta": {"planner_model": "deepseek"}, "patches": [{"id": "A", "target_file": "x.py", "op": "add_verifier"}]},
            {"meta": {"planner_model": "mimo"}, "patches": [{"id": "A", "target_file": "x.py", "op": "add_verifier"}]},
        ]
        result = consult.run_discussion_rounds(plans, current_best={"patches": plans[0]["patches"]}, models=["claude", "codex", "deepseek", "mimo"], offline=True)
        self.assertEqual(result["status"], "certified")
        self.assertEqual(len(result["ratification_votes"]), 4)
        self.assertEqual(result["rounds_used"], 1)

    def test_filter_planners_by_quota_skips_exhausted_and_reports_snapshot(self):
        """Fan-out should gate exhausted providers and preserve quota provenance for outputs."""
        config = {"pricing": {"models": {
            "claude-opus-4-7": {"provider": "anthropic"},
            "gpt-5.5": {"provider": "openai-codex"},
        }}}
        snapshots = {
            "anthropic::claude-opus-4-7": {"model": "claude-opus-4-7", "provider": "anthropic", "status": "exhausted", "reset_at": "2999-04-28T09:00:00Z"},
            "openai-codex::gpt-5.5": {"model": "gpt-5.5", "provider": "openai-codex", "status": "unobservable"},
        }
        allowed, skipped, attached = consult.filter_planners_by_quota(
            ["claude-opus-4-7", "gpt-5.5"], config=config, quota_snapshot=snapshots
        )
        self.assertEqual(allowed, ["gpt-5.5"])
        self.assertEqual(skipped[0]["model"], "claude-opus-4-7")
        self.assertEqual(skipped[0]["reason"], "quota_exhausted_until_reset")
        self.assertEqual(attached["openai-codex::gpt-5.5"]["observability"], "unobservable")

    def test_select_planners_gates_quota_before_quorum_trim(self):
        """Later healthy planners should backfill exhausted preferred planners before quorum trim."""
        config = {"pricing": {"models": {
            "claude-opus-4-7": {"provider": "anthropic"},
            "gpt-5.5": {"provider": "openai-codex"},
            "deepseek-v4-pro": {"provider": "deepseek"},
        }}}
        snapshots = {
            "anthropic::claude-opus-4-7": {"model": "claude-opus-4-7", "provider": "anthropic", "status": "exhausted"},
            "openai-codex::gpt-5.5": {"model": "gpt-5.5", "provider": "openai-codex", "status": "ok"},
            "deepseek::deepseek-v4-pro": {"model": "deepseek-v4-pro", "provider": "deepseek", "status": "ok"},
        }
        selected, skipped, attached = consult.select_planners_for_fanout(
            ["claude-opus-4-7", "gpt-5.5", "deepseek-v4-pro"],
            q_count=2,
            config=config,
            quota_snapshot=snapshots,
        )
        self.assertEqual(selected, ["gpt-5.5", "deepseek-v4-pro"])
        self.assertEqual(skipped[0]["model"], "claude-opus-4-7")
        self.assertIn("deepseek::deepseek-v4-pro", attached)

    def test_filter_planners_by_quota_allows_elapsed_reset_window(self):
        """Expired rate-limit resets should re-enter fan-out instead of staying skipped forever."""
        config = {"pricing": {"models": {
            "claude-opus-4-7": {"provider": "anthropic"},
            "gpt-5.5": {"provider": "openai-codex"},
        }}}
        snapshots = {
            "anthropic::claude-opus-4-7": {"model": "claude-opus-4-7", "provider": "anthropic", "status": "exhausted", "reset_at": "2000-01-01T00:00:00Z"},
            "openai-codex::gpt-5.5": {"model": "gpt-5.5", "provider": "openai-codex", "status": "ok"},
        }
        allowed, skipped, attached = consult.filter_planners_by_quota(
            ["claude-opus-4-7", "gpt-5.5"], config=config, quota_snapshot=snapshots
        )
        self.assertEqual(allowed, ["claude-opus-4-7", "gpt-5.5"])
        self.assertEqual(skipped, [])
        self.assertEqual(attached["anthropic::claude-opus-4-7"]["status"], "reset_elapsed")

    def test_planner_prompt_truncation_preserves_truth_gate_fields(self):
        """Oversized state prompts must not silently drop claims/evidence/truth_gate."""
        state = consult.build_state(
            question="large state",
            context={"blob": "x" * (consult.MAX_PLANNER_STATE_CHARS + 1000)},
            claims=[{"id": "C-KEEP", "text": "critical claim", "severity": 4}],
            evidence=[{"id": "E-KEEP", "type": "command", "summary": "critical evidence", "supports": ["C-KEEP"]}],
        )
        bundle = consult.build_evidence_bundle(state)
        state["evidence_bundle"] = bundle
        state["truth_gate"] = consult.evaluate_truth_gate(bundle)
        prompt = consult.build_planner_prompt(state, "hash", "model", "T3")
        self.assertIn("STATE_TRUNCATION_NOTICE", prompt)
        self.assertIn("C-KEEP", prompt)
        self.assertIn("E-KEEP", prompt)
        self.assertIn('"truth_gate"', prompt)
        self.assertIn('"state_truncated": true', prompt)

    def test_evidence_bundle_marks_unsupported_claims(self):
        """Truth gate should separate model agreement from evidence-backed truth."""
        state = {
            "claims": [
                {"id": "C-001", "text": "origin/main has no commits ahead of HEAD", "severity": 4},
                {"id": "C-002", "text": "self-test passed", "severity": 3},
            ],
            "evidence": [
                {"id": "E-001", "type": "command", "summary": "git rev-list HEAD..origin/main returned 0", "supports": ["C-001"], "exit_code": 0}
            ],
        }
        bundle = consult.build_evidence_bundle(state)
        self.assertEqual(bundle["schema_version"], consult.EVIDENCE_BUNDLE_SCHEMA_VERSION)
        self.assertEqual(bundle["grounding"]["C-001"]["truth_status"], "verified_by_evidence")
        self.assertEqual(bundle["grounding"]["C-002"]["truth_status"], "unsupported")
        gate = consult.evaluate_truth_gate(bundle)
        self.assertEqual(gate["truth_status"], "partially_grounded")
        self.assertFalse(gate["can_certify_truth"])
        self.assertIn("C-002", gate["unsupported_claim_ids"])

    def test_evidence_bundle_gate_requirement_does_not_verify_claim(self):
        """A gate requirement is an obligation, not proof that execution happened."""
        state = {
            "claims": [{"id": "C-GATE", "text": "final certification tick exists", "severity": 5}],
            "evidence": [{"id": "E-GATE", "kind": "   ", "type": " gate_requirement ", "summary": "must run T3", "supports": ["C-GATE"]}],
        }
        bundle = consult.build_evidence_bundle(state)
        self.assertEqual(bundle["grounding"]["C-GATE"]["truth_status"], "unsupported")
        self.assertEqual(bundle["grounding"]["C-GATE"]["supporting_evidence_ids"], [])
        self.assertEqual(bundle["grounding"]["C-GATE"]["non_verifying_supporting_evidence_ids"], ["E-GATE"])
        gate = consult.evaluate_truth_gate(bundle)
        self.assertFalse(gate["can_certify_truth"])
        self.assertIn("C-GATE", gate["unsupported_high_severity_claim_ids"])

    def test_evidence_requests_are_extracted_from_model_outputs(self):
        """Other brains should request evidence instead of claiming tool-verified truth."""
        outputs = [
            {"meta": {"planner_model": "deepseek"}, "evidence_requests": [
                {"claim_id": "C-007", "tool_needed": "terminal", "command": "git status --short", "why": "verify clean worktree"}
            ]},
            {"meta": {"planner_model": "mimo"}, "evidence_requests": [
                {"claim": "pytest passed", "tool_needed": "terminal", "command": "python3 -m pytest -q", "why": "confirm tests"}
            ]},
        ]
        requests = consult.collect_evidence_requests(outputs)
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["requested_by"], "deepseek")
        self.assertEqual(requests[0]["status"], "requested")
        self.assertIn("read_only", requests[0]["safety"])

    def test_evidence_request_scalar_container_is_one_malformed_request(self):
        requests = consult.collect_evidence_requests([
            {"meta": {"planner_model": "mimo"}, "evidence_requests": "not-a-list"},
            {"meta": {"planner_model": "deepseek"}, "diagnosis": {"evidence_requests": "also-bad"}},
        ])
        self.assertEqual(len(requests), 2)
        self.assertTrue(all(req.get("malformed_request") for req in requests))
        self.assertEqual([req["raw_type"] for req in requests], ["str", "str"])

    def test_evidence_fulfillment_allowlist_rejects_shell_and_credentials(self):
        state = consult.build_state(
            question="evidence execution safety",
            implementation_target={"files": [], "verify_commands": ["python3 scripts/test_consult_models_integration.py"], "forbidden_changes": []},
        )
        allowed = consult.classify_evidence_request_safety({"command": "git status --short", "tool_needed": "terminal"}, state=state)
        self.assertTrue(allowed["allowed"])
        self.assertTrue(Path(allowed["argv"][0]).is_absolute())
        self.assertEqual(Path(allowed["argv"][0]).name, "git")
        injection = consult.classify_evidence_request_safety({"command": "git status --short; cat ~/.hermes/.env", "tool_needed": "terminal"}, state=state)
        credential = consult.classify_evidence_request_safety({"command": "cat ~/.hermes/auth.json", "tool_needed": "terminal"}, state=state)
        outside = consult.classify_evidence_request_safety({"command": "python3 -c 'print(1)'", "tool_needed": "terminal"}, state=state)
        ext_diff = consult.classify_evidence_request_safety({"command": "git diff --ext-diff", "tool_needed": "terminal"}, state=state)
        bare_diff = consult.classify_evidence_request_safety({"command": "git diff", "tool_needed": "terminal"}, state=state)
        no_index = consult.classify_evidence_request_safety({"command": "git diff --no-index a b", "tool_needed": "terminal"}, state=state)
        output_file = consult.classify_evidence_request_safety({"command": "git diff --output=/tmp/leak.diff", "tool_needed": "terminal"}, state=state)
        show_blob = consult.classify_evidence_request_safety({"command": "git show --stat HEAD:scripts/consult_models.py", "tool_needed": "terminal"}, state=state)
        fake_brainctl = consult.classify_evidence_request_safety({"command": "python3 /tmp/brainctl.py status --json", "tool_needed": "terminal"}, state=state)
        canonical_brainctl_path = Path(consult.HERMES_HOME) / "scripts" / "brainctl.py"
        fake_interpreter_brainctl = consult.classify_evidence_request_safety({"command": f"/tmp/python3 {canonical_brainctl_path} status --json", "tool_needed": "terminal"}, state=state)
        relative_interpreter_brainctl = consult.classify_evidence_request_safety({"command": f"./python3 {canonical_brainctl_path} status --json", "tool_needed": "terminal"}, state=state)
        brainctl_status = consult.classify_evidence_request_safety({"command": f"{sys.executable} {canonical_brainctl_path} status --json", "tool_needed": "terminal"}, state=state)
        brainctl_search = consult.classify_evidence_request_safety({"command": f"{sys.executable} {canonical_brainctl_path} --json search scope", "tool_needed": "terminal"}, state=state)
        brainctl_path_flag = consult.classify_evidence_request_safety({"command": f"{sys.executable} {canonical_brainctl_path} --json search scope --path /tmp", "tool_needed": "terminal"}, state=state)
        anti_drift_path = Path(consult.HERMES_HOME) / "scripts" / "anti_drift_guard.py"
        anti_drift_out = consult.classify_evidence_request_safety({"command": f"{sys.executable} {anti_drift_path} check-anchors --json --out /tmp/drift.json", "tool_needed": "terminal"}, state=state)

        self.assertTrue(allowed["allowed"])
        self.assertFalse(injection["allowed"])
        self.assertIn("shell metacharacters", injection["reason"])
        self.assertFalse(credential["allowed"])
        self.assertIn("credential", credential["reason"])
        self.assertFalse(outside["allowed"])
        self.assertFalse(ext_diff["allowed"])
        self.assertFalse(bare_diff["allowed"])
        self.assertFalse(no_index["allowed"])
        self.assertFalse(output_file["allowed"])
        self.assertFalse(show_blob["allowed"])
        self.assertFalse(fake_brainctl["allowed"])
        self.assertFalse(fake_interpreter_brainctl["allowed"])
        self.assertFalse(relative_interpreter_brainctl["allowed"])
        self.assertFalse(brainctl_status["allowed"])
        self.assertFalse(brainctl_search["allowed"])
        self.assertFalse(brainctl_path_flag["allowed"])
        self.assertFalse(anti_drift_out["allowed"])

    def test_evidence_fulfillment_updates_state_truth_gate(self):
        verify_command = "git status --short"
        state = consult.build_state(
            question="evidence execution",
            claims=[{"id": "C-EXEC", "text": "approved verifier command ran", "severity": 4}],
            evidence=[],
            implementation_target={"files": [], "verify_commands": [verify_command], "forbidden_changes": []},
        )
        state["evidence_fulfillment_policy"] = {"claim_command_allowlist": {"C-EXEC": [verify_command]}}
        requests = [{
            "id": "ER-EXEC",
            "requested_by": "codex",
            "claim_id": "C-EXEC",
            "tool_needed": "terminal",
            "command": verify_command,
            "why": "verify execution",
        }]
        report = consult.fulfill_evidence_requests(requests, state=state, cwd=str(Path(__file__).resolve().parents[1]), timeout=10)
        updated = consult.update_state_with_fulfilled_evidence(state, report)

        self.assertEqual(report["schema_version"], consult.EVIDENCE_FULFILLMENT_SCHEMA_VERSION)
        self.assertEqual(report["succeeded_count"], 1)
        self.assertEqual(report["rejected_count"], 0)
        self.assertEqual(updated["truth_gate"]["truth_status"], "grounded")
        self.assertTrue(updated["truth_gate"]["can_certify_truth"])
        self.assertIn("C-EXEC", updated["evidence"][-1]["supports"])
        self.assertEqual(updated["evidence_fulfillment_reports"][-1]["results"][0]["status"], "succeeded")

    def test_evidence_fulfillment_verify_command_requires_allowlisted_command(self):
        verify_command = f"{sys.executable} -c 'print(\"evidence-ok\")'"
        state = consult.build_state(
            question="verify command policy",
            claims=[{"id": "C-EXEC", "text": "approved verifier command ran", "severity": 4}],
            implementation_target={"files": [], "verify_commands": [verify_command], "forbidden_changes": []},
        )
        state["evidence_fulfillment_policy"] = {"claim_command_allowlist": {"C-EXEC": [verify_command]}}
        safety = consult.classify_evidence_request_safety({
            "id": "ER-EXEC",
            "requested_by": "codex",
            "claim_id": "C-EXEC",
            "tool_needed": "terminal",
            "command": verify_command,
        }, state=state)
        self.assertFalse(safety["allowed"])
        self.assertIn("outside evidence fulfillment allowlist", safety["reason"])

    def test_evidence_fulfillment_subprocess_env_is_scrubbed(self):
        old = os.environ.get("LEAKVAR")
        os.environ["LEAKVAR"] = "should-not-leak"
        try:
            env = consult._evidence_subprocess_env()
        finally:
            if old is None:
                os.environ.pop("LEAKVAR", None)
            else:
                os.environ["LEAKVAR"] = old
        self.assertNotIn("LEAKVAR", env)
        self.assertEqual(env.get("HERMES_MULTI_BRAIN_OFFLINE"), "1")
        self.assertEqual(env.get("GIT_TERMINAL_PROMPT"), "0")
        self.assertEqual(env.get("GIT_OPTIONAL_LOCKS"), "0")
        self.assertEqual(env.get("GIT_CONFIG_NOSYSTEM"), "1")
        self.assertEqual(env.get("GIT_CONFIG_GLOBAL"), "/dev/null")
        self.assertEqual(env.get("GIT_CONFIG_SYSTEM"), "/dev/null")
        self.assertIn("PATH", env)

    def test_evidence_fulfillment_subprocess_oserror_is_auditable_failure(self):
        with mock.patch.object(consult.subprocess, "run", side_effect=OSError("missing /Users/me/.ssh/id_rsa")):
            report = consult.fulfill_evidence_requests([
                {"id": "ER-OS", "requested_by": "codex", "tool_needed": "terminal", "command": "git status --short", "why": "probe"}
            ], state={}, cwd=str(Path(__file__).resolve().parents[1]), timeout=10)
        self.assertEqual(report["approved_count"], 1)
        self.assertEqual(report["failed_count"], 1)
        self.assertEqual(report["results"][0]["status"], "failed")
        self.assertEqual(report["results"][0]["reason"], "subprocess execution failed")
        self.assertNotIn("/Users/me/.ssh/id_rsa", report["results"][0]["stderr_excerpt"])

    def test_evidence_fulfillment_does_not_auto_ground_model_claim_links(self):
        state = consult.build_state(
            question="candidate-only evidence",
            claims=[{"id": "C-ARB", "text": "arbitrary claim is true", "severity": 4}],
            evidence=[],
        )
        report = consult.fulfill_evidence_requests([
            {"id": "ER-ARB", "requested_by": "deepseek", "claim_id": "C-ARB", "tool_needed": "terminal", "command": "git status --short", "why": "unrelated successful command"}
        ], state=state, cwd=str(Path(__file__).resolve().parents[1]), timeout=10)
        updated = consult.update_state_with_fulfilled_evidence(state, report)

        self.assertEqual(report["succeeded_count"], 1)
        self.assertEqual(report["evidence"][0]["supports"], [])
        self.assertEqual(report["evidence"][0]["candidate_claim_ids"], ["C-ARB"])
        self.assertEqual(updated["truth_gate"]["truth_status"], "needs_link_review")
        self.assertFalse(updated["truth_gate"]["can_certify_truth"])

    def test_evidence_fulfillment_counts_malformed_requests_as_rejected(self):
        report = consult.fulfill_evidence_requests(["not-an-object"], state={}, dry_run=True)
        self.assertEqual(report["processed_count"], 1)
        self.assertEqual(report["rejected_count"], 1)
        self.assertEqual(report["results"][0]["status"], "rejected")

    def test_evidence_fulfillment_redacts_secret_shaped_output(self):
        redacted = consult.redact_evidence_text("token=abcdef1234567890 and Bearer abcdefghijklmnop")
        self.assertNotIn("abcdef1234567890", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_evidence_fulfillment_redacts_credential_paths_in_output(self):
        redacted = consult.redact_evidence_text("fatal: could not read /Users/me/.ssh/id_rsa or ~/.hermes/auth.json")
        self.assertNotIn("/Users/me/.ssh/id_rsa", redacted)
        self.assertNotIn("~/.hermes/auth.json", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_evidence_fulfillment_redacts_json_style_secrets(self):
        payload = """
        {"api_key": "abcdef1234567890", "token": "tok_abcdef123456", "safe": "visible"}
        password: abcdef1234567890
        aws_secret_access_key = ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890
        authorization = "Bearer abcdefghijklmnopqrstuvwxyz"
        ghp_ab...3456
        [REDACTED PRIVATE KEY]
        """
        redacted = consult.redact_evidence_text(payload)
        self.assertNotIn("abcdef1234567890", redacted)
        self.assertNotIn("tok_abcdef123456", redacted)
        self.assertNotIn("ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890", redacted)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz123456", redacted)
        self.assertNotIn("BEGIN PRIVATE KEY", redacted)
        self.assertIn("visible", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_decode_claude_code_output_handles_success_error_and_string_false(self):
        success = consult._decode_claude_code_output(json.dumps({
            "type": "result",
            "is_error": False,
            "api_error_status": None,
            "result": '{"ok": true}',
        }))
        self.assertFalse(success["is_error"])
        self.assertEqual(success["result_text"], '{"ok": true}')

        error = consult._decode_claude_code_output(json.dumps({
            "type": "result",
            "is_error": "false",
            "api_error_status": 403,
            "result": "Credit balance is too low",
        }))
        self.assertTrue(error["is_error"])
        self.assertEqual(error["api_error_status"], 403)
        self.assertIn("Credit balance is too low", error["detail"])

        not_error = consult._decode_claude_code_output(json.dumps({
            "type": "result",
            "is_error": "false",
            "api_error_status": None,
            "result": "{}",
        }))
        self.assertFalse(not_error["is_error"])

    def test_extract_plan_json_rejects_claude_error_wrapper_as_runtime_error(self):
        raw = json.dumps({
            "type": "result",
            "is_error": True,
            "api_error_status": 403,
            "result": "API failed but {\"meta\":{},\"diagnosis\":{},\"patches\":[]}",
        })
        with self.assertRaises(consult.ModelRuntimeError) as cm:
            consult.extract_plan_json(raw)
        self.assertEqual(cm.exception.status, 403)
        self.assertIn("Claude Code API error 403", str(cm.exception))

    def test_call_discussion_model_unwraps_claude_json_success_wrapper(self):
        config = {"pricing": {"models": {"claude-opus-4-7": {"provider": "anthropic"}}}}
        inner = {
            "vote": "approve",
            "best_within_constraints": True,
            "reasoning": "wrapped discussion ok",
            "critiques": [],
            "evidence_requests": [],
        }
        stdout = json.dumps({"type": "result", "is_error": False, "result": json.dumps(inner)})

        with mock.patch.object(consult.shutil, "which", side_effect=lambda name: "/usr/bin/claude" if name == "claude" else None), \
             mock.patch.object(consult, "model_quota", None), \
             mock.patch.object(consult.subprocess, "run", return_value=mock.Mock(returncode=0, stdout=stdout, stderr="")) as run:
            raw = consult.call_discussion_model("claude-opus-4-7", "prompt", config, timeout=5)

        self.assertEqual(raw, json.dumps(inner))
        self.assertEqual(json.loads(raw)["vote"], "approve")
        cmd = run.call_args[0][0]
        self.assertEqual(cmd[0], "claude")
        self.assertIn("--output-format", cmd)
        self.assertIn("json", cmd)

    def test_call_discussion_model_raises_model_runtime_error_for_claude_is_error_wrapper(self):
        config = {"pricing": {"models": {"claude-opus-4-7": {"provider": "anthropic"}}}}
        stdout = json.dumps({
            "type": "result",
            "is_error": True,
            "api_error_status": 403,
            "result": "Credit balance is too low",
        })

        with mock.patch.object(consult.shutil, "which", side_effect=lambda name: "/usr/bin/claude" if name == "claude" else None), \
             mock.patch.object(consult, "model_quota", None), \
             mock.patch.object(consult.subprocess, "run", return_value=mock.Mock(returncode=0, stdout=stdout, stderr="")):
            with self.assertRaises(consult.ModelRuntimeError) as cm:
                consult.call_discussion_model("claude-opus-4-7", "prompt", config, timeout=5)

        self.assertEqual(cm.exception.status, 403)
        self.assertIn("Claude Code API error 403", str(cm.exception))
        self.assertIn("Credit balance is too low", str(cm.exception))

    def test_call_planner_model_unwraps_claude_json_success_wrapper(self):
        config = {"pricing": {"models": {"claude-opus-4-7": {"provider": "anthropic"}}}}
        inner_plan = {
            "meta": {"confidence": 0.9},
            "diagnosis": {"summary": "wrapped planner ok"},
            "patches": [],
        }
        stdout = json.dumps({"type": "result", "is_error": False, "result": json.dumps(inner_plan)})

        with mock.patch.object(consult.shutil, "which", side_effect=lambda name: "/usr/bin/claude" if name == "claude" else None), \
             mock.patch.object(consult, "model_quota", None), \
             mock.patch.object(consult.subprocess, "run", return_value=mock.Mock(returncode=0, stdout=stdout, stderr="")):
            plan, info = consult.call_planner_model(
                "claude-opus-4-7", "prompt", "state123", "T2", "chain123", config, timeout=5
            )

        self.assertTrue(info["ok"])
        self.assertEqual(info["adapter"], "claude-code")
        self.assertEqual(info["provider"], "anthropic")
        self.assertEqual(plan["meta"]["planner_model"], "claude-opus-4-7")
        self.assertEqual(plan["meta"]["adapter"], "claude-code")
        self.assertEqual(plan["meta"]["provider"], "anthropic")
        self.assertEqual(plan["diagnosis"]["summary"], "wrapped planner ok")

    def test_call_planner_model_treats_claude_api_error_wrapper_as_runtime_failure_not_parse_failure(self):
        config = {"pricing": {"models": {"claude-opus-4-7": {"provider": "anthropic"}}}}
        stdout = json.dumps({
            "type": "result",
            "is_error": False,
            "api_error_status": 403,
            "result": "Credit balance is too low",
        })

        with mock.patch.object(consult.shutil, "which", side_effect=lambda name: "/usr/bin/claude" if name == "claude" else None), \
             mock.patch.object(consult, "model_quota", None), \
             mock.patch.object(consult.subprocess, "run", return_value=mock.Mock(returncode=0, stdout=stdout, stderr="")):
            plan, info = consult.call_planner_model(
                "claude-opus-4-7", "prompt", "state123", "T2", "chain123", config, timeout=5
            )

        self.assertFalse(info["ok"])
        self.assertEqual(info["adapter"], "claude-code")
        self.assertEqual(info["provider"], "anthropic")
        self.assertEqual(info.get("api_error_status"), 403)
        self.assertIn("Claude Code API error 403", info.get("error", ""))
        self.assertIn("Credit balance is too low", info.get("error", ""))
        self.assertNotIn("Expecting value", info.get("error", ""))
        self.assertNotIn("output parse/invoke failed", plan["diagnosis"]["summary"])
        self.assertIn("Claude Code API error 403", plan["diagnosis"]["summary"])

    def test_run_discussion_does_not_retry_model_runtime_errors(self):
        calls = {"claude": 0}

        def runtime_failure(model, prompt):
            calls[model] += 1
            raise consult.ModelRuntimeError("Claude Code API error 403: blocked", raw_response="wrapped-error", status=403)

        result = consult.run_discussion_rounds(
            [{"meta": {"planner_model": "claude"}, "patches": []}],
            current_best={"patches": []},
            models=["claude"],
            max_rounds=1,
            call_model_fn=runtime_failure,
        )
        self.assertEqual(calls["claude"], 1)
        self.assertEqual(result["status"], "not_certified")
        self.assertEqual(result["discussion_transcript"][0]["parse_status_by_model"]["claude"], "runtime_error")
        self.assertIn("runtime/provider failure", result["ratification_votes"][0]["reasoning"])

    def test_module_truncate_text_keeps_marker_after_claude_runtime_helpers(self):
        self.assertIn("<truncated:", consult._truncate_text("x" * (consult.MAX_COMM_TEXT_CHARS + 100)))

    def test_evidence_fulfillment_counts_malformed_requests_loaded_from_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "requests.json"
            path.write_text(json.dumps([
                {"claim_id": "C-1", "tool_needed": "terminal", "command": "git status --short", "why": "ok"},
                "bad-request",
            ]), encoding="utf-8")
            requests = consult.load_evidence_requests_from_file(str(path))
        self.assertEqual(len(requests), 2)
        malformed = [req for req in requests if req.get("malformed_request")]
        self.assertEqual(len(malformed), 1)
        report = consult.fulfill_evidence_requests(requests, state={}, dry_run=True)
        self.assertEqual(report["processed_count"], 2)
        self.assertEqual(report["rejected_count"], 1)
        self.assertEqual(report["results"][1]["status"], "rejected")
        self.assertIn("object", report["results"][1]["reason"])

    def test_evidence_fulfillment_counts_malformed_scalar_requests_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "requests.json"
            path.write_text(json.dumps("bad-top-level"), encoding="utf-8")
            requests = consult.load_evidence_requests_from_file(str(path))
        self.assertEqual(len(requests), 1)
        self.assertTrue(requests[0].get("malformed_request"))
        self.assertEqual(requests[0].get("raw_type"), "str")
        report = consult.fulfill_evidence_requests(requests, state={}, dry_run=True)
        self.assertEqual(report["processed_count"], 1)
        self.assertEqual(report["rejected_count"], 1)

    def test_evidence_fulfillment_counts_malformed_nested_scalar_requests_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "requests.json"
            path.write_text(json.dumps({"evidence_requests": "bad-nested"}), encoding="utf-8")
            requests = consult.load_evidence_requests_from_file(str(path))
        self.assertEqual(len(requests), 1)
        self.assertTrue(requests[0].get("malformed_request"))
        self.assertEqual(requests[0].get("raw_type"), "str")

    def test_evidence_fulfillment_counts_invalid_requests_file_as_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "requests.json"
            path.write_text("{not-json", encoding="utf-8")
            requests = consult.load_evidence_requests_from_file(str(path))
        self.assertEqual(len(requests), 1)
        self.assertTrue(requests[0].get("malformed_request"))
        self.assertIn("invalid JSON", requests[0].get("malformed_reason", ""))
        report = consult.fulfill_evidence_requests(requests, state={}, dry_run=True)
        self.assertEqual(report["processed_count"], 1)
        self.assertEqual(report["rejected_count"], 1)

    def test_evidence_fulfillment_counts_malformed_requests_loaded_from_tick(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tick = Path(tmpdir)
            plans = tick / "plans"
            plans.mkdir()
            (plans / "planner.json").write_text(json.dumps({
                "meta": {"planner_model": "mimo"},
                "evidence_requests": ["bad-request"],
            }), encoding="utf-8")
            requests = consult.load_evidence_requests_from_tick(str(tick))
        self.assertEqual(len(requests), 1)
        self.assertTrue(requests[0].get("malformed_request"))
        report = consult.fulfill_evidence_requests(requests, state={}, dry_run=True)
        self.assertEqual(report["processed_count"], 1)
        self.assertEqual(report["rejected_count"], 1)
        self.assertEqual(report["results"][0]["status"], "rejected")

    def test_discussion_packet_uses_manifest_and_delta_only_to_reduce_prompt_size(self):
        """Discussion prompts should send compact pointers/deltas instead of full merged/evidence blobs."""
        current_best = {
            "diagnosis": {"summary": "x" * 4000},
            "patches": [
                {"id": "P1", "target_file": "a.py", "op": "add_verifier", "rationale": "r" * 2000},
                {"id": "P2", "target_file": "b.py", "op": "modify_router_weight", "rationale": "s" * 2000},
            ],
            "large_irrelevant_blob": "z" * 12000,
            "fanout_certification": {"status": "fanout_quorum_met", "planner_outputs": "f" * 9000},
        }
        evidence_bundle = {
            "schema_version": 1,
            "claims": [{"id": "C-1", "text": "claim " + "c" * 4000, "severity": 4}],
            "evidence": [{"id": "E-1", "summary": "evidence " + "e" * 4000, "supports": ["C-1"]}],
            "grounding": {"C-1": {"truth_status": "verified_by_evidence", "supporting_evidence_ids": ["E-1"]}},
        }
        truth_gate = {"truth_status": "grounded", "can_certify_truth": True, "verified_claim_count": 1, "claim_count": 1}
        unresolved = [{"id": "I-1", "status": "unresolved", "severity": 3, "claim": "Need decide", "evidence": "tiny"}]

        packet = consult.build_discussion_comm_packet(
            current_best=current_best,
            unresolved_issues=unresolved,
            evidence_bundle=evidence_bundle,
            truth_gate=truth_gate,
            round_no=2,
            previous_transcript=[{"round": 1, "votes": [{"model": "m1", "vote": "amend", "reasoning": "long" * 1000}], "status": {"status": "not_certified"}}],
        )
        raw_context = json.dumps({"current_best": current_best, "unresolved_issues": unresolved, "evidence_bundle": evidence_bundle, "truth_gate": truth_gate}, ensure_ascii=False)
        compact_context = json.dumps(packet, ensure_ascii=False)

        self.assertLess(len(compact_context), len(raw_context) // 3)
        self.assertEqual(packet["schema"], consult.COMM_PACKET_SCHEMA_VERSION)
        self.assertEqual(packet["mode"], "manifest_delta")
        self.assertIn("artifact_manifest", packet)
        self.assertIn("current_best", packet["artifact_manifest"])
        self.assertNotIn("large_irrelevant_blob", compact_context)
        self.assertIn("P1", compact_context)
        self.assertNotIn("planner_outputs", compact_context)
        self.assertNotIn("ffffffffffffffffffffffff", compact_context)
        self.assertEqual(packet["round_delta"]["round"], 2)
        self.assertEqual(packet["token_budget"]["packet_chars"], len(json.dumps(packet, ensure_ascii=False)))
        self.assertIn("token_budget", packet)

    def test_run_discussion_records_communication_telemetry_and_sends_compact_prompt(self):
        """Online discussion should expose prompt telemetry so token waste is auditable."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": []},
            {"meta": {"planner_model": "codex"}, "patches": []},
        ]
        prompts = []

        def capturing_call(model, prompt):
            prompts.append(prompt)
            self.assertIn('"schema": "multi_model_comm_packet_v1"', prompt)
            self.assertIn('"mode": "manifest_delta"', prompt)
            return '{"vote":"approve","best_within_constraints":true,"reasoning":"compact ok","critiques":[],"evidence_requests":[]}'

        result = consult.run_discussion_rounds(
            plans,
            current_best={"patches": [], "large_irrelevant_blob": "x" * 10000},
            models=["claude", "codex"],
            max_rounds=1,
            call_model_fn=capturing_call,
        )
        self.assertEqual(result["status"], "certified")
        self.assertEqual(len(prompts), 2)
        self.assertIn("communication", result)
        self.assertEqual(result["communication"]["mode"], "manifest_delta")
        self.assertGreater(result["communication"]["estimated_chars_saved"], 0)
        self.assertIn("prompt_chars", result["discussion_transcript"][0])

    def test_offline_discussion_communication_summary_does_not_report_manifest_savings(self):
        """Offline rounds send no prompts, so communication telemetry must not invent savings."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": []},
            {"meta": {"planner_model": "codex"}, "patches": []},
        ]
        result = consult.run_discussion_rounds(plans, current_best={"patches": []}, models=["claude", "codex"], offline=True)
        self.assertEqual(result["communication"]["mode"], "offline")
        self.assertEqual(result["communication"]["total_prompt_chars"], 0)
        self.assertEqual(result["communication"]["estimated_chars_saved"], 0)

    def test_packet_reports_zero_token_savings_when_manifest_has_no_char_savings(self):
        """Telemetry must never claim token savings when char savings are zero."""
        packet = consult.build_discussion_comm_packet(
            current_best={},
            unresolved_issues=[],
            evidence_bundle={},
            truth_gate={},
            round_no=1,
            previous_transcript=[],
        )
        if packet["token_budget"]["estimated_chars_saved"] == 0:
            self.assertEqual(packet["token_budget"]["estimated_tokens_saved"], 0)
            self.assertEqual(packet["mode"], "manifest_delta_no_savings")
        self.assertEqual(packet["token_budget"]["packet_chars"], len(json.dumps(packet, ensure_ascii=False)))

    def test_ratification_fails_closed_when_high_severity_truth_unsupported(self):
        """Multi-model approval must not certify unsupported high-severity factual claims."""
        votes = [
            {"model": "claude", "vote": "approve", "best_within_constraints": True},
            {"model": "codex", "vote": "approve", "best_within_constraints": True},
            {"model": "deepseek", "vote": "approve", "best_within_constraints": True},
        ]
        truth_gate = {
            "truth_status": "partially_grounded",
            "can_certify_truth": False,
            "unsupported_claim_ids": ["C-009"],
            "unsupported_high_severity_claim_ids": ["C-009"],
        }
        status = consult.evaluate_ratification(
            votes=votes,
            agreement_matrix={"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
            issue_ledger=[],
            revised_this_round=False,
            novel_redteam_blocker=False,
            truth_gate=truth_gate,
        )
        self.assertEqual(status["status"], "not_certified")
        self.assertIn("unsupported high-severity factual claims", " ".join(status["reasons"]))

    def test_run_discussion_output_includes_truth_assessment_and_evidence_requests(self):
        """Discussion artifacts should expose provenance, truth status, and requested missing evidence."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": [], "evidence_requests": [{"claim_id": "C-1", "tool_needed": "terminal", "command": "git status", "why": "verify"}]},
            {"meta": {"planner_model": "codex"}, "patches": []},
        ]
        bundle = consult.build_evidence_bundle({"claims": [{"id": "C-1", "text": "worktree clean", "severity": 4}], "evidence": []})
        result = consult.run_discussion_rounds(plans, current_best={"patches": []}, models=["claude", "codex"], offline=True, evidence_bundle=bundle)
        self.assertEqual(result["status"], "not_certified")
        self.assertEqual(result["truth_assessment"]["truth_status"], "unsupported")
        self.assertEqual(result["evidence_requests"][0]["requested_by"], "claude")

    def test_evidence_bundle_supports_claims_supported_alias(self):
        """Evidence should link explicit claims_supported aliases to claim ids."""
        state = {
            "claims": [{"id": "C-001", "text": "self-test passed", "severity": 4}],
            "evidence": [{"id": "E-001", "type": "command", "summary": "self-test output", "claims_supported": ["C-001"], "exit_code": 0}],
        }
        bundle = consult.build_evidence_bundle(state)
        self.assertEqual(bundle["grounding"]["C-001"]["truth_status"], "verified_by_evidence")
        self.assertEqual(bundle["grounding"]["C-001"]["supporting_evidence_ids"], ["E-001"])

    def test_evidence_bundle_does_not_verify_provenance_only_support(self):
        state = {
            "claims": [{"id": "C-001", "text": "runtime gate passed", "severity": 5}],
            "evidence": [{"id": "E-prov", "kind": " provenance ", "summary": "planner said gate should exist", "supports": ["C-001"]}],
        }
        bundle = consult.build_evidence_bundle(state)
        self.assertEqual(bundle["grounding"]["C-001"]["truth_status"], "unsupported")
        self.assertEqual(bundle["grounding"]["C-001"]["supporting_evidence_ids"], [])
        self.assertEqual(bundle["grounding"]["C-001"]["non_verifying_supporting_evidence_ids"], ["E-prov"])

    def test_evidence_bundle_marks_raw_evidence_present_as_needs_link_review(self):
        """Raw evidence with no explicit supports should request linkage review, not assert unsupported."""
        state = {
            "claims": [{"id": "C-001", "text": "self-test passed", "severity": 4}],
            "evidence": [{"id": "E-001", "type": "command", "summary": "self-test output says ALL PASS", "exit_code": 0}],
        }
        bundle = consult.build_evidence_bundle(state)
        self.assertEqual(bundle["grounding"]["C-001"]["truth_status"], "needs_link_review")
        gate = consult.evaluate_truth_gate(bundle)
        self.assertEqual(gate["truth_status"], "needs_link_review")
        self.assertFalse(gate["can_certify_truth"])
        self.assertIn("C-001", gate["needs_link_review_claim_ids"])

    def test_issue_ledger_normalizes_equivalent_target_paths(self):
        """consult_models.py and scripts/consult_models.py should group as one target."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": [{"target_file": "scripts/consult_models.py", "op": "add_verifier", "rationale": "checkpoint"}]},
            {"meta": {"planner_model": "mimo"}, "patches": [{"target_file": "consult_models.py", "op": "add_verifier", "rationale": "resume"}]},
        ]

        ledger = consult.build_issue_ledger(plans)

        targets = {issue.get("target_file") for issue in ledger}
        self.assertEqual(targets, {"scripts/consult_models.py"})
        self.assertEqual(len(ledger), 1)

    def test_audit_certification_fails_closed_without_discussion_result(self):
        """A tick with plans/merged output but no discussion_result must stay partial_uncertified."""
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            (tick / "plans" / "claude.json").write_text(json.dumps({"meta": {"planner_model": "claude"}, "patches": []}))
            (tick / "merged_plan.json").write_text(json.dumps({
                "fanout_certification": consult.fanout_certification_status(2, 2, 2, 0),
                "truth_assessment": {"can_certify_truth": True},
            }))

            manifest = consult.audit_certification(str(tick), write=True)

            self.assertEqual(manifest["schema_version"], consult.CERTIFICATION_MANIFEST_SCHEMA_VERSION)
            self.assertEqual(manifest["status"], "partial_uncertified")
            self.assertFalse(manifest["can_claim_complete_certification"])
            self.assertIn("missing discussion_result.json", " ".join(manifest["reasons"]))
            self.assertTrue((tick / "final" / "certification_manifest.json").exists())

    def test_audit_certification_fails_closed_missing_fanout_truth_or_votes(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            for model in ["claude", "codex", "deepseek", "mimo"]:
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}))
            (tick / "merged_plan.json").write_text(json.dumps({"patches": []}))
            (tick / "discussion_result.json").write_text(json.dumps({
                "status": "certified",
                "issue_ledger": [],
                "ratification_votes": [],
                "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
            }))

            manifest = consult.audit_certification(str(tick), write=True)

            self.assertEqual(manifest["status"], "not_certified")
            self.assertFalse(manifest["can_claim_complete_certification"])
            self.assertIn("missing fanout_certification", manifest["reasons"])
            self.assertIn("missing truth_assessment", manifest["reasons"])
            self.assertTrue(any("ratification quorum not met" in r for r in manifest["reasons"]))

    def test_audit_certification_rejects_malformed_merged_fanout_counts_even_when_discussion_is_clean(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            models = ["claude", "codex", "deepseek", "mimo"]
            for model in models:
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}))
            discussion_fanout = {"certified": True, "multi_model_certified": True, "planner_count": 4, "success_count": 4}
            merged_fanout = {"certified": True, "multi_model_certified": True, "planner_count": "4", "success_count": 3}
            truth = {"can_certify_truth": True}
            votes = [{"model": m, "vote": "approve", "best_within_constraints": True} for m in models]
            (tick / "merged_plan.json").write_text(json.dumps({
                "patches": [],
                "planner_patch_summary": {"concrete_patch_count": 0, "certification_intent": "no_action_certification"},
                "fanout_certification": merged_fanout,
                "truth_assessment": truth,
            }))
            (tick / "discussion_result.json").write_text(json.dumps({
                "status": "certified",
                "fanout_certification": discussion_fanout,
                "truth_assessment": truth,
                "issue_ledger": [],
                "ratification_votes": votes,
                "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
            }))

            manifest = consult.audit_certification(str(tick), write=True)

            self.assertEqual(manifest["status"], "not_certified")
            self.assertFalse(manifest["can_claim_complete_certification"])
            self.assertIn("merged fanout planner_count/success_count must be strict integers", manifest["reasons"])

    def test_audit_certification_rejects_validator_invalid_fanout_artifacts(self):
        def write_tick(tick, discussion_fanout, merged_fanout):
            models = ["claude", "codex", "deepseek", "mimo"]
            (tick / "plans").mkdir()
            for model in models:
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}))
            truth = {"can_certify_truth": True}
            votes = [{"model": m, "vote": "approve", "best_within_constraints": True} for m in models]
            (tick / "merged_plan.json").write_text(json.dumps({
                "patches": [],
                "planner_patch_summary": {"concrete_patch_count": 0, "certification_intent": "no_action_certification"},
                "fanout_certification": merged_fanout,
                "truth_assessment": truth,
            }))
            (tick / "discussion_result.json").write_text(json.dumps({
                "status": "certified",
                "fanout_certification": discussion_fanout,
                "truth_assessment": truth,
                "issue_ledger": [],
                "ratification_votes": votes,
                "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
            }))

        valid = consult.fanout_certification_status(4, 4, 2, 0)
        cases = []

        invalid_discussion = dict(valid)
        invalid_discussion["fail_count"] = 1
        cases.append((invalid_discussion, valid, "fanout_certification invalid", "success_count + fail_count cannot exceed planner_count"))

        invalid_discussion = dict(valid)
        invalid_discussion["status"] = "single_model_quorum_met"
        invalid_discussion["multi_model_certified"] = True
        cases.append((invalid_discussion, valid, "fanout_certification invalid", "single_model_quorum_met cannot be multi_model_certified"))

        invalid_merged = dict(valid)
        invalid_merged["status"] = "degraded_not_certified"
        invalid_merged["certified"] = True
        cases.append((valid, invalid_merged, "merged fanout_certification invalid", "degraded_not_certified cannot be certified"))

        invalid_merged = dict(valid)
        invalid_merged["status"] = "fanout_quorum_met"
        invalid_merged["certified"] = False
        cases.append((valid, invalid_merged, "merged fanout_certification invalid", "fanout_quorum_met requires certified=true"))

        for discussion_fanout, merged_fanout, reason_prefix, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                with tempfile.TemporaryDirectory() as td:
                    tick = Path(td)
                    write_tick(tick, discussion_fanout, merged_fanout)

                    manifest = consult.audit_certification(str(tick), write=True)

                    self.assertEqual(manifest["status"], "not_certified")
                    self.assertFalse(manifest["can_claim_complete_certification"])
                    joined = "\n".join(manifest["reasons"])
                    self.assertIn(reason_prefix, joined)
                    self.assertIn(expected_error, joined)

    def test_audit_certification_rejects_empty_patches_without_no_action_summary(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            for model in ["claude", "codex", "deepseek", "mimo"]:
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}))
            fanout = {"certified": True, "multi_model_certified": True, "planner_count": 4, "success_count": 4}
            truth = {"can_certify_truth": True}
            votes = [{"model": m, "vote": "approve", "best_within_constraints": True} for m in ["claude", "codex", "deepseek", "mimo"]]
            (tick / "merged_plan.json").write_text(json.dumps({"patches": [], "fanout_certification": fanout, "truth_assessment": truth}))
            (tick / "discussion_result.json").write_text(json.dumps({
                "status": "certified",
                "fanout_certification": fanout,
                "truth_assessment": truth,
                "issue_ledger": [],
                "ratification_votes": votes,
                "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
            }))

            manifest = consult.audit_certification(str(tick), write=True)

            self.assertEqual(manifest["status"], "not_certified")
            self.assertFalse(manifest["can_claim_complete_certification"])
            self.assertIn("empty merged patches require planner_patch_summary no_action_certification", manifest["reasons"])

    def test_audit_certification_accepts_empty_patches_with_no_action_summary(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            for model in ["claude", "codex", "deepseek", "mimo"]:
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}))
            fanout = consult.fanout_certification_status(4, 4, 2, 0)
            truth = {"can_certify_truth": True}
            votes = [{"model": m, "vote": "approve", "best_within_constraints": True} for m in ["claude", "codex", "deepseek", "mimo"]]
            (tick / "merged_plan.json").write_text(json.dumps({
                "patches": [],
                "planner_patch_summary": {"concrete_patch_count": 0, "certification_intent": "no_action_certification"},
                "fanout_certification": fanout,
                "truth_assessment": truth,
            }))
            (tick / "discussion_result.json").write_text(json.dumps({
                "status": "certified",
                "fanout_certification": fanout,
                "truth_assessment": truth,
                "issue_ledger": [],
                "ratification_votes": votes,
                "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
            }))

            manifest = consult.audit_certification(str(tick), write=True)

            self.assertEqual(manifest["status"], "certified")
            self.assertTrue(manifest["can_claim_complete_certification"])
            self.assertTrue((tick / "final" / "certification_manifest.json").exists())
            self.assertTrue(manifest["artifacts"]["certification_manifest"]["exists"])

    def test_audit_certification_rejects_alias_votes_when_expected_participants_are_canonical(self):
        """Expected participants are a hard identity contract, not self-attested aliases."""
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            aliases = ["claude", "codex", "deepseek", "mimo"]
            canonical = ["claude-opus-4-7", "gpt-5.5", "deepseek-v4-pro", "mimo-v2.5-pro"]
            for model in aliases:
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}))
            fanout = consult.fanout_certification_status(4, 4, 4, 0)
            truth = {"can_certify_truth": True}
            votes = [{"model": m, "vote": "approve", "best_within_constraints": True} for m in aliases]
            (tick / "merged_plan.json").write_text(json.dumps({
                "patches": [],
                "planner_patch_summary": {"concrete_patch_count": 0, "certification_intent": "no_action_certification"},
                "fanout_certification": fanout,
                "truth_assessment": truth,
            }))
            (tick / "discussion_result.json").write_text(json.dumps({
                "status": "certified",
                "expected_participants": canonical,
                "models_consulted": aliases,
                "fanout_certification": fanout,
                "truth_assessment": truth,
                "issue_ledger": [],
                "ratification_votes": votes,
                "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
            }))

            manifest = consult.audit_certification(str(tick), write=True)

            self.assertEqual(manifest["status"], "not_certified")
            self.assertFalse(manifest["can_claim_complete_certification"])
            joined = "\n".join(manifest["reasons"])
            self.assertIn("plan models do not match expected participants", joined)
            self.assertIn("models_consulted do not match expected participants", joined)
            self.assertIn("ratification approvals do not cover expected participants", joined)

    def test_audit_certification_rejects_malformed_plan_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            for model in ["claude", "codex", "deepseek", "mimo"]:
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}))
            (tick / "plans" / "codex.json").write_text(json.dumps("bad-plan"))
            fanout = {"certified": True, "multi_model_certified": True, "planner_count": 4, "success_count": 4}
            truth = {"can_certify_truth": True}
            votes = [{"model": m, "vote": "approve", "best_within_constraints": True} for m in ["claude", "codex", "deepseek", "mimo"]]
            (tick / "merged_plan.json").write_text(json.dumps({
                "patches": [],
                "planner_patch_summary": {"concrete_patch_count": 0, "certification_intent": "no_action_certification"},
                "fanout_certification": fanout,
                "truth_assessment": truth,
            }))
            (tick / "discussion_result.json").write_text(json.dumps({
                "status": "certified",
                "fanout_certification": fanout,
                "truth_assessment": truth,
                "issue_ledger": [],
                "ratification_votes": votes,
                "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
            }))

            manifest = consult.audit_certification(str(tick), write=True)

            self.assertFalse(manifest["can_claim_complete_certification"])
            self.assertIn("plan artifact malformed: codex.json", manifest["reasons"])

    def test_audit_certification_rejects_malformed_plan_patch_structures(self):
        malformed_cases = [
            ("missing-patches", {"meta": {"planner_model": "codex"}}),
            ("non-list-patches", {"meta": {"planner_model": "codex"}, "patches": "not-a-list"}),
            ("non-dict-patch-entry", {"meta": {"planner_model": "codex"}, "patches": ["not-a-dict"]}),
        ]
        for case_name, malformed_plan in malformed_cases:
            with self.subTest(case_name):
                with tempfile.TemporaryDirectory() as td:
                    tick = Path(td)
                    (tick / "plans").mkdir()
                    models = ["claude", "codex", "deepseek", "mimo"]
                    for model in models:
                        plan = {"meta": {"planner_model": model}, "patches": []}
                        if model == "codex":
                            plan = malformed_plan
                        (tick / "plans" / f"{model}.json").write_text(json.dumps(plan))
                    fanout = {"certified": True, "multi_model_certified": True, "planner_count": 4, "success_count": 4}
                    truth = {"can_certify_truth": True}
                    votes = [{"model": m, "vote": "approve", "best_within_constraints": True} for m in models]
                    (tick / "merged_plan.json").write_text(json.dumps({
                        "patches": [],
                        "planner_patch_summary": {"concrete_patch_count": 0, "certification_intent": "no_action_certification"},
                        "fanout_certification": fanout,
                        "truth_assessment": truth,
                    }))
                    (tick / "discussion_result.json").write_text(json.dumps({
                        "status": "certified",
                        "fanout_certification": fanout,
                        "truth_assessment": truth,
                        "issue_ledger": [],
                        "ratification_votes": votes,
                        "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
                    }))

                    manifest = consult.audit_certification(str(tick), write=True)

                    self.assertFalse(manifest["can_claim_complete_certification"])
                    self.assertIn("plan patches missing or malformed", manifest["reasons"])
                    self.assertIn("empty merged patches require planner_patch_summary no_action_certification", manifest["reasons"])

    def test_audit_certification_rejects_missing_or_non_list_merged_patches(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            for model in ["claude", "codex", "deepseek", "mimo"]:
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}))
            fanout = {"certified": True, "multi_model_certified": True, "planner_count": 4, "success_count": 4}
            truth = {"can_certify_truth": True}
            votes = [{"model": m, "vote": "approve", "best_within_constraints": True} for m in ["claude", "codex", "deepseek", "mimo"]]
            for merged in [{"fanout_certification": fanout, "truth_assessment": truth}, {"patches": "not-a-list", "fanout_certification": fanout, "truth_assessment": truth}]:
                (tick / "merged_plan.json").write_text(json.dumps(merged))
                (tick / "discussion_result.json").write_text(json.dumps({
                    "status": "certified",
                    "fanout_certification": fanout,
                    "truth_assessment": truth,
                    "issue_ledger": [],
                    "ratification_votes": votes,
                    "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
                }))

                manifest = consult.audit_certification(str(tick), write=True)

                self.assertFalse(manifest["can_claim_complete_certification"])
                self.assertIn("merged_plan patches missing or malformed", manifest["reasons"])

    def test_audit_certification_rejects_empty_merged_patches_when_planner_has_concrete_patch(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            models = ["claude", "codex", "deepseek", "mimo"]
            for model in models:
                patches = [{"op": "replace", "target_file": "scripts/x.py", "rationale": "real change"}] if model == "codex" else [{"op": "noop"}]
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": patches}))
            fanout = {"certified": True, "multi_model_certified": True, "planner_count": 4, "success_count": 4}
            truth = {"can_certify_truth": True}
            votes = [{"model": m, "vote": "approve", "best_within_constraints": True} for m in models]
            (tick / "merged_plan.json").write_text(json.dumps({
                "patches": [],
                "planner_patch_summary": {"concrete_patch_count": 0, "certification_intent": "no_action_certification"},
                "fanout_certification": fanout,
                "truth_assessment": truth,
            }))
            (tick / "discussion_result.json").write_text(json.dumps({
                "status": "certified",
                "fanout_certification": fanout,
                "truth_assessment": truth,
                "issue_ledger": [],
                "ratification_votes": votes,
                "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
            }))

            manifest = consult.audit_certification(str(tick), write=True)

            self.assertFalse(manifest["can_claim_complete_certification"])
            self.assertIn("empty merged patches require planner_patch_summary no_action_certification", manifest["reasons"])

    def test_audit_certification_rejects_discussion_truth_masking_failing_merged_truth(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            models = ["claude", "codex", "deepseek", "mimo"]
            for model in models:
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}))
            fanout = {"certified": True, "multi_model_certified": True, "planner_count": 4, "success_count": 4}
            votes = [{"model": m, "vote": "approve", "best_within_constraints": True} for m in models]
            (tick / "merged_plan.json").write_text(json.dumps({
                "patches": [],
                "planner_patch_summary": {"concrete_patch_count": 0, "certification_intent": "no_action_certification"},
                "fanout_certification": fanout,
                "truth_assessment": {"can_certify_truth": False, "reasons": ["unsupported claims"]},
            }))
            (tick / "discussion_result.json").write_text(json.dumps({
                "status": "certified",
                "fanout_certification": fanout,
                "truth_assessment": {"can_certify_truth": True},
                "issue_ledger": [],
                "ratification_votes": votes,
                "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
            }))

            manifest = consult.audit_certification(str(tick), write=True)

            self.assertFalse(manifest["can_claim_complete_certification"])
            self.assertIn("merged truth gate cannot certify", manifest["reasons"])

    def test_resume_discussion_preserves_failing_merged_truth_assessment(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            models = ["claude", "codex", "deepseek", "mimo"]
            for model in models:
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}))
            fanout = {"certified": True, "multi_model_certified": True, "planner_count": 4, "success_count": 4}
            (tick / "merged_plan.json").write_text(json.dumps({
                "patches": [],
                "planner_patch_summary": {"concrete_patch_count": 0, "certification_intent": "no_action_certification"},
                "fanout_certification": fanout,
                "truth_assessment": {"can_certify_truth": False, "reasons": ["unsupported claims"]},
            }))

            result = consult.resume_discussion_from_tick_dir(str(tick), offline=True, max_rounds=1, force=True)

            self.assertFalse(result["discussion"]["truth_assessment"]["can_certify_truth"])
            self.assertFalse(result["certification_manifest"]["can_claim_complete_certification"])
            self.assertIn("truth gate cannot certify", result["certification_manifest"]["reasons"])

    def test_audit_certification_rejects_string_false_signature_and_low_agreement(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            for model in ["claude", "codex", "deepseek", "mimo"]:
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}))
            (tick / "merged_plan.json").write_text(json.dumps({
                "patches": [],
                "fanout_certification": {"certified": True, "multi_model_certified": True, "planner_count": 4, "success_count": 4},
                "truth_assessment": {"can_certify_truth": True},
            }))
            (tick / "discussion_result.json").write_text(json.dumps({
                "status": "certified",
                "fanout_certification": {"certified": True, "multi_model_certified": True, "planner_count": 4, "success_count": 4},
                "truth_assessment": {"can_certify_truth": True},
                "issue_ledger": [],
                "ratification_votes": [
                    {"model": "claude", "vote": "approve", "best_within_constraints": "false"},
                    {"model": "codex", "vote": "approve", "best_within_constraints": True},
                    {"model": "deepseek", "vote": "approve", "best_within_constraints": True},
                    {"model": "mimo", "vote": "approve", "best_within_constraints": True},
                ],
                "agreement_matrix": {"framing": 0.95, "approach": 0.5, "implementation_order": 0.95},
            }))

            manifest = consult.audit_certification(str(tick), write=True)

            self.assertEqual(manifest["status"], "not_certified")
            self.assertFalse(manifest["can_claim_complete_certification"])
            self.assertIn("ratification contains unsigned/non-true best_within_constraints", manifest["reasons"])
            self.assertIn("agreement matrix missing or below 0.85", manifest["reasons"])

    def test_audit_certification_rejects_boolean_severity_and_agreement_axes(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            for model in ["claude", "codex", "deepseek", "mimo"]:
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}))
            (tick / "merged_plan.json").write_text(json.dumps({
                "patches": [],
                "fanout_certification": {"certified": True, "multi_model_certified": True, "planner_count": 4, "success_count": 4},
                "truth_assessment": {"can_certify_truth": True},
            }))
            (tick / "discussion_result.json").write_text(json.dumps({
                "status": "certified",
                "fanout_certification": {"certified": True, "multi_model_certified": True, "planner_count": 4, "success_count": 4},
                "truth_assessment": {"can_certify_truth": True},
                "issue_ledger": [
                    {"id": "I-bool", "status": "unresolved", "severity": False},
                    {"id": "I-inf", "status": "unresolved", "severity": float("inf")},
                ],
                "ratification_votes": [
                    {"model": "claude", "vote": "approve", "best_within_constraints": True},
                    {"model": "codex", "vote": "approve", "best_within_constraints": True},
                    {"model": "deepseek", "vote": "approve", "best_within_constraints": True},
                    {"model": "mimo", "vote": "approve", "best_within_constraints": True},
                ],
                "agreement_matrix": {"framing": True, "approach": float("nan"), "implementation_order": 0.95},
            }))

            manifest = consult.audit_certification(str(tick), write=True)

            self.assertEqual(manifest["status"], "not_certified")
            self.assertFalse(manifest["can_claim_complete_certification"])
            self.assertIn("unresolved severity>=3 issues remain", manifest["reasons"])
            self.assertIn("agreement matrix missing or below 0.85", manifest["reasons"])

    def test_audit_certification_rejects_malformed_top_level_and_nested_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            for model in ["claude", "codex", "deepseek", "mimo"]:
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}))
            (tick / "merged_plan.json").write_text(json.dumps("bad-merged"))
            (tick / "discussion_result.json").write_text(json.dumps({
                "status": "certified",
                "fanout_certification": "bad-fanout",
                "truth_assessment": "bad-truth",
                "issue_ledger": [],
                "ratification_votes": [],
                "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
            }))

            manifest = consult.audit_certification(str(tick), write=True)

            self.assertEqual(manifest["status"], "not_certified")
            self.assertFalse(manifest["can_claim_complete_certification"])
            self.assertIn("merged_plan malformed", manifest["reasons"])
            self.assertIn("fanout_certification malformed", manifest["reasons"])
            self.assertIn("truth_assessment malformed", manifest["reasons"])
            self.assertIn("missing fanout_certification", manifest["reasons"])
            self.assertIn("missing truth_assessment", manifest["reasons"])

    def test_audit_certification_rejects_malformed_ledger_votes_and_fanout_counts(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            for model in ["claude", "codex", "deepseek", "mimo"]:
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}))
            (tick / "merged_plan.json").write_text(json.dumps({
                "patches": [],
                "fanout_certification": {"certified": True, "multi_model_certified": True, "planner_count": "4", "success_count": 3},
                "truth_assessment": {"can_certify_truth": True},
            }))
            (tick / "discussion_result.json").write_text(json.dumps({
                "status": "certified",
                "fanout_certification": {"certified": True, "multi_model_certified": True, "planner_count": "4", "success_count": 3},
                "truth_assessment": {"can_certify_truth": True},
                "issue_ledger": [{"status": "resolved", "severity": 1}, "bad-entry"],
                "ratification_votes": [
                    {"model": "claude", "vote": "approve", "best_within_constraints": True},
                    {"model": "claude", "vote": "approve", "best_within_constraints": True},
                    {"model": "", "vote": "approve", "best_within_constraints": True},
                    {"model": "unexpected", "vote": "approve", "best_within_constraints": True},
                    "bad-vote",
                ],
                "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
            }))

            manifest = consult.audit_certification(str(tick), write=True)

            self.assertEqual(manifest["status"], "not_certified")
            self.assertFalse(manifest["can_claim_complete_certification"])
            self.assertIn("fanout planner_count/success_count must be strict integers", manifest["reasons"])
            self.assertIn("issue_ledger contains malformed entries", manifest["reasons"])
            self.assertIn("ratification_votes contains malformed entries", manifest["reasons"])
            self.assertTrue(any("duplicate ratification votes" in r for r in manifest["reasons"]))
            self.assertTrue(any("unexpected ratification vote models" in r for r in manifest["reasons"]))
            self.assertIn("ratification vote missing model identity", manifest["reasons"])

    def test_run_discussion_rejects_string_false_best_within_constraints(self):
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": []},
            {"meta": {"planner_model": "codex"}, "patches": []},
        ]

        def string_false(_model, _prompt):
            return json.dumps({"critiques": [], "evidence_requests": [], "vote": "approve", "best_within_constraints": "false", "reasoning": "bad type"})

        result = consult.run_discussion_rounds(
            plans,
            current_best={"patches": []},
            models=["claude", "codex"],
            call_model_fn=string_false,
            max_rounds=1,
        )

        self.assertEqual(result["status"], "not_certified")
        self.assertTrue(all(v["best_within_constraints"] is False for v in result["ratification_votes"]))

    def test_run_discussion_checkpoint_writes_cursor_and_round_summary(self):
        """Discussion should checkpoint each completed round before final certification."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": []},
            {"meta": {"planner_model": "codex"}, "patches": []},
        ]
        with tempfile.TemporaryDirectory() as td:
            def approve(_model, _prompt):
                return json.dumps({"critiques": [], "evidence_requests": [], "vote": "approve", "best_within_constraints": True, "reasoning": "checkpoint smoke"})

            result = consult.run_discussion_rounds(
                plans,
                current_best={"patches": []},
                models=["claude", "codex"],
                call_model_fn=approve,
                max_rounds=1,
                checkpoint_dir=td,
            )
            cursor = json.loads((Path(td) / "discussion" / "cursor.json").read_text())
            state = json.loads((Path(td) / "discussion" / "state.json").read_text())
            summary = json.loads((Path(td) / "discussion" / "round_001" / "round_summary.json").read_text())

            self.assertEqual(result["status"], "certified")
            self.assertEqual(cursor["rounds_completed"], 1)
            self.assertEqual(cursor["latest_status"], "certified")
            self.assertEqual(state["status"], "certified")
            self.assertEqual(summary["round"], 1)
            self.assertIn("votes", summary)
            self.assertTrue((Path(td) / "discussion" / "round_001" / "model_response_claude.json").exists())
            parse_status = json.loads((Path(td) / "discussion" / "round_001" / "parse_status_claude.json").read_text())
            self.assertEqual(parse_status["parse_status"], "ok")

    def test_online_discussion_does_not_blanket_resolve_existing_blockers(self):
        """Aggregate approval votes alone must not erase existing issue-ledger blockers."""
        plans = [
            {"meta": {"planner_model": "claude"}, "patches": [{"target_file": "scripts/consult_models.py", "op": "add_verifier", "rationale": "checkpoint"}]},
            {"meta": {"planner_model": "codex"}, "patches": [{"target_file": "scripts/consult_models.py", "op": "tune_threshold", "rationale": "budget"}]},
        ]

        def approve(_model, _prompt):
            return json.dumps({"critiques": [], "evidence_requests": [], "vote": "approve", "best_within_constraints": True, "reasoning": "resolved by implementation evidence"})

        result = consult.run_discussion_rounds(
            plans,
            current_best={"patches": []},
            models=["claude", "codex"],
            call_model_fn=approve,
            max_rounds=1,
        )

        self.assertEqual(result["status"], "not_certified")
        self.assertTrue([i for i in result["issue_ledger"] if i.get("status") == "unresolved"])

    def test_resume_discussion_from_tick_dir_creates_discussion_and_manifest(self):
        """A resumable tick should be able to create missing discussion_result + final manifest."""
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            plan = {"meta": {"planner_model": "claude"}, "patches": []}
            (tick / "plans" / "claude.json").write_text(json.dumps(plan))
            (tick / "plans" / "codex.json").write_text(json.dumps({"meta": {"planner_model": "codex"}, "patches": []}))
            (tick / "merged_plan.json").write_text(json.dumps({
                "patches": [],
                "planner_patch_summary": {"concrete_patch_count": 0, "certification_intent": "no_action_certification"},
                "fanout_certification": consult.fanout_certification_status(2, 2, 2, 0),
                "truth_assessment": {"can_certify_truth": True},
            }))

            result = consult.resume_discussion_from_tick_dir(str(tick), offline=True, max_rounds=1)

            self.assertEqual(result["discussion"]["status"], "certified")
            self.assertTrue((tick / "discussion_result.json").exists())
            self.assertTrue((tick / "final" / "certification_manifest.json").exists())
            self.assertTrue(result["certification_manifest"]["can_claim_complete_certification"])

    def test_rmcs_runner_is_bounded_and_can_resume_missing_discussion(self):
        """Background/cron use should be a bounded runner, not an unbounded foreground hang."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tick = root / "tick-20260507-000000"
            (tick / "plans").mkdir(parents=True)
            (tick / "plans" / "claude.json").write_text(json.dumps({"meta": {"planner_model": "claude"}, "patches": []}))
            (tick / "plans" / "codex.json").write_text(json.dumps({"meta": {"planner_model": "codex"}, "patches": []}))
            (tick / "merged_plan.json").write_text(json.dumps({
                "patches": [],
                "planner_patch_summary": {"concrete_patch_count": 0, "certification_intent": "no_action_certification"},
                "fanout_certification": consult.fanout_certification_status(2, 2, 2, 0),
                "truth_assessment": {"can_certify_truth": True},
            }))

            report = consult.run_rmcs_runner(str(root), max_ticks=1, resume_missing=True, offline=True, max_rounds=1)

            self.assertEqual(report["schema_version"], "rmcs_runner_report_v1")
            self.assertEqual(report["bounded"]["max_ticks"], 1)
            self.assertEqual(len(report["processed"]), 1)
            self.assertEqual(report["processed"][0]["action"], "resumed")
            self.assertTrue((tick / "discussion_result.json").exists())
            self.assertTrue((root / "state" / "rmcs-runner-last.json").exists())
            status = json.loads((root / "state" / "rmcs-runner-status.json").read_text())
            self.assertEqual(status["status"], "complete")
            self.assertEqual(status["processed_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
