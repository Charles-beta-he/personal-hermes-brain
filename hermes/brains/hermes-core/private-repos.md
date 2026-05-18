# Hermes Core Private Repositories v0.1.0

## Runtime private code repo

- Path: `/Users/charles/.hermes/hermes-agent`
- Private origin: `Charles-beta-he/hermes-agent-private`
- Official upstream: `NousResearch/hermes-agent`
- Stable branch: `private/main`
- Governance: `docs/private/`
- Guard: `post-update-check.py` includes `private_repo_governance`.

Purpose: private Hermes runtime enhancements, tests, upgrade SOP, overlay metadata.

Never include: live `.hermes/`, `state.db`, sessions, logs, auth, tokens, env files, caches.

## Sanitized personal brain backup repo

- Path: `/Users/charles/Code/personal-hermes-brain`
- Remote: `Charles-beta-he/personal-hermes-brain`
- Role: portable sanitized brain/skills/scripts/project-profiles backup.

Current local WIP assigned to hermes-core:
- `brain_task_dispatch_tick.py` — bounded command timeout / process-group termination / structured diagnostics.
- `brain_task_orchestrator.py` — taskpool event hook smart routing, budget/governance ratchet, priority mode, lifecycle boundaries.
- `consult_models.py` — conductor-enhanced prompt/trace and self-relaxing governance patch detection.
- related tests.

Handling rule: before pushing to main, classify WIP into topic commits and reconcile remote divergence. Until then, use safe backup branches for isolated snapshots.
