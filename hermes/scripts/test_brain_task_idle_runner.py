#!/usr/bin/env python3
"""Tests for brain_task_idle_runner.py.
Run with: python3 ~/.hermes/scripts/test_brain_task_idle_runner.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOME = Path.home()
ORCH = HOME / ".hermes" / "scripts" / "brain_task_orchestrator.py"
IDLE = HOME / ".hermes" / "scripts" / "brain_task_idle_runner.py"


def run(cmd, env, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if check and r.returncode != 0:
        raise AssertionError(f"command failed {cmd}\nstdout={r.stdout}\nstderr={r.stderr}")
    return r


def make_env_and_vault():
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    vault = root / "brain"
    (vault / "05-实践与项目" / "tasks").mkdir(parents=True)
    (vault / "07-仪表盘").mkdir(parents=True)
    env = os.environ.copy()
    env["HERMES_BRAIN_VAULT"] = str(vault)
    env["HERMES_BRAIN_IDLE_RUNNER_STATE_DIR"] = str(root / "idle-state")
    env.pop("HERMES_LOCAL_BRAIN_IDLE_RUNNER", None)
    return td, vault, env


def add_task(env, title, priority="P1", project="test", accept="Observable result"):
    r = run([
        sys.executable,
        str(ORCH),
        "add",
        title,
        "--priority",
        priority,
        "--project",
        project,
        "--expires-at",
        "2099-01-01",
        "--accept",
        accept,
        "--json",
    ], env)
    return json.loads(r.stdout)["id"]


def patch_frontmatter(vault: Path, task_id: str, extra_lines: list[str]):
    path = vault / "05-实践与项目" / "tasks" / f"{task_id}.md"
    text = path.read_text(encoding="utf-8")
    insert_at = text.index("---\n", 4)
    text = text[:insert_at] + "\n" + "\n".join(extra_lines) + "\n" + text[insert_at:]
    path.write_text(text, encoding="utf-8")


def idle(env):
    return json.loads(run([sys.executable, str(IDLE), "--json"], env).stdout)


def test_idle_runner_default_disabled_and_read_only():
    td, _vault, env = make_env_and_vault()
    with td:
        task_id = add_task(env, "多模型分析 external repo", project="repo-audit")
        data = idle(env)
        assert data["status"] == "OK", data
        assert data["policy"]["kill_switch_enabled"] is False
        assert "idle_runner_disabled" in data["deny_reasons"]
        assert data["next_action"] == "observe_only"
        rows = json.loads(run([sys.executable, str(ORCH), "list", "--json"], env).stdout)["rows"]
        assert next(r for r in rows if r["id"] == task_id)["status"] == "pending"


def test_idle_runner_blocks_active_lease_even_when_enabled():
    td, _vault, env = make_env_and_vault()
    with td:
        task_id = add_task(env, "多模型分析 external repo", project="repo-audit")
        run([sys.executable, str(ORCH), "claim", task_id, "--actor", "test", "--ttl-minutes", "60", "--json"], env)
        env["HERMES_LOCAL_BRAIN_IDLE_RUNNER"] = "1"
        data = idle(env)
        assert data["active_count"] == 1, data
        assert "active_lease_or_running_task_present" in data["deny_reasons"]
        assert data["next_action"] == "observe_only"


def test_idle_runner_blocks_review_status_active_claim_with_pending_candidate():
    td, _vault, env = make_env_and_vault()
    with td:
        review_task = add_task(env, "多模型分析 in review", project="repo-audit")
        candidate = add_task(env, "多模型分析 pending candidate", project="repo-audit")
        run([sys.executable, str(ORCH), "claim", review_task, "--actor", "test", "--ttl-minutes", "60", "--json"], env)
        run([sys.executable, str(ORCH), "transition", review_task, "--to", "running", "--actor", "test", "--json"], env)
        run([sys.executable, str(ORCH), "transition", review_task, "--to", "review", "--actor", "test", "--evidence", "command:review-proof", "--json"], env)
        env["HERMES_LOCAL_BRAIN_IDLE_RUNNER"] = "1"
        data = idle(env)
        by_id = {r["task_id"]: r for r in data["routes"]}
        assert by_id[review_task]["status"] == "review", by_id[review_task]
        assert by_id[candidate]["status"] == "pending", by_id[candidate]
        assert data["active_count"] == 1, data
        assert "active_lease_or_running_task_present" in data["deny_reasons"]
        assert data["next_action"] == "observe_only"


def test_idle_runner_treats_pending_task_with_run_id_metadata_as_active_blocker():
    td, vault, env = make_env_and_vault()
    with td:
        partial = add_task(env, "多模型分析 partial run metadata", project="repo-audit")
        candidate = add_task(env, "多模型分析 pending candidate", project="repo-audit")
        patch_frontmatter(vault, partial, ["run_id: external-run-123"])
        env["HERMES_LOCAL_BRAIN_IDLE_RUNNER"] = "1"
        data = idle(env)
        by_id = {r["task_id"]: r for r in data["routes"]}
        assert by_id[partial]["status"] == "pending", by_id[partial]
        assert by_id[partial]["run_id"] == "external-run-123", by_id[partial]
        assert by_id[candidate]["status"] == "pending", by_id[candidate]
        assert data["active_count"] > 0, data
        assert "active_lease_or_running_task_present" in data["deny_reasons"]
        assert data["next_action"] == "observe_only"


def test_idle_runner_risk_routes_high_and_blocked_tasks():
    td, vault, env = make_env_and_vault()
    with td:
        high = add_task(env, "Deploy prod and delete old secrets", priority="P0", project="ops")
        blocked = add_task(env, "多模型分析 blocked repo", priority="P1", project="repo-audit")
        multiline = add_task(env, "多模型分析 multiline blocked repo", priority="P1", project="repo-audit")
        patch_frontmatter(vault, blocked, ["blocked_by: upstream-certification"])
        patch_frontmatter(vault, multiline, ["blocked_by:", "  - upstream-certification", "  - human-review"])
        env["HERMES_LOCAL_BRAIN_IDLE_RUNNER"] = "1"
        data = idle(env)
        by_id = {r["task_id"]: r for r in data["routes"]}
        assert by_id[high]["risk"] == "high", by_id[high]
        assert by_id[high]["execution_mode"] == "manual", by_id[high]
        assert "high_risk_manual_gate" in by_id[high]["blockers"]
        assert "blocked_by_dag" in by_id[blocked]["blockers"], by_id[blocked]
        assert by_id[blocked]["blocked_by"] == ["upstream-certification"], by_id[blocked]
        assert "blocked_by_dag" in by_id[multiline]["blockers"], by_id[multiline]
        assert by_id[multiline]["blocked_by"] == ["upstream-certification", "human-review"], by_id[multiline]
        assert data["candidate"] is None
        assert "no_eligible_pending_task" in data["deny_reasons"]


def test_idle_runner_write_state_does_not_mutate_task_markdown():
    td, vault, env = make_env_and_vault()
    with td:
        task_id = add_task(env, "多模型分析 write-state safety", project="repo-audit")
        task_path = vault / "05-实践与项目" / "tasks" / f"{task_id}.md"
        before = task_path.read_text(encoding="utf-8")
        data = json.loads(run([sys.executable, str(IDLE), "--json", "--write-state"], env).stdout)
        after = task_path.read_text(encoding="utf-8")
        assert before == after
        assert data["state_file"].endswith("brain_task_idle_runner_state.json")
        assert Path(data["state_file"]).exists()
        assert json.loads(Path(data["state_file"]).read_text(encoding="utf-8"))["status"] == "OK"


def test_redact_sensitive_subprocess_diagnostics():
    import importlib.util
    spec = importlib.util.spec_from_file_location("brain_task_idle_runner", IDLE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    raw = "api_key: abcdefgh token=tok123 password=pass123 auth_token=aaa; ct0=bbb proxy=http://user:pass@host"
    redacted = module.redact_sensitive(raw)
    assert "abcdefgh" not in redacted
    assert "tok123" not in redacted
    assert "pass123" not in redacted
    assert "aaa" not in redacted
    assert "bbb" not in redacted
    assert "[REDACTED]" in redacted


if __name__ == "__main__":
    test_idle_runner_default_disabled_and_read_only()
    test_idle_runner_blocks_active_lease_even_when_enabled()
    test_idle_runner_blocks_review_status_active_claim_with_pending_candidate()
    test_idle_runner_treats_pending_task_with_run_id_metadata_as_active_blocker()
    test_idle_runner_risk_routes_high_and_blocked_tasks()
    test_idle_runner_write_state_does_not_mutate_task_markdown()
    test_redact_sensitive_subprocess_diagnostics()
    print("PASS")
