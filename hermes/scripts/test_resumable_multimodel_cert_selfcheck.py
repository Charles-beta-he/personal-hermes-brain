import json
import tempfile
import unittest
from pathlib import Path

from scripts import resumable_multimodel_cert_selfcheck as selfcheck


def write_tick(
    tick: Path,
    *,
    discussion_overrides=None,
    manifest_overrides=None,
    vote_overrides=None,
    include_fanout=True,
    include_truth=True,
):
    (tick / "plans").mkdir(exist_ok=True)
    for model in ["claude-opus-4-7", "gpt-5.5", "deepseek-v4-pro", "mimo-v2.5-pro"]:
        (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}), encoding="utf-8")
    (tick / "final").mkdir(exist_ok=True)
    votes = [
        {"model": "claude-opus-4-7", "vote": "approve", "best_within_constraints": True},
        {"model": "gpt-5.5", "vote": "approve", "best_within_constraints": True},
        {"model": "deepseek-v4-pro", "vote": "approve", "best_within_constraints": True},
        {"model": "mimo-v2.5-pro", "vote": "approve", "best_within_constraints": True},
    ]
    if vote_overrides is not None:
        votes = vote_overrides
    discussion = {
        "status": "certified",
        "issue_ledger": [],
        "ratification_votes": votes,
        "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
    }
    if include_fanout:
        discussion["fanout_certification"] = {
            "certified": True,
            "multi_model_certified": True,
            "planner_count": 4,
            "success_count": 4,
        }
    if include_truth:
        discussion["truth_assessment"] = {"can_certify_truth": True}
    if discussion_overrides:
        discussion.update(discussion_overrides)
    manifest = {"status": "certified", "can_claim_complete_certification": True}
    if manifest_overrides:
        manifest.update(manifest_overrides)
    (tick / "discussion_result.json").write_text(json.dumps(discussion), encoding="utf-8")
    (tick / "merged_plan.json").write_text(json.dumps({
        "patches": [],
        "planner_patch_summary": {"concrete_patch_count": 0, "certification_intent": "no_action_certification"},
        "fanout_certification": discussion.get("fanout_certification", {}),
        "truth_assessment": discussion.get("truth_assessment", {}),
    }), encoding="utf-8")
    (tick / "final" / "certification_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


class TestResumableMultimodelCertSelfcheck(unittest.TestCase):
    def test_safe_numeric_parsers_reject_bool_and_nonfinite_values(self):
        """Standalone selfcheck parser must mirror runtime fail-closed semantics."""
        self.assertEqual(selfcheck._safe_int(True, 3), 3)
        self.assertEqual(selfcheck._safe_int(False, 3), 3)
        self.assertEqual(selfcheck._safe_int(float("inf"), 3), 3)
        self.assertEqual(selfcheck._safe_float(True, 0.0), 0.0)
        self.assertEqual(selfcheck._safe_float(False, 0.0), 0.0)
        self.assertEqual(selfcheck._safe_float(float("nan"), 0.0), 0.0)
        self.assertEqual(selfcheck._safe_float(float("inf"), 0.0), 0.0)
        self.assertEqual(selfcheck._safe_float(float("-inf"), 0.0), 0.0)

    def test_certification_tick_gate_fails_closed_when_artifacts_missing(self):
        with tempfile.TemporaryDirectory() as td:
            result = selfcheck.audit_certification_tick(Path(td))
            self.assertFalse(result["can_claim_complete_certification"])
            self.assertIn("discussion_result_missing", result["reasons"])
            self.assertIn("certification_manifest_missing", result["reasons"])

    def test_certification_tick_gate_accepts_clean_certified_artifact_chain(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            write_tick(tick)

            result = selfcheck.audit_certification_tick(tick)
            self.assertTrue(result["can_claim_complete_certification"])
            self.assertEqual(result["reasons"], [])
            self.assertEqual(result["approval_count"], 4)
            self.assertTrue(result["fanout_certified"])
            self.assertTrue(result["multi_model_certified"])

    def test_certification_tick_gate_accepts_conditional_advisory_verifier_no_action(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            write_tick(tick)
            (tick / "plans" / "gpt-5.5.json").write_text(json.dumps({
                "meta": {"planner_model": "gpt-5.5"},
                "patches": [{
                    "id": "verify-if-missing",
                    "target_file": "scripts/test_resumable_multimodel_cert_selfcheck.py",
                    "op": "add_verifier",
                    "rationale": "Only if the named regression is missing, add a verifier before deciding.",
                    "risk": "low",
                }],
            }), encoding="utf-8")

            result = selfcheck.audit_certification_tick(tick)

            self.assertTrue(result["can_claim_complete_certification"])
            self.assertEqual(result["reasons"], [])

    def test_certification_tick_gate_rejects_empty_merged_patches_without_no_action_summary(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            write_tick(tick)
            merged = json.loads((tick / "merged_plan.json").read_text(encoding="utf-8"))
            merged.pop("planner_patch_summary", None)
            (tick / "merged_plan.json").write_text(json.dumps(merged), encoding="utf-8")

            result = selfcheck.audit_certification_tick(tick)

            self.assertFalse(result["can_claim_complete_certification"])
            self.assertIn("empty_merged_patches_require_no_action_certification", result["reasons"])

    def test_certification_tick_gate_rejects_malformed_plan_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            write_tick(tick)
            (tick / "plans" / "gpt-5.5.json").write_text(json.dumps("bad-plan"), encoding="utf-8")

            result = selfcheck.audit_certification_tick(tick)

            self.assertFalse(result["can_claim_complete_certification"])
            self.assertTrue(any(r.startswith("plan_artifact_malformed:gpt-5.5.json") for r in result["reasons"]))

    def test_certification_tick_gate_rejects_malformed_plan_patch_structures(self):
        malformed_cases = [
            ("missing-patches", {"meta": {"planner_model": "gpt-5.5"}}),
            ("non-list-patches", {"meta": {"planner_model": "gpt-5.5"}, "patches": "not-a-list"}),
            ("non-dict-patch-entry", {"meta": {"planner_model": "gpt-5.5"}, "patches": ["not-a-dict"]}),
        ]
        for case_name, malformed_plan in malformed_cases:
            with self.subTest(case_name):
                with tempfile.TemporaryDirectory() as td:
                    tick = Path(td)
                    write_tick(tick)
                    (tick / "plans" / "gpt-5.5.json").write_text(json.dumps(malformed_plan), encoding="utf-8")

                    result = selfcheck.audit_certification_tick(tick)

                    self.assertFalse(result["can_claim_complete_certification"])
                    self.assertIn("plan_patches_missing_or_malformed", result["reasons"])
                    self.assertIn("empty_merged_patches_require_no_action_certification", result["reasons"])

    def test_certification_tick_gate_rejects_missing_or_non_list_merged_patches(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            write_tick(tick)
            for merged in [{}, {"patches": "not-a-list"}]:
                current = json.loads((tick / "merged_plan.json").read_text(encoding="utf-8"))
                current.update(merged)
                if "patches" not in merged:
                    current.pop("patches", None)
                (tick / "merged_plan.json").write_text(json.dumps(current), encoding="utf-8")

                result = selfcheck.audit_certification_tick(tick)

                self.assertFalse(result["can_claim_complete_certification"])
                self.assertIn("merged_plan_patches_missing_or_malformed", result["reasons"])

    def test_certification_tick_gate_rejects_manifest_false_even_if_discussion_certified(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            write_tick(tick, manifest_overrides={"status": "partial_uncertified", "can_claim_complete_certification": False})

            result = selfcheck.audit_certification_tick(tick)
            self.assertFalse(result["can_claim_complete_certification"])
            self.assertIn("manifest_can_claim_false", result["reasons"])
            self.assertIn("manifest_status_not_certified:partial_uncertified", result["reasons"])

    def test_certification_tick_gate_rejects_empty_votes(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            write_tick(tick, vote_overrides=[])
            result = selfcheck.audit_certification_tick(tick)
            self.assertFalse(result["can_claim_complete_certification"])
            self.assertIn("ratification_votes_missing", result["reasons"])
            self.assertIn("insufficient_approval_votes", result["reasons"])

    def test_certification_tick_gate_rejects_missing_fanout_or_truth(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            write_tick(tick, include_fanout=False, include_truth=False)
            result = selfcheck.audit_certification_tick(tick)
            self.assertFalse(result["can_claim_complete_certification"])
            self.assertIn("fanout_certification_missing", result["reasons"])
            self.assertIn("fanout_not_multi_model_certified", result["reasons"])
            self.assertIn("truth_gate_missing", result["reasons"])

    def test_certification_tick_gate_rejects_malformed_merged_fanout_counts_even_when_discussion_is_clean(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            write_tick(tick)
            merged = json.loads((tick / "merged_plan.json").read_text(encoding="utf-8"))
            merged["fanout_certification"] = {"certified": True, "multi_model_certified": True, "planner_count": "4", "success_count": 3}
            (tick / "merged_plan.json").write_text(json.dumps(merged), encoding="utf-8")

            result = selfcheck.audit_certification_tick(tick)

            self.assertFalse(result["can_claim_complete_certification"])
            self.assertIn("merged_fanout_counts_not_strict_integers", result["reasons"])

    def test_certification_tick_gate_rejects_string_false_signature(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            write_tick(tick, vote_overrides=[
                {"model": "claude-opus-4-7", "vote": "approve", "best_within_constraints": "false"},
                {"model": "gpt-5.5", "vote": "approve", "best_within_constraints": True},
                {"model": "deepseek-v4-pro", "vote": "approve", "best_within_constraints": True},
                {"model": "mimo-v2.5-pro", "vote": "approve", "best_within_constraints": True},
            ])
            result = selfcheck.audit_certification_tick(tick)
            self.assertFalse(result["can_claim_complete_certification"])
            self.assertIn("best_within_constraints_not_strict_true", result["reasons"])

    def test_certification_tick_gate_rejects_low_or_missing_agreement(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            write_tick(tick, discussion_overrides={"agreement_matrix": {"framing": 0.95, "approach": 0.5}})
            result = selfcheck.audit_certification_tick(tick)
            self.assertFalse(result["can_claim_complete_certification"])
            self.assertIn("agreement_approach_below_0_85", result["reasons"])
            self.assertIn("agreement_implementation_order_missing", result["reasons"])

    def test_certification_tick_gate_rejects_malformed_top_level_and_nested_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            (tick / "plans").mkdir()
            (tick / "final").mkdir()
            for model in ["claude-opus-4-7", "gpt-5.5", "deepseek-v4-pro", "mimo-v2.5-pro"]:
                (tick / "plans" / f"{model}.json").write_text(json.dumps({"meta": {"planner_model": model}, "patches": []}), encoding="utf-8")
            (tick / "discussion_result.json").write_text(json.dumps({
                "status": "certified",
                "fanout_certification": "bad-fanout",
                "truth_assessment": "bad-truth",
                "agreement_matrix": "bad-agreement",
                "issue_ledger": [],
                "ratification_votes": [],
            }), encoding="utf-8")
            (tick / "final" / "certification_manifest.json").write_text(json.dumps("bad-manifest"), encoding="utf-8")

            result = selfcheck.audit_certification_tick(tick)

            self.assertFalse(result["can_claim_complete_certification"])
            self.assertIn("certification_manifest_malformed", result["reasons"])
            self.assertIn("fanout_certification_malformed", result["reasons"])
            self.assertIn("truth_gate_malformed", result["reasons"])
            self.assertIn("agreement_matrix_malformed", result["reasons"])
            self.assertIn("fanout_certification_missing", result["reasons"])
            self.assertIn("truth_gate_missing", result["reasons"])

    def test_certification_tick_gate_rejects_malformed_ledger_votes_and_fanout_counts(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            write_tick(
                tick,
                discussion_overrides={
                    "fanout_certification": {"certified": True, "multi_model_certified": True, "planner_count": "4", "success_count": 3},
                    "issue_ledger": [{"status": "resolved", "severity": 1}, "bad-entry"],
                },
                vote_overrides=[
                    {"model": "claude-opus-4-7", "vote": "approve", "best_within_constraints": True},
                    {"model": "claude-opus-4-7", "vote": "approve", "best_within_constraints": True},
                    {"model": "", "vote": "approve", "best_within_constraints": True},
                    {"model": "unexpected", "vote": "approve", "best_within_constraints": True},
                    "bad-vote",
                ],
            )
            result = selfcheck.audit_certification_tick(tick)
            self.assertFalse(result["can_claim_complete_certification"])
            self.assertIn("fanout_counts_not_strict_integers", result["reasons"])
            self.assertIn("issue_ledger_contains_malformed_entries", result["reasons"])
            self.assertIn("ratification_votes_contains_malformed_entries", result["reasons"])
            self.assertIn("duplicate_ratification_vote_models", result["reasons"])
            self.assertIn("ratification_vote_missing_model_identity", result["reasons"])
            self.assertIn("unexpected_ratification_vote_models", result["reasons"])

    def test_certification_tick_gate_handles_malformed_severity_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            write_tick(tick, discussion_overrides={"issue_ledger": [{"status": "unresolved", "severity": "not-an-int"}]})
            result = selfcheck.audit_certification_tick(tick)
            self.assertFalse(result["can_claim_complete_certification"])
            self.assertIn("unresolved_severity_ge_3_issues", result["reasons"])
            self.assertEqual(result["unresolved_severity_ge_3_count"], 1)
    def test_certification_tick_gate_rejects_boolean_severity_and_agreement_axes(self):
        with tempfile.TemporaryDirectory() as td:
            tick = Path(td)
            write_tick(tick, discussion_overrides={
                "issue_ledger": [
                    {"status": "unresolved", "severity": False},
                    {"status": "unresolved", "severity": float("inf")},
                ],
                "agreement_matrix": {"framing": True, "approach": float("nan"), "implementation_order": 0.95},
            })
            result = selfcheck.audit_certification_tick(tick)
            self.assertFalse(result["can_claim_complete_certification"])
            self.assertIn("unresolved_severity_ge_3_issues", result["reasons"])
            self.assertIn("agreement_framing_below_0_85", result["reasons"])
            self.assertIn("agreement_approach_below_0_85", result["reasons"])
            self.assertEqual(result["unresolved_severity_ge_3_count"], 2)


if __name__ == "__main__":
    unittest.main()
