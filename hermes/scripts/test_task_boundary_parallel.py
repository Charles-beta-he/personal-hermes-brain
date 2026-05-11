#!/usr/bin/env python3
"""Tests for task boundary alignment and multi-Agent parallel processing.

Tests cover:
1. compute_boundary_key() aligns with orchestrator's resolution order
2. classify_deterministic() v2 boundary-aligned classification
3. validate_boundary_consistency() cross-validation
4. build_worker_context() includes full boundary constraints
5. conflict_group / parallel_group isolation semantics
6. get_parallel_schedule() respects boundary groups
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path.home() / ".hermes" / "scripts"
sys.path.insert(0, str(SCRIPTS))

# Load modules under test
TC_PATH = SCRIPTS / "task_classifier.py"
ATC_PATH = SCRIPTS / "agent_team_controller.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ComputeBoundaryKeyTest(unittest.TestCase):
    """Test that compute_boundary_key matches orchestrator's resolution order."""

    def setUp(self):
        self.tc = load_module("task_classifier", TC_PATH)

    def test_explicit_parallel_boundary(self):
        task = {"id": "t1", "parallel_boundary": "workspace:/tmp/special"}
        self.assertEqual(self.tc.compute_boundary_key(task), "boundary:workspace:/tmp/special")

    def test_workspace_isolation_worktree(self):
        task = {"id": "t2", "workspace_isolation": "worktree"}
        self.assertEqual(self.tc.compute_boundary_key(task), "isolated:t2")

    def test_workspace_isolation_copy(self):
        task = {"id": "t3", "workspace_isolation": "copy"}
        self.assertEqual(self.tc.compute_boundary_key(task), "isolated:t3")

    def test_workspace_isolation_none_ignored(self):
        task = {"id": "t4", "workspace_isolation": "none", "workspace": "/tmp/ws"}
        self.assertEqual(self.tc.compute_boundary_key(task), "workspace:/tmp/ws")

    def test_conflict_group_with_workspace(self):
        task = {"id": "t5", "conflict_group": "db-migration", "workspace": "/tmp/proj"}
        self.assertEqual(self.tc.compute_boundary_key(task), "conflict:/tmp/proj:db-migration")

    def test_conflict_group_without_workspace_falls_through(self):
        task = {"id": "t6", "conflict_group": "db-migration", "project": "myproj"}
        self.assertEqual(self.tc.compute_boundary_key(task), "project:myproj")

    def test_workspace_only(self):
        task = {"id": "t7", "workspace": "/tmp/shared"}
        self.assertEqual(self.tc.compute_boundary_key(task), "workspace:/tmp/shared")

    def test_evolution_lane_with_target(self):
        task = {"id": "t8", "lane": "evolution", "architecture_target": "taskpool"}
        self.assertEqual(self.tc.compute_boundary_key(task), "evolution:taskpool")

    def test_evolution_lane_without_target_falls_through(self):
        task = {"id": "t9", "lane": "evolution", "project": "evo-proj"}
        self.assertEqual(self.tc.compute_boundary_key(task), "project:evo-proj")

    def test_project_only(self):
        task = {"id": "t10", "project": "uvisa-app"}
        self.assertEqual(self.tc.compute_boundary_key(task), "project:uvisa-app")

    def test_nothing_set_self_isolates(self):
        task = {"id": "t11"}
        self.assertEqual(self.tc.compute_boundary_key(task), "task:t11")

    def test_resolution_order_explicit_overrides_all(self):
        """parallel_boundary takes precedence even when workspace/conflict set."""
        task = {
            "id": "t12",
            "parallel_boundary": "custom:boundary",
            "workspace": "/tmp/ws",
            "conflict_group": "group-a",
        }
        self.assertEqual(self.tc.compute_boundary_key(task), "boundary:custom:boundary")

    def test_resolution_order_isolation_overrides_workspace(self):
        """workspace_isolation=worktree takes precedence over workspace."""
        task = {
            "id": "t13",
            "workspace_isolation": "worktree",
            "workspace": "/tmp/ws",
        }
        self.assertEqual(self.tc.compute_boundary_key(task), "isolated:t13")


