---
type: project
layer: L2
status: active
created: 2026-05-06T18:07:23+08:00
project: local-brain-mempalace-derived
canonical_vault: /Users/charles/Documents/brain
source_repo: /tmp/mempalace-audit
source_commit: f0d236019abc8cda09b621045511799720a4c6f7
---

# Project: MemPalace Derived Local Brain

## North star

把 MemPalace 的优点吸收为本地大脑的派生检索/唤醒/证据索引层，但不改变 `/Users/charles/Documents/brain` 作为人类可读 Markdown vault 的权威地位。

核心判断：MemPalace 有帮助，但帮助点是 retrieval architecture，不是 ontology replacement。

## Scope

- 设计 L0-L3 冷热加载协议。
- 设计 Drawer / Closet 的证据边界：原文与摘要分层。
- 设计 Temporal facts / tunnels 的派生关系层，减少 ghost memory。
- 只落地 Hermes-native 文档、playbook、自检脚本和 proof ledger。

## Non-goals

- 不把 ChromaDB 或 MemPalace palace 变成事实源。
- 不在 canonical vault 上运行 `mempalace init`。
- 不默认调用外部 LLM 或上传本地脑内容。
- 不重排现有 Obsidian 目录层级。

## Decision links

- [[05-实践与项目/projects/local-brain-mempalace-derived/P10 - Long-term Strategy]]
- [[05-实践与项目/projects/local-brain-mempalace-derived/P9 - Implementation Backlog]]
- [[05-实践与项目/实践方案/05-MemPalace派生索引落地Playbook]]
- [[06-治理与评审/reviews/2026-05-06-local-brain-mempalace-multimodel-selfcheck]]
- [[05-实践与项目/tasks/2026-05-06-local-brain-mempalace-landing-log]]
- [[06-治理与评审/进化日志/2026-05-06-MemPalace派生索引落地]]

## Success criteria

1. P10 策略没有 blocker。
2. P9 backlog 给出 P0/P1/P2 可验收任务。
3. Playbook 可按本地优先原则执行。
4. 自检脚本通过：`python3 ~/.hermes/scripts/local_brain_mempalace_selfcheck.py --json`。
5. `brainctl sync/reindex/search` 可检索到本项目与 proof notes。
