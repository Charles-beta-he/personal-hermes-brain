# Evolution Event: Symphony → Obsidian Local Brain Control Plane

**Date:** 2026-05-06
**Type:** methodology-migration | local-brain-architecture | workflow-hardening
**Status:** completed
**Scope:** Level 0 update-safe notes/skills/memory; no upstream push required

## Source Signal

User provided a screenshot/OCR source pointing to OpenAI Symphony:

- Article: `https://openai.com/index/open-source-codex-orchestration-symphony/`
- GitHub: `https://github.com/openai/symphony`
- Screenshot OCR: `symphony github地址: https://github.com/openai/symphony` and `原文链接: https://openai.com/index/open-source-codex-orchestration-symphony/ #大模型开发 #AI应用开发 #harness_`

The user intent was not to copy Symphony, but to absorb its orchestration ideas into Hermes' own local-first memory and self-evolution control plane.

A later Obsidian screenshot confirmed the official CLI setting was enabled with:

```text
Successfully registered to PATH.
```

## Mechanisms Extracted from Symphony

- Issue/task board as agent control plane.
- Per-issue isolated workspace.
- `WORKFLOW.md` as explicit execution contract.
- State machine lifecycle for autonomous agent work.
- Proof-of-work before completion claims.
- Dashboard/logging/observability for humans.
- Trusted-environment caveat: do not treat orchestration as a security sandbox.

## Hermes-Specific Output

Local Hermes-home commit:

```text
fix(brain): record Symphony local-brain evolution
```

Note: exact commit hash is intentionally not embedded because amending this note changes the hash. Use `git -C /Users/charles/.hermes log -1 --oneline` for the current local commit ID.

Created/updated local-brain artifacts:

| Artifact | Purpose |
|----------|---------|
| `/Users/charles/Documents/brain/01-系统与偏好/system/Hermes Local Brain Memory Hierarchy.md` | Canonical 7-layer memory hierarchy and write routing rules |
| `/Users/charles/Documents/brain/04-知识原子/ai-systems/OpenAI Symphony - Codex Orchestration.md` | Source analysis and Hermes adaptation map |
| `/Users/charles/Documents/brain/06-治理与评审/reviews/2026-05-06-hermes-brain-hierarchy-multi-model-review.md` | Multi-model provenance and timeout/dissent caveat |
| `/Users/charles/Documents/brain/01-系统与偏好/system/Obsidian Setup - Hermes Local Brain.md` | Obsidian.app / official CLI / vault registration record |
| `/Users/charles/.hermes/notes/evolution/2026-05-06-symphony-obsidian-local-brain.md` | Formal self-evolution event log |
| `/Users/charles/.hermes/logs/evolve.log` | Append-only self-evolution event stream |
| `/Users/charles/.hermes/notes/engineering-cybernetics/autonomous-evolution-log.jsonl` | Engineering-cybernetics evolution event stream |
| `/Users/charles/.hermes/scripts/sync-brain.py` | Fixed push filter so notes with `brain` in filename are not skipped |
| `/Users/charles/.hermes/scripts/test_sync_brain.py` | Regression test proving the sync filter fix |
| `/Users/charles/.hermes/skills/note-taking/obsidian/SKILL.md` | Patched with official CLI runtime-enable caveat and sync filter pitfall |
| Hermes durable memory | Updated compact environment fact for active local brain |

## Memory / Control-Plane Decision

Canonical source of truth:

```text
/Users/charles/Documents/brain
```

Derived and rebuildable layers:

```text
/Users/charles/.hermes/memory/index.sqlite
/Users/charles/.hermes/memory/wal.jsonl
```

Final hierarchy:

1. `00_evidence/` — raw evidence, source links, command outputs, screenshots.
2. `10_atoms/` — atomic stable claims linked to evidence.
3. `20_projects/` — project-level context, decisions, MOCs.
4. `30_tasks/` — WIP/task state with expiry; never durable memory.
5. `40_skills/` — reusable procedures; Hermes skills remain canonical, vault mirrors for visibility.
6. `50_prefs/` — long-term user/environment facts only after stability threshold.
7. `60_reviews/` — multi-model reviews, truth gates, evidence bundles.

## Multi-Model Evidence

Ran T3 four-model seed fanout:

- `claude-opus-4-7`
- `gpt-5.5`
- `deepseek-v4-pro`
- `mimo-v2.5-pro`

Artifact directory:

```text
/Users/charles/.hermes/tick-20260506-073039
```

Important certification caveat:

```text
fanout completed, but discussion/consensus timed out after 600s.
merged_plan.json reported consensus_verdict=dissent, arbitration_needed=true, confidence=0.261.
```

Therefore this event records multi-model provenance, not a fully ratified multi-model consensus.