class ClassifyDeterministicV2Test(unittest.TestCase):
    """Test v2 boundary-aligned classification."""

    def setUp(self):
        self.tc = load_module("task_classifier", TC_PATH)

    def test_parallel_group_overrides_boundary(self):
        """Tasks with parallel_group use pg:<name> as their group."""
        task = {"id": "t1", "parallel_group": "cohort-alpha", "workspace": "/tmp/ws"}
        self.assertEqual(self.tc.classify_deterministic(task), "pg:cohort-alpha")

    def test_same_workspace_same_group(self):
        """Tasks sharing workspace without parallel_group get same group."""
        t1 = {"id": "t1", "workspace": "/tmp/shared"}
        t2 = {"id": "t2", "workspace": "/tmp/shared"}
        self.assertEqual(
            self.tc.classify_deterministic(t1),
            self.tc.classify_deterministic(t2),
        )

    def test_different_workspace_different_group(self):
        t1 = {"id": "t1", "workspace": "/tmp/ws-a"}
        t2 = {"id": "t2", "workspace": "/tmp/ws-b"}
        self.assertNotEqual(
            self.tc.classify_deterministic(t1),
            self.tc.classify_deterministic(t2),
        )

    def test_conflict_group_isolation(self):
        """Tasks with same workspace but different conflict_groups get different groups."""
        t1 = {"id": "t1", "workspace": "/tmp/proj", "conflict_group": "frontend"}
        t2 = {"id": "t2", "workspace": "/tmp/proj", "conflict_group": "backend"}
        self.assertNotEqual(
            self.tc.classify_deterministic(t1),
            self.tc.classify_deterministic(t2),
        )

    def test_same_conflict_group_same_boundary(self):
        """Tasks with same workspace and conflict_group are in same boundary."""
        t1 = {"id": "t1", "workspace": "/tmp/proj", "conflict_group": "db"}
        t2 = {"id": "t2", "workspace": "/tmp/proj", "conflict_group": "db"}
        self.assertEqual(
            self.tc.classify_deterministic(t1),
            self.tc.classify_deterministic(t2),
        )


class ClassifyBatchTest(unittest.TestCase):
    """Test classify_batch with v2 classification."""

    def setUp(self):
        self.tc = load_module("task_classifier", TC_PATH)

    def test_batch_groups_by_boundary(self):
        tasks = [
            {"id": "t1", "workspace": "/tmp/a"},
            {"id": "t2", "workspace": "/tmp/a"},
            {"id": "t3", "workspace": "/tmp/b"},
        ]
        groups = self.tc.classify_batch(tasks)
        # t1 and t2 should be in same group, t3 in different
        self.assertEqual(len(groups), 2)
        g1 = tasks[0]['_conflict_group']
        g3 = tasks[2]['_conflict_group']
        self.assertEqual(g1, tasks[1]['_conflict_group'])
        self.assertNotEqual(g1, g3)

    def test_batch_parallel_group_override(self):
        tasks = [
            {"id": "t1", "workspace": "/tmp/a", "parallel_group": "cohort"},
            {"id": "t2", "workspace": "/tmp/b", "parallel_group": "cohort"},
        ]
        groups = self.tc.classify_batch(tasks)
        # Both should be in same group due to shared parallel_group
        self.assertEqual(len(groups), 1)
        self.assertIn("pg:cohort", groups)


class ValidateBoundaryConsistencyTest(unittest.TestCase):
    """Test cross-validation between classifier and boundary keys."""

    def setUp(self):
        self.tc = load_module("task_classifier", TC_PATH)

    def test_consistent_when_aligned(self):
        tasks = [
            {"id": "t1", "workspace": "/tmp/a"},
            {"id": "t2", "workspace": "/tmp/b"},
        ]
        result = self.tc.validate_boundary_consistency(tasks)
        self.assertTrue(result['consistent'])
        self.assertEqual(result['mismatch_count'], 0)

    def test_parallel_group_tasks_excluded_from_mismatch(self):
        """parallel_group tasks have pg: group != boundary_key by design."""
        tasks = [
            {"id": "t1", "workspace": "/tmp/a", "parallel_group": "cohort"},
        ]
        result = self.tc.validate_boundary_consistency(tasks)
        self.assertTrue(result['consistent'])

    def test_empty_tasks_consistent(self):
        result = self.tc.validate_boundary_consistency([])
        self.assertTrue(result['consistent'])


