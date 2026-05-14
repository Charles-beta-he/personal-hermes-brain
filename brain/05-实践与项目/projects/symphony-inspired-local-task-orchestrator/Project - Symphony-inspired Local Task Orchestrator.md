---
type: project
layer: L2
status: active
created: 2026-05-08T00:06:02+08:00
source_repo: https://github.com/openai/symphony
source_commit: 58cf97da06d556c019ccea20c67f4f77da124bf3
concepts: [symphony-inspired, local-brain-task-orchestrator, markdown-canonical, derived-queue]
---

# Project - Symphony-inspired Local Task Orchestrator

## North Star

把 OpenAI Symphony 的长期任务编排思想翻译成本地大脑原生能力：`~/Documents/brain` Markdown 仍是唯一事实源，待完成任务队列、运行态 dashboard、claim/lease、retry/backoff、reconciliation 都是从 Markdown frontmatter 派生出来的可重建控制面。

## Strategic Decision

Decision: selective extraction, not runtime adoption.

- Adopt: workflow contract, claim/lease state machine, bounded concurrency, retry/backoff, reconciliation tick, persistent workpad, observability-only dashboard.
- Reject: Linear as canonical control plane, Elixir/Phoenix runtime, Codex app-server lock-in, direct arbitrary hooks against the vault.
- Boundary: external tracker/runner can mirror or consume tasks, but cannot become canonical unless a future P10 decision explicitly changes source-of-truth.

## Source Evidence

- Symphony README lines 3-8: project work becomes isolated autonomous implementation runs with proof of work.
- Symphony SPEC lines 18-29: long-running service reads tracker work, creates isolated workspace per issue, runs coding agent, keeps policy in `WORKFLOW.md`, emits observability.
- Symphony SPEC lines 598-799: explicit internal states, claim/running/retry, bounded concurrency, retry/backoff, active-run reconciliation.
- Symphony SPEC lines 1604-1674: trusted-environment/safety caveat, hooks are trusted arbitrary shell scripts, sandbox posture is deployment-specific.
- Local brain index: [[00-索引/00-大脑索引]] defines P10 control-plane hierarchy and [[05-实践与项目/00-实践与项目索引]] owns projects/tasks/playbooks.

## Local Architecture

Contract labels used by the verifier:

- Markdown canonical: `~/Documents/brain` Markdown is the source of truth.
- Derived queue: task queues, dashboards, and tracker mirrors are rebuildable views.

| Layer | Artifact | Role |
|---|---|---|
| L0/L1 | [[04-知识原子/atoms/task-queue-is-derived-from-canonical-markdown]] | Durable principle: queues are derived from canonical Markdown |
| L2 | This project folder | Strategy, backlog, decision history |
| L3 | [[05-实践与项目/tasks/2026-05-08-symphony-inspired-task-orchestrator-landing-log]] | Expiring proof ledger |
| L4 | Hermes skill/process | Operational procedure remains in skills/scripts, not memory |
| L6 | [[06-治理与评审/reviews/2026-05-08-symphony-inspired-task-orchestrator-multimodel-selfcheck]] | Multi-model caveat and issue ledger |
| Dashboard | [[07-仪表盘/待完成任务运行态]] | Derived observability, never canonical |

## Success Criteria

- Required durable artifacts exist and link to each other.
- Task note template has explicit lifecycle fields: `status`, `priority`, `claimed_by`, `claim_expires_at`, `retry_count`, `next_attempt_at`, `workspace`, `evidence`, `expires_at`.
- Workflow contract template defines active/terminal statuses, concurrency, retry/backoff, allowed tools, evidence gates, stop conditions, and hook safety boundaries.
- Dashboard explicitly says it is derived/rebuildable and not source-of-truth.
- Self-check script passes without network or external LLM calls.
- `brainctl sync`, `brainctl reindex`, and search queries can find project/playbook/gate terms.

## Non-goals

- No Linear migration.
- No Symphony daemon install.
- No auto-execution of arbitrary hooks from Markdown.
- No rewrite of the Obsidian hierarchy.
- No claim of full multi-model certification if discussion artifacts time out or truth gate is unsupported.
