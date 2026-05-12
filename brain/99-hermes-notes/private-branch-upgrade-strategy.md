# Hermes Private Branch Upgrade Strategy

**Date:** 2026-04-29
**Supersedes:** general-NousResearch-public-sync workflow
**Purpose:** define how to safely upgrade from upstream when operating a private fork

## Current State

```
main...origin/main [ahead 1, behind 96]
```

- `ahead 1`: P0 multi-model governance commit `132093a53`
- `behind 96`: upstream NousResearch has 96 new commits since our last sync
- Worktree also has ~15 modified/untracked files from prior sessions

## Branch Strategy

Since this is a private fork (no push to origin needed):

**Option A — Work on a feature branch (recommended for P1+)**
```
git checkout -b p1-evolution-governance
```
- Keeps main as clean base for upstream syncs
- Feature branches are private, can be squashed
- Cherry-pick to main after stable

**Option B — Stay on main with local commits**
- Simple, single-branch
- Risk: upstream pull creates merge commits instead of fast-forward
- Fine for small-scale evolution

**Current:** Option B (main with local commit). Consider Option A for P1.

## Upgrade Steps

When ready to sync upstream (not required now):

### Phase 0: Pre-flight
```bash
cd ~/.hermes/hermes-agent

# Count ahead/behind
git rev-list --left-right --count HEAD...origin/main

# Backup everything
mkdir -p ~/.hermes/backups
git diff --binary > ~/.hermes/backups/pre-upgrade-$(date +%Y%m%d-%H%M%S).patch
```

### Phase 1: Stash + Pull + Post-Update
```bash
# Stash all tracked + untracked changes
git stash push -u -m "pre-upgrade-$(date +%Y%m%d-%H%M%S)"

# Pull (fast-forward preferred)
git pull --ff-only origin main
# → post-merge hook auto-triggers post-update-check.py --fix
```

### Phase 2: Restore Private Changes
```bash
# Check which stash items exist
git stash list

# Restore modified files that checker already fixed, then pop
git checkout HEAD -- agent/context_compressor.py agent/memory_manager.py \
  agent/prompt_builder.py agent/transports/chat_completions.py \
  tools/mcp_tool.py
git stash pop
```

### Phase 3: Verify
```bash
~/.hermes/scripts/hermes-pre-upgrade-verify.sh
post-update-check.py
```

## What Happens to P0 Files on Upgrade

| File | Where it lives | Upgrade survival |
|------|---------------|------------------|
| `specs/p0-multimodel-governance/*` | `<repo>/specs/` | ✅ Local commit, survived git stash + pop |
| `docs/workflows/*.md` | `<repo>/docs/` | ✅ Same |
| `docs/adr/ADR-0001-*.md` | `<repo>/docs/` | ✅ Same |
| `docs/specs/review.schema.json` | `<repo>/docs/` | ✅ Same |
| `~/.hermes/notes/evolution/*` | `~/.hermes/` | ✅ Outside git, always safe |
| `~/.hermes/notes/hermes-private-evolution-manifesto.md` | `~/.hermes/` | ✅ Outside git |

## Current Worktree State (Apr 29)

Non-P0 dirty/untracked files (must NOT be attributed to evolution events):

```
Modified tracked:
  AGENTS.md
  agent/context_compressor.py
  agent/memory_manager.py
  agent/prompt_builder.py
  agent/transports/chat_completions.py
  cli.py
  hermes_cli/commands.py
  run_agent.py
  tools/mcp_tool.py (staged + unstaged)
  tools/skill_manager_tool.py
  web/package-lock.json

Untracked:
  agent/model_health.py
  agent/spl.py
  agent/task_classifier.py
  tests/test_model_health.py
  tests/test_task_classifier.py

Modified unstaged:
  tests/tools/test_mcp_tool.py
```

These were NOT created by this evolution event. They were pre-existing.

## Decision Record

| Decision | Rationale |
|----------|-----------|
| No fork on GitHub needed | Remote is read-only reference; all work is local |
| No PR to upstream needed | Private evolution, not open-source contribution |
| evolution notes outside git | Survives upgrades, no commit noise |
| Manifesto outside git | Same reason |
| Local commit for repo artifacts | Traceability + rollback + diff-ability |
