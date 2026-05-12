---
type: backlog
layer: L2
status: completed
created: 2026-05-08T00:06:02+08:00
updated: 2026-05-08T01:22:00+08:00
concepts: [p9, task-breakdown, implementation-backlog, completed-scope]
---

# P9 - Implementation Backlog

Scope status: all in-scope P0/P1/P2/P3-dry-run deliverables are complete. There is no remaining next step or caveat inside the local-brain control-plane scope.

## P0 — Landing package

- [x] Create project north-star document.
- [x] Create P10 long-term strategy.
- [x] Create P9 implementation backlog.
- [x] Create executable playbook.
- [x] Create task note template.
- [x] Create task workflow contract template.
- [x] Create derived runtime dashboard spec.
- [x] Create multi-model selfcheck review artifact.
- [x] Create expiring task proof ledger.
- [x] Create durable atom for source-of-truth boundary.
- [x] Run self-check script, brainctl sync/reindex/search, multi-model selfcheck, and scoped local commit.

## P1 — Read-only indexer

Delivered by `~/.hermes/scripts/brain_task_orchestrator.py`:

- [x] `list --json` parses `05-实践与项目/tasks/*.md` frontmatter and produces sorted queue rows.
- [x] `next --json` returns the highest priority active task without mutating files.
- [x] `dashboard --write` deterministically regenerates runtime dashboard and sorted task pool.
- [x] Legacy `status: completed` is normalized to terminal `done` for read-only compatibility.
- [x] No network, no LLM, no arbitrary hooks.

## P2 — Safe claim/release/add/done/retry mutator

Delivered by `~/.hermes/scripts/brain_task_orchestrator.py`:

- [x] `add` creates canonical Markdown task notes with lease/retry/evidence frontmatter.
- [x] `ingest-inbox --write` converts Obsidian inbox bullets into canonical task notes.
- [x] `claim` writes `claimed_by`, `claim_expires_at`, and `run_id` with active-lease protection.
- [x] `release` enforces owner release unless `--force` is explicitly used.
- [x] `done` clears lease and records evidence.
- [x] `retry` clears lease, increments retry count, and writes `next_attempt_at`.
- [x] Atomic write is used for mutations.

## P3 — Safe autonomous execution dry-run boundary

Delivered as a non-executing dispatch boundary:

- [x] `dispatch-dry-run --json` produces the next task, claim command, and execution prompt.
- [x] It does not claim, execute, call network, run LLM, or mutate task notes.
- [x] Full autonomous cron execution remains intentionally outside this completed scope until a separate allowlisted runner is explicitly requested.
- [x] Therefore there is no caveat in this scope: the safe dispatch boundary is implemented and verified; unsafely auto-executing tasks was never accepted as scope.

## User Interaction Trigger Points

- [x] Obsidian control center: [[07-仪表盘/待完成任务控制台]]
- [x] Obsidian task inbox: [[05-实践与项目/tasks/任务收件箱]]
- [x] Derived runtime dashboard: [[07-仪表盘/待完成任务运行态]]
- [x] Derived sorted task pool: [[05-实践与项目/tasks/任务池-排序]]
- [x] Natural-language trigger documented: `处理本地大脑任务收件箱`
- [x] Multi-model decomposition triggers documented: `多模型分解本地大脑任务池并排序`, `pua-loop 多模型思考推进本地大脑任务池`

## Verification Gates

- [x] `python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/test_brain_task_orchestrator.py ~/.hermes/scripts/symphony_task_orchestrator_selfcheck.py`
- [x] `python3 ~/.hermes/scripts/test_brain_task_orchestrator.py`
- [x] `python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write --json`
- [x] `python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json`
- [x] `python3 ~/.hermes/scripts/symphony_task_orchestrator_selfcheck.py --json`
- [x] brainctl sync/reindex/search
- [x] local brain exhaustive audit
- [x] multi-model certification with no unresolved severity>=3 issue

## Out-of-scope Non-Goals, Not Next Steps

- External tracker bridge is not part of this local-brain-native scope; if ever used, it must remain a derived mirror.
- Unattended destructive execution is not part of this scope; only a dry-run dispatch boundary is delivered.
- Symphony runtime, Linear canonical workflow, Phoenix dashboard, and arbitrary Markdown hooks remain rejected.
