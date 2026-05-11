---
type: backlog
layer: L2
status: completed
created: 2026-05-06T19:29:36+08:00
project: local-brain-main-hierarchy-migration
---

# P9 - Main Hierarchy Migration Backlog

## P0 backup and plan

- Create manifest and tar backup。
- Run multi-model provenance review。

## P1 migration execution

- Move old top dirs into target control-plane hierarchy。
- Rewrite wikilinks using deterministic mapping。
- Create new top-level MOCs。

## P2 verification

- Run migration self-check。
- Run brainctl sync/reindex/search。
- Write proof ledger。
- Commit scoped changes。

## Acceptance checks

- self-check PASS。
- indexed_blocks observed。
- Chinese and English migration queries hit top artifacts。
- no old top dirs remaining。

中文检索别名：P9 主层级迁移 backlog 本地大脑主层级迁移 无遗留
