import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("brain_task_autorun_step.py")


def load_module():
    spec = importlib.util.spec_from_file_location("brain_task_autorun_step", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_policy_project_local_brain_matches_architecture_target():
    module = load_module()
    ok, reasons, _workspace, command_ids, _max_seconds = module.validate_policy_for_task(
        {
            "lanes": ["evolution"],
            "projects": ["project:local-brain"],
            "command_ids": ["py_compile_taskpool"],
            "close_mode": "review_only",
            "workspace": "/Users/charles/.hermes",
            "workspace_roots": ["/Users/charles/.hermes"],
            "max_seconds": 300,
        },
        {
            "id": "task-1",
            "lane": "evolution",
            "project": "hermes",
            "architecture_target": "local-brain",
            "brain": "hermes-core",
        },
    )

    assert ok, reasons
    assert command_ids == ["py_compile_taskpool"]


def test_policy_unrelated_project_still_fails_closed():
    module = load_module()
    ok, reasons, _workspace, _command_ids, _max_seconds = module.validate_policy_for_task(
        {
            "lanes": ["evolution"],
            "projects": ["project:uvisa-app-2.0-work"],
            "command_ids": ["py_compile_taskpool"],
            "close_mode": "review_only",
            "workspace": "/Users/charles/.hermes",
            "workspace_roots": ["/Users/charles/.hermes"],
            "max_seconds": 300,
        },
        {
            "id": "task-1",
            "lane": "evolution",
            "project": "hermes",
            "architecture_target": "local-brain",
            "brain": "hermes-core",
        },
    )

    assert not ok
    assert "policy_task_miss" in reasons
