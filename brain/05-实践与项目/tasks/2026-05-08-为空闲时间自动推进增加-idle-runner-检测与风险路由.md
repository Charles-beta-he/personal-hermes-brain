---
type: task
layer: L3
status: done
priority: P1
created: 2026-05-08T17:09:35+08:00
updated: 2026-05-11T08:52:19+08:00
expires_at: 2026-06-07T17:09:35+08:00
project: local-brain-task-orchestration
workflow_contract: idle-runner-design + risk-gated autonomous execution + proof-check structured evidence
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 1
next_attempt_at: 
workspace: 
evidence:
  - file:/Users/charles/.hermes/scripts/brain_task_idle_runner.py
  - file:/Users/charles/.hermes/scripts/test_brain_task_idle_runner.py
  - file:/Users/charles/.hermes/scripts/brain_task_orchestrator.py
  - file:/Users/charles/.hermes/scripts/test_brain_task_orchestrator.py
  - file:/Users/charles/.hermes/tick-20260511-004637/discussion_result.json
  - file:/Users/charles/.hermes/tick-20260511-004637/final/certification_manifest.json
concepts: ["idle-runner", "task-pool", "autonomous-execution", "risk-routing", "control-plane"]
multimodel_status: certified
multimodel_ratification_artifact: file:/Users/charles/.hermes/tick-20260511-004637/discussion_result.json
---

# Task - 为空闲时间自动推进增加 idle-runner 检测与风险路由

## Objective

在现有本地大脑任务池安全控制面之上，新增空闲时间检测与风险路由设计/最小落地：先只检测不执行，明确 idle_decision、budget、claim lease、kill switch、execution_mode、blocked_by DAG 边界，再决定是否进入只读/低风险自动执行。

## Acceptance Criteria

- [x] 产出 idle-runner 设计审计与实现计划；补充任务 frontmatter 字段 risk/execution_mode/blocked_by 的判定规则；新增或更新安全 tick/idle detector 的最小脚本或文档；验证不会自动执行高风险任务；brain_task_orchestrator selfcheck/proof-check、brainctl sync/reindex/search 通过；必要时多模型 ratification。

## Plan / Workpad

- [x] Reconcile current state before execution.
- [x] Execute the smallest verifiable slice.
- [x] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| `python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/brain_task_idle_runner.py ~/.hermes/scripts/test_brain_task_orchestrator.py ~/.hermes/scripts/test_brain_task_idle_runner.py` | PASS | `/tmp/idle-*` run bundle, 2026-05-11 |
| `python3 ~/.hermes/scripts/test_brain_task_idle_runner.py` | PASS | `/tmp/idle-test-idle-runner.log` |
| `python3 ~/.hermes/scripts/test_brain_task_orchestrator.py` | PASS | `/tmp/idle-test-orchestrator.log` |
| `python3 ~/.hermes/scripts/test_brain_task_dispatch_tick.py` | PASS | `/tmp/idle-test-dispatch.log` |
| `python3 ~/.hermes/scripts/skill-steward.py --graph-check --json` | OK | `/tmp/idle-skill-graph.json` |
| `python3 ~/.hermes/scripts/brain_task_idle_runner.py --json --write-state` | OK / observe_only | `/tmp/idle-runner-current.json`; `active_count=2`, deny reasons include `idle_runner_disabled` and `active_lease_or_running_task_present` |
| `python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json` | PASS | `/tmp/idle-selfcheck.json` |
| `python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json` | PASS | `/tmp/idle-proof-check.json` |
| `python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write --json` | OK | `/tmp/idle-dashboard.json` |
| `python3 ~/.hermes/scripts/brainctl.py --json sync && reindex && search brain_task_idle_runner` | PASS | sync pulled 5; reindex `indexed_blocks=2818`; search hits=3 |
| `consult_models.py run /tmp/idle-runner-ratification-state.json --tier T3 --quorum 4 --discussion --max-rounds 2 --keep` | CERTIFIED | `/Users/charles/.hermes/tick-20260511-004637/discussion_result.json`; manifest `can_claim_complete_certification=true` |

## Proof Log

- 2026-05-08T17:09:35+08:00: Task created from local-brain control point.
- 2026-05-11T08:50:56+08:00: Bounded auto-executor verified idle-runner implementation and added ratification-gate hardening for exact four-model participant identity plus PUA-loop proof fields. Deterministic gates passed; T3 four-model discussion certified 5/5 claims with evidence coverage 1.0. Artifact: `/Users/charles/.hermes/tick-20260511-004637/final/certification_manifest.json`.

## Blockers / Confusions

- None.

## Final Handoff

- Status: Completed bounded slice; ready for proof-gated close.
- Evidence: `file:/Users/charles/.hermes/tick-20260511-004637/final/certification_manifest.json`; `file:/Users/charles/.hermes/tick-20260511-004637/discussion_result.json`; `/tmp/idle-*` deterministic validation logs.
- Residual risk: No automatic task execution enabled; idle-runner remains observe-only/default disabled. Provider quota evidence in ratification is unobservable for some providers, so certification scope is implementation/risk-router correctness, not autonomous budget-handoff readiness.

- 2026-05-09T11:27:29+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-pua-loop`. Reason: pua-loop full-line multi-model push

- 2026-05-09T11:28:10+08:00: Lifecycle transition `claimed` -> `running` by `hermes-pua-loop`. Reason: begin round-1 full-line execution

- 2026-05-09T15:32:52+08:00: Reconcile action `stale_running_retry` by `hermes-reconcile`. Previous status `running`.

- 2026-05-09T16:50:07+08:00: Reconcile action `retry_due_promoted` by `hermes-reconcile`. Previous status `retry`.

- 2026-05-10T23:42:02+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 3 parallel dispatch

- 2026-05-11T01:35:39+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: stale_claim_cleanup_ttl_expired

- 2026-05-11T08:38:42+08:00: Lifecycle transition `pending` -> `claimed` by `hermes-taskpool-auto`.

- 2026-05-11T08:52:19+08:00: Lifecycle transition `claimed` -> `running` by `hermes-taskpool-auto`. Reason: begin proof-gated closeout for verified bounded slice

- 2026-05-11T08:52:19+08:00: Lifecycle transition `running` -> `review` by `hermes-taskpool-auto`. Reason: deterministic gates and T3 ratification passed Evidence: file:/Users/charles/.hermes/tick-20260511-004637/final/certification_manifest.json

- 2026-05-11T08:52:19+08:00: Lifecycle transition `review` -> `done` by `hermes-taskpool-auto`. Reason: proof-gated close: idle-runner observe-only/risk router and ratification-gate hardening certified Evidence: file:/Users/charles/.hermes/tick-20260511-004637/final/certification_manifest.json
