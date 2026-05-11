#!/usr/bin/env python3
"""
Evolution System Test Suite
用法: python3 test_evolution_system.py [-v]
"""
import os, sys, json, unittest

HERMES = os.path.expanduser("~/.hermes")
DB = os.path.join(HERMES, "skills/bayesian-agent/confidence-db.json")
HEALTH = os.path.join(HERMES, "notes/engineering-cybernetics/health-history.jsonl")

class TestEvolutionSystem(unittest.TestCase):
    def test_db_exists(self):
        self.assertTrue(os.path.exists(DB), "confidence-db.json 不存在")
    
    def test_db_has_skills(self):
        with open(DB) as f:
            db = json.load(f)
        self.assertIn("skills", db)
        self.assertGreater(len(db["skills"]), 0)
    
    def test_no_d_grade(self):
        with open(DB) as f:
            db = json.load(f)
        d_count = sum(1 for d in db["skills"].values() if d.get("darwin_grade") == "D")
        self.assertEqual(d_count, 0, f"发现 {d_count} 个 D 级 skill")
    
    def test_health_history_exists(self):
        self.assertTrue(os.path.exists(HEALTH), "health-history.jsonl 不存在")
    
    def test_health_records_valid(self):
        with open(HEALTH) as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    self.assertIn("timestamp", rec)
                    self.assertIn("V", rec)
                    self.assertGreaterEqual(rec["V"], 0.0)
                    self.assertLessEqual(rec["V"], 1.0)
    
    def test_critical_scripts_exist(self):
        required = [
            "session-end-recorder.py",
            "pa-evolution-trigger.py",
            "sync-to-obsidian.py",
            "nl-dashboard-query.py",
            "emergency-recovery.py",
        ]
        for s in required:
            path = os.path.join(HERMES, "scripts", s)
            self.assertTrue(os.path.exists(path), f"{s} 不存在")

if __name__ == "__main__":
    verbosity = 2 if "-v" in sys.argv else 1
    unittest.main(verbosity=verbosity)
