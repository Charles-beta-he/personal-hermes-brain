---
type: task
lane: work
layer: L3
status: pending
priority: P2
created: 2026-05-12T22:20:17+08:00
updated: 2026-05-12T22:20:17+08:00
expires_at: 2026-06-11T22:20:17+08:00
project: uvisa-app-2.0-work
architecture_target: 
capability_delta: 
anti_drift_check: 
acceptance_evidence: 
workflow_contract: [[08-模板/task-workflow-contract-template]]
required_authority: autonomous-execution
max_authority: yolo-execution
permission_tier: autonomous-execution
write_surfaces: ["taskpool", "codebase"]
completion_gate: project-evidence-review-done
lane_semantics: "work/product delivery: project evidence, tests/build, scoped commit, report/push policy as required"
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence: []
concepts: ["task"]
lark_task_guid: "625423d8-8381-4297-a29e-005b6b4c62c8"
lark_suite_entity_num: "t103436"
lark_task_url: "https://applink.larksuite.com/client/todo/detail?guid=625423d8-8381-4297-a29e-005b6b4c62c8&suite_entity_num=t103436"
lark_scope: "UVISA-2.0新版开发"
lark_assignee_open_id: "ou_156c85ee34f5f5a7faf039e86d246afb"
lark_assignee_name: "贺程"
lark_collected_at: "2026-05-12T22:20:17+08:00"
status: done
proof_commit: 08e1de7
proof_log:
  - 2026-05-13T00:08:00+08:00 FE-only. HomeScreen 法币钱包 CNY 行接入 platformConfigService.getTopup().domesticCnyTransferEnabled, fail-open default true. 单测 3/3 PASS (enabled/disabled/fail-open), home 套件 25/25 PASS.
---

# Task - 用户端-资产页面，法币钱包内的CNY接口是跟随admin后台管理内的“用户端运营配置”选项页面的“境内 CNY 转账入口启用”这个按钮的勾选来决定展示或者不展示，勾选就是正常展示法币钱包内的CNY通道，不勾选就是法币钱包内的CNY通道会自动隐藏掉，这里是跟随后台配置变化，当前未跟随后台配置变化。

## Objective

用户端-资产页面，法币钱包内的CNY接口是跟随admin后台管理内的“用户端运营配置”选项页面的“境内 CNY 转账入口启用”这个按钮的勾选来决定展示或者不展示，勾选就是正常展示法币钱包内的CNY通道，不勾选就是法币钱包内的CNY通道会自动隐藏掉，这里是跟随后台配置变化，当前未跟随后台配置变化。

Lark comments snapshot:
[unknown] [Image]


## Live Lark Evidence

- Collected: `2026-05-12T22:20:17+08:00`
- Scope: `UVISA-2.0新版开发`
- Assignee: `贺程` / `ou_156c85ee34f5f5a7faf039e86d246afb`
- Lark GUID: `625423d8-8381-4297-a29e-005b6b4c62c8`
- Suite entity: `t103436`
- URL: `https://applink.larksuite.com/client/todo/detail?guid=625423d8-8381-4297-a29e-005b6b4c62c8&suite_entity_num=t103436`
- Comments snapshot: [unknown] [Image]

## Closeout Gates

- [ ] Re-read current task/comment evidence before execution; screenshots/comments may contain prototype deltas.
- [ ] Classify FE/BE/contract/infrastructure landing point before coding.
- [ ] Run scoped tests/build and record evidence.
- [ ] Commit scoped changes, follow UVISA push/remote monitor policy, and report result.

## Acceptance Criteria

- [ ] Live Lark assigned task is implemented with current comments/screenshots reviewed, FE/BE landing classified, scoped tests/build evidence recorded, and UVISA closeout policy followed.

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-12T22:20:17+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:
