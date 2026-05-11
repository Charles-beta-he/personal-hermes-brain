#!/usr/bin/env python3
"""Regression tests for usage-score semantics."""
from __future__ import annotations

import importlib.util
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path.home() / ".hermes" / "scripts" / "usage-score.py"


class UsageScoreTests(unittest.TestCase):
    def load_module(self, db_path: str):
        old = os.environ.get("HERMES_ROUTE_DB_PATH")
        os.environ["HERMES_ROUTE_DB_PATH"] = db_path
        try:
            spec = importlib.util.spec_from_file_location("usage_score_under_test", SCRIPT)
            assert spec and spec.loader
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.read_jsonl = lambda path: []
            mod.cron_stats = lambda: {
                "score_raw": 1.0,
                "ok": 1,
                "total": 1,
                "recent_24h": 1,
                "pending_first_run": 0,
                "bad": 0,
                "source": "test",
            }
            return mod
        finally:
            if old is None:
                os.environ.pop("HERMES_ROUTE_DB_PATH", None)
            else:
                os.environ["HERMES_ROUTE_DB_PATH"] = old

    def make_db(self, path: str):
        conn = sqlite3.connect(path)
        conn.execute(
            """
            CREATE TABLE route_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                skill TEXT NOT NULL,
                task_class TEXT NOT NULL DEFAULT '',
                route TEXT NOT NULL DEFAULT '',
                verdict TEXT NOT NULL DEFAULT 'unknown',
                duration_s REAL DEFAULT 0,
                tokens_in INTEGER DEFAULT 0,
                tokens_out INTEGER DEFAULT 0,
                task_id TEXT DEFAULT '',
                model_chain TEXT DEFAULT '',
                cost_usd REAL DEFAULT 0,
                error TEXT DEFAULT '',
                is_synthetic INTEGER DEFAULT 0,
                chain_id TEXT
            )
            """
        )
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for model in ["gpt-5.5", "claude-opus-4-7", "deepseek-v4-pro", "mimo-v2.5-pro"]:
            conn.execute(
                "INSERT INTO route_outcomes (ts, skill, route, verdict, duration_s, tokens_in, tokens_out, model_chain, cost_usd, is_synthetic) VALUES (?,?,?,?,?,?,?,?,?,0)",
                (ts, "probe", "probe:smoke", "pass", 1.0, 10, 10, model, 0.001),
            )
        for route in ["hook:terminal", "hook:read_file", "hook:patch"]:
            conn.execute(
                "INSERT INTO route_outcomes (ts, skill, route, verdict, duration_s, tokens_in, tokens_out, model_chain, cost_usd, is_synthetic) VALUES (?,?,?,?,?,?,?,?,?,0)",
                (ts, "hook", route, "pass", 0.0, 0, 0, "gpt-5.5", 0.0),
            )
        conn.commit()
        conn.close()

    def test_route_diversity_excludes_hook_bookkeeping_rows(self):
        with tempfile.TemporaryDirectory() as td:
            db = str(Path(td) / "route_outcomes.db")
            self.make_db(db)
            mod = self.load_module(db)
            data = mod.compute()
            rd = data["components"]["route_diversity"]
            self.assertEqual(rd["score"], 15)
            self.assertEqual(rd["evaluated_rows"], 4)
            self.assertEqual(rd["excluded_hook_rows"], 3)
            self.assertEqual(list(rd["routes"].keys()), ["probe:smoke"])

    def test_compute_splits_operational_health_from_evidence_readiness(self):
        with tempfile.TemporaryDirectory() as td:
            db = str(Path(td) / "route_outcomes.db")
            self.make_db(db)
            mod = self.load_module(db)
            data = mod.compute()
            self.assertIn("semantic_grades", data)
            self.assertEqual(data["semantic_grades"]["operational_health"]["grade"], "A")
            self.assertEqual(data["semantic_grades"]["operational_health"]["cron_bad_count"], 0)
            self.assertIn("evidence_readiness", data["semantic_grades"])
            self.assertIn("interpretation", data)
            self.assertIn("runtime", data["interpretation"])

    def test_certified_discussion_results_count_as_ratification_corpus(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = str(root / "route_outcomes.db")
            self.make_db(db)
            tick = root / "tick-20260506-170132"
            tick.mkdir()
            (tick / "discussion_result.json").write_text(
                '{"status":"certified","models_consulted":["gpt-5.5","mimo-v2.5-pro","deepseek-v4-pro"],"truth_assessment":{"truth_status":"grounded","can_certify_truth":true}}'
            )
            mod = self.load_module(db)
            mod.H = root
            data = mod.compute()
            self.assertEqual(data["components"]["ratification_corpus"]["count_7d"], 1)
            self.assertIn("discussion_result", data["components"]["ratification_corpus"]["sources"])
            self.assertNotIn("ratification_corpus", data["semantic_grades"]["evidence_readiness"]["missing"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