class BuildWorkerContextBoundaryTest(unittest.TestCase):
    """Test that worker context includes full boundary constraints."""

    def setUp(self):
        self.atc = load_module("agent_team_controller", ATC_PATH)

    def test_context_includes_allowed_globs(self):
        task = {
            "title": "test", "id": "t1", "priority": "P1", "project": "proj",
            "parallel_boundary": "b", "lane": "work",
            "allowed_globs": "~/.hermes/scripts/*.py",
        }
        ctx = self.atc.build_worker_context(task, "group-a")
        self.assertIn("ALLOWED_GLOBS: ~/.hermes/scripts/*.py", ctx)
        self.assertIn("BOUNDARY CONSTRAINTS", ctx)

    def test_context_includes_forbidden_globs(self):
        task = {
            "title": "test", "id": "t1", "priority": "P1", "project": "proj",
            "parallel_boundary": "b", "lane": "work",
            "forbidden_globs": "~/.hermes/config/*",
        }
        ctx = self.atc.build_worker_context(task, "group-a")
        self.assertIn("FORBIDDEN_GLOBS: ~/.hermes/config/*", ctx)

    def test_context_includes_loc_budget(self):
        task = {
            "title": "test", "id": "t1", "priority": "P1", "project": "proj",
            "parallel_boundary": "b", "lane": "work",
            "loc_budget": "500",
        }
        ctx = self.atc.build_worker_context(task, "group-a")
        self.assertIn("LOC_BUDGET: 500 lines max", ctx)

    def test_context_includes_workspace_isolation(self):
        task = {
            "title": "test", "id": "t1", "priority": "P1", "project": "proj",
            "parallel_boundary": "b", "lane": "work",
            "workspace_isolation": "worktree",
        }
        ctx = self.atc.build_worker_context(task, "group-a")
        self.assertIn("WORKSPACE_ISOLATION: worktree", ctx)

    def test_context_includes_merge_gate(self):
        task = {
            "title": "test", "id": "t1", "priority": "P1", "project": "proj",
            "parallel_boundary": "b", "lane": "work",
            "merge_gate": "build-and-tests",
        }
        ctx = self.atc.build_worker_context(task, "group-a")
        self.assertIn("MERGE_GATE: build-and-tests", ctx)

    def test_context_includes_parallel_group(self):
        task = {
            "title": "test", "id": "t1", "priority": "P1", "project": "proj",
            "parallel_boundary": "b", "lane": "work",
            "parallel_group": "cohort-alpha",
        }
        ctx = self.atc.build_worker_context(task, "group-a")
        self.assertIn("PARALLEL_GROUP: cohort-alpha", ctx)

    def test_context_no_boundary_section_when_empty(self):
        task = {
            "title": "test", "id": "t1", "priority": "P1", "project": "proj",
            "parallel_boundary": "", "lane": "work",
        }
        ctx = self.atc.build_worker_context(task, "group-a")
        # No BOUNDARY CONSTRAINTS section header when no constraints are set
        self.assertNotIn("BOUNDARY CONSTRAINTS (fail-closed:", ctx)
        # But Rule 6 still references boundary concepts (always present)
        self.assertIn("Respect BOUNDARY CONSTRAINTS", ctx)

    def test_context_rule_6_mentions_boundary(self):
        task = {
            "title": "test", "id": "t1", "priority": "P1", "project": "proj",
            "parallel_boundary": "b", "lane": "work",
            "forbidden_globs": "*.secret",
        }
        ctx = self.atc.build_worker_context(task, "group-a")
        self.assertIn("Respect BOUNDARY CONSTRAINTS", ctx)
        self.assertIn("FORBIDDEN_GLOBS", ctx)

    def test_context_includes_workspace(self):
        task = {
            "title": "test", "id": "t1", "priority": "P1", "project": "proj",
            "parallel_boundary": "b", "lane": "work",
            "workspace": "/tmp/shared-client-workspace",
        }
        ctx = self.atc.build_worker_context(task, "group-a")
        self.assertIn("WORKSPACE: /tmp/shared-client-workspace", ctx)


