---
type: atom
layer: L1
status: active
created: 2026-05-08T00:06:02+08:00
concepts: [canonical-markdown, derived-queue, source-of-truth, task-orchestration]
---

# Task queue is derived from canonical Markdown

## Claim

本地大脑里的任务队列、运行态 dashboard、外部 tracker mirror、agent dispatch list 都必须是 `~/Documents/brain` Markdown task notes 的派生视图；它们可以被重建，不能反过来成为事实源。

## Why

OpenAI Symphony 展示了 tracker-driven agent orchestration 的价值，但它的默认事实源是 Linear。对当前本地大脑，canonical truth 已经是 Obsidian Markdown P10 hierarchy。整体迁移到外部 tracker 会制造第二事实源和 ghost state。

## Operational Rule

- Task truth: `05-实践与项目/tasks/*.md` frontmatter + body workpad.
- Project context: `05-实践与项目/projects/<project>/`.
- Evidence: `02-证据与原文/` or task proof links.
- Dashboard/index/queue: derived, rebuildable, safe to delete/regenerate.

## Related

- [[05-实践与项目/projects/symphony-inspired-local-task-orchestrator/Project - Symphony-inspired Local Task Orchestrator]]
- [[07-仪表盘/待完成任务运行态]]
- [[08-模板/local-brain-task-note-template]]
