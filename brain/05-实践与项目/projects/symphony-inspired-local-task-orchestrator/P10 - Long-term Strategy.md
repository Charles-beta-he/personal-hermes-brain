---
type: strategy
layer: L2
status: active
created: 2026-05-08T00:06:02+08:00
concepts: [p10, task-control-plane, long-term-maintainability, symphony-inspired]
---

# P10 - Long-term Strategy

## Direction

Build a local-brain-native task control plane, not a second task system. The control plane must let Hermes run long autonomous loops without corrupting the brain's hierarchy or creating ghost state.

## Invariants

1. Markdown canonical: task truth lives in `~/Documents/brain/05-实践与项目/tasks/` and project notes.
2. Derived queue: dashboards, indexes, and agent work queues are rebuildable from Markdown frontmatter.
3. Lease before work: any autonomous worker must acquire a claim/lease before changing a task.
4. Reconcile before dispatch: release expired claims and detect stale tasks before starting new work.
5. Evidence before promotion: completed tasks link to evidence/review; WIP never becomes durable Hermes memory.
6. Hooks are allowlisted: workflow contracts can describe hooks, but execution requires explicit allowlist and sandbox policy.
7. Multi-model is a gate for high-risk design, not a substitute for deterministic local checks.

## Phases

### P0 — Durable Planning Package

- Land project, strategy, backlog, playbook, templates, dashboard, review, task log, atom.
- Add self-check script.
- Verify with brainctl and search.

### P1 — Read-only Task Indexer

- Implement `brainctl task list` or standalone prototype that parses task frontmatter.
- Report pending/running/retry/stale without modifying notes.
- Generate dashboard deterministically.

### P2 — Claim/Release Mutator

- Add local-only safe mutations: claim, release, retry, mark blocked.
- Require file-locking or atomic write guard.
- Never mutate files outside `05-实践与项目/tasks/` unless explicitly configured.

### P3 — Controlled Execution Loop

- Cron scans eligible tasks, claims one bounded task, invokes Hermes with task-specific contract, writes proof back.
- High-risk tasks route to T2/T3 multi-model selfcheck before execution.

## Risk Register

| Risk | Severity | Mitigation |
|---|---:|---|
| Second source of truth | 5 | Markdown canonical; queue/dashboard derived only |
| Stale claim ghost | 4 | `claim_expires_at`, reconcile-first tick, stale dashboard |
| Arbitrary hook damage | 5 | Allowlist hooks; no shell execution from note by default |
| Model fanout without truth | 4 | Record fanout as provenance unless ratification/truth gate passes |
| Chinese/English search miss | 3 | Bilingual aliases in every artifact; narrow search verification |
| Overengineering | 3 | P0 docs + selfcheck first; P1 read-only before mutators |

## Stop Condition

This landing is complete when P0 artifacts and self-check pass, brainctl sync/reindex/search observes them, multi-model review has no unresolved severity >=3 blocker, and a scoped local commit records only relevant artifacts.