class ParallelScheduleV2Test(unittest.TestCase):
    """Test that get_parallel_schedule respects v2 boundary classification."""

    def setUp(self):
        self.tc = load_module("task_classifier", TC_PATH)

    def test_same_workspace_tasks_in_same_group(self):
        tasks = [
            {"id": "t1", "workspace": "/tmp/shared", "score": 100},
            {"id": "t2", "workspace": "/tmp/shared", "score": 90},
            {"id": "t3", "workspace": "/tmp/other", "score": 80},
        ]
        schedule = self.tc.get_parallel_schedule(tasks, max_groups=3)
        # Should have 2 groups: one for /tmp/shared, one for /tmp/other
        self.assertEqual(schedule['total_groups'], 2)
        self.assertEqual(schedule['selected_groups'], 2)

    def test_conflict_group_creates_separate_groups(self):
        tasks = [
            {"id": "t1", "workspace": "/tmp/proj", "conflict_group": "fe", "score": 100},
            {"id": "t2", "workspace": "/tmp/proj", "conflict_group": "be", "score": 90},
        ]
        schedule = self.tc.get_parallel_schedule(tasks, max_groups=3)
        self.assertEqual(schedule['total_groups'], 2)

    def test_parallel_group_merges_tasks(self):
        tasks = [
            {"id": "t1", "workspace": "/tmp/a", "parallel_group": "cohort", "score": 100},
            {"id": "t2", "workspace": "/tmp/b", "parallel_group": "cohort", "score": 90},
        ]
        schedule = self.tc.get_parallel_schedule(tasks, max_groups=3)
        # Both in same group due to parallel_group
        self.assertEqual(schedule['total_groups'], 1)

    def test_max_groups_caps_selected(self):
        tasks = [
            {"id": f"t{i}", "workspace": f"/tmp/ws-{i}", "score": 100 - i}
            for i in range(5)
        ]
        schedule = self.tc.get_parallel_schedule(tasks, max_groups=2)
        self.assertEqual(schedule['selected_groups'], 2)
        self.assertEqual(schedule['deferred_groups'], 3)


class InferConflictGroupTest(unittest.TestCase):
    """Test automatic conflict group inference from task metadata."""

    def setUp(self):
        self.tc = load_module("task_classifier", TC_PATH)

    def test_explicit_conflict_group_passthrough(self):
        task = {"id": "t1", "conflict_group": "my-group"}
        self.assertEqual(self.tc.infer_conflict_group(task), "my-group")

    def test_infer_from_title_skill(self):
        task = {"id": "t1", "title": "增强本地任务池技能管理"}
        self.assertEqual(self.tc.infer_conflict_group(task), "hermes-skills")

    def test_infer_from_title_taskpool(self):
        task = {"id": "t1", "title": "增强本地任务池任务边界与多Agent并行处理"}
        self.assertEqual(self.tc.infer_conflict_group(task), "hermes-taskpool")

    def test_infer_from_title_agent_team(self):
        task = {"id": "t1", "title": "Multi-agent parallel dispatch"}
        self.assertEqual(self.tc.infer_conflict_group(task), "hermes-agent-team")

    def test_infer_from_title_uvisa(self):
        task = {"id": "t1", "title": "修复uvisa-app-2.0个人信息卡片"}
        self.assertEqual(self.tc.infer_conflict_group(task), "uvisa-app")

    def test_infer_from_concepts(self):
        task = {"id": "t1", "title": "misc task", "concepts": ["cron", "定时调度"]}
        self.assertEqual(self.tc.infer_conflict_group(task), "hermes-cron")

    def test_infer_from_project(self):
        task = {"id": "t1", "title": "misc", "project": "hermes-memory-manager"}
        self.assertEqual(self.tc.infer_conflict_group(task), "hermes-memory")

    def test_infer_from_allowed_globs(self):
        task = {"id": "t1", "title": "misc", "allowed_globs": "~/.hermes/skills/**/*.md"}
        self.assertEqual(self.tc.infer_conflict_group(task), "hermes-skills")

    def test_no_inference_returns_empty(self):
        task = {"id": "t1", "title": "random generic task"}
        self.assertEqual(self.tc.infer_conflict_group(task), "")

    def test_infer_chinese_title_evolution(self):
        task = {"id": "t1", "title": "自进化流程优化"}
        self.assertEqual(self.tc.infer_conflict_group(task), "hermes-evolution")

    def test_infer_chinese_title_config(self):
        task = {"id": "t1", "title": "更新配置文件"}
        self.assertEqual(self.tc.infer_conflict_group(task), "hermes-config")


