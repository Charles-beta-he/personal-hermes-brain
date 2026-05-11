---
type: project
layer: L2
status: completed
created: 2026-05-06T19:29:36+08:00
project: local-brain-main-hierarchy-migration
---

# Project - Local Brain Main Hierarchy Migration

## North star

把本地大脑从历史增量式顶层目录迁移为 P10 control-plane 主层级，同时保留全部原文、证据、任务、项目和 wikilink 可达性。

## Target hierarchy

- 00-索引
- 01-系统与偏好
- 02-证据与原文
- 03-理论与元认知
- 04-知识原子
- 05-实践与项目
- 06-治理与评审
- 07-仪表盘
- 08-模板
- 99-hermes-notes

## Non-goals

- 不丢弃任何原有 Markdown 内容。
- 不把多模型共识当成证据。
- 不把 Chroma/外部 memory runtime 作为 source of truth。

## Success criteria

- old top dirs are gone or mapped。
- new top dirs all have direct MOCs。
- path wikilinks rewritten。
- self-check PASS。
- brainctl sync/reindex/search PASS。
- scoped local commit completed。

中文检索别名：本地大脑主层级迁移 项目 主层级完成 P10 control-plane layout 无遗留
