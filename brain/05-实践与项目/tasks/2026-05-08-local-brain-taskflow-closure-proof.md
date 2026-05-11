---
type: task
layer: L3
status: done
priority: P0
created: 2026-05-08T16:47:43+08:00
updated: 2026-05-08T22:38:24+08:00
expires_at: 2026-06-08T00:00:00+08:00
project: local-brain-taskflow
workflow_contract: local-brain-task-orchestration + ratification-gate-pattern
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: ~/.hermes/scripts
evidence:
  - command: python3 ~/.hermes/scripts/test_brain_task_orchestrator.py PASS
  - command: python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json PASS
  - command: python3 ~/.hermes/scripts/brain_task_dispatch_tick.py --print-always OK
  - file:/Users/charles/Documents/brain/06-治理与评审/reviews/2026-05-08-local-brain-taskflow-closure-certification.json
  - artifact:/Users/charles/.hermes/tick-20260508-084332/
concepts: [taskflow-closure, proof-gate, no-agent-cron, skill-route-matrix]
---

# Local-brain Taskflow Closure Proof

## Objective

补齐任务池长期闭环 P0/P1：reconcile、structured proof gate、safe dispatch tick、派生视图、cron、技能路由矩阵接入，并完成多模型复核。

## Acceptance Criteria

- [x] `reconcile` handles expired/stale/due retry tasks.
- [x] `done` requires structured evidence.
- [x] `proof-check` fails missing/unstructured done evidence and accepts legacy body evidence only as warning.
- [x] `brain_task_dispatch_tick.py` does not execute task content and does not mark done.
- [x] no_agent cron `local-brain-task-dispatch-safe-tick` is scheduled.
- [x] `Agent技能树路由矩阵` contains task-pool closure and external GitHub project analysis routes.
- [x] deterministic tests and brainctl search proof pass.
- [x] T1 multi-model scoped certification exists.

## Proof Log

- 2026-05-08T16:35:01+08:00: first tick exposed two issues: inbox parser ingested fenced/comment examples; proof-check failed legacy done task without frontmatter evidence.
- 2026-05-08T16:40:57+08:00: fixed parser to only ingest real `Inbox Drafts` items and skip code fences / HTML comments; cleaned accidental sample tasks after project-wide reference scan.
- 2026-05-08T16:41:57+08:00: deterministic gates passed: py_compile, unit test, selfcheck, proof-check, safe dispatch tick, symphony selfcheck, brainctl sync/reindex/search.
- 2026-05-08T16:43:32+08:00: T1 multi-model discussion certified scoped closure in `/Users/charles/.hermes/tick-20260508-084332/`.
- 2026-05-08T16:47:43+08:00: review/certification/evolution artifacts written back to local brain.

## Final Handoff

- Status: done / certified for taskflow closure infrastructure.
- Next dispatchable task: [[05-实践与项目/tasks/2026-05-08-多模型分析-simular-ai-agent-s-并完善-hermes-技能树]].
- Residual risk: Agent-S analysis is intentionally separate pending work; not part of this closure certification.

- 2026-05-08T22:38:24+08:00: Reconcile action `orphan_claim_metadata_cleared` by `lifecycle-audit`. Previous status `done`.