class BoundaryKeyInferenceTest(unittest.TestCase):
    """Test that compute_boundary_key uses inferred conflict groups."""

    def setUp(self):
        self.tc = load_module("task_classifier", TC_PATH)

    def test_same_workspace_different_inferred_groups(self):
        """Tasks in same workspace with different inferred groups get different keys."""
        t1 = {"id": "t1", "workspace": "/Users/charles/.hermes",
               "title": "增强本地任务池任务边界"}
        t2 = {"id": "t2", "workspace": "/Users/charles/.hermes",
               "title": "修复uvisa-app个人信息"}
        k1 = self.tc.compute_boundary_key(t1)
        k2 = self.tc.compute_boundary_key(t2)
        self.assertNotEqual(k1, k2)
        self.assertIn("hermes-taskpool", k1)
        self.assertIn("uvisa-app", k2)

    def test_same_workspace_same_inferred_group(self):
        """Tasks in same workspace with same inferred group share key."""
        t1 = {"id": "t1", "workspace": "/Users/charles/.hermes",
               "title": "增强任务池边界"}
        t2 = {"id": "t2", "workspace": "/Users/charles/.hermes",
               "title": "任务池dispatch优化"}
        k1 = self.tc.compute_boundary_key(t1)
        k2 = self.tc.compute_boundary_key(t2)
        self.assertEqual(k1, k2)

    def test_explicit_conflict_group_beats_inference(self):
        task = {"id": "t1", "workspace": "/tmp/ws",
                "conflict_group": "explicit-group", "title": "skill management"}
        key = self.tc.compute_boundary_key(task)
        self.assertIn("explicit-group", key)
        self.assertNotIn("hermes-skills", key)

    def test_no_inference_falls_back_to_workspace(self):
        task = {"id": "t1", "workspace": "/tmp/ws", "title": "random task"}
        key = self.tc.compute_boundary_key(task)
        self.assertEqual(key, "workspace:/tmp/ws")


class ParallelScheduleInferenceTest(unittest.TestCase):
    """Test that get_parallel_schedule separates tasks by inferred groups."""

    def setUp(self):
        self.tc = load_module("task_classifier", TC_PATH)

    def test_different_inferred_groups_parallel(self):
        """Tasks with different inferred groups can run in parallel."""
        tasks = [
            {"id": "t1", "workspace": "/Users/charles/.hermes",
             "title": "增强任务池任务边界", "score": 100},
            {"id": "t2", "workspace": "/Users/charles/.hermes",
             "title": "修复uvisa前端样式", "score": 90},
            {"id": "t3", "workspace": "/Users/charles/.hermes",
             "title": "model router优化", "score": 80},
        ]
        schedule = self.tc.get_parallel_schedule(tasks, max_groups=3)
        # All 3 should be in different groups
        self.assertEqual(schedule['total_groups'], 3)
        self.assertEqual(schedule['selected_groups'], 3)

    def test_same_inferred_group_serial(self):
        """Tasks with same inferred group are in same group (serial)."""
        tasks = [
            {"id": "t1", "workspace": "/Users/charles/.hermes",
             "title": "增强任务池边界", "score": 100},
            {"id": "t2", "workspace": "/Users/charles/.hermes",
             "title": "任务池dispatch优化", "score": 90},
        ]
        schedule = self.tc.get_parallel_schedule(tasks, max_groups=3)
        self.assertEqual(schedule['total_groups'], 1)


