#!/usr/bin/env python3
"""Tests for Agent COS ratification-first status gates."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SELF_SCRIPT = Path(__file__).parent / "agent_cos_selfcheck.py"
SELF_SPEC = importlib.util.spec_from_file_location("agent_cos_selfcheck", SELF_SCRIPT)
selfcheck = importlib.util.module_from_spec(SELF_SPEC)
SELF_SPEC.loader.exec_module(selfcheck)

GATE_SCRIPT = Path(__file__).parent / "ratification_gate.py"


def load_gate():
    spec = importlib.util.spec_from_file_location("ratification_gate", GATE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MATRIX = """# Agent 认知操作系统互补矩阵

## Self-check Contract

<!-- COS_CONTRACT_START -->
```json
{
  "matrix_status": "A_PLUS_MATRIX_COMPLETE",
  "deterministic_gate_status": "PASS",
  "ratification_status": "CERTIFIED",
  "final_integration_status": "FULLY_CERTIFIED",
  "required_pairings_count": 24,
  "missing_pairs": 0,
  "below_a_plus": 0,
  "required_domains": ["control theory", "systems theory", "cognitive science", "governance"],
  "a_plus_rubric_gates": ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
}
```
<!-- COS_CONTRACT_END -->

控制论/工程控制论 系统科学/复杂性 认知科学 进化论/生物学 认识论/科学哲学 经济学/资源理论 组织管理/军事 C2 计算机科学/AI 治理理论 可靠性工程
R1 R2 R3 R4 R5 R6 R7

| ID | Agent 子系统 | 主理论 | 互补配对 | 操作化机制 | 多模型路由 | 配对状态 | 评级 |
|---|---|---|---|---|---|---|---|
{rows}

## 缺失配对归零说明
"""


class TestAgentCosRatification(unittest.TestCase):
    def make_vault(self, contract_status="CERTIFIED"):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        required = [Path(p) for p in selfcheck.REQUIRED_FILES]
        for rel in required:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if rel.as_posix() == "07-仪表盘/Agent认知操作系统互补矩阵.md":
                rows = "\n".join(
                    f"| COS-{i:02d} | S{i} | T | C | M | T1 | paired | A+ |" for i in range(1, 25)
                )
                text = MATRIX.replace("{rows}", rows).replace('"ratification_status": "CERTIFIED"', f'"ratification_status": "{contract_status}"')
                path.write_text(text, encoding="utf-8")
            else:
                path.write_text("# stub\n", encoding="utf-8")
        return tmp, root

    def test_selfcheck_splits_matrix_completion_from_ratification_status(self):
        tmp, root = self.make_vault(contract_status="NOT_CERTIFIED_TIMEOUT")
        try:
            result = selfcheck.run_check(root)
        finally:
            tmp.cleanup()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["matrix_status"], "A_PLUS_MATRIX_COMPLETE")
        self.assertEqual(result["deterministic_gate_status"], "PASS")
        self.assertEqual(result["ratification_status"], "NOT_CERTIFIED_TIMEOUT")
        self.assertEqual(result["final_integration_status"], "LOCAL_COMPLETE_UNRATIFIED")
        self.assertEqual(result["missing_pairs"], 0)
        self.assertEqual(result["below_a_plus"], 0)

    def test_ratification_gate_fails_without_discussion_artifact(self):
        gate = load_gate()
        tmp, root = self.make_vault(contract_status="NOT_CERTIFIED_TIMEOUT")
        try:
            result = gate.evaluate(root=root, discussion_result_path=root / "missing-discussion.json")
        finally:
            tmp.cleanup()
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["ratification_status"], "NOT_CERTIFIED_NO_ARTIFACT")
        self.assertEqual(result["final_integration_status"], "LOCAL_COMPLETE_UNRATIFIED")
        self.assertIn("discussion_result_missing", result["blocking_reasons"])

    def test_ratification_gate_fails_closed_when_no_target_bound_default_artifact(self):
        gate = load_gate()
        tmp, root = self.make_vault(contract_status="NOT_CERTIFIED_NO_ARTIFACT")
        original_latest = gate.latest_discussion_result
        gate.latest_discussion_result = lambda: None
        try:
            result = gate.evaluate(root=root)
        finally:
            gate.latest_discussion_result = original_latest
            tmp.cleanup()
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["ratification_status"], "NOT_CERTIFIED_NO_ARTIFACT")
        self.assertIn("discussion_result_missing", result["blocking_reasons"])

    def test_ratification_gate_passes_certified_discussion_with_no_open_severity3(self):
        gate = load_gate()
        tmp, root = self.make_vault(contract_status="CERTIFIED")
        try:
            discussion = root / "discussion_result.json"
            discussion.write_text(json.dumps({
                "status": "certified",
                "agreement_matrix": {"framing": 0.9, "approach": 0.9, "implementation_order": 0.9},
                "issue_ledger": [{"id": "I-1", "severity": 3, "status": "resolved"}],
                "ratification_votes": [
                    {"model": "claude", "vote": "approve", "best_within_constraints": True},
                    {"model": "codex", "vote": "approve", "best_within_constraints": True},
                    {"model": "deepseek", "vote": "approve", "best_within_constraints": True},
                    {"model": "mimo", "vote": "approve", "best_within_constraints": True},
                ],
                "truth_assessment": {"can_certify_truth": True, "unsupported_high_severity_claim_ids": []},
                "remaining_risks": []
            }), encoding="utf-8")
            result = gate.evaluate(root=root, discussion_result_path=discussion)
        finally:
            tmp.cleanup()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["ratification_status"], "CERTIFIED")
        self.assertEqual(result["final_integration_status"], "FULLY_CERTIFIED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
