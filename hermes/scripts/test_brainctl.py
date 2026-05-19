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

    def test_html_build_generates_clickable_sidecar_without_mutating_canonical_markdown(self):
        md = self.write_note(
            "07-仪表盘/Dashboard.md",
            "# Dashboard\n\nSee [[05-实践与项目/tasks/Task A]] and [external](https://example.com).\n",
        )
        self.write_note("05-实践与项目/tasks/Task A.md", "# Task A\n\nProof.\n")
        before = md.read_text(encoding="utf-8")
        result = brainctl.html_build(paths=["07-仪表盘/Dashboard.md"], json_mode=True)
        self.assertEqual(result["written_count"], 1)
        html_path = self.vault / "07-仪表盘/Dashboard.html"
        self.assertTrue(html_path.exists())
        html = html_path.read_text(encoding="utf-8")
        self.assertIn('data-canonical-source="07-仪表盘/Dashboard.md"', html)
        self.assertIn('href="Dashboard.md"', html)
        self.assertIn('href="本地大脑图形导航.html"', html)
        self.assertIn('href="../05-实践与项目/tasks/Task A.md"', html)
        self.assertIn('href="https://example.com"', html)
        self.assertEqual(md.read_text(encoding="utf-8"), before)

    def test_html_status_marks_source_stale_and_refresh_restores_freshness(self):
        md = self.write_note("07-仪表盘/Dynamic.md", "# Dynamic\n\nfirst\n")
        brainctl.html_build(paths=["07-仪表盘/Dynamic.md"], json_mode=True)
        md.write_text("# Dynamic\n\nsecond\n", encoding="utf-8")
        status = brainctl.html_status(paths=["07-仪表盘/Dynamic.md"], json_mode=True)
        self.assertEqual(status["items"][0]["status"], "stale_source")
        refreshed = brainctl.html_refresh(paths=["07-仪表盘/Dynamic.md"], json_mode=True)
        self.assertEqual(refreshed["written_count"], 1)
        status = brainctl.html_status(paths=["07-仪表盘/Dynamic.md"], json_mode=True)
        self.assertEqual(status["items"][0]["status"], "fresh")
        self.assertIn("second", (self.vault / "07-仪表盘/Dynamic.html").read_text(encoding="utf-8"))

    def test_html_status_marks_dependency_stale_and_refreshes_dependent_page(self):
        self.write_note("Deps/Source.md", "# Source\n\n[[Deps/Target]]\n")
        target = self.write_note("Deps/Target.md", "# Target\n\nold\n")
        brainctl.html_build(paths=["Deps/Source.md"], json_mode=True)
        target.write_text("# Target\n\nnew\n", encoding="utf-8")
        status = brainctl.html_status(paths=["Deps/Source.md"], json_mode=True)
        self.assertEqual(status["items"][0]["status"], "stale_dependency")
        refreshed = brainctl.html_refresh(paths=["Deps/Source.md"], json_mode=True)
        self.assertEqual(refreshed["written_count"], 1)
        self.assertEqual(brainctl.html_status(paths=["Deps/Source.md"], json_mode=True)["items"][0]["status"], "fresh")

    def test_html_refresh_noops_when_requested_source_is_fresh(self):
        source = self.vault / "07-仪表盘" / "dashboard.md"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("# Dashboard\n", encoding="utf-8")
        brainctl.html_build(paths=["07-仪表盘/dashboard.md"], json_mode=True)

        result = brainctl.html_refresh(paths=["07-仪表盘/dashboard.md"], json_mode=True)

        self.assertEqual(result["written_count"], 0)

    def test_html_graph_generates_big_screen_navigation_from_manifest(self):
        self.write_note("07-仪表盘/Dashboard.md", "# Dashboard\n\n[[05-实践与项目/projects/Demo/Project - Demo]]\n")
        self.write_note("05-实践与项目/projects/Demo/Project - Demo.md", "# Demo\n\n[review](../../../../06-治理与评审/reviews/Review.md)\n")
        self.write_note("06-治理与评审/reviews/Review.md", "# Review\n")
        brainctl.html_build(json_mode=True)

        result = brainctl.html_graph(json_mode=True)

        self.assertEqual(result["schema"], "local_brain_html_graph_v1")
        self.assertEqual(result["node_count"], 3)
        graph_path = self.vault / "07-仪表盘" / "本地大脑图形导航.html"
        self.assertTrue(graph_path.exists())
        html = graph_path.read_text(encoding="utf-8")
        self.assertIn('data-local-brain-entry="react-app-redirect"', html)
        self.assertIn('url=local-brain-app/index.html', html)
        self.assertIn('href="local-brain-app/index.html"', html)
        self.assertIn("React Cockpit / Mission Control", html)
        self.assertIn("HTML nodes", html)
        self.assertIn("Edges", html)
        self.assertIn("本地大脑HTML入口", html)

    def test_html_graph_creates_obsidian_visible_markdown_launcher(self):
        self.write_note("07-仪表盘/Dashboard.md", "# Dashboard\n")
        brainctl.html_build(json_mode=True)

        result = brainctl.html_graph(json_mode=True)

        launcher = self.vault / "07-仪表盘" / "本地大脑HTML入口.md"
        self.assertTrue(launcher.exists())
        text = launcher.read_text(encoding="utf-8")
        self.assertIn("generated: true", text)
        self.assertIn("本地大脑图形导航.html", text)
        self.assertIn("本地大脑HTML跳转测试.md", text)
        self.assertIn("file://", text)
        self.assertEqual(result["launcher"], "07-仪表盘/本地大脑HTML入口.md")

    def test_html_graph_creates_jump_test_file_and_richer_big_screen_details(self):
        self.write_note("07-仪表盘/Dashboard.md", "# Dashboard\n\n[[05-实践与项目/projects/Demo/Project - Demo]]\n")
        self.write_note("05-实践与项目/projects/Demo/Project - Demo.md", "# Demo\n\n[[06-治理与评审/reviews/Review]]\n")
        self.write_note("06-治理与评审/reviews/Review.md", "# Review\n")
        brainctl.html_build(json_mode=True)

        result = brainctl.html_graph(json_mode=True)

        self.assertEqual(result["jump_test"], "07-仪表盘/本地大脑HTML跳转测试.md")
        graph = (self.vault / "07-仪表盘" / "本地大脑图形导航.html").read_text(encoding="utf-8")
        self.assertIn('data-local-brain-entry="react-app-redirect"', graph)
        self.assertIn('url=local-brain-app/index.html', graph)
        self.assertIn("跳转测试", graph)
        self.assertIn("React Cockpit / Mission Control", graph)
        self.assertIn("HTML nodes", graph)
        jump = (self.vault / "07-仪表盘" / "本地大脑HTML跳转测试.md").read_text(encoding="utf-8")
        self.assertIn("# 本地大脑 HTML 跳转测试", jump)
        self.assertIn("兼容图形导航入口", jump)
        self.assertIn("仪表盘样例", jump)
        self.assertIn("项目样例", jump)
        self.assertIn("治理评审样例", jump)
        self.assertIn("file://", jump)
        self.assertIn("05-实践与项目/projects/Demo/Project - Demo.html", jump)

    def test_parser_exposes_html_command(self):
        parser = brainctl.build_parser()
        subparsers = next(action for action in parser._actions if action.dest == "cmd")
        self.assertIn("html", set(subparsers.choices))
        html_parser = subparsers.choices["html"]
        html_subparsers = next(action for action in html_parser._actions if action.dest == "html_cmd")
        self.assertIn("watch", set(html_subparsers.choices))
        self.assertIn("graph", set(html_subparsers.choices))

    def test_dev_brain_snapshot_contains_engineering_execution_contract(self):
        import yaml

        dev_path = SCRIPT.parent.parent / "brains" / "dev" / "brain.yaml"
        dev = yaml.safe_load(dev_path.read_text(encoding="utf-8"))

        self.assertEqual(dev["id"], "dev")
        self.assertEqual(dev["inherits"], "base")
        self.assertIn("software_engineering_execution", dev.get("capabilities", []))
        self.assertIn("frontend", dev["profiles"])
        self.assertIn("backend", dev["profiles"])
        self.assertIn("fullstack", dev["profiles"])
        self.assertIn("qa_verification", dev["profiles"])
        self.assertIn("no_feature_entry_field_loss", dev["red_lines"])
        self.assertIn("backend_field_change_requires_flyway_and_prod_confirmation", dev["red_lines"])
        self.assertIn("project_code_not_pushed_by_default", dev["red_lines"])
        self.assertIn("required_fields", dev["taskpool_contract"])
        self.assertIn("brain", dev["taskpool_contract"]["required_fields"])
        self.assertIn("verification_contract", dev["taskpool_contract"]["required_fields"])
        self.assertIn("required_context", dev["worker_handoff"])
        self.assertIn("required_output", dev["worker_handoff"])
        self.assertIn("desktop_1280", dev["verification_matrix"]["frontend"])
        self.assertIn("mobile_375", dev["verification_matrix"]["frontend"])
        self.assertTrue(dev["parallelization_policy"]["requires_integration_owner_when"])

    def test_registry_snapshot_routes_engineering_to_dev_and_governance_to_hermes_core(self):
        import yaml

        registry_path = SCRIPT.parent.parent / "brains" / "registry.yaml"
        registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        routing = registry["routing"]

        self.assertEqual(routing["general_software_project_changes"], "dev")
        self.assertEqual(routing["frontend_backend_fullstack_delivery"], "dev")
        self.assertEqual(routing["api_contract_and_browser_harness_verification"], "dev")
        self.assertEqual(routing["brain_overlay_schema_changes"], "hermes-core")
        self.assertEqual(routing["taskpool_multimodel_hook_changes"], "hermes-core")
        self.assertEqual(routing["external_repo_absorption_or_source_validation"], "dev")
        self.assertEqual(routing["local_first_static_app_delivery"], "dev")
        self.assertEqual(routing["cross_brain_capability_gap_closure"], "dev")
        self.assertEqual(routing["design_system_or_design_manual"], "design")
        self.assertEqual(routing["external_source_registry_or_fresh_context"], "research")
        self.assertEqual(routing["media_voice_video_tool_evaluation"], "media")
        self.assertEqual(routing["model_routing_quota_or_mlops"], "mlops")
        self.assertEqual(routing["skill_workflow_ecosystem_or_template_extraction"], "workflow")

    def test_multibrain_route_covers_specialized_brain_profiles(self):
        cases = [
            ("analyze external GitHub repo and decide adopt or reject", "dev", "external_repo_absorption_or_source_validation"),
            ("UI implementation using project DESIGN.md", "design", "design_system_or_design_manual"),
            ("local first React static app browser QA", "dev", "local_first_static_app_delivery"),
            ("research brain has a missing browser connector; implement and hand back", "dev", "cross_brain_capability_gap_closure"),
            ("verify OmniVoiceStudio source validation 404 before adoption", "media", "media_voice_video_tool_evaluation"),
            ("build external source registry from public APIs and Context7", "research", "external_source_registry_or_fresh_context"),
            ("optimize model provider quota routing with keycompute", "mlops", "model_routing_quota_or_mlops"),
            ("absorb spec-kit into workflow templates", "workflow", "skill_workflow_ecosystem_or_template_extraction"),
            ("map OpenClaw control-plane lessons into Hermes taskpool", "hermes-core", "hermes_private_repo_governance"),
        ]
        for query, brain, reason in cases:
            with self.subTest(query=query):
                result = brainctl.multibrain_route(query, json_mode=True)
                self.assertEqual(result["brain"], brain)
                self.assertEqual(result["reason"], reason)


if __name__ == "__main__":
    unittest.main()