## Level Classification

| Level | Files |
|-------|-------|
| Level 0 — User data / update-safe | `/Users/charles/.hermes/notes/evolution/2026-05-06-symphony-obsidian-local-brain.md`, `/Users/charles/Documents/brain/...`, `/Users/charles/.hermes/logs/evolve.log`, `/Users/charles/.hermes/notes/engineering-cybernetics/autonomous-evolution-log.jsonl`, `/Users/charles/.hermes/skills/note-taking/obsidian/SKILL.md`, `/Users/charles/.hermes/scripts/sync-brain.py`, `/Users/charles/.hermes/scripts/test_sync_brain.py`, Hermes memory entry |
| Level 1 — Repo-local | none |
| Level 2 — Vendor core patch | none |

No remote push is required. This is private local evolution.

## Verification

Observed verification before this note:

```text
Obsidian CLI: /usr/local/bin/obsidian
obsidian --help prints "Obsidian CLI" usage, so runtime CLI is enabled.
brainctl status vault: /Users/charles/Documents/brain
brainctl indexed_blocks: 800 before this event note reindex
brainctl mode: obsidian_cli_available
```

Required final verification commands for this event:

```bash
python3 ~/.hermes/scripts/verify-evolution-event.py \
  /Users/charles/.hermes/notes/evolution/2026-05-06-symphony-obsidian-local-brain.md \
  /Users/charles/Documents/brain/01-系统与偏好/system/Hermes\ Local\ Brain\ Memory\ Hierarchy.md \
  /Users/charles/Documents/brain/04-知识原子/ai-systems/OpenAI\ Symphony\ -\ Codex\ Orchestration.md \
  /Users/charles/Documents/brain/06-治理与评审/reviews/2026-05-06-hermes-brain-hierarchy-multi-model-review.md \
  /Users/charles/Documents/brain/01-系统与偏好/system/Obsidian\ Setup\ -\ Hermes\ Local\ Brain.md \
  --repo=/Users/charles/.hermes/hermes-agent

python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "Symphony Obsidian Local Brain" --limit 5
```

Final observed verifier result:

```text
Evolution Event Compliance: COMPLIANT
Checks: 8/8 passed
Has evolution note: yes
Has repo artifact: yes
Has verification: yes
Git HEAD: f999f798f
Ahead/Behind: 3 / 118
Final: COMPLIANT
```

TDD evidence for the sync bug discovered during this event:

```text
RED: test_sync_brain.py reported 2 failures because sync-brain.py skipped any path containing "brain".
GREEN: test_sync_brain.py reported 2/2 OK after changing the filter to skip only ~/.hermes/notes/brain/ as the pull mirror subtree.
py_compile: sync-brain.py and test_sync_brain.py OK.
```

Brain visibility after the fix:

```text
brainctl sync: Sync complete: 1 pushed, 0 pulled
brainctl reindex: indexed_blocks=811
brainctl search: hit 99-hermes-notes/evolution/2026-05-06-symphony-obsidian-local-brain.md
```

The repo state `ahead 3, behind 118` is normal for this private fork: 3 private local evolutions ahead of upstream and 118 upstream commits available for a controlled upgrade later. No push is required.

## Upgrade Survival

All durable artifacts are Level 0. They live outside the upstream Hermes source tree and survive `hermes update` / upstream `git pull`.

The only modified skill is under:

```text
/Users/charles/.hermes/skills/note-taking/obsidian/SKILL.md
```

That is also Level 0 and update-safe relative to `~/.hermes/hermes-agent`.

## Pitfalls Discovered

- Obsidian CLI binary presence is not enough. Runtime CLI must be enabled in the app UI.
- In Simplified Chinese UI, the setting appears as `命令行界面` under the `关于` page's `高级` section.
- Multi-model fanout completion is not the same as consensus certification; timeout/dissent must be recorded explicitly.
- Local brain Markdown is canonical; SQLite/FTS/WAL are caches and must remain rebuildable.
- `sync-brain.py` previously skipped any Hermes note path containing the substring `brain`; self-evolution notes named `...local-brain.md` were therefore silently not pushed into Obsidian. The filter must skip only the mirror subtree `~/.hermes/notes/brain/`.

## P1/P2 Candidates

- Implement `brainctl validate` for local-brain schema and required frontmatter.
- Implement `brainctl promote` to move evidence-backed notes from tasks/reviews into atoms/projects.
- Implement `brainctl expire` for WIP task-state garbage collection.
- Implement a Hermes Symphony Layer: task state machine + per-task worktree + proof-of-work bundle.
- Add a lightweight self-evolution-log check to `self-test.py` so future methodology migrations cannot miss the evolution note.
