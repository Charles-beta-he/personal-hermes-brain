---
type: review
layer: L6
status: current
created: 2026-05-08T19:06:00+08:00
updated: 2026-05-08T19:06:00+08:00
project: local-brain-governance
concepts: [doc-function-closure, local-brain, repair-apply, multi-model-advisory]
models:
  - gpt-5.5
  - mimo-v2.5-pro
  - claude-opus-4-7
artifacts:
  - /tmp/local_brain_doc_func_closure_20260508185219
  - /Users/charles/.hermes/tick-20260508-105533
  - /tmp/local_brain_doc_func_final_verify_20260508190519
---

# 本地大脑文档-功能闭环多模型修复记录

## Evidence Boundary

Model agreement is provenance only. Closure status is based on deterministic command/file/search proof: hierarchy selfcheck, exhaustive audit, brainctl validate, task orchestrator selfcheck/proof-check, skill graph, brainctl sync/reindex/search.

## Initial findings

Audit artifact: `/tmp/local_brain_doc_func_closure_20260508185219`

- `local_brain_main_hierarchy_migration_selfcheck.py --json`: FAIL
  - top-level legacy `06-仪表盘/` still existed.
  - old path wikilink hit existed inside legacy dashboard index.
  - JSON proof artifact was linked as Obsidian wikilink.
- `local_brain_exhaustive_audit.py`: stop_gate_pass=false, broken_wikilinks_count=1.
- `brainctl validate --write-dashboard`: passed=false, 24 violations.
- `brain_task_orchestrator selfcheck`: PASS.
- `brain_task_orchestrator proof-check`: PASS, one legacy evidence warning.
- doc/function association scan: missing `calculate-health.py` reference; canonical implementation exists as `agent-health-monitor.py`.

## Multi-model advisory

Artifact: `/Users/charles/.hermes/tick-20260508-105533`

- gpt-5.5, MiMo-v2.5-pro, Claude Opus all agreed on the core issue class: schema mismatch / migration residue / doc-function drift.
- truth assessment: grounded; 6/6 claims verified, evidence coverage 1.0.
- consensus: weak_consensus; discussion did not finish inside tool budget, so this is not full ratification.

## Issue ledger

| Issue | Severity | Status | Resolution |
|---|---:|---|---|
| I-001 legacy `06-仪表盘/` caused hierarchy selfcheck FAIL | 4 | resolved | Archived to `06-治理与评审/历史快照/legacy-06-dashboard-20260508/` with repair manifest; removed top-level old dir. |
| I-002 JSON proof artifact was written as wikilink | 4 | resolved | Replaced double-bracket JSON artifact reference with plain file path reference. |
| I-003 brainctl validate 24 violations | 4 | resolved | Added missing type/status keys and Evidence Boundary sections; patched false-positive L3 classification. |
| I-004 derived task views were treated as L3 tasks requiring expiry | 4 | resolved | Patched `brainctl.is_l3` to exempt `task_inbox`, `derived_task_pool`, `derived_*`, proof/review/evolution/moc/dashboard unless explicitly layer L3. |
| I-005 stale `calculate-health.py` doc-function association | 3 | resolved | Added compatibility wrapper and documented canonical `agent-health-monitor.py`. |
| I-006 task pool proof-check legacy body-only warning | 2 | accepted_risk | Existing old evidence accepted as warning; not blocking current closure. |

## Applied changes

- `~/.hermes/scripts/brainctl.py`: fixed L3 classification for derived/inbox/proof/review/evolution docs.
- `~/.hermes/scripts/test_brainctl.py`: regression test for task inbox and derived sorted pool false positives.
- `~/.hermes/scripts/calculate-health.py`: compatibility wrapper to `agent-health-monitor.py`.
- Vault frontmatter: filled missing `type` / `status` keys on governance-visible notes.
- Review/evolution/proof notes: added `## Evidence Boundary` where absent.
- Broken JSON wikilink: converted to plain artifact path.
- Legacy dashboard: archived `06-仪表盘/` under governance history with `repair-manifest.json`.

## Final verification

Artifact: `/tmp/local_brain_doc_func_final_verify_20260508190519`

- `python3 -m py_compile ...`: PASS
- `python3 ~/.hermes/scripts/test_brainctl.py -v`: PASS, 15 tests
- `local_brain_main_hierarchy_migration_selfcheck.py --json`: PASS
- `local_brain_exhaustive_audit.py --sample-limit 100`: PASS, stop_gate_pass=true, broken_wikilinks_count=0, secret_pattern_hits=0
- `brainctl.py --json validate --write-dashboard`: PASS, violations=0, l3_expiry_open=0
- `brain_task_orchestrator.py selfcheck --json`: PASS
- `brain_task_orchestrator.py proof-check --json`: PASS, only legacy body-only warning
- `skill-steward.py --graph-check --json`: OK, cycles=0
- `brainctl.py --json sync`: exit_code=0
- `brainctl.py --json reindex`: indexed_blocks=2390, skipped_secret_blocks=18
- `brainctl.py --json search 'doc-function-closure local-brain legacy dashboard'`: returned 1 hit

## Verdict

本轮文档-功能关联与治理闭环已经完成：结构迁移、断链、validate、task proof、索引同步均通过。剩余 warning 是历史 legacy evidence 格式，不阻塞当前闭环。
