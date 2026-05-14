#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path

SCRIPT = Path.home() / ".hermes" / "scripts" / "personal_hermes_brain_export.py"


def load_module():
    spec = importlib.util.spec_from_file_location("personal_hermes_brain_export", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_secret_pattern_blocks_token_assignment():
    m = load_module()
    assert m.has_secret_text("api_key = 'abcd1234abcd1234'")
    assert not m.has_secret_text("api_key = '[REDACTED]'")


def test_denies_raw_memory_and_env_paths():
    m = load_module()
    root = Path("/tmp/root")
    assert m.denied_path(root / "hermes" / "memory" / "index.sqlite", root)
    assert m.denied_path(root / ".env", root)
    assert m.denied_path(root / "auth.json", root)


def test_noagent_timeout_wrappers_are_allowlisted_for_backup():
    m = load_module()
    scripts = set(m.SELECTED_SCRIPT_GLOBS)
    assert "autonomous_evolution_nightly_noagent.py" in scripts
    assert "skill_steward_daily_audit_noagent.py" in scripts
    assert "taskpool_dynamic_runner.py" in scripts
    assert "multimodel_intervention_dynamic_step.py" in scripts


def build_fixture_tree(tmp: Path):
    hermes_home = tmp / "hermes-home"
    brain = tmp / "brain"
    dest = tmp / "export-repo"
    restore_home = tmp / "restore-home"
    restore_vault = tmp / "restore-brain"

    (brain / "notes").mkdir(parents=True)
    (brain / "notes" / "north-star.md").write_text("hello\n", encoding="utf-8")
    restore_vault.mkdir(parents=True)

    profiles = hermes_home / "project-profiles"
    profiles.mkdir(parents=True)
    (profiles / "hermes.json").write_text('{"project":"hermes"}\n', encoding="utf-8")
    (profiles / "sample.json").write_text(json.dumps({
        "project": "sample",
        "paths": {"repo": "/old/root/sample", "nested": {"frontend": "/old/root/sample/frontend"}},
        "project_identity": {"frontend_repo": "/old/root/sample"}
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    scripts = hermes_home / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "brain_task_orchestrator.py").write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "cmd = sys.argv[1] if len(sys.argv) > 1 else ''\n"
        "if cmd == 'selfcheck':\n"
        "    print(json.dumps({'status':'PASS','cmd':'selfcheck'}))\n"
        "elif cmd == 'boundary-check':\n"
        "    print(json.dumps({'status':'PASS','cmd':'boundary-check'}))\n"
        "else:\n"
        "    print(json.dumps({'status':'PASS','cmd':cmd}))\n",
        encoding="utf-8",
    )
    (scripts / "brainctl.py").write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "cmd = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == '--json' else (sys.argv[1] if len(sys.argv) > 1 else '')\n"
        "print(json.dumps({'status':'OK','cmd':cmd}))\n",
        encoding="utf-8",
    )
    (scripts / "ignored.py").write_text("print('ignored')\n", encoding="utf-8")

    skills = hermes_home / "skills" / "demo-skill"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text("---\nname: demo-skill\n---\n", encoding="utf-8")
    return hermes_home, profiles, brain, dest, restore_home, restore_vault


def run_export(m, hermes_home: Path, profiles: Path, brain: Path, dest: Path):
    old_hermes_home = m.HERMES_HOME
    old_project_profiles = m.PROJECT_PROFILES_DIR
    old_brain = m.BRAIN
    old_dest = m.DEST
    try:
        m.HERMES_HOME = hermes_home
        m.PROJECT_PROFILES_DIR = profiles
        m.BRAIN = brain
        m.DEST = dest
        return m.export(dest)
    finally:
        m.HERMES_HOME = old_hermes_home
        m.PROJECT_PROFILES_DIR = old_project_profiles
        m.BRAIN = old_brain
        m.DEST = old_dest


def test_export_includes_project_profiles_and_sync_import_restores_them():
    m = load_module()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        hermes_home, profiles, brain, dest, restore_home, _restore_vault = build_fixture_tree(tmp)
        result = run_export(m, hermes_home, profiles, brain, dest)

        assert result["stats"]["project_profiles"]["copied"] == 2
        assert (dest / "hermes" / "project-profiles" / "sample.json").exists()
        assert (dest / "hermes" / "scripts" / "brain_task_orchestrator.py").exists()
        assert (dest / "hermes" / "scripts" / "brainctl.py").exists()
        assert not (dest / "hermes" / "scripts" / "ignored.py").exists()

        env = os.environ.copy()
        env["HERMES_HOME"] = str(restore_home)
        subprocess.run(["bash", str(dest / "bootstrap" / "sync_import.sh")], check=True, env=env, cwd=dest)

        assert (restore_home / "project-profiles" / "sample.json").exists()
        assert (restore_home / "scripts" / "brain_task_orchestrator.py").exists()
        assert (restore_home / "scripts" / "brainctl.py").exists()
        assert (restore_home / "skills" / "demo-skill" / "SKILL.md").exists()


def test_bootstrap_machine_rewrites_paths_and_runs_validation():
    m = load_module()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        hermes_home, profiles, brain, dest, restore_home, restore_vault = build_fixture_tree(tmp)
        run_export(m, hermes_home, profiles, brain, dest)

        env = os.environ.copy()
        env["HERMES_HOME"] = str(restore_home)
        env["HERMES_BRAIN_VAULT"] = str(restore_vault)
        proc = subprocess.run(
            [
                "bash",
                str(dest / "bootstrap" / "bootstrap_machine.sh"),
                "--rewrite-prefix",
                "/old/root=/new/root",
            ],
            check=True,
            env=env,
            cwd=dest,
            text=True,
            capture_output=True,
        )
        raw = proc.stdout.strip()
        marker = '{\n  "schema": "portable_restore_validation_v1"'
        start = raw.rfind(marker)
        assert start >= 0, raw
        summary = json.loads(raw[start:])
        sample = json.loads((restore_home / "project-profiles" / "sample.json").read_text(encoding="utf-8"))
        assert summary["status"] == "PASS"
        assert summary["checks"]["project_profiles_present"]["passed"] is True
        assert summary["checks"]["brainctl_present"]["passed"] is True
        assert summary["checks"]["orchestrator_present"]["passed"] is True
        assert sample["paths"]["repo"] == "/new/root/sample"
        assert sample["paths"]["nested"]["frontend"] == "/new/root/sample/frontend"
        assert sample["project_identity"]["frontend_repo"] == "/new/root/sample"


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for test in tests:
        test()
    print(f"PASS {len(tests)} tests")
