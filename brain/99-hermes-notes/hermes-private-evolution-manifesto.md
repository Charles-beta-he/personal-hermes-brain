# Hermes Private Evolution Manifesto

**Date:** 2026-04-29
**Status:** active
**Scope:** applies to all Hermes Agent modifications on this machine

## Foundational Truths

1. **This Hermes is a private fork of upstream `NousResearch/hermes-agent`.**
   - Upstream is a reference source and update pipeline, NOT the canonical remote.
   - No commits need to be pushed to upstream unless specifically requested.
   - No PRs need to be opened on upstream unless specifically requested.

2. **`hermes update` / `git pull` = upgrade, not sync.**
   - Pulling upstream code is a controlled upgrade, like updating an OS.
   - Local patches, skills, scripts, and data survive via `post-update-patch-healing`.
   - Upgrade validation means: local changes still work, tests pass, post-update-check runs.

3. **External project analysis = valid Hermes evolution input.**
   - Studying Warp, Claude Code, OpenCode, Codex, or any external agent/project.
   - Extracting mechanism → adapting to Hermes architecture → creating Hermes-specific artifact.
   - This IS evolution, not "reading competitor code". Methodology migration is the core mechanism.

4. **No upstream-style push required for work completion.**
   - Local commit is sufficient for traceability and rollback.
   - `docs/`, `specs/`, `~/.hermes/notes/` are primary artifacts.
   - `ahead N, behind M` is normal, not a failure state.

## Artifact Requirements

Every evolution event MUST produce at least one of:

| Artifact | Location | Example |
|----------|----------|---------|
| Skill | `~/.hermes/skills/` | `my-workflow/skill.md` |
| Script | `~/.hermes/scripts/` | `verify-evolution-event.py` |
| Spec | `<repo>/specs/<feature>/PRODUCT.md` + `TECH.md` | P0 multi-model governance |
| ADR | `<repo>/docs/adr/` | ADR-0001 |
| Workflow doc | `<repo>/docs/workflows/` | issue-taxonomy.md |
| Evolution note | `~/.hermes/notes/evolution/YYYY-MM-DD-slug.md` | warp-p0 |
| Config/quorum | `~/.hermes/config/` | quorum.yaml tier change |
| Post-update check | `~/.hermes/scripts/post-update-check.py` | Added patch detection |

Minimal acceptable artifact for a trivial change: evolution note only.

## Verification Requirements

Every evolution event MUST have verification:

| Change type | Minimum verification |
|-------------|---------------------|
| Spec-only | `python3 -m json.tool` for schemas, `head/cat` review for markdown |
| Script change | `python3 -m py_compile script.py` + functional test |
| Runtime change | `pytest -q` with isolated `HERMES_HOME` |
| Config change | `hermes doctor` or config syntax check |
| Skill change | `skill_view` loads without error, trigger test passes |

## Upgrade Process

When upgrading (`git pull --ff-only origin main`):

1. Pre-upgrade: backup with `~/.hermes/scripts/hermes-pre-upgrade-verify.sh`
2. Stash all local changes: `git stash push -u -m "pre-upgrade-$(date +%Y%m%d-%H%M%S)"`
3. Pull: `git pull --ff-only origin main` → auto-triggers `post-update-check.py --fix`
4. Pop stash with conflict resolution if needed
5. Verify: `post-update-check.py` dry-run + isolated pytest + `hermes doctor`

## Change Classification

| Level | Location | Survival | Risk |
|-------|----------|----------|------|
| 0 — User data | `~/.hermes/skills/`, `~/.hermes/scripts/`, `~/.hermes/config/`, `~/.hermes/plugins/`, `~/.hermes/notes/`, `~/.hermes/cron/`, `~/.hermes/memory/` | Update-safe (outside git) | None |
| 1 — Repo-local | `<repo>/docs/`, `<repo>/specs/`, `<repo>/tests/`, `agent/model_health.py`, `agent/task_classifier.py` | Survives with local commit + possible rebase conflicts | Low |
| 2 — Vendor core | `<repo>/run_agent.py`, `<repo>/cli.py`, `<repo>/agent/prompt_builder.py`, `<repo>/agent/context_compressor.py`, `<repo>/tools/mcp_tool.py` | Overwritten by git pull; protected by post-update-check | Medium |

Prefer Level 0 >> Level 1 > Level 2. If a change can be a skill or script, it should be.

## Acceptance Criteria

Evolution event is DONE when:

- [ ] Artifact exists (≥1 from table above)
- [ ] Verification passes
- [ ] Upgrade survival path is clear (Level 0 = natural; Level 1/2 = documented in post-update-check or evolution note)
- [ ] If relevant: skill/script/ADR/evolution note is created or updated
- [ ] Local commit exists (not pushed unless explicitly requested)
