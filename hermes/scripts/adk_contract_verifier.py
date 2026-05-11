#!/usr/bin/env python3
"""ADK Contract Verifier — Check Hermes against Agent Development Kit five-folder contract.

Reports each ADK component as: existing | gap | duplicate | intentionally_unsupported.

Usage:
    python3 ~/.hermes/scripts/adk_contract_verifier.py [--json]
"""
import json
import os
import sys
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))


def check_policy():
    """ADK CLAUDE.md -> Hermes AGENTS.md / repo-local constitution."""
    agents_md = HERMES_HOME / "AGENTS.md"
    repo_agents = HERMES_HOME / "hermes-agent" / "AGENTS.md"
    if agents_md.exists():
        return {"status": "existing", "path": str(agents_md), "note": "Repo-local constitution present"}
    elif repo_agents.exists():
        return {"status": "gap", "path": str(repo_agents), "note": "AGENTS.md exists at repo level only, not at workspace root"}
    return {"status": "gap", "path": None, "note": "No AGENTS.md or CLAUDE.md found"}


def check_skills():
    """ADK skills/ -> Hermes skills/ registry."""
    skills_dir = HERMES_HOME / "skills"
    if not skills_dir.exists():
        return {"status": "gap", "count": 0, "note": "No skills directory"}
    entries = [d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    usage_file = skills_dir / ".usage.json"
    has_usage = usage_file.exists()
    hub_dir = skills_dir / ".hub"
    has_hub = hub_dir.exists()
    return {
        "status": "existing",
        "count": len(entries),
        "has_usage_tracking": has_usage,
        "has_hub": has_hub,
        "note": f"{len(entries)} skills, usage tracking={'yes' if has_usage else 'no'}, hub={'yes' if has_hub else 'no'}"
    }


def check_hooks():
    """ADK hooks/ -> Hermes hooks/ + config hooks + shell hooks."""
    hooks_dir = HERMES_HOME / "hooks"
    registry = hooks_dir / "registry.yaml" if hooks_dir.exists() else None
    config_hooks = HERMES_HOME / "config.yaml"
    agent_hooks = HERMES_HOME / "agent-hooks"

    has_registry = registry and registry.exists()
    has_config_hooks = config_hooks.exists()
    has_agent_hooks = agent_hooks.exists() and any(agent_hooks.iterdir())

    if has_registry:
        return {"status": "existing", "path": str(registry), "note": "Hook registry present"}
    elif has_config_hooks or has_agent_hooks:
        return {"status": "gap", "note": "Shell hooks exist but no centralized registry"}
    return {"status": "gap", "note": "No hook infrastructure found"}


def check_subagents():
    """ADK subagents/ -> Hermes delegate_task system."""
    # delegate_task is a built-in tool, not a directory
    # Check if there's any subagent contract schema
    subagents_dir = HERMES_HOME / "subagents"
    if subagents_dir.exists():
        return {"status": "existing", "note": "Subagents directory exists"}
    # delegate_task is built-in
    return {
        "status": "existing",
        "note": "delegate_task built-in tool provides subagent isolation (role, toolsets, context). No separate directory needed."
    }


def check_plugins():
    """ADK plugins/ -> Hermes plugins/ + MCP."""
    plugins_dir = HERMES_HOME / "plugins"
    if not plugins_dir.exists():
        return {"status": "gap", "count": 0, "note": "No plugins directory"}
    plugins = [d for d in plugins_dir.iterdir() if d.is_dir()]
    has_manifest = all((p / "plugin.yaml").exists() for p in plugins) if plugins else False
    return {
        "status": "existing" if plugins else "gap",
        "count": len(plugins),
        "has_manifest": has_manifest,
        "note": f"{len(plugins)} plugins, manifest={'all' if has_manifest else 'partial'}"
    }


def check_observability():
    """ADK extension: observability/eval/audit."""
    obs_dir = HERMES_HOME / "observability"
    eval_dir = HERMES_HOME / "evals"
    return {
        "status": "gap",
        "observability_dir": obs_dir.exists(),
        "evals_dir": eval_dir.exists(),
        "note": "No observability or evaluation directories. Skills audit log exists in skills_hub.py."
    }


def main():
    as_json = "--json" in sys.argv
    report = {
        "schema": "adk_contract_v1",
        "hermes_home": str(HERMES_HOME),
        "components": {
            "policy": check_policy(),
            "skills": check_skills(),
            "hooks": check_hooks(),
            "subagents": check_subagents(),
            "plugins": check_plugins(),
            "observability": check_observability(),
        }
    }
    # Summary
    statuses = [v["status"] for v in report["components"].values()]
    report["summary"] = {
        "existing": statuses.count("existing"),
        "gap": statuses.count("gap"),
        "duplicate": statuses.count("duplicate"),
        "intentionally_unsupported": statuses.count("intentionally_unsupported"),
    }

    if as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("=== ADK Contract Verification Report ===")
        print(f"Hermes home: {HERMES_HOME}")
        print()
        for comp, result in report["components"].items():
            status = result["status"].upper()
            print(f"  [{status:>10}] {comp}: {result.get('note', '')}")
        print()
        s = report["summary"]
        print(f"  Summary: {s['existing']} existing, {s['gap']} gaps, {s['duplicate']} duplicates, {s['intentionally_unsupported']} unsupported")


if __name__ == "__main__":
    main()
