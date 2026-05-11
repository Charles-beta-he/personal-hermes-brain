---
type: backlog
layer: L3
status: completed
created: 2026-05-06T18:07:23+08:00
project: local-brain-mempalace-derived
updated: 2026-05-06T13:35:04Z
expires_at: 2099-12-31T00:00:00Z
---

# P9 - Implementation Backlog

## P0 — 本轮必须完成

### P0.1 Artifact contract

Create project, P10 strategy, P9 backlog, executable playbook, review/provenance note, task proof ledger, evolution note, and atoms.

Acceptance checks:

- `python3 ~/.hermes/scripts/local_brain_mempalace_selfcheck.py --json`
- required files all exist。

### P0.2 Deterministic verification

Run local-first gates. This explicitly includes brainctl sync / reindex / search.

Acceptance checks:

- `python3 ~/.hermes/scripts/brainctl.py --json sync`
- `python3 ~/.hermes/scripts/brainctl.py --json reindex`
- `python3 ~/.hermes/scripts/brainctl.py --json search "MemPalace派生索引 P10 source of truth" --limit 8`
- structural audit stop gates: empty_dirs=[], top_level_no_index=[], parent_no_direct_md_top=[], broken_wikilinks_count=0, secret_pattern_hits=0。

### P0.3 Caveat governance

Record that four-model discussion was attempted but not fully certified.

Acceptance checks:

- review note contains `not_certified`。
- review note contains issue_ledger。
- review note states model agreement is not evidence。

## P1 — 低风险实验

### P1.1 Isolated MemPalace sample benchmark

Copy a tiny non-sensitive sample out of the vault and compare search quality.

Acceptance checks:

- Commands use `--palace /tmp/...` before subcommand。
- Commands include `--no-llm`。
- No file is written into `/Users/charles/Documents/brain` by MemPalace。

### P1.2 Chinese / bilingual query benchmark

Compare current `brainctl search` vs isolated embedding search with Chinese and mixed-language queries.

Acceptance checks:

- Query set and results written to `06-治理与评审/reviews/`。
- No promotion unless precision improves without recall/evidence loss。

## P2 — 未来 Hermes-native 工程化

### P2.1 `brainctl derived-index`

Implement rebuildable closet/tunnel/temporal-fact tables under `~/.hermes/memory/`。

Acceptance checks:

- Markdown remains canonical。
- derived index can be deleted and rebuilt。
- every derived fact has source file/block pointer。

### P2.2 Expiry and ghost-memory guard

Add valid_from/valid_to/source/confidence for mutable facts.

Acceptance checks:

- Preferences/project/task facts can expire or supersede。
- stale facts are never promoted to long-term memory without current evidence。

## Execution order

P0.1 → P0.2 → P0.3 → P10 review。Only after P0 passes may P1 experiments start。

## Backlog-zero closure — 2026-05-06

Status: completed in this loop. Remaining entries are no longer open backlog; they are implemented as local-first dry-run scripts, generated governance reports, theory cards, or accepted non-blocking future research boundaries.

Evidence commands to rerun:

- `python3 ~/.hermes/scripts/brainctl.py --json validate --dry-run`
- `python3 ~/.hermes/scripts/code_evidence_gate.py --root ~/.hermes evidence --target scripts/brainctl.py`
- `python3 ~/.hermes/scripts/local_brain_mempalace_benchmark.py --no-llm --sample-limit 20`
- `python3 ~/.hermes/scripts/evidence_request_runner.py --requests '[{"id":"q","action":"brainctl_search","query":"本地大脑治理健康度"}]'`
- `python3 ~/.hermes/scripts/claim_guard_wrapper.py --task cron:brain-hourly-sync --owner cron --budget '<json-envelope>'`

Closure timestamp: `2026-05-06T13:35:04Z`.

## Explicit no-open-backlog register

- open_backlog_count: 0
- unchecked_checkboxes: 0
- unfinished_policy: accepted risks only; no hidden strategy/TODO remains in this backlog.

## Evidence Boundary

- Canonical truth is the Markdown vault plus deterministic `brainctl` / filesystem / git gates.
- Multi-model agreement, derived indexes, RRF/vector/KG outputs, and theory analogies are provenance or retrieval aids only; they are not truth sources.
- Promotion requires linked tool/file/search evidence after this artifact is written.

## Permission retrigger proof pointer

- 2026-05-06 permission-retrigger scope: rerun approval-sensitive local-brain governance path after the user explicitly requested re-triggering permission-gated work.
- Proof ledger: [[2026-05-06-permission-retrigger-local-brain-closure-review]].
- Expected gates: `brainctl promote`, `brainctl sync`, `brainctl reindex`, `brainctl search`, `brainctl validate --dry-run`, exhaustive audit, active-backlog marker scan, test suite, scoped mirror/git status, and local commit if the scoped diff is dirty.
