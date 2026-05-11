#!/usr/bin/env python3
"""Integration tests for ensemble-vote.py tally logic."""

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "ensemble-vote.py"
spec = importlib.util.spec_from_file_location("ensemble_vote", SCRIPT)
ensemble_vote = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ensemble_vote)


class TestEnsembleVoteTally(unittest.TestCase):
    def test_majority_unanimous_pass(self):
        """All 3 vote pass -> consensus=True, verdict=pass"""
        votes = [
            {"model": "m1", "verdict": "pass", "confidence": 0.9},
            {"model": "m2", "verdict": "pass", "confidence": 0.8},
            {"model": "m3", "verdict": "pass", "confidence": 0.7},
        ]
        result = ensemble_vote.majority_vote(votes)
        self.assertTrue(result["consensus"])
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["total_voters"], 3)

    def test_majority_split_no_consensus(self):
        """2 pass, 1 fail -> verdict=pass but consensus=False (not unanimous)"""
        votes = [
            {"model": "m1", "verdict": "pass", "confidence": 0.9},
            {"model": "m2", "verdict": "pass", "confidence": 0.8},
            {"model": "m3", "verdict": "fail", "confidence": 0.7},
        ]
        result = ensemble_vote.majority_vote(votes)
        self.assertEqual(result["verdict"], "pass")
        self.assertFalse(result["consensus"])  # not unanimous

    def test_majority_fail_wins(self):
        """1 pass, 2 fail -> verdict=fail"""
        votes = [
            {"model": "m1", "verdict": "pass", "confidence": 0.9},
            {"model": "m2", "verdict": "fail", "confidence": 0.8},
            {"model": "m3", "verdict": "fail", "confidence": 0.7},
        ]
        result = ensemble_vote.majority_vote(votes)
        self.assertEqual(result["verdict"], "fail")

    def test_weighted_vote_higher_weight_wins(self):
        """Weighted: m1(pass, w=3) vs m2(fail, w=1) -> pass"""
        votes = [
            {"model": "m1", "verdict": "pass"},
            {"model": "m2", "verdict": "fail"},
        ]
        weights = {"m1": 3.0, "m2": 1.0}
        result = ensemble_vote.weighted_vote(votes, weights)
        self.assertEqual(result["verdict"], "pass")

    def test_weighted_vote_lower_weight_loses(self):
        """Weighted: m1(pass, w=1) vs m2(fail, w=3) -> fail"""
        votes = [
            {"model": "m1", "verdict": "pass"},
            {"model": "m2", "verdict": "fail"},
        ]
        weights = {"m1": 1.0, "m2": 3.0}
        result = ensemble_vote.weighted_vote(votes, weights)
        self.assertEqual(result["verdict"], "fail")

    def test_single_voter(self):
        """Single voter -> consensus=True"""
        votes = [{"model": "m1", "verdict": "pass"}]
        result = ensemble_vote.majority_vote(votes)
        self.assertTrue(result["consensus"])
        self.assertEqual(result["verdict"], "pass")

    def test_execute_vote_records_execute_flag_for_usage_score(self):
        """Executed votes must persist execute=True so usage-score can count fresh ensemble evidence."""
        old_call_model = ensemble_vote._call_model
        old_log_file = ensemble_vote.LOG_FILE
        tmp_log = Path(os.environ.get("TMPDIR", "/tmp")) / "ensemble-vote-test.jsonl"
        if tmp_log.exists():
            tmp_log.unlink()
        try:
            ensemble_vote.LOG_FILE = str(tmp_log)
            ensemble_vote._call_model = lambda task, model, workdir=None: {
                "model": model,
                "provider": "test",
                "adapter": "stub",
                "verdict": "pass",
                "output": "PASS",
                "exit_code": 0,
            }
            result = ensemble_vote.vote("smoke", ["m1", "m2", "m3"], execute=True)
            self.assertTrue(result["execute"])
            logged = json.loads(tmp_log.read_text().splitlines()[-1])
            self.assertTrue(logged["execute"])
            self.assertEqual(logged["total_voters"], 3)
        finally:
            ensemble_vote._call_model = old_call_model
            ensemble_vote.LOG_FILE = old_log_file
            if tmp_log.exists():
                tmp_log.unlink()


if __name__ == "__main__":
    unittest.main(verbosity=2)
