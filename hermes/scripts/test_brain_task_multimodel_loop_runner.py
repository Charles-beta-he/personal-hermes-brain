#!/usr/bin/env python3
"""Tests for brain_task_multimodel_loop_runner.py.
Run with: python3 ~/.hermes/scripts/test_brain_task_multimodel_loop_runner.py
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOME = Path.home()
SCRIPT = HOME / ".hermes" / "scripts" / "brain_task_multimodel_loop_runner.py"


def load_module():
    spec = importlib.util.spec_from_file_location("brain_task_multimodel_loop_runner", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def certified_discussion() -> dict:
    return {
        "status": "certified",
        "models_consulted": ["claude-opus-4-7", "gpt-5.5", "deepseek-v4-pro", "mimo-v2.5-pro"],
        "agreement_matrix": {"framing": 0.95, "approach": 0.95, "implementation_order": 0.95},
        "issue_ledger": [{"id": "I-001", "severity": 3, "status": "resolved"}],
        "remaining_risks": [],
        "ratification_votes": [
            {"model": "claude-opus-4-7", "vote": "approve", "best_within_constraints": True},
            {"model": "gpt-5.5", "vote": "approve", "best_within_constraints": True},
            {"model": "deepseek-v4-pro", "vote": "approve", "best_within_constraints": True},
            {"model": "mimo-v2.5-pro", "vote": "approve", "best_within_constraints": True},
        ],
        "truth_assessment": {"can_certify_truth": True, "evidence_coverage": 1.0, "unsupported_high_severity_claim_ids": [], "contradicted_high_severity_claim_ids": []},
    }


def test_certified_discussion_stops_loop():
    module = load_module()
    verdict = module.evaluate_discussion(certified_discussion())
    assert verdict["done"] is True, verdict
    assert verdict["next_action"] == "LOOP_DONE", verdict
    assert verdict["blocking_reasons"] == [], verdict


def test_verify_ratification_exposes_explicit_pass_reasons_api():
    module = load_module()
    passed, reasons = module.verify_ratification(certified_discussion())
    assert passed is True
    assert reasons == []


def test_should_continue_inverts_ratification_api():
    module = load_module()
    should_continue, reason = module.should_continue(certified_discussion())
    assert should_continue is False
    assert reason == "all_criteria_met"


def test_amend_vote_continues_loop():
    module = load_module()
    data = certified_discussion()
    data["ratification_votes"][2]["vote"] = "amend"
    verdict = module.evaluate_discussion(data)
    assert verdict["done"] is False, verdict
    assert verdict["next_action"] == "continue_loop", verdict
    assert "non_approve_vote" in verdict["blocking_reasons"], verdict
    should_continue, reason = module.should_continue(data)
    assert should_continue is True
    assert "non_approve_vote" in reason


def test_unresolved_high_severity_issue_blocks_even_if_status_certified():
    module = load_module()
    data = certified_discussion()
    data["issue_ledger"].append({"id": "I-002", "severity": 4, "status": "unresolved"})
    verdict = module.evaluate_discussion(data)
    assert verdict["done"] is False, verdict
    assert "open_high_severity_issue" in verdict["blocking_reasons"], verdict


def test_run_consult_timeout_fails_closed_without_traceback():
    module = load_module()
    original_run = module.subprocess.run
    def fake_run(*args, **kwargs):
        raise module.subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout", 1), output="partial-out", stderr="partial-err")
    module.subprocess.run = fake_run
    try:
        result = module.run_consult(Path("/tmp/state.json"), tier="T3", quorum=4, max_rounds=3, timeout=1)
    finally:
        module.subprocess.run = original_run
    assert result["returncode"] == "timeout", result
    assert result["timed_out"] is True, result
    assert "discussion_result_path" in result, result


def test_newest_discussion_result_ignores_concurrent_unrelated_tick():
    module = load_module()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        target_state = write_json(root / "target-state.json", {"question": "target-q", "claims": [{"text": "target-claim"}]})
        unrelated_tick = root / "tick-20990101-000000"
        unrelated_tick.mkdir()
        write_json(unrelated_tick / "state.json", {"question": "other-q", "claims": [{"text": "other-claim"}]})
        write_json(unrelated_tick / "discussion_result.json", certified_discussion())
        original_home = module.HERMES_HOME
        module.HERMES_HOME = root
        try:
            assert module.newest_discussion_result(0, target_state) is None
            related_tick = root / "tick-20990101-000001"
            related_tick.mkdir()
            write_json(related_tick / "state.json", {"question": "target-q", "claims": [{"text": "target-claim"}]})
            discussion = write_json(related_tick / "discussion_result.json", certified_discussion())
            assert module.newest_discussion_result(0, target_state) == discussion
        finally:
            module.HERMES_HOME = original_home


def test_build_consult_command_uses_quorum4_discussion_and_keep():
    module = load_module()
    cmd = module.build_consult_run_command(Path("/tmp/state.json"), tier="T3", quorum=4, max_rounds=5, timeout=180)
    joined = " ".join(str(x) for x in cmd)
    assert "consult_models.py" in joined, cmd
    assert "--quorum 4" in joined, cmd
    assert "--discussion" in cmd, cmd
    assert "--keep" in cmd, cmd
    assert "--max-rounds 5" in joined, cmd


def test_ratification_artifact_exports_explicit_acceptance_fields():
    module = load_module()
    artifact = module.build_ratification_artifact(
        certified_discussion(),
        {"done": True, "next_action": "LOOP_DONE", "blocking_reasons": []},
        discussion_result_path=Path("/tmp/discussion_result.json"),
        issue_ledger_path=Path("/tmp/issue-ledger.json"),
        state_path=Path("/tmp/state.json"),
    )
    assert artifact["consult_models"]["discussion_result_status"] == "certified", artifact
    assert artifact["consult_models"]["agreement_matrix"]["approach"] == 0.95, artifact
    assert len(artifact["consult_models"]["ratification_votes"]) == 4, artifact
    assert artifact["consult_models"]["best_within_constraints_by_model"]["claude-opus-4-7"] is True, artifact
    assert artifact["consult_models"]["issue_ledger"][0]["status"] == "resolved", artifact
    assert artifact["consult_models"]["remaining_risks"] == [], artifact
    assert artifact["verifier"]["done"] is True, artifact


def test_build_state_payload_records_quota_probe_and_ratification_export_claims():
    module = load_module()
    state = module.build_state_payload("q", {"status": "PASS", "commands": [], "failures": []}, 1)
    claim_ids = {claim["id"] for claim in state["claims"]}
    evidence_types = {evidence.get("type") for evidence in state["evidence"]}
    assert "C-003" in claim_ids, state
    assert "C-004" in claim_ids, state
    assert "runner_capability_probe" in evidence_types, state
    assert "model_quota_probe" in evidence_types, state
    assert state["budget"]["model_quota_probe"]["status"] in {"ok", "unknown", "unavailable"}, state


def test_ratification_selfcheck_cli_dumps_certification_artifact():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        fixture = write_json(root / "discussion_result.json", certified_discussion())
        r = subprocess.run([
            sys.executable,
            str(SCRIPT),
            "ratification-selfcheck",
            "--discussion-result",
            str(fixture),
            "--json",
        ], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr or r.stdout
        payload = json.loads(r.stdout)
        assert payload["status"] == "PASS", payload
        assert payload["artifact"]["consult_models"]["discussion_result_status"] == "certified", payload
        assert payload["artifact"]["consult_models"]["best_within_constraints_by_model"], payload


def test_probe_quota_cli_outputs_read_only_probe():
    r = subprocess.run([
        sys.executable,
        str(SCRIPT),
        "--probe-quota",
        "--json",
    ], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr or r.stdout
    payload = json.loads(r.stdout)
    assert payload["status"] in {"ok", "unavailable"}, payload
    assert "model_quota_probe" in payload, payload
    assert len(payload["model_quota_probe"]["models"]) == 4, payload


def test_dry_run_injected_amend_vote_reports_stop_gate_false():
    r = subprocess.run([
        sys.executable,
        str(SCRIPT),
        "--dry-run",
        "--inject",
        "amend_vote",
        "--json",
    ], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr or r.stdout
    payload = json.loads(r.stdout)
    assert payload["ratification"]["stop_gate"] is False, payload
    assert "non_approve_vote" in payload["ratification"]["reasons"], payload


def test_selfcheck_runtime_writes_synthetic_ratification_artifact():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "runtime-artifact.json"
        r = subprocess.run([
            sys.executable,
            str(SCRIPT),
            "--selfcheck-runtime",
            "--artifact-out",
            str(out),
            "--json",
        ], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr or r.stdout
        payload = json.loads(r.stdout)
        assert payload["status"] == "PASS", payload
        assert payload["ratification"]["stop_gate"] is True, payload
        assert out.exists(), payload
        artifact = json.loads(out.read_text())
        assert artifact["consult_models"]["discussion_result_status"] == "certified", artifact


def test_cli_fixture_certified_exits_zero_and_writes_state():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        fixture = write_json(root / "discussion_result.json", certified_discussion())
        out = root / "state.json"
        r = subprocess.run([
            sys.executable,
            str(SCRIPT),
            "--discussion-result",
            str(fixture),
            "--round-dir",
            str(root / "rounds"),
            "--state-out",
            str(out),
            "--skip-deterministic",
            "--json",
        ], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr or r.stdout
        payload = json.loads(r.stdout)
        assert payload["status"] == "LOOP_DONE", payload
        assert payload["rounds_used"] == 1, payload
        assert out.exists(), payload


def test_cli_fixture_not_certified_max_rounds_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        data = certified_discussion()
        data["status"] = "not_certified"
        data["issue_ledger"].append({"id": "I-003", "severity": 3, "status": "unresolved"})
        fixture = write_json(root / "discussion_result.json", data)
        r = subprocess.run([
            sys.executable,
            str(SCRIPT),
            "--discussion-result",
            str(fixture),
            "--round-dir",
            str(root / "rounds"),
            "--skip-deterministic",
            "--max-loop-rounds",
            "1",
            "--json",
        ], capture_output=True, text=True)
        assert r.returncode == 3, r.stderr or r.stdout
        payload = json.loads(r.stdout)
        assert payload["status"] == "NOT_CERTIFIED_MAX_ROUNDS", payload
        assert payload["rounds"][0]["verdict"]["done"] is False, payload


def test_cli_missing_discussion_writes_fail_closed_artifact():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        missing = root / "missing-discussion_result.json"
        r = subprocess.run([
            sys.executable,
            str(SCRIPT),
            "--discussion-result",
            str(missing),
            "--round-dir",
            str(root / "rounds"),
            "--skip-deterministic",
            "--max-loop-rounds",
            "1",
            "--json",
        ], capture_output=True, text=True)
        assert r.returncode == 3, r.stderr or r.stdout
        payload = json.loads(r.stdout)
        round0 = payload["rounds"][0]
        assert round0["verdict"]["blocking_reasons"] == ["discussion_result_missing"], payload
        artifact_path = Path(round0["ratification_artifact_path"])
        assert artifact_path.exists(), payload
        artifact = json.loads(artifact_path.read_text())
        assert artifact["consult_models"]["discussion_result_status"] == "missing", artifact
        assert artifact["verifier"]["done"] is False, artifact
        assert artifact["verifier"]["next_action"] == "continue_loop", artifact


def test_main_empty_consult_discussion_path_writes_fail_closed_artifact_without_traceback():
    module = load_module()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        original_run_consult = module.run_consult
        module.run_consult = lambda *args, **kwargs: {"mode": "fake", "discussion_result_path": "", "returncode": 0}
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                code = module.main([
                    "--round-dir", str(root / "rounds"),
                    "--skip-deterministic",
                    "--max-loop-rounds", "1",
                    "--json",
                ])
        finally:
            module.run_consult = original_run_consult
        assert code == 3
        payload = json.loads(out.getvalue())
        round0 = payload["rounds"][0]
        assert round0["verdict"]["blocking_reasons"] == ["discussion_result_missing"], payload
        artifact_path = Path(round0["ratification_artifact_path"])
        assert artifact_path.exists(), payload
        artifact = json.loads(artifact_path.read_text())
        assert artifact["consult_models"]["discussion_result_status"] == "missing", artifact


def test_verify_ratification_rejects_partial_certified_shell():
    module = load_module()
    data = {
        "status": "certified",
        "models_consulted": ["claude-opus-4-7", "gpt-5.5", "deepseek-v4-pro"],
        "issue_ledger": [],
        "remaining_risks": [],
    }
    passed, reasons = module.verify_ratification(data)
    assert passed is False
    assert "agreement_matrix_missing" in reasons, reasons
    assert "ratification_votes_missing" in reasons, reasons
    assert "truth_assessment_missing" in reasons, reasons
    assert "evidence_coverage_missing" in reasons, reasons
    verdict = module.evaluate_discussion(data)
    assert verdict["done"] is False, verdict


def test_verify_ratification_rejects_missing_best_within_constraints():
    module = load_module()
    data = certified_discussion()
    del data["ratification_votes"][0]["best_within_constraints"]
    passed, reasons = module.verify_ratification(data)
    assert passed is False
    assert "best_within_constraints_missing_or_false" in reasons, reasons


def test_verify_ratification_rejects_bool_and_nonfinite_numeric_fields():
    module = load_module()
    data = certified_discussion()
    data["agreement_matrix"]["approach"] = True
    data["truth_assessment"]["evidence_coverage"] = "NaN"
    passed, reasons = module.verify_ratification(data)
    assert passed is False
    assert "agreement_invalid:approach" in reasons, reasons
    assert "evidence_coverage_invalid" in reasons, reasons


def run_fixture_cli(fixture: Path, round_root: Path) -> dict:
    r = subprocess.run([
        sys.executable,
        str(SCRIPT),
        "--discussion-result",
        str(fixture),
        "--round-dir",
        str(round_root / "rounds"),
        "--skip-deterministic",
        "--max-loop-rounds",
        "1",
        "--json",
    ], capture_output=True, text=True)
    assert r.returncode == 3, r.stderr or r.stdout
    return json.loads(r.stdout)


def assert_fail_closed_malformed_payload(payload: dict, reason: str):
    assert payload["status"] == "NOT_CERTIFIED_MAX_ROUNDS", payload
    round0 = payload["rounds"][0]
    reasons = round0["verdict"]["blocking_reasons"]
    assert reason in reasons, payload
    assert round0["verdict"]["done"] is False, payload
    artifact_path = Path(round0["ratification_artifact_path"])
    assert artifact_path.exists(), payload
    artifact = json.loads(artifact_path.read_text())
    assert artifact["consult_models"]["discussion_result_status"] == "malformed", artifact
    assert artifact["verifier"]["next_action"] == "continue_loop", artifact


def test_cli_invalid_json_discussion_writes_fail_closed_artifact():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        fixture = root / "discussion_result.json"
        fixture.write_text("{not json", encoding="utf-8")
        payload = run_fixture_cli(fixture, root)
        assert_fail_closed_malformed_payload(payload, "discussion_result_malformed")


def test_cli_zero_byte_discussion_writes_fail_closed_artifact():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        fixture = root / "discussion_result.json"
        fixture.write_text("", encoding="utf-8")
        payload = run_fixture_cli(fixture, root)
        assert_fail_closed_malformed_payload(payload, "discussion_result_malformed")


def test_cli_non_object_discussion_writes_fail_closed_artifact():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        fixture = root / "discussion_result.json"
        fixture.write_text("[]", encoding="utf-8")
        payload = run_fixture_cli(fixture, root)
        assert_fail_closed_malformed_payload(payload, "discussion_result_schema_invalid")


def test_cli_partial_certified_discussion_fails_closed_without_loop_done():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        fixture = write_json(root / "discussion_result.json", {
            "status": "certified",
            "models_consulted": ["claude-opus-4-7", "gpt-5.5", "deepseek-v4-pro"],
            "issue_ledger": [],
            "remaining_risks": [],
        })
        payload = run_fixture_cli(fixture, root)
        assert_fail_closed_malformed_payload(payload, "discussion_result_schema_invalid")



def test_verify_ratification_rejects_nonfinite_numeric_fields():
    module = load_module()
    data = certified_discussion()
    data["agreement_matrix"]["approach"] = float("nan")
    data["truth_assessment"]["evidence_coverage"] = float("inf")
    data["issue_ledger"].append({"id": "I-BAD", "severity": "NaN", "status": "unresolved"})
    passed, reasons = module.verify_ratification(data)
    assert passed is False
    assert "agreement_invalid:approach" in reasons, reasons
    assert "evidence_coverage_invalid" in reasons, reasons
    assert "open_high_severity_issue" not in reasons, reasons


def test_not_certified_schema_gaps_remain_not_certified_not_malformed():
    module = load_module()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        fixture = write_json(root / "discussion_result.json", {"status": "not_certified"})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = module.main([
                "--discussion-result", str(fixture),
                "--round-dir", str(root / "rounds"),
                "--skip-deterministic",
                "--max-loop-rounds", "1",
                "--json",
            ])
        assert code == 3
        payload = json.loads(out.getvalue())
        round0 = payload["rounds"][0]
        assert "discussion_result_schema_invalid" not in round0["verdict"]["blocking_reasons"], payload
        assert "status_not_certified" in round0["verdict"]["blocking_reasons"], payload
        artifact = json.loads(Path(round0["ratification_artifact_path"]).read_text())
        assert artifact["consult_models"]["discussion_result_status"] == "not_certified", artifact


def test_verify_ratification_rejects_duplicate_or_missing_approval_vote_models():
    module = load_module()
    data = certified_discussion()
    data["ratification_votes"][1]["model"] = data["ratification_votes"][0]["model"]
    data["ratification_votes"][2].pop("model")
    passed, reasons = module.verify_ratification(data)
    assert passed is False
    assert "duplicate_approval_vote_model" in reasons, reasons
    assert "ratification_vote_model_missing" in reasons, reasons
    assert "insufficient_approval_votes" in reasons, reasons


def test_verify_ratification_rejects_malformed_ledger_blocker_shapes():
    module = load_module()
    data = certified_discussion()
    data["issue_ledger"] = [{"id": "I-BAD", "severity": "NaN", "status": "unresolved"}]
    data["remaining_risks"] = [{"id": "R-BAD", "severity": True, "status": "unresolved"}]
    passed, reasons = module.verify_ratification(data)
    assert passed is False
    assert "issue_severity_invalid" in reasons, reasons
    assert "remaining_risk_severity_invalid" in reasons, reasons


def test_ratification_selfcheck_fails_when_verifier_stop_gate_false():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        data = certified_discussion()
        data["ratification_votes"][0]["vote"] = "amend"
        fixture = write_json(root / "discussion_result.json", data)
        r = subprocess.run([
            sys.executable,
            str(SCRIPT),
            "ratification-selfcheck",
            "--discussion-result",
            str(fixture),
            "--json",
        ], capture_output=True, text=True)
        assert r.returncode == 2, r.stderr or r.stdout
        payload = json.loads(r.stdout)
        assert payload["status"] == "FAIL", payload
        assert payload["ratification"]["stop_gate"] is False, payload


def test_ratification_selfcheck_empty_path_fails_closed_without_traceback():
    r = subprocess.run([
        sys.executable,
        str(SCRIPT),
        "ratification-selfcheck",
        "--discussion-result",
        "",
        "--json",
    ], capture_output=True, text=True)
    assert r.returncode == 2, r.stderr or r.stdout
    payload = json.loads(r.stdout)
    assert payload["status"] == "FAIL", payload
    assert payload["artifact"]["consult_models"]["discussion_result_status"] == "malformed", payload
    assert payload["ratification"]["stop_gate"] is False, payload



def test_verify_ratification_rejects_duplicate_consulted_models_and_fake_approval_models():
    module = load_module()
    data = certified_discussion()
    data["models_consulted"] = ["claude-opus-4-7", "claude-opus-4-7", "gpt-5.5"]
    data["ratification_votes"] = [
        {"model": "claude-opus-4-7", "vote": "approve", "best_within_constraints": True},
        {"model": "fake-b", "vote": "approve", "best_within_constraints": True},
        {"model": "fake-c", "vote": "approve", "best_within_constraints": True},
    ]
    passed, reasons = module.verify_ratification(data)
    assert passed is False
    assert "duplicate_consulted_model" in reasons, reasons
    assert "duplicate_consulted_model_family" in reasons, reasons
    assert "insufficient_model_count" in reasons, reasons
    assert "ratification_vote_model_unknown" in reasons, reasons


def test_verify_ratification_rejects_missing_truth_negative_evidence_fields():
    module = load_module()
    data = certified_discussion()
    data["truth_assessment"] = {"can_certify_truth": True, "evidence_coverage": 1.0}
    passed, reasons = module.verify_ratification(data)
    assert passed is False
    assert "unsupported_claims_missing" in reasons, reasons
    assert "contradicted_claims_missing" in reasons, reasons
    assert "unsupported_high_severity_claim" in reasons, reasons
    assert "contradicted_high_severity_claim" in reasons, reasons


def test_verify_ratification_requires_explicit_truth_certification():
    module = load_module()
    data = certified_discussion()
    data["truth_assessment"].pop("can_certify_truth")
    passed, reasons = module.verify_ratification(data)
    assert passed is False
    assert "truth_not_certified" in reasons, reasons




def test_verify_ratification_requires_vote_from_every_consulted_model():
    module = load_module()
    data = certified_discussion()
    data["models_consulted"] = ["claude-opus-4-7", "gpt-5.5", "deepseek-v4-pro", "mimo-v2.5-pro"]
    data["ratification_votes"] = [
        {"model": "claude-opus-4-7", "vote": "approve", "best_within_constraints": True},
        {"model": "gpt-5.5", "vote": "approve", "best_within_constraints": True},
        {"model": "deepseek-v4-pro", "vote": "approve", "best_within_constraints": True},
    ]
    passed, reasons = module.verify_ratification(data)
    assert passed is False
    assert "insufficient_approval_votes" in reasons, reasons
    verdict = module.evaluate_discussion(data)
    assert verdict["done"] is False, verdict


def test_verify_ratification_rejects_same_family_spoofed_model_names():
    module = load_module()
    data = certified_discussion()
    data["models_consulted"] = ["claude-fake", "gpt-fake", "deepseek-fake"]
    data["ratification_votes"] = [
        {"model": "anthropic-shadow", "vote": "approve", "best_within_constraints": True},
        {"model": "openai-shadow", "vote": "approve", "best_within_constraints": True},
        {"model": "deepseek-shadow", "vote": "approve", "best_within_constraints": True},
    ]
    passed, reasons = module.verify_ratification(data)
    assert passed is False
    assert "model_consulted_unknown" in reasons, reasons
    assert "ratification_vote_model_unknown" in reasons, reasons
    verdict = module.evaluate_discussion(data)
    assert verdict["done"] is False, verdict



if __name__ == "__main__":
    test_certified_discussion_stops_loop()
    test_verify_ratification_exposes_explicit_pass_reasons_api()
    test_should_continue_inverts_ratification_api()
    test_amend_vote_continues_loop()
    test_unresolved_high_severity_issue_blocks_even_if_status_certified()
    test_run_consult_timeout_fails_closed_without_traceback()
    test_build_consult_command_uses_quorum4_discussion_and_keep()
    test_ratification_artifact_exports_explicit_acceptance_fields()
    test_build_state_payload_records_quota_probe_and_ratification_export_claims()
    test_ratification_selfcheck_cli_dumps_certification_artifact()
    test_probe_quota_cli_outputs_read_only_probe()
    test_dry_run_injected_amend_vote_reports_stop_gate_false()
    test_selfcheck_runtime_writes_synthetic_ratification_artifact()
    test_cli_fixture_certified_exits_zero_and_writes_state()
    test_cli_fixture_not_certified_max_rounds_fails_closed()
    test_cli_missing_discussion_writes_fail_closed_artifact()
    test_main_empty_consult_discussion_path_writes_fail_closed_artifact_without_traceback()
    test_verify_ratification_rejects_partial_certified_shell()
    test_verify_ratification_rejects_missing_best_within_constraints()
    test_verify_ratification_rejects_bool_and_nonfinite_numeric_fields()
    test_cli_invalid_json_discussion_writes_fail_closed_artifact()
    test_cli_zero_byte_discussion_writes_fail_closed_artifact()
    test_cli_non_object_discussion_writes_fail_closed_artifact()
    test_cli_partial_certified_discussion_fails_closed_without_loop_done()
    test_verify_ratification_rejects_nonfinite_numeric_fields()
    test_not_certified_schema_gaps_remain_not_certified_not_malformed()
    test_verify_ratification_rejects_duplicate_or_missing_approval_vote_models()
    test_verify_ratification_rejects_malformed_ledger_blocker_shapes()
    test_ratification_selfcheck_fails_when_verifier_stop_gate_false()
    test_ratification_selfcheck_empty_path_fails_closed_without_traceback()
    test_verify_ratification_rejects_duplicate_consulted_models_and_fake_approval_models()
    test_verify_ratification_rejects_missing_truth_negative_evidence_fields()
    test_verify_ratification_requires_explicit_truth_certification()
    test_verify_ratification_requires_vote_from_every_consulted_model()
    test_verify_ratification_rejects_same_family_spoofed_model_names()
    print("PASS")
