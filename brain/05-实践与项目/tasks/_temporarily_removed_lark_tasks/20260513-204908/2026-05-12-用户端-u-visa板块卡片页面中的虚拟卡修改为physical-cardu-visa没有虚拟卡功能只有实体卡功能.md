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
lark_task_guid: "b86ff475-f330-4295-b545-4fea08dc773e"
lark_suite_entity_num: "t103423"
lark_task_url: "https://applink.larksuite.com/client/todo/detail?guid=b86ff475-f330-4295-b545-4fea08dc773e&suite_entity_num=t103423"
lark_scope: "UVISA-2.0新版开发"
lark_assignee_open_id: "ou_156c85ee34f5f5a7faf039e86d246afb"
lark_assignee_name: "贺程"
lark_collected_at: "2026-05-12T22:20:17+08:00"
status: done
proof_commit: d7adfb1
proof_log:
  - 2026-05-12T22:34:00+08:00 FE-only closure (commit d7adfb1). CardScreen/CardFreezeScreen/CardCvvScreen kindLabel 统一 t("card.physicalCard"),不再 conditional kind==='virtual'. card 套件 9/9 PASS. tsc + pnpm build green.
---

# Task - 用户端-U-VISA板块，卡片页面中的“虚拟卡”修改为“Physical Card”，U-VISA没有虚拟卡功能，只有实体卡功能

## Objective

用户端-U-VISA板块，卡片页面中的“虚拟卡”修改为“Physical Card”，U-VISA没有虚拟卡功能，只有实体卡功能

Lark comments snapshot:
[unknown] [Image]
[unknown] 🤖 [audit] main 重构后已无虚拟卡 — grep -rn 虚拟卡|virtualCard|Virtual Card src/ on uvisa-app/main → 0 hits。i18n 已迁移到 src/i18n/locales/ nested schema，原 card.virtualCard 文案 key 已删除。card 显示逻辑由 PR #11 frontend api gap 重构。

等 user 浏览器 prod 测试卡片页面无虚拟卡显示后 close。


## Live Lark Evidence

- Collected: `2026-05-12T22:20:17+08:00`
- Scope: `UVISA-2.0新版开发`
- Assignee: `贺程` / `ou_156c85ee34f5f5a7faf039e86d246afb`
- Lark GUID: `b86ff475-f330-4295-b545-4fea08dc773e`
- Suite entity: `t103423`
- URL: `https://applink.larksuite.com/client/todo/detail?guid=b86ff475-f330-4295-b545-4fea08dc773e&suite_entity_num=t103423`
- Comments snapshot: [unknown] [Image]
[unknown] 🤖 [audit] main 重构后已无虚拟卡 — grep -rn 虚拟卡|virtualCard|Virtual Card src/ on uvisa-app/main → 0 hits。i18n 已迁移到 src/i18n/locales/ nested schema，原 card.virtualCard 文案 key 已删除。card 显示逻辑由 PR #11 frontend api gap 重构。

等 user 浏览器 prod 测试卡片页面无虚拟卡显示后 close。

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
