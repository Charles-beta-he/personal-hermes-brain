---
type: backlog
layer: L3
status: completed
created: 2026-05-06T18:29:31+08:00
project: cybernetic-multimodel-intervention
updated: 2026-05-06T13:35:04Z
expires_at: 2099-12-31T00:00:00Z
---

# P9 - Implementation Backlog

## P0 — 本轮完成

### P0.1 Artifact landing

Create P10/P9/project/playbook/review/task/evolution/atoms and link theory notes。

Acceptance checks:

- `python3 ~/.hermes/scripts/cybernetic_multimodel_selfcheck.py --json`
- required artifacts exist。

### P0.2 Deterministic gate

Run local proof commands。This includes brainctl sync / reindex / search as the deterministic audit path。

Acceptance checks:

- `python3 ~/.hermes/scripts/brainctl.py --json sync`
- `python3 ~/.hermes/scripts/brainctl.py --json reindex`
- `python3 ~/.hermes/scripts/brainctl.py --json search "cybernetic multi-model intervention first-order second-order observer" --limit 8`
- structural audit: empty_dirs=[], top_level_no_index=[], parent_no_direct_md_top=[], broken_wikilinks_count=0, secret_pattern_hits=0。

### P0.3 Multi-model caveat ledger

Record planner status and timeout/dissent as provenance。

Acceptance checks:

- review contains `not_certified`。
- review contains `issue_ledger`。
- review contains `timeout` and `dissent`。

## P1 — 协议工程化

### P1.1 consult_models state template

Create reusable state template for cybernetic multi-model intervention：

- object_task
- first_order_claims
- evidence_requests
- second_order_self_audit
- issue_ledger
- deterministic_stop_gates

Acceptance checks:

- template can generate a state JSON without external API。
- self-audit fields are required, not optional。

### P1.2 local-brain promotion rule

Create rule: review hypotheses can only promote to atom/project after evidence pointer exists。

Acceptance checks:

- `04-知识原子/atoms/model-agreement-is-not-evidence.md` linked。
- new review note records promotion status。

## P2 — 自动化与治理

### P2.1 Second-order periodic audit

Add optional scheduled local report that checks whether multi-model reviews are being falsely promoted。

Acceptance checks:

- local-first script only。
- no automatic external model calls。
- alert only on concrete violations。

### P2.2 Skill integration

Patch relevant skills if future runs reveal missing steps。

Acceptance checks:

- skill patch records pitfall and verification commands。

## Execution order

P0.1 → P0.2 → P0.3 → P10 verification → P1 template if requested。

## P0.4 — Hierarchy overlay routing matrix

Land keypoint-to-multimodel routing without rewriting the main Obsidian hierarchy.

Acceptance checks:

- [[05-实践与项目/实践方案/07-关键点多模型介入路由矩阵]] exists。
- [[04-知识原子/atoms/semantic-overlay-before-hierarchy-rewrite]] exists。
- [[04-知识原子/atoms/keypoint-to-multimodel-routing]] exists。
- Chinese and English `brainctl search` queries hit the route matrix。
- self-check validates hierarchy decision and route matrix patterns。

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
