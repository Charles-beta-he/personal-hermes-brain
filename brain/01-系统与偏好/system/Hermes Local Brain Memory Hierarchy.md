---
type: system-design
status: active
created: 2026-05-06T07:41:43Z
updated: 2026-05-06T12:56:02Z
source: hermes_multi_model_review
review_artifact: /Users/charles/.hermes/tick-20260506-073039
models_consulted:
  - claude-opus-4-7
  - gpt-5.5
  - deepseek-v4-pro
  - mimo-v2.5-pro
certification: fanout_completed_discussion_timeout
canonical_vault: /Users/charles/Documents/brain
index: /Users/charles/.hermes/memory/index.sqlite
---

# Hermes Local Brain Memory Hierarchy

This is the current design contract for Hermes + Obsidian local brain.

Important certification note: four-model seed fanout completed on 2026-05-06 at `/Users/charles/.hermes/tick-20260506-073039`; the discussion/ratification phase timed out during consensus, so this is a synthesized design with multi-model provenance, not a fully ratified `consult_models.py --discussion` certification. Model agreement is not evidence; factual claims still need evidence links.

## Core principle

`~/Documents/brain` is the human-readable canonical source of truth. SQLite, embeddings, FTS, WAL, and other indexes are derived caches and must be rebuildable.

Obsidian.app is the human visualization/editor. `brainctl.py`, `sync-brain.py`, cron, skills, and Hermes memory are the agent control plane.

## Layer model

| Layer | Name | Canonical storage | Purpose | TTL / decay |
|---|---|---|---|---|
| L0 | Evidence | `02-证据与原文/evidence/` or source-linked note blocks | Raw fetched/source facts, URLs, screenshots, command output summaries, checksums | GC only if unreferenced and old |
| L1 | Atomic notes | `04-知识原子/atoms/` | One durable idea/claim per note, with evidence links | Deprecate when contradicted or superseded |
| L2 | Project knowledge | `05-实践与项目/projects/<project>/` | Project-specific architecture, decisions, context, glossary | Review when project changes |
| L3 | Task state | `05-实践与项目/tasks/<task-id>/` | Current/expiring work state, task lifecycle, proof links | Must expire/archive; never durable memory |
| L4 | Skills / procedures | `~/.hermes/skills/` primary, optional `06-治理与评审/skills/` mirror | Reusable workflows, commands, pitfalls, verification | Versioned; patch when stale |
| L5 | Long-term preferences / environment facts | Hermes memory primary, optional `01-系统与偏好/prefs/` mirror | Compact facts useful in future sessions | Only stable facts; no WIP ghosts |
| L6 | Model review artifacts | `06-治理与评审/reviews/<date>-<slug>/` | Multi-model proposals, issue ledger, evidence requests, votes, final adjudication | Archive/summarize after usefulness decays |

## Routing rules

1. Raw fact/source/screenshot/link/command evidence -> L0 evidence note. Do not write raw dumps into Hermes memory.
2. Durable idea synthesized from evidence -> L1 atomic note with `evidence:` frontmatter or backlinks.
3. Project-scoped knowledge -> L2 project note; link to L0/L1 instead of copying large evidence.
4. WIP / task progress / temporary todo -> L3 task state with `expires_at`; never store in Hermes durable memory.
5. Reusable procedure, workflow, or repeated successful pattern -> L4 skill via `skill_manage`; vault may mirror but skill is operational source.
6. Stable user preference or stable environment fact useful across many sessions -> L5 Hermes memory, compact declarative fact only.
7. Multi-model thinking output -> L6 review artifact. It is proof of review, not proof of truth.
8. SQLite index -> derived only. Rebuild via `brainctl.py --json reindex`; never edit it as canonical truth.

## Promotion rules

- L0 -> L1: allowed only when the note has source/evidence id, timestamp, and a single clear claim.
- L1 -> L2: allowed when the claim is repeatedly used in a project or is required to understand a project decision.
- L3 -> L4: allowed when a task produced a reusable workflow, overcame non-trivial failure, or involved 5+ tool calls and verification.
- L5 memory: allowed only if the fact will still be useful in 10 sessions; no session-local state.
- L6 -> L1/L2/L4: allowed only after evidence requests are satisfied; model agreement alone cannot promote a claim.

## Expiry and ghost prevention

- Every L3 task note must have `expires_at` or a terminal state.
- Completed tasks should keep proof links but should not be injected into future prompts as current state.
- Old review artifacts should be summarized into atomic/project notes only if evidence-backed.
- Superseded claims should be marked `superseded_by`, not silently deleted.

## Retrieval path

1. User query -> `brainctl.py --json search/evidence` over derived index.
2. Load matching L1/L2 notes.
3. Expand backlinks to L0 evidence and L6 review artifacts.
4. Return a compact evidence bundle to the active agent.
5. Inject Hermes memory only for stable L5 facts; all other brain context is on-demand.

## Governance checks to add incrementally

- `brainctl validate`: frontmatter/layer schema check.
- `brainctl promote`: applies promotion gates; dry-run by default.
- `brainctl expire`: archives expired L3 tasks; dry-run by default.
- `brainctl review record`: writes L6 review artifact with evidence requests and votes.
- `brainctl gc-evidence --dry-run`: reports old unreferenced L0 evidence.
- Cron: run sync + reindex + validate + expiry report, but do not delete automatically without policy.


## Governance implementation status — 2026-05-06 PUA-loop

- `brainctl validate`: done. Dry-run checks frontmatter/status, L3 expiry/terminal state, review evidence-boundary, and can refresh dashboard.
- `brainctl promote`: done. Dry-run reports evidence-backed terminal artifacts and rejects insufficient evidence/provenance.
- `brainctl expire`: done. Dry-run reports expired/no-expiry L3 tasks; no automatic deletion.
- `brainctl review record`: done. Writes standardized L6 review artifacts with evidence requests, votes, and final adjudication.
- `brainctl gc-evidence --dry-run`: P2 open. Only report unreferenced L0 evidence; never delete source evidence without an explicit whitelist.
- Deterministic structure audit: available as `~/.hermes/scripts/local_brain_exhaustive_audit.py` and currently passing.
- Backlog owner: [[05-实践与项目/projects/hermes-local-brain/P9 - Outstanding Optimization Backlog]].

## Symphony-inspired mapping

| Symphony | Hermes local brain equivalent |
|---|---|
| Linear board as control plane | `05-实践与项目/tasks/` task notes + brainctl status/search |
| Per-issue workspace | Per-task folder/worktree/workdir linked from L3 task note |
| `WORKFLOW.md` | Skill + task/project workflow contract |
| Issue state machine | L3 state transitions: proposed -> claimed -> running -> review -> done/archived/expired |
| Agent proof of work | L0 evidence + L6 review artifact + test/build/commit links |
| Observability dashboard | brainctl status, WAL, cron output, review ledger |
| Human manages work, not sessions | Obsidian MOCs + Hermes cron/subagents manage execution loops |

## Current incremental landing order

1. Keep Obsidian vault canonical and indexed.
2. Add this design note and the Symphony note.
3. Patch the Obsidian skill with install/CLI caveats and hierarchy routing.
4. Completed: `brainctl validate/promote/expire/review` added additively as dry-run/local-first governance gates.
5. Later: create task-state templates and policy YAML.