class BoundaryConsistencyInferenceTest(unittest.TestCase):
    """Test that inferred groups maintain classifier/orchestrator consistency."""

    def setUp(self):
        self.tc = load_module("task_classifier", TC_PATH)

    def test_inferred_groups_consistent(self):
        """Tasks with inferred groups should have consistent classifier/boundary keys."""
        tasks = [
            {"id": "t1", "workspace": "/Users/charles/.hermes",
             "title": "增强任务池边界"},
            {"id": "t2", "workspace": "/Users/charles/.hermes",
             "title": "skill graph优化"},
            {"id": "t3", "workspace": "/tmp/other",
             "title": "random task"},
        ]
        result = self.tc.validate_boundary_consistency(tasks)
        self.assertTrue(result['consistent'], f"Mismatches: {result['mismatches']}")


class DetectGlobOverlapTest(unittest.TestCase):
    """Test file-level glob overlap detection between parallel tasks."""

    def setUp(self):
        self.tc = load_module("task_classifier", TC_PATH)

    def test_exact_match_overlap(self):
        result = self.tc.detect_glob_overlap("~/.hermes/scripts/*.py", "~/.hermes/scripts/*.py")
        self.assertTrue(result['overlap'])
        self.assertTrue(any('exact_match' in r for r in result['reasons']))

    def test_no_overlap_different_extensions(self):
        result = self.tc.detect_glob_overlap("~/.hermes/scripts/*.py", "~/.hermes/skills/*.md")
        self.assertFalse(result['overlap'])

    def test_empty_patterns_no_overlap(self):
        result = self.tc.detect_glob_overlap("", "~/*.py")
        self.assertFalse(result['overlap'])

    def test_both_empty_no_overlap(self):
        result = self.tc.detect_glob_overlap("", "")
        self.assertFalse(result['overlap'])

    def test_extension_overlap(self):
        result = self.tc.detect_glob_overlap("~/*.py", "~/*.py")
        self.assertTrue(result['overlap'])

    def test_prefix_overlap(self):
        result = self.tc.detect_glob_overlap("~/.hermes/", "~/.hermes/skills/")
        self.assertTrue(result['overlap'])

    def test_list_input(self):
        result = self.tc.detect_glob_overlap(
            ["~/.hermes/scripts/*.py"],
            ["~/.hermes/scripts/test_*.py"]
        )
        self.assertTrue(result['overlap'])


class CheckParallelFileConflictsTest(unittest.TestCase):
    """Test file-level conflict detection among parallel-scheduled tasks."""

    def setUp(self):
        self.tc = load_module("task_classifier", TC_PATH)

    def test_no_conflict_different_globs(self):
        tasks = [
            {"id": "t1", "workspace": "/tmp/a", "allowed_globs": "~/*.py"},
            {"id": "t2", "workspace": "/tmp/b", "allowed_globs": "~/*.md"},
        ]
        self.tc.classify_batch(tasks)
        result = self.tc.check_parallel_file_conflicts(tasks)
        self.assertEqual(result['conflict_count'], 0)

    def test_conflict_same_globs(self):
        tasks = [
            {"id": "t1", "workspace": "/tmp/a", "allowed_globs": "~/.hermes/scripts/*.py"},
            {"id": "t2", "workspace": "/tmp/b", "allowed_globs": "~/.hermes/scripts/*.py"},
        ]
        self.tc.classify_batch(tasks)
        result = self.tc.check_parallel_file_conflicts(tasks)
        self.assertEqual(result['conflict_count'], 1)

    def test_no_conflict_same_group_serial(self):
        """Tasks in the same group are serial (already blocked by boundary)."""
        tasks = [
            {"id": "t1", "workspace": "/tmp/shared", "allowed_globs": "~/*.py"},
            {"id": "t2", "workspace": "/tmp/shared", "allowed_globs": "~/*.py"},
        ]
        self.tc.classify_batch(tasks)
        result = self.tc.check_parallel_file_conflicts(tasks)
        # Same group = same boundary = serial, no cross-group conflict
        self.assertEqual(result['conflict_count'], 0)

    def test_empty_tasks(self):
        result = self.tc.check_parallel_file_conflicts([])
        self.assertEqual(result['conflict_count'], 0)
        self.assertEqual(result['safe_pairs'], 0)


