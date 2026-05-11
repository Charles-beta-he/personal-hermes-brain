---
type: task
lane: work
layer: 05-实践与项目
status: pending
priority: P1
created: 2026-05-10T16:24:53+08:00
updated: 2026-05-11T23:29:37+08:00
expires_at: 2026-05-24T16:24:53+08:00
project: uvisa-app-2.0-work
architecture_target:
capability_delta:
anti_drift_check:
acceptance_evidence:
workflow_contract: "work/product delivery: user explicitly allows temporary hardcoded fake data for this U-VISA page; keep scope narrow; restore original UI style; do not delete features/routes/buttons/fields; do not hide backend drift as final truth; mark fake data as temporary/test-only; verify mobile UI; run relevant tests + pnpm run build; update UI_TEST_CASES; commit locally only; no push"
claimed_by:
claim_expires_at:
run_id:
retry_count: 0
next_attempt_at:
workspace: /Users/charles/Desktop/folder/work/uvisa-app-2.0
evidence:
  - /Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/evidence/screenshots/uvisa-card-home-restore-original-ui-hardcoded-data-20260510-162453.jpg
  - /Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/evidence/screenshots/uvisa-card-home-restore-original-ui-hardcoded-data-20260510-162453.json
  - /Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/Workpad - uvisa-app-2.0.md
concepts: ["work-task", "uvisa", "uvisa-app-2.0", "ui-restore", "uvisa-card", "hardcoded-fake-data", "test-forward-page", "visual-regression", "mobile-h5", "temporary-mock"]
---

# Task - 恢复 uvisa-app-2.0 U-VISA 页面原有 UI 样式并暂用硬编码假数据

## Objective

根据用户截图与指令：U-VISA 页面因测试前置测试页而默认展示“待激活/暂无实体卡/暂无卡片交易”空状态，需要恢复原有 U-VISA 首页/卡片页 UI 样式；当前阶段暂时使用硬编码假数据展示卡片、余额、操作入口和最近交易，后续再接回真实接口。

## Source Artifact / Screenshot Evidence

- 原始 Lark 本地图片路径：`/Users/charles/Library/Containers/com.larksuite.macos.lark/Data/Library/Application Support/LarkInternational/sdk_storage/f860a8b25f5ba958f164d39bf7fed0f5/resources/images/img_v3_0211i_af3618be-ec53-4bd0-8a3a-cafc5b50f7hu.jpg`
- 已复制到 canonical brain evidence：`/Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/evidence/screenshots/uvisa-card-home-restore-original-ui-hardcoded-data-20260510-162453.jpg`
- 元数据：`/Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/evidence/screenshots/uvisa-card-home-restore-original-ui-hardcoded-data-20260510-162453.json`
- sha256：`584f0dabbef2f7aa0cefda0ce0a4a1b19e0b059877dff6f11602311a3d1d0b45`

## User Instruction

用户明确说明：这个页面因为测试想前置测试页面，需要恢复至原有 UI 样式，暂时使用硬编码假数据。

边界解释：允许“暂时硬编码假数据”仅限本页面 UI 恢复/测试前置目的；不得把假数据当作真实后端闭环，不得用它掩盖 mock/real backend 漂移；任务完成时必须在 docs/UI_TEST_CASES.md 或任务 note 中留下后续接回真实接口/移除硬编码的 TODO。

## Screenshot-derived Problem Statement

截图显示 U-VISA Tab 当前选中，页面主体为两张简化白色卡片：

- 第一张显示 `待激活`、`暂无实体卡`，并提示理财顾问线下交付后激活实体 U-Visa 卡，真实卡片存在前充值/提现/冻结/CVV/限额操作不可用；按钮为 `联系顾问`。
- 第二张为 `最近交易`，内容为 `暂无卡片交易`。
- 底部 Tab 为 `资产 / U-VISA / 财富 / 我的`，其中 `U-VISA` 蓝色选中。

异常现象：当前默认页面像测试用前置空状态/无卡状态，不是原有 U-VISA 首页完整 UI；缺少原有卡片卡面、余额/状态、功能入口、交易列表等视觉与数据。

## Restore Target

- 恢复 U-VISA 首页/卡片首页原有视觉样式。
- 默认展示“有实体卡/正常卡片”样式，用硬编码假数据填充。
- 假数据建议覆盖：卡片状态、卡号尾号、持卡人/有效期、余额、充值/提现/冻结/CVV/限额入口、最近交易列表。
- 现有 `待激活/暂无实体卡` 状态保留为条件分支或测试开关，不作为默认 U-VISA Tab UI，不删除功能。
- 若找不到“原有 UI”实现，需要从 git 历史、已有组件、UI_TEST_CASES、历史截图/报告中恢复，不凭空重画。

## Execution Notes

- 先按 Workpad section 12 boot：读 repo 状态、`docs/UI_TEST_CASES.md`、`docs/PRODUCT_USER_LOGIC_TEST_CASES.md`、ADR。
- 优先定位 U-VISA Tab 路由/组件，可能是 Card/U-VISA 首页相关组件。
- 先查 git 历史中该页面原样式，恢复已有实现优先；不要用删除空状态逻辑的方式制造 PASS。
- 临时硬编码数据应集中在清晰命名的 mock/fake data 常量中，写明 TODO/测试前置原因，避免散落魔法值。
- 验收包含 375/390 移动视口、底部 Tab 不遮挡、console/pageerror/API non-2xx 记录、build/test。

## Acceptance Criteria

- [ ] 1) 定位截图对应路由/组件；2) 默认 U-VISA Tab 恢复原有有卡片 UI 样式，不再默认显示测试前置空状态；3) 使用明确标记的临时硬编码假数据展示卡片信息、余额/状态、功能入口、最近交易；4) 待激活/无卡空状态保留为条件分支或测试开关，不删除；5) 375/390 移动视口底部 Tab 与主体无遮挡/溢出；6) 相关单测/Playwright 或 browser-harness 通过，pnpm run build 通过；7) docs/UI_TEST_CASES.md 与任务 note 记录临时假数据边界和后续移除/接接口事项。

## Plan / Workpad

- [ ] Reconcile current state before execution.
- [ ] Execute the smallest verifiable slice.
- [ ] Record proof and update status.

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| brain_task_orchestrator list | pending | |

## Proof Log

- 2026-05-10T16:24:53+08:00: Added screenshot evidence, user instruction boundary, restore target, hardcoded-data caveat, and execution notes for taskpool auto-completer.
- 2026-05-10T16:24:53+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-11T00:42:51+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T01:39:48+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: deadlock_fix_release

- 2026-05-11T17:54:59+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T18:58:40+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-11T20:02:09+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T20:06:48+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: orphan_worker_cleaned_after_manual_agent_cycle_timeout

- 2026-05-11T21:15:31+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T22:18:40+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-11T22:27:32+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T23:29:37+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup
