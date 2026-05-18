import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).with_name("brain_task_orchestrator.py")


def load_module():
    spec = importlib.util.spec_from_file_location("brain_task_orchestrator", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_auto_subtask_backfill_relationship_evidence_is_structured():
    module = load_module()

    assert module.evidence_is_structured("child-task:2026-05-14-example:status:done")
    assert module.evidence_is_structured("child-axis:fallback_threshold:2026-05-14-example")


def test_unprefixed_free_text_evidence_still_fails_closed():
    module = load_module()

    assert not module.evidence_is_structured("child task 2026-05-14-example status done")


def test_legacy_project_local_brain_allowlist_matches_architecture_target():
    module = load_module()
    task = SimpleNamespace(
        id="task-1",
        project="hermes",
        title="Task - local brain evolution",
        architecture_target="local-brain",
        fm={"architecture_target": "local-brain", "brain": "hermes-core"},
    )

    assert module.autorun_allowlist_matches(task, ["project:local-brain"])
    assert module.autorun_allowlist_matches(task, ["architecture:local-brain"])
    assert module.autorun_allowlist_matches(task, ["brain:hermes-core"])
    assert not module.autorun_allowlist_matches(task, ["project:uvisa-app-2.0-work"])
