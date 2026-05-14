---
type: task
lane: work
layer: L3
status: review
priority: P2
created: 2026-05-12T17:21:14+08:00
updated: 2026-05-12T17:21:14+08:00
expires_at: 2026-06-11T17:21:14+08:00
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
---

# Task - 用户端-点击我的，点击收款人管理，点击新增收款人，选择SWIFT国际电汇汇款方式，在收款人信息页面中，“国际银行帐号IBAN”的输入框内未进行特殊字符的校验，已经查过相关国际规定，允许的字符集，大写字母（A-Z）和数字（0-9），不允许空格

## Objective

用户端-点击我的，点击收款人管理，点击新增收款人，选择SWIFT国际电汇汇款方式，在收款人信息页面中，“国际银行帐号IBAN”的输入框内未进行特殊字符的校验，已经查过相关国际规定，允许的字符集，大写字母（A-Z）和数字（0-9），不允许空格

## Acceptance Criteria

- [ ] Observable result is recorded in Proof Log.

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-12T17:21:14+08:00: Task created from local-brain control point.

- 2026-05-12T20:45:00+08:00: FE-only closure (commit `3880249`).
  - Fix: RemitNewSwiftScreen IBAN onChange 实时过滤非 [A-Z0-9] 字符（空格、连字符、斜线、点等）+ 小写自动转大写。
  - 长度 6-34 验证保留在 validateSwiftAccountNumber，提交时继续触发 remit.ibanFormatError 文案。
  - 单测 11/11 PASS（新增 live-strip 断言 + 改写既有 length-overflow 用例）；tsc + eslint + pnpm build 全 green。

## Blockers / Confusions

- None.

## Final Handoff

- Status: review (FE-only)
- Evidence: commit 3880249 + vitest 11/11
- Residual risk: 无；BE 已是大写字母+数字校验。
