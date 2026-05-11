#!/usr/bin/env python3
"""Regression tests for self-improvement priority ghost suppression."""

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "self-improvement-pipeline.py"


def load_module():
    spec = importlib.util.spec_from_file_location("self_improvement_pipeline", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestSelfImprovementPipeline(unittest.TestCase):
    def test_stale_tool_failure_is_suppressed_when_ops_are_green(self):
        mod = load_module()
        old_health = mod.current_ops_healthy
        try:
            mod.current_ops_healthy = lambda: True
            signals = [{
                "signals": [{
                    "type": "tool_failures",
                    "count": 9,
                    "detail": "terminal failed historically",
                    "_parent_timestamp": "2000-01-01T00:00:00",
                }]
            }]
            items = mod.aggregate_items(signals, [], {}, [])
            self.assertFalse(any(it.act_type == "fix_tool_config" for it in items))
        finally:
            mod.current_ops_healthy = old_health

    def test_low_skill_detection_uses_latest_score_per_skill(self):
        mod = load_module()
        darwin = [
            {"skill": "p10", "new_score": "51", "status": "baseline"},
            {"skill": "p10", "new_score": "100", "status": "accepted"},
            {"skill": "p9", "new_score": "46", "status": "baseline"},
            {"skill": "p9", "new_score": "100", "status": "accepted"},
        ]
        items = mod.aggregate_items([], [], {}, darwin)
        self.assertFalse(any(it.act_type == "improve_low_skills" for it in items))

    def test_auto_execute_skipped_fix_tool_config_writes_readonly_diagnostic(self):
        mod = load_module()
        import tempfile, json
        with tempfile.TemporaryDirectory() as td:
            old_notes = mod.NOTES_DIR
            old_diag = getattr(mod, "DIAGNOSTICS_DIR", None)
            try:
                mod.NOTES_DIR = td
                mod.DIAGNOSTICS_DIR = td
                item = mod.ActionItem(
                    "fix_tool_config",
                    "工具失败 2 次",
                    "high",
                    "medium",
                    detail=json.dumps({
                        "failure_groups": [{
                            "tool_name": "terminal",
                            "error_signature": "timeout",
                            "exit_code": 124,
                            "count": 2,
                            "first_seen": "2026-05-06T00:00:00",
                            "last_seen": "2026-05-06T00:01:00",
                        }]
                    }, ensure_ascii=False),
                    source="session_autopsy",
                    category="reliability",
                )
                summary = mod.auto_execute([item])
                self.assertEqual(summary["actionable_count"], 0)
                self.assertEqual(summary["skipped_below_threshold_count"], 1)
                self.assertEqual(summary["pending_review_count"], 1)
                self.assertEqual(summary["executed_count"], 0)
                self.assertEqual(summary["top_item_roi"], 1.75)
                self.assertEqual(summary["skipped_reason"], "roi_below_threshold")
                self.assertEqual(len(summary["diagnostic_paths"]), 1)
                diagnostic = json.loads(Path(summary["diagnostic_paths"][0]).read_text())
                self.assertFalse(diagnostic["auto_edit_config"])
                self.assertEqual(diagnostic["schema_version"], "tool_failure_diagnostic_v1")
                self.assertEqual(diagnostic["safe_next_action"], "human_review_or_targeted_fix")
                self.assertEqual(diagnostic["action_type"], "fix_tool_config")
                self.assertEqual(diagnostic["failures"][0]["tool_name"], "terminal")
            finally:
                mod.NOTES_DIR = old_notes
                if old_diag is not None:
                    mod.DIAGNOSTICS_DIR = old_diag

    def test_actionable_fix_tool_config_counts_single_pending_review(self):
        mod = load_module()
        import tempfile, json
        with tempfile.TemporaryDirectory() as td:
            old_notes = mod.NOTES_DIR
            old_diag = getattr(mod, "DIAGNOSTICS_DIR", None)
            try:
                mod.NOTES_DIR = td
                mod.DIAGNOSTICS_DIR = td
                item = mod.ActionItem(
                    "fix_tool_config",
                    "工具失败 3 次",
                    "high",
                    "low",
                    detail=json.dumps({"failure_groups": [{"tool_name": "terminal", "error_signature": "timeout", "count": 3}]}, ensure_ascii=False),
                    source="session_autopsy",
                    category="reliability",
                )
                summary = mod.auto_execute([item])
                self.assertEqual(summary["actionable_count"], 1)
                self.assertEqual(summary["executed_count"], 0)
                self.assertEqual(summary["pending_review_count"], 1)
                self.assertEqual(summary["skipped_below_threshold_count"], 0)
                self.assertEqual(len(summary["diagnostic_paths"]), 1)
            finally:
                mod.NOTES_DIR = old_notes
                if old_diag is not None:
                    mod.DIAGNOSTICS_DIR = old_diag

    def test_evolution_closure_distinguishes_queue_from_useful_evolution(self):
        mod = load_module()
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            old_log = mod.EVOLVE_LOG_PATH
            try:
                mod.EVOLVE_LOG_PATH = str(Path(td) / "evolve.log")
                item = mod.ActionItem("fix_tool_config", "工具失败 2 次", "high", "medium")
                summary = {
                    "actionable_count": 0,
                    "executed_count": 0,
                    "pending_review_count": 1,
                    "skipped_below_threshold_count": 1,
                    "top_item_roi": 1.75,
                    "top_item_impact": 7,
                    "skipped_reason": "roi_below_threshold",
                    "diagnostic_paths": ["/tmp/tool-failure-diagnostic-test.json"],
                }
                event = mod.append_evolution_closure([item], mode="auto_exec", execution_summary=summary)
                self.assertEqual(event["eval_result"], "not_evaluated_no_execution")
                self.assertFalse(event["useful_evolution"])
                self.assertFalse(event["eval_applicable"])
                self.assertEqual(event["generated_count"], 1)
                self.assertEqual(event["actionable_count"], 0)
                self.assertEqual(event["pending_review_count"], 1)
                self.assertEqual(event["skipped_reason"], "roi_below_threshold")
                self.assertNotIn("baseline", event)
                self.assertNotIn("delta", event)
            finally:
                mod.EVOLVE_LOG_PATH = old_log


if __name__ == "__main__":
    unittest.main(verbosity=2)
