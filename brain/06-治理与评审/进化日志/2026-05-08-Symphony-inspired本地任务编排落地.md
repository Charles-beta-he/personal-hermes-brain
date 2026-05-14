---
type: evolution-log
layer: L6
status: active
created: 2026-05-08T00:06:02+08:00
concepts: [evolution, symphony-inspired, task-control-plane]
---

# 2026-05-08 Symphony-inspired 本地任务编排落地

## Event

OpenAI Symphony 的任务编排思想被翻译为 Hermes/local-brain 原生方案。

## What Changed

- 新增 project/P10/P9 本地大脑项目包。
- 新增 playbook：reconcile -> claim -> execute -> verify -> proof -> release。
- 新增 task note template 与 workflow contract template。
- 新增 derived dashboard 规范。
- 新增 multi-model selfcheck review 与 task proof ledger。
- 新增 durable atom：任务队列是 canonical Markdown 的派生视图。

## Why It Matters

这把“待完成任务规划”从静态 backlog 推进为可维护控制面：任务有生命周期、lease、防重复、重试、证据、过期和 dashboard，同时避免 Linear/Symphony 成为第二事实源。

## Evidence Links

- [[05-实践与项目/projects/symphony-inspired-local-task-orchestrator/Project - Symphony-inspired Local Task Orchestrator]]
- [[05-实践与项目/实践方案/11-Symphony-inspired本地任务编排Playbook]]
- [[06-治理与评审/reviews/2026-05-08-symphony-inspired-task-orchestrator-multimodel-selfcheck]]
- [[05-实践与项目/tasks/2026-05-08-symphony-inspired-task-orchestrator-landing-log]]

## Certification Caveat

Prior multi-model fanout is not full ratification. Final completion depends on deterministic self-check, sync/reindex/search, post-landing model issue ledger, and scoped local commit.

## Evidence Boundary

Model agreement is provenance only; status promotion requires command/file/search proof recorded in this note or linked artifacts.

