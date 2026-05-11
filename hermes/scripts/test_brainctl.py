#!/usr/bin/env python3
"""Tests for brainctl.py local-brain evidence index."""

import importlib.util
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).parent / "brainctl.py"
spec = importlib.util.spec_from_file_location("brainctl", SCRIPT)
brainctl = importlib.util.module_from_spec(spec)
import sys
sys.modules["brainctl"] = brainctl
spec.loader.exec_module(brainctl)


class BrainctlTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.vault = self.root / "brain"
        self.memory = self.root / "memory"
        self.vault.mkdir()
        self.memory.mkdir()
        self.index = self.memory / "index.sqlite"
        self.wal = self.memory / "wal.jsonl"
        os.environ["HERMES_BRAIN_VAULT"] = str(self.vault)
        os.environ["HERMES_MEMORY_HOME"] = str(self.memory)

    def tearDown(self):
        os.environ.pop("HERMES_BRAIN_VAULT", None)
        os.environ.pop("HERMES_MEMORY_HOME", None)
        os.environ.pop("HERMES_SYNC_BRAIN_SCRIPT", None)
        self.tmp.cleanup()

    def write_note(self, rel, text):
        path = self.vault / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_status_works_without_obsidian_cli(self):
        with patch("shutil.which", return_value=None):
            data = brainctl.status(json_mode=True)
        self.assertEqual(Path(data["vault"]).resolve(), self.vault.resolve())
        self.assertFalse(data["obsidian_cli_available"])
        self.assertEqual(data["mode"], "filesystem_fallback")
        self.assertTrue(data["sync_script"].endswith("sync-brain.py"))

    def test_reindex_creates_fts_blocks_with_schema(self):
        self.write_note("Projects/Test.md", "# Alpha\n\nHermes local brain remembers Obsidian evidence.\n")
        result = brainctl.reindex(json_mode=True)
        self.assertEqual(result["indexed_blocks"], 1)
        con = sqlite3.connect(self.index)
        try:
            rows = con.execute("select path, heading, line_start, line_end, content_hash, excerpt from blocks").fetchall()
        finally:
            con.close()
        self.assertEqual(len(rows), 1)
        path, heading, line_start, line_end, digest, excerpt = rows[0]
        self.assertEqual(path, "Projects/Test.md")
        self.assertEqual(heading, "Alpha")
        self.assertGreaterEqual(line_start, 1)
        self.assertGreaterEqual(line_end, line_start)
        self.assertEqual(len(digest), 64)
        self.assertIn("local brain", excerpt)

    def test_search_returns_evidence_fields_and_wal_without_raw_query_secret(self):
        self.write_note("Research/MemPalace.md", "# MemPalace\n\nEvidence drawer improves local brain recall.\n")
        brainctl.reindex(json_mode=True)
        results = brainctl.search("evidence local", limit=5, json_mode=True)
        self.assertEqual(len(results), 1)
        hit = results[0]
        for key in ["path", "heading", "line_start", "line_end", "content_hash", "excerpt", "score"]:
            self.assertIn(key, hit)
        self.assertEqual(hit["path"], "Research/MemPalace.md")
        secret_query = "sk-1234567890abcdef local"
        brainctl.search(secret_query, limit=5, json_mode=True)
        wal_text = self.wal.read_text(encoding="utf-8")
        self.assertNotIn("sk-1234567890abcdef", wal_text)
        self.assertIn("query_hash", wal_text)

    def test_brainignore_excludes_matching_files(self):
        (self.vault / ".brainignore").write_text("Private/**\n", encoding="utf-8")
        self.write_note("Private/Secret.md", "# Secret\n\nThis should not be indexed.\n")
        self.write_note("Public/Note.md", "# Public\n\nThis should be indexed.\n")
        result = brainctl.reindex(json_mode=True)
        self.assertEqual(result["indexed_blocks"], 1)
        hits = brainctl.search("indexed", json_mode=True)
        self.assertEqual([h["path"] for h in hits], ["Public/Note.md"])

    def test_secret_blocks_are_skipped_and_not_written_to_index_or_wal(self):
        self.write_note("Leak.md", "# Leak\n\nOPENAI_API_KEY=sk-1234567890abcdef should not be indexed.\n")
        result = brainctl.reindex(json_mode=True)
        self.assertEqual(result["skipped_secret_blocks"], 1)
        hits = brainctl.search("OPENAI_API_KEY", json_mode=True)
        self.assertEqual(hits, [])
        if self.wal.exists():
            wal_text = self.wal.read_text(encoding="utf-8")
            self.assertNotIn("sk-1234567890abcdef", wal_text)
            self.assertNotIn("OPENAI_API_KEY=", wal_text)

    def test_wal_tail_returns_json_entries(self):
        self.write_note("A.md", "# A\n\nAlpha beta gamma.\n")
        brainctl.reindex(json_mode=True)
        brainctl.search("alpha", json_mode=True)
        entries = brainctl.wal_tail(limit=2, json_mode=True)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[-1]["op"], "search")
        self.assertIn("ts", entries[-1])

    def test_evidence_alias_returns_same_schema_as_search(self):
        self.write_note("Evidence.md", "# Evidence\n\nObsidian evidence blocks cite line ranges and hashes.\n")
        brainctl.reindex(json_mode=True)
        hits = brainctl.evidence("Obsidian evidence", limit=3, json_mode=True)
        self.assertEqual(len(hits), 1)
        for key in ["path", "heading", "line_start", "line_end", "content_hash", "excerpt", "score"]:
            self.assertIn(key, hits[0])

    def test_parser_does_not_expose_destructive_or_executable_commands(self):
        parser = brainctl.build_parser()
        subparsers = next(action for action in parser._actions if action.dest == "cmd")
        commands = set(subparsers.choices)
        self.assertFalse({"delete", "eval", "command", "plugin"} & commands)
        self.assertTrue({"status", "reindex", "search", "evidence", "wal", "sync", "open"} <= commands)

    def test_status_cli_json_prints_parseable_json(self):
        import contextlib
        import io
        with patch("shutil.which", return_value=None):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = brainctl.main(["--json", "status"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(Path(data["vault"]).resolve(), self.vault.resolve())
        self.assertEqual(data["mode"], "filesystem_fallback")

    def test_sync_delegates_to_configured_script(self):
        sync_script = self.root / "sync-brain.py"
        sync_script.write_text("#!/usr/bin/env python3\nprint('fake sync ok')\n", encoding="utf-8")
        sync_script.chmod(0o755)
        os.environ["HERMES_SYNC_BRAIN_SCRIPT"] = str(sync_script)
        result = brainctl.sync(json_mode=True)
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("fake sync ok", result["stdout"])

    def test_governance_validate_reports_l3_and_review_violations_and_writes_dashboard(self):
        self.write_note(
            "05-实践与项目/tasks/Open Task.md",
            "---\ntype: task\nlayer: L3\nstatus: active\n---\n\n# Open Task\n\nNo expiry yet.\n",
        )
        self.write_note(
            "05-实践与项目/tasks/任务收件箱.md",
            "---\ntype: task_inbox\nstatus: active\nderived: false\n---\n\n# Inbox\n",
        )
        self.write_note(
            "05-实践与项目/tasks/任务池-排序.md",
            "---\ntype: derived_task_pool\nstatus: active\nderived: true\n---\n\n# Sorted Pool\n",
        )
        self.write_note(
            "06-治理与评审/reviews/Review.md",
            "---\ntype: review\nlayer: L6\nstatus: active\n---\n\n# Review\n\nModel agreement only.\n",
        )
        result = brainctl.validate(dry_run=True, write_dashboard=True, json_mode=True)
        self.assertFalse(result["passed"])
        violation_types = {v["type"] for v in result["violations"]}
        missing_expiry_paths = {v["path"] for v in result["violations"] if v["type"] == "missing_l3_expiry"}
        self.assertIn("missing_l3_expiry", violation_types)
        self.assertEqual(missing_expiry_paths, {"05-实践与项目/tasks/Open Task.md"})
        self.assertIn("review_missing_evidence_boundary", violation_types)
        dashboard = self.vault / "07-仪表盘" / "本地大脑治理健康度.md"
        self.assertTrue(dashboard.exists())
        dashboard_text = dashboard.read_text(encoding="utf-8")
        self.assertIn("current snapshot", dashboard_text)
        self.assertIn("missing_l3_expiry", dashboard_text)

    def test_expire_dry_run_reports_missing_and_expired_l3_without_mutation(self):
        self.write_note(
            "05-实践与项目/tasks/Expired.md",
            "---\ntype: task\nlayer: L3\nstatus: active\nexpires_at: 2000-01-01T00:00:00Z\n---\n\n# Expired\n",
        )
        self.write_note(
            "05-实践与项目/tasks/Missing Expiry.md",
            "---\ntype: task\nlayer: L3\nstatus: active\n---\n\n# Missing Expiry\n",
        )
        result = brainctl.expire(dry_run=True, json_mode=True)
        self.assertEqual(result["dry_run"], True)
        self.assertEqual({i["status"] for i in result["items"]}, {"expired", "missing_expiry"})
        self.assertIn("status: active", (self.vault / "05-实践与项目/tasks/Expired.md").read_text(encoding="utf-8"))

    def test_promote_dry_run_finds_evidence_backed_completed_candidates(self):
        self.write_note(
            "05-实践与项目/tasks/Done.md",
            "---\ntype: task\nlayer: L3\nstatus: completed\nexpires_at: 2099-01-01T00:00:00Z\n---\n\n# Done\n\n## Evidence Boundary\n\nTool output proves this.\n\n## Closure Links\n\n- [[Atom]]\n",
        )
        self.write_note(
            "05-实践与项目/tasks/Weak.md",
            "---\ntype: task\nlayer: L3\nstatus: completed\n---\n\n# Weak\n\nNo proof.\n",
        )
        result = brainctl.promote(dry_run=True, json_mode=True)
        candidate_paths = {c["path"] for c in result["candidates"]}
        rejected_paths = {r["path"] for r in result["rejected"]}
        self.assertIn("05-实践与项目/tasks/Done.md", candidate_paths)
        self.assertIn("05-实践与项目/tasks/Weak.md", rejected_paths)

    def test_review_record_writes_standard_l6_artifact(self):
        result = brainctl.review_record(
            title="TDD Review",
            slug="tdd-review",
            evidence_requests=["Run tests"],
            votes=["orchestrator: pass"],
            final_adjudication="accepted with local evidence",
            json_mode=True,
        )
        self.assertTrue(result["ok"])
        note = Path(result["path"])
        self.assertTrue(note.exists())
        text = note.read_text(encoding="utf-8")
        self.assertIn("## Evidence Boundary", text)
        self.assertIn("Run tests", text)
        self.assertIn("accepted with local evidence", text)

    def test_parser_exposes_governance_commands(self):
        parser = brainctl.build_parser()
        subparsers = next(action for action in parser._actions if action.dest == "cmd")
        commands = set(subparsers.choices)
        self.assertTrue({"validate", "expire", "promote", "review"} <= commands)


if __name__ == "__main__":
    unittest.main()
