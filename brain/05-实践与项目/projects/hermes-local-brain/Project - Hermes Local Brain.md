---
type: project
layer: L2
status: active
created: 2026-05-06T08:10:29Z
project: hermes-local-brain
canonical_vault: /Users/charles/Documents/brain
---

# Project: Hermes Local Brain

## Purpose

Make `/Users/charles/Documents/brain` the canonical local-first brain for both human browsing and Hermes agent control.

## Current implemented state

- Obsidian.app installed and CLI runtime enabled.
- Vault registered as canonical Obsidian vault.
- `brainctl.py` status/search/sync/reindex works against the vault.
- `sync-brain.py` fixed so notes with `brain` in the filename are no longer skipped.
- Local-brain hierarchy note exists.
- Symphony/Codex orchestration source analysis exists.
- Multi-model review artifact exists, with timeout caveat.
- Formal self-evolution event exists and is mirrored under `99-hermes-notes/evolution/`.

## Category landing map

| Layer | Folder | Initial fill |
|---|---|---|
| L0 Evidence | `02-证据与原文/evidence/` | Symphony source + Obsidian CLI evidence note |
| L1 Atoms | `04-知识原子/atoms/` | Canonical vault atom; model-agreement caveat atom |
| L2 Project | `05-实践与项目/projects/hermes-local-brain/` | This project MOC |
| L3 Tasks | `05-实践与项目/tasks/` | Category fill log with proof and expiry |
| L4 Skills | `06-治理与评审/skills/` | Obsidian sync/routing skill mirror |
| L5 Preferences | `01-系统与偏好/prefs/` | Local-first/Obsidian/Hermes routing preference mirror |
| L6 Reviews | `06-治理与评审/reviews/` | Multi-model review + landing/fill review log |

## Next engineering candidates

- `brainctl validate`: schema/frontmatter/layer check.
- `brainctl promote`: controlled promotion from evidence/reviews/tasks to atoms/projects/skills.
- `brainctl expire`: WIP task expiry and archive report.
- `brainctl review record`: structured multi-model issue ledger and vote artifact.

Related:

- [[Hermes Local Brain Memory Hierarchy]]
- [[OpenAI Symphony - Codex Orchestration]]
- [[2026-05-06-multimodel-local-brain-category-fill-log]]

## Governance closure — 2026-05-06

- Unified backlog: [[05-实践与项目/projects/hermes-local-brain/P9 - Outstanding Optimization Backlog]]
- Governance dashboard: [[07-仪表盘/本地大脑治理健康度]]
- Remaining-strategy review: [[06-治理与评审/reviews/2026-05-06-local-brain-remaining-strategy-audit]]
- PUA-loop proof log: [[05-实践与项目/tasks/2026-05-06-local-brain-remaining-strategy-loop-log]]
