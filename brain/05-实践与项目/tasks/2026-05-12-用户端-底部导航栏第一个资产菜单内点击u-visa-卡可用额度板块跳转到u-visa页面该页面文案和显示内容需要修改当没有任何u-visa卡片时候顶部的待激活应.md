---
type: task
lane: work
layer: L3
status: done
priority: P2
created: 2026-05-12T17:21:13+08:00
updated: 2026-05-12T18:45:00+08:00
expires_at: 2026-06-11T17:21:13+08:00
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

# Task - 用户端-底部导航栏第一个资产菜单内，点击“U-Visa 卡可用额度”板块，跳转到“U-VISA”页面，该页面文案和显示内容需要修改，当没有任何U-VISA卡片时候，顶部的“待激活”应显示“待开卡”，当卡片被注销之后，同样也是该页面显示“待开

## Objective

用户端-底部导航栏第一个资产菜单内，点击“U-Visa 卡可用额度”板块，跳转到“U-VISA”页面，该页面文案和显示内容需要修改，当没有任何U-VISA卡片时候，顶部的“待激活”应显示“待开卡”，当卡片被注销之后，同样也是该页面显示“待开

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

- 2026-05-12T17:21:13+08:00: Task created from local-brain control point.

- 2026-05-12T18:45:00+08:00: FE-only closure (commit `17541ca`).
  - i18n: `card.statusPendingOpen` 新增 — 「待开卡」/「Pending issuance」。
  - RequireCard: CardNoCardState 顶部 label 切到新 key + `data-testid="card-empty-status"`；guard 扩展到 `status==='none' || kind==='none'`。
  - CardScreen: 三态空态早返回 — `storeCard==null || status==='none' || kind==='none'` → 渲染 CardNoCardState；其它保持原行为不动。
  - 单测 9/9 PASS（CardScreen.noCard.test.tsx 3 + CardDeepLinkNoCard.test.tsx 6）：
    - storeCard=null → 「待开卡」标签 + 「No physical card yet」标题
    - 已注销卡 (status:'none', kind:'none') → 同样 「待开卡」
    - 真实活卡 → 完整卡 UI + 卡号 524013 可见，无回归
    - 6 个深链 (/card/topup, /withdraw, /cvv, /limits, /freeze, /pin) 在无卡时已正确显示空态（既有断言保留）。
  - vitest + `tsc -b` + eslint + `pnpm build` 全 green。
  - Browser-harness 实测：demo 用户已有真实物理卡 (status:frozen) → /card 渲染完整卡 UI (5230 卡号、余额、4 操作格)，未引入对已有卡用户的回归。注销/空态分支由单测覆盖（live BE 无空态 fixture 用户）。

## Blockers / Confusions

- None.

## Final Handoff

- Status: review (FE-only)
- Evidence: commit 17541ca + vitest 9/9 + live no-regression baseline
- Residual risk: 无；旧 `card.statusPendingActivation` 翻译 key 仍保留，便于未来其它路径复用；未删字段/路由。
