---
type: audit-log
layer: L3
status: done
created: 2026-05-06T08:32:00Z
expires_at: 2026-06-06T00:00:00Z
task: local-brain-empty-directory-audit
proof_required: true
---

# 2026-05-06 本地大脑空白目录审计

## Scope

Canonical vault:

```text
/Users/charles/Documents/brain
```

Ignored: hidden/system directories such as `.obsidian`.

## Summary

Scanned 27 non-hidden directories.

Findings:

| Class | Count | Meaning |
|---|---:|---|
| Fully blank directories | 4 | No `.md` files in directory or subtree |
| Parent-only / missing direct MOC | 1 | No direct `.md`, but child subtree has content |
| Top-level folders without explicit index/MOC | 15 | Content exists, but folder lacks direct index/overview note |
| Thin top-level folders | 16 | Top-level folder has 0-2 notes; may be intentional or underfilled |

## Fully blank directories

These are true blank folders and should be filled or intentionally marked as reserved:

| Directory | Current state | Suggested minimum landing |
|---|---|---|
| `07-元认知` | 0 md, 0 files, 0 subdirs | MOC + metacognition model cards: reflection, calibration, epistemic humility, error taxonomy |
| `08-实践方案` | 0 md, 0 files, 0 subdirs | MOC + concrete implementation playbooks linked from theory notes |
| `09-引用原文` | 0 md, 0 files, 0 subdirs | Source/evidence intake policy + raw-source index; avoid credential or copyrighted bulk dumps |
| `10-模板` | 0 md, 0 files, 0 subdirs | Note templates: theory card, project MOC, task log, evidence note, review artifact |

## Parent-only / missing direct MOC

| Directory | Current state | Suggested action |
|---|---|---|
| `20-projects` | 0 direct md, 1 child folder, 1 subtree md | Add `05-实践与项目/projects/00-projects-index.md` linking `hermes-local-brain` and future projects |

## Top-level folders with content but no direct index/MOC

These are not blank, but would benefit from an index note:

- `00-evidence`
- `00-system`
- `02-治理理论`
- `03-系统理论`
- `04-技能生态`
- `05-进化日志`
- `06-仪表盘`
- `10-ai-systems`
- `10-atoms`
- `20-projects`
- `30-tasks`
- `40-skills`
- `50-prefs`
- `60-reviews`
- `99-hermes-notes`

Note: `01-控制论基础` now has `00-控制论基础索引.md`, so it is no longer blank/hollow.

## Recommended fill order

P0:

1. `10-模板` — templates prevent future category-fill drift.
2. `09-引用原文` — source policy prevents evidence chaos and secret leakage.
3. `05-实践与项目/projects/00-projects-index.md` — project layer needs a parent MOC.

P1:

4. `07-元认知` — important for self-audit, calibration, uncertainty tracking.
5. `08-实践方案` — bridge theory notes to execution playbooks.

P2:

6. Add lightweight MOCs to non-empty top-level folders.

## Verification checklist

Final verification:

- [x] `brainctl sync` completed: `Sync complete: 0 pushed, 2 pulled`.
- [x] `brainctl reindex` completed: `indexed_blocks=944`, `skipped_secret_blocks=0`, `skipped_ignored_files=0`.
- [x] Search finds this audit with `local brain empty directory audit`.
- [x] Search finds Chinese query `本地大脑 空白目录 审计`.

Observed search hits:

```text
local brain empty directory audit -> 05-实践与项目/tasks/2026-05-06-local-brain-empty-directory-audit.md
本地大脑 空白目录 审计 -> 05-实践与项目/tasks/2026-05-06-local-brain-empty-directory-audit.md
```

## Evidence Boundary

- Canonical truth is the Markdown vault plus deterministic `brainctl` / filesystem / git gates.
- Multi-model agreement, derived indexes, RRF/vector/KG outputs, and theory analogies are provenance or retrieval aids only; they are not truth sources.
- Promotion requires linked tool/file/search evidence after this artifact is written.

## Permission retrigger proof pointer

- 2026-05-06 permission-retrigger scope: rerun approval-sensitive local-brain governance path after the user explicitly requested re-triggering permission-gated work.
- Proof ledger: [[2026-05-06-permission-retrigger-local-brain-closure-review]].
- Expected gates: `brainctl promote`, `brainctl sync`, `brainctl reindex`, `brainctl search`, `brainctl validate --dry-run`, exhaustive audit, active-backlog marker scan, test suite, scoped mirror/git status, and local commit if the scoped diff is dirty.