class BoundaryHealthCheckTest(unittest.TestCase):
    """Test boundary system health audit."""

    def setUp(self):
        self.tc = load_module("task_classifier", TC_PATH)

    def test_healthy_tasks(self):
        tasks = [
            {"id": "t1", "workspace": "/tmp/a"},
            {"id": "t2", "workspace": "/tmp/b"},
        ]
        result = self.tc.boundary_health_check(tasks)
        self.assertTrue(result['healthy'])
        self.assertEqual(len(result['issues']), 0)

    def test_no_boundary_metadata_warning(self):
        tasks = [
            {"id": "t1"},  # No workspace, project, or boundary
        ]
        result = self.tc.boundary_health_check(tasks)
        # Should have a warning about no metadata (falls back to task:id)
        has_warning = any(i['type'] == 'no_boundary_metadata' for i in result['issues'])
        self.assertTrue(has_warning)

    def test_isolation_vs_cooperative_conflict(self):
        tasks = [
            {
                "id": "t1",
                "workspace_isolation": "worktree",
                "parallel_group": "cohort",
                "workspace": "/tmp/ws",
            },
        ]
        result = self.tc.boundary_health_check(tasks)
        has_error = any(i['type'] == 'isolation_vs_cooperative_conflict' for i in result['issues'])
        self.assertTrue(has_error)
        self.assertFalse(result['healthy'])

    def test_boundary_distribution(self):
        tasks = [
            {"id": "t1", "workspace": "/tmp/a"},
            {"id": "t2", "workspace": "/tmp/a"},
            {"id": "t3", "workspace": "/tmp/b"},
        ]
        result = self.tc.boundary_health_check(tasks)
        self.assertEqual(result['unique_boundaries'], 2)
        self.assertEqual(result['total_tasks'], 3)


class VerifyWorkerBoundaryTest(unittest.TestCase):
    """Test controller's verify_worker_boundary function."""

    def setUp(self):
        self.atc = load_module("agent_team_controller", ATC_PATH)

    def test_pass_compliant_proof(self):
        task = {
            "id": "t1",
            "allowed_globs": "~/.hermes/scripts/*.py",
            "forbidden_globs": "~/.hermes/config/*",
            "loc_budget": "5",
        }
        proof = {
            "files_changed": [
                "~/.hermes/scripts/new_feature.py",
                "~/.hermes/scripts/test_feature.py",
            ]
        }
        result = self.atc.verify_worker_boundary(task, proof)
        self.assertEqual(result['status'], 'PASS')

    def test_fail_forbidden_match(self):
        task = {
            "id": "t1",
            "forbidden_globs": "~/.hermes/config/*",
        }
        proof = {
            "files_changed": [
                "~/.hermes/config/config.yaml",
            ]
        }
        result = self.atc.verify_worker_boundary(task, proof)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(any('forbidden_match' in v for v in result['violations']))

    def test_fail_not_in_allowed_globs(self):
        task = {
            "id": "t1",
            "allowed_globs": "~/.hermes/scripts/*.py",
        }
        proof = {
            "files_changed": [
                "~/.hermes/skills/some_skill.md",  # Not in allowed
            ]
        }
        result = self.atc.verify_worker_boundary(task, proof)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(any('not_in_allowed_globs' in v for v in result['violations']))

    def test_fail_loc_budget_exceeded(self):
        task = {
            "id": "t1",
            "loc_budget": "2",
        }
        proof = {
            "files_changed": ["a.py", "b.py", "c.py"]  # 3 > 2
        }
        result = self.atc.verify_worker_boundary(task, proof)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(any('loc_budget_exceeded' in v for v in result['violations']))

    def test_skip_no_constraints(self):
        task = {"id": "t1"}
        proof = {"files_changed": ["anything.py"]}
        result = self.atc.verify_worker_boundary(task, proof)
        self.assertEqual(result['status'], 'SKIP')

    def test_empty_files_changed(self):
        task = {
            "id": "t1",
            "allowed_globs": "~/*.py",
            "loc_budget": "5",
        }
        proof = {"files_changed": []}
        result = self.atc.verify_worker_boundary(task, proof)
        self.assertEqual(result['status'], 'PASS')

    def test_forbidden_dominates_allowed(self):
        """A file matching both forbidden and allowed should be rejected."""
        task = {
            "id": "t1",
            "allowed_globs": "~/.hermes/**",
            "forbidden_globs": "~/.hermes/config/*",
        }
        proof = {
            "files_changed": ["~/.hermes/config/secrets.yaml"]
        }
        result = self.atc.verify_worker_boundary(task, proof)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(any('forbidden_match' in v for v in result['violations']))


