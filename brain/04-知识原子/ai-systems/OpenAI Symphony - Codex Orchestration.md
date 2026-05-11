---
type: ai-system-note
layer: L1
status: active
created: 2026-05-08T00:06:02+08:00
source_repo: https://github.com/openai/symphony
source_commit: 58cf97da06d556c019ccea20c67f4f77da124bf3
concepts: [openai-symphony, codex-orchestration, linear, agent-runner]
---

# OpenAI Symphony - Codex Orchestration

## Summary

OpenAI Symphony is a preview service/spec for turning tracker work into isolated autonomous coding-agent runs. It polls Linear, creates per-issue workspaces, launches Codex app-server, tracks retries/reconciliation, and exposes observability.

## Useful Concepts for Local Brain

- Repository-owned workflow contract (`WORKFLOW.md`).
- Internal orchestration state: claimed/running/retry/released.
- Bounded concurrency and candidate selection.
- Reconciliation before dispatch.
- Exponential retry/backoff and stall detection.
- Per-issue workspace isolation.
- Observability-only dashboard/API.

## Adoption Decision

Selective extraction only. Do not adopt Symphony runtime as local-brain control plane. For this user, Markdown in `~/Documents/brain` remains canonical.

## Risks

- Preview/prototype software.
- Linear/Codex runtime lock-in.
- Arbitrary trusted hooks.
- Safety posture is deployment-specific.
- Does not solve Chinese local-brain retrieval or knowledge hierarchy design.

## Related

- [[04-知识原子/atoms/task-queue-is-derived-from-canonical-markdown]]
- [[05-实践与项目/projects/symphony-inspired-local-task-orchestrator/Project - Symphony-inspired Local Task Orchestrator]]
