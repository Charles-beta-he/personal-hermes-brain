#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path
import importlib.util

SCRIPT = Path.home() / ".hermes" / "scripts" / "envelope_bus.py"


def load_module():
    spec = importlib.util.spec_from_file_location("envelope_bus_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EnvelopeEscapeAckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.bus = load_module()
        self.bus.DB_PATH = root / "envelope_bus.db"
        self.bus.ESCAPE_ACK_PATH = root / "envelope_escape_ack.json"
        self.bus.get_db()

    def tearDown(self):
        self.tmp.cleanup()

    def _insert(self, eid, status, ts):
        conn = self.bus.get_db()
        conn.execute(
            """
            INSERT INTO envelopes
              (id,type,status,title,project,assignee,payload,trace,created_at,updated_at,completed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (eid, "TASK", status, eid, "p", "a", "{}", "[]", ts, ts, ts),
        )
        conn.commit()

    def test_missing_ack_counts_historical_failures_fail_closed(self):
        for i in range(3):
            self._insert(f"old-fail-{i}", "FAILED", f"2026-05-10T00:00:0{i}Z")

        triggered, info = self.bus.human_escape_check()

        self.assertTrue(triggered)
        self.assertEqual(info["failures"], 3)
        self.assertEqual(info["since_ack"]["failures"], 3)
        self.assertEqual(info["ack"]["status"], "missing")

    def test_ack_watermark_ignores_reviewed_history_but_not_new_failures(self):
        for i in range(3):
            self._insert(f"old-fail-{i}", "FAILED", f"2026-05-10T00:00:0{i}Z")
        self.bus.acknowledge_escape("reviewed historical timeouts", actor="unit-test", acked_at="2026-05-11T00:00:00Z")

        triggered, info = self.bus.human_escape_check()
        self.assertFalse(triggered)
        self.assertEqual(info["historical"]["failures"], 3)
        self.assertEqual(info["since_ack"]["failures"], 0)
        self.assertEqual(info["ack"]["status"], "ok")

        for i in range(3):
            self._insert(f"new-fail-{i}", "FAILED", f"2026-05-11T00:00:0{i + 1}Z")

        triggered, info = self.bus.human_escape_check()
        self.assertTrue(triggered)
        self.assertEqual(info["since_ack"]["failures"], 3)
        self.assertEqual(info["historical"]["failures"], 6)

    def test_malformed_ack_fails_closed(self):
        for i in range(3):
            self._insert(f"old-fail-{i}", "FAILED", f"2026-05-10T00:00:0{i}Z")
        self.bus.ESCAPE_ACK_PATH.write_text("not-json", encoding="utf-8")

        triggered, info = self.bus.human_escape_check()

        self.assertTrue(triggered)
        self.assertEqual(info["since_ack"]["failures"], 3)
        self.assertEqual(info["ack"]["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