class BuildWorkerContextSiblingTest(unittest.TestCase):
    """Test enhanced build_worker_context with sibling awareness."""

    def setUp(self):
        self.atc = load_module("agent_team_controller", ATC_PATH)

    def test_context_includes_sibling_section(self):
        task = {
            "title": "test", "id": "t1", "priority": "P1", "project": "proj",
            "parallel_boundary": "b", "lane": "work",
        }
        siblings = [
            {"id": "t2", "title": "other task", "status": "RUNNING", "parallel_boundary": "b2"},
            {"id": "t3", "title": "third task", "status": "PENDING", "workspace": "/tmp/ws"},
        ]
        ctx = self.atc.build_worker_context(task, "group-a", sibling_tasks=siblings)
        self.assertIn("SIBLING TASKS IN SAME CONFLICT GROUP", ctx)
        self.assertIn("t2", ctx)
        self.assertIn("t3", ctx)
        self.assertIn("other task", ctx)

    def test_context_no_sibling_section_when_empty(self):
        task = {
            "title": "test", "id": "t1", "priority": "P1", "project": "proj",
            "parallel_boundary": "b", "lane": "work",
        }
        ctx = self.atc.build_worker_context(task, "group-a", sibling_tasks=None)
        self.assertNotIn("SIBLING TASKS", ctx)

    def test_context_no_sibling_section_when_empty_list(self):
        task = {
            "title": "test", "id": "t1", "priority": "P1", "project": "proj",
            "parallel_boundary": "b", "lane": "work",
        }
        ctx = self.atc.build_worker_context(task, "group-a", sibling_tasks=[])
        self.assertNotIn("SIBLING TASKS", ctx)

    def test_sibling_tasks_capped_at_5(self):
        task = {
            "title": "test", "id": "t1", "priority": "P1", "project": "proj",
            "parallel_boundary": "b", "lane": "work",
        }
        siblings = [{"id": f"t{i}", "title": f"task {i}", "status": "RUNNING"} for i in range(10)]
        ctx = self.atc.build_worker_context(task, "group-a", sibling_tasks=siblings)
        # Should only include first 5
        self.assertIn("t0", ctx)
        self.assertIn("t4", ctx)
        self.assertNotIn("t5", ctx)
        self.assertNotIn("t9", ctx)

    def test_backward_compat_no_siblings_param(self):
        """build_worker_context works without sibling_tasks param (backward compat)."""
        task = {
            "title": "test", "id": "t1", "priority": "P1", "project": "proj",
            "parallel_boundary": "b", "lane": "work",
        }
        ctx = self.atc.build_worker_context(task, "group-a")
        self.assertNotIn("SIBLING TASKS", ctx)
        self.assertIn("BOUNDARY CONSTRAINTS", ctx)


if __name__ == "__main__":
    unittest.main()
