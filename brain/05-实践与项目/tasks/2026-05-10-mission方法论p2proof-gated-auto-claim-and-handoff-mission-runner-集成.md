---
type: task
lane: evolution
layer: L3
status: done
priority: P2
created: 2026-05-10T18:23:40+08:00
updated: 2026-05-10T20:00:53+08:00
expires_at: 2026-06-09T18:23:40+08:00
project: Hermes-local-brain
architecture_target: taskpool
capability_delta: 把 Mission ready 节点接入默认关闭的 auto-claim-and-handoff；输出 bounded handoff/run log/proof head；遇到 ask-human/permission gate 暂停而非继续执行
anti_drift_check: HERMES_LOCAL_BRAIN_AUTORUN 未开启或 allowlist 为空时 deny；绝不直接执行 Markdown body；runner error 只能 release/retry/review，不能 done；done 必须 proof-chain + review gate
acceptance_evidence: autorun off/allowlist empty/permission pending/runner error/proof-chain broken 全部 fail-closed 测试；auto-claim-and-handoff 写入 handoff 与 proof head；proof-check/lifecycle/selfcheck PASS
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - file:/tmp/missions-taskpool-mm-state.json
  - file:/tmp/missions-task-planning-mm-state.json
  - artifact:tick-20260510-102004/merged_plan.json (historical advisory provenance; source file GC'd)
  - artifact:tick-20260510-101903/merged_plan.json (historical advisory provenance; source file GC'd)
  - "command: autorun-runner permission pause regression PASS"
  - "command: default-off autorun-runner denied no-claim PASS"
  - artifact:proof-gated-autorun-runner-implementation
concepts: ["missions", "autorun", "auto-claim-and-handoff", "permission-gate", "proof-chain", "runner"]
---

# Task - Mission方法论P2：proof-gated auto-claim-and-handoff Mission runner 集成

## Objective

让 Mission 能安全进入自动化执行桥：只 claim+handoff，不把任务 Markdown 当脚本，也不绕过 proof review。

补充安全边界：handoff bundle 是数据，不是脚本；worker/tick 不能直接置 `done`；permission/ask-human gate 必须暂停到 `blocked`/`review` 并写明 unblock condition；最终完成只走 proof-check + review gate。

## Acceptance Criteria

- [x] 默认关闭安全；开启后只处理 allowlist ready node；权限/人审 gate 暂停；proof-gated review 才可 done。

## Plan / Workpad

- [x] Reconcile current state before execution.
- [x] Execute the smallest verifiable slice.
- [x] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| python3 ~/.hermes/scripts/test_brain_task_orchestrator.py | PASS | command: regression suite includes mission DAG dashboard + autorun-runner permission pause |
| python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/test_brain_task_orchestrator.py | PASS | command: py_compile PASS |
| python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json | PASS | command: real vault selfcheck PASS |
| python3 ~/.hermes/scripts/brain_task_orchestrator.py boundary-check --json | PASS | command: real vault boundary-check PASS |
| python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --include-active --json | PASS | command: proof-check PASS; only legacy body-evidence warnings |
| python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write --json | PASS | command: dashboard regenerated with Mission DAG Progress section |
| python3 ~/.hermes/scripts/brain_task_orchestrator.py autorun-runner --json | PASS | command: default-off denied; no claim/no execution |


## Proof Log

- 2026-05-10T18:23:40+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status: implemented and closing through lifecycle gates.
- Evidence: autorun-runner command, permission_gate_pending pause, default-off/allowlist/write-guard proof-gated claim+handoff path landed; no Markdown execution/no auto done.
- Residual risk: live multi-model T3 discussion was not rerun for this final patch; deterministic gates are PASS. MiMo provider remains a separate adapter issue for full four-model certification.

## Multi-model Missions synthesis

Status: truth-grounded advisory, not patch-level certification.

Artifacts:
- State: `/tmp/missions-taskpool-mm-state.json`
- Tick: `/Users/charles/.hermes/tick-20260510-102004/`
- Merged plan: `/Users/charles/.hermes/tick-20260510-102004/merged_plan.json`
- Source repo reference: `rowboatlabs/rowboat` cloned at `/tmp/rowboat-missions`, commit `10995ebed69f56db899619b8636c8c14b5f9b6cb`

Consensus summary:
- Truth gate grounded 4/4 claims: current Hermes taskpool has lifecycle primitives; Rowboat contributes local-first KG/run/permission/scheduled-agent patterns; safe Missions landing is envelope + DAG + proof/permission gates, not direct Markdown execution.
- Planner consensus was dissent/low score because planners named patches differently, but all useful concrete proposals converged on P0 envelope, P1 DAG/router/dashboard, P2 proof-gated autorun/handoff, plus local-first artifacts.
- Therefore this task is an executable taskpool landing slice, not a claim that implementation is already certified.

Mission rules to preserve:
- Mission notes are data/workpads, not scripts.
- Safe dispatch, claim/handoff, executor, and proof-gated completion remain separate stages.
- Evolution Missions must not starve work/product P0/P1 tasks.
- Canonical source is `~/Documents/brain`; SQLite/FTS/dashboard are derived caches.

## Implementation notes

This is intentionally P2 because it touches automation/write surfaces. It must reuse the existing `auto-claim-and-handoff` pattern rather than creating a new executor path.

Smallest safe slice:
1. Default-off mission autorun flag.
2. Allowlist-gated claim of exactly one ready mission node.
3. Write bounded handoff + proof head, then stop.
4. Pause cleanly on `ask-human` / permission gate states.
5. Require review/proof-chain before any done transition.


- 2026-05-10T20:00:00+08:00: Implementation complete: autorun-runner command, permission_gate_pending pause, default-off/allowlist/write-guard proof-gated claim+handoff path landed; no Markdown execution/no auto done.

- 2026-05-10T20:00:53+08:00: Lifecycle transition `pending` -> `claimed` by `hermes`.

- 2026-05-10T20:00:53+08:00: Lifecycle transition `claimed` -> `running` by `hermes`.

- 2026-05-10T20:00:53+08:00: Lifecycle transition `running` -> `review` by `hermes`. Evidence: command: autorun-runner permission pause regression PASS, command: default-off autorun-runner denied no-claim PASS

- 2026-05-10T20:00:53+08:00: Lifecycle transition `review` -> `done` by `hermes`. Evidence: artifact:proof-gated-autorun-runner-implementation

- 2026-05-12T02:54:25+08:00: Permission taxonomy defaults applied by `permission-migrate --apply`. Changes: {"required_authority": "budget-handoff", "max_authority": "autonomous-execution", "permission_tier": "budget-handoff", "write_surfaces": ["taskpool", "hermes-scripts", "brain"], "completion_gate": "ratification-or-selfcheck-review-done", "lane_semantics": "self-evolution: deterministic gates plus ratification/proof before review->done"}
