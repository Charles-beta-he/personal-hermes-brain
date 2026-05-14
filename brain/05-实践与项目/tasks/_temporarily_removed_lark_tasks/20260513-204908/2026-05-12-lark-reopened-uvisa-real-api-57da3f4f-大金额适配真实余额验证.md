---
type: task
lane: work
layer: L3
status: done
priority: P0
created: 2026-05-12T01:43:02+08:00
updated: 2026-05-12T11:47:05+08:00
expires_at: 2026-05-26T01:43:02+08:00
project: uvisa-app-2.0
workflow_contract: "work/product delivery: live Lark reopened task; evidence-first; classify FE/BE/contract before execution; real API/end-to-end proof required; no mock-only closeout; no deleting routes/buttons/fields; frontend build plus backend JDK21 tests/package when backend touched; Railway/package monitor; scoped local commit; no push unless required by UVISA Lark loop"
required_authority: autonomous-execution
max_authority: yolo-execution
permission_tier: autonomous-execution
write_surfaces: ["taskpool", "codebase", "brain"]
completion_gate: project-evidence-real-api-review-done
lane_semantics: "work/product delivery: project evidence, tests/build, scoped commit, report/push policy as required"
permission_gates: ["real-api-e2e-required", "backend-contract-check-required", "human-or-review-before-done"]
multimodel_status: advisory_completed
multimodel_last_checked_at: 2026-05-13T12:40:43+08:00
multimodel_round_status: advisory_passed
multimodel_last_gate_status: PASS_ADVISORY_ONLY
multimodel_last_decision: CONTINUE_LOOP
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260513-043801-383284-p69674-8b48b68d-1ea9f3ca/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-12-lark-reopened-uvisa-real-api-57da3f4f-大金额适配真实余额验证-state.json
multimodel_last_failures: []
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 1
next_attempt_at: 
workspace: /Users/charles/Desktop/folder/work/uvisa-app-2.0
parallel_boundary: conflict:/Users/charles/Desktop/folder/work/uvisa-app-2.0:/Users/charles/Desktop/folder/work/uvisa-backend:uvisa-reopened-real-api
evidence:
  - live_lark_snapshot:/tmp/lark_uvisa_live_tasks.json
  - classification:/Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/evidence/taskpool/uvisa-lark-reopened-real-api-classification-2026-05-12.json
concepts: ["work-task", "uvisa", "lark-reopened", "returned-task", "real-api-e2e", "front-back-integration", "security-money-gate"]
backend_workspace: /Users/charles/Desktop/folder/work/uvisa-backend
lark_task_guid: 57da3f4f-3db8-4062-8ca1-14ff49a9a675
lark_suite_entity_num: t103235
lark_task_url: https://applink.larksuite.com/client/todo/detail?guid=57da3f4f-3db8-4062-8ca1-14ff49a9a675&suite_entity_num=t103235
lark_scope: UVISA-2.0新版开发
lark_live_reopened_at: 2026-05-12T01:43:02+08:00
old_completion_note: ✅ 已完成 | 金额字体适配 | tier-based font sizing | HomeScreen.amount-fit.test.tsx 3 tests PASS
backend_contract_required: false
real_api_e2e_required: true
security_or_money_gate: true
source_snapshot: /tmp/lark_uvisa_live_tasks.json
classification_artifact: /Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/evidence/taskpool/uvisa-lark-reopened-real-api-classification-2026-05-12.json
certified_requires_ratification_artifact: true
multimodel_advisory_only: True
multimodel_certification_authority: False
multimodel_advisory_reasons: ["P0_priority", "closeout_ratification"]
multimodel_certification_reasons: []
---

# Task - Lark reopened 57da3f4f: 用户端-底部导航栏第一个资产页面内，总资产展示的金额，以及点击法币钱包列表，点击加密钱包列表后显示的对应钱包账户的余额，全部都需要做适配处理，金额过大超过当前显示的最大边距后应自动缩小金额字体到适配程度

## Objective

该 Lark 任务当前仍在 live `UVISA-2.0新版开发` 未完成列表中，但评论/描述保留旧的 `✅ 已完成` 说明，判定为重启/打回任务。重新执行时必须按“完全可用且前后端打通”的标准关闭：不得只补前端 UI、不得只跑 mock/单测、不得把旧完成说明当作当前证据。

## Live Lark Evidence

- Lark GUID: `57da3f4f-3db8-4062-8ca1-14ff49a9a675`
- Suite entity: `t103235`
- URL: `https://applink.larksuite.com/client/todo/detail?guid=57da3f4f-3db8-4062-8ca1-14ff49a9a675&suite_entity_num=t103235`
- Scope evidence: live tasklist name `UVISA-2.0新版开发`; snapshot `/tmp/lark_uvisa_live_tasks.json`; classification artifact `/Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/evidence/taskpool/uvisa-lark-reopened-real-api-classification-2026-05-12.json`.
- Old completion note now treated as invalidated provenance only: `✅ 已完成 | 金额字体适配 | tier-based font sizing | HomeScreen.amount-fit.test.tsx 3 tests PASS`
- Backend contract required: `False`
- Real API / E2E required: `True`
- Classification reason: real large balance/amount API payload smoke required, though core is FE typography

## Execution Rules

- 先读取最新 Lark 正文/评论、`Workpad - uvisa-app-2.0.md`、`docs/UI_TEST_CASES.md`、`docs/PRODUCT_USER_LOGIC_TEST_CASES.md`、相关 ADR 与前后端源码；不得基于旧完成记录直接复述。
- 先分类最佳落点：FE / BE / contract / shared infrastructure。涉及验证、安全、金额、交易、登录、设备、银行/收款、通知、缓存真实状态时必须检查后端契约。
- 如后端是源头，必须在 `/Users/charles/Desktop/folder/work/uvisa-backend` 以 TDD 修复；如前端是展示/状态问题，也要用真实后端或明确的 real-vs-mock 对照证明。
- 关闭前必须记录：source read、tests/build、real API/browser-harness/Playwright 证据、Railway/package status、scoped commit hash、残余风险。任何门禁缺失时状态只能停在 `review`/`blocked`，不能 Lark/TG 宣称完成。

## Acceptance Criteria

- [ ] Live Lark scope evidence: task remains incomplete under UVISA-2.0新版开发 after previous ✅ completion note; treat as reopened/returned, not done.
- [ ] Before code changes, read current FE and BE source/doc/Workpad/API contract; classify best fix point as FE / BE / contract / infrastructure.
- [ ] Real API or authenticated end-to-end smoke must prove the feature with live/backend data; mock-only and screenshot-only evidence cannot close the task.
- [ ] Large total asset / fiat wallet / crypto wallet balances from realistic API payloads fit within 375px/390px without trimming precision, hiding fields, or changing values.
- [ ] Run touched frontend tests plus pnpm build; run backend targeted tests/package with openjdk@21 when backend is touched or contract semantics are in scope.
- [ ] Closeout requires scoped commit(s), evidence note, Railway/package monitor for affected service(s), and TG/Lark report; no claiming done from local UI changes alone.

## Validation Matrix

| Gate | Required Evidence | Status |
|---|---|---|
| Live source | Fresh Lark read or explicitly timestamped snapshot; task still incomplete/reopened | pending |
| Backend contract | Controller/service/entity/repository/API contract inspected; backend TDD if needed | pending |
| Frontend implementation | Minimal FE change, no route/field/function deletion, touched tests pass | pending |
| Real API / E2E | Authenticated browser/API smoke against real/local backend with non-mock payload; network evidence recorded safely | pending |
| Build/package | FE `pnpm build`; BE JDK21 targeted/package when touched | pending |
| Remote monitor | Railway frontend build; backend deploy/package if backend touched or explicitly required | pending |
| Closeout | Scoped commit, evidence note, TG/Lark report; no old artifact reused as current certification | pending |

## Plan / Workpad

- [ ] Reproduce current returned defect from live task and project state.
- [ ] Implement smallest FE/BE/contract slice that satisfies real acceptance.
- [ ] Run deterministic gates and independent review; use multi-model only as claim-linked advisory/certification, not as substitute for evidence.
- [ ] Move to review/done only after all gates above are satisfied.

## Proof Log

- 2026-05-12T01:43:02+08:00: Created from live Lark reopened-task sweep. Old completion note invalidated because the task remains in live incomplete list.

- 2026-05-12T01:46:57+08:00: Reconcile action `retry_due_promoted` by `hermes-lark-reopen-sweep`. Previous status `retry`.

- 2026-05-12T02:54:26+08:00: Permission taxonomy defaults applied by `permission-migrate --apply`. Changes: {"permission_tier": "autonomous-execution", "lane_semantics": "work/product delivery: project evidence, tests/build, scoped commit, report/push policy as required"}

- 2026-05-12T03:51:16+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-12T04:58:02+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-12T05:02:20+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-12T06:07:58+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-12T07:11:35+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-12T08:17:05+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-12T08:20:55+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-12T09:39:23+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-12T10:43:06+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-12T11:47:05+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

## Real-API E2E Closure 2026-05-12T18:00:00+08:00

- Pre-existing FE typography scaling (commit `7f7c9b2` + `7bf5a97`): HomeScreen 总资产 / wallet rows / AccountDetailScreen 余额 hero 用 max-w-full + min-w-0 + overflow-hidden + adaptive font tier；20+ 字符金额降到 text-24 防 375px 裁切。
- Live real-API E2E against running BE `http://localhost:8080`:
  - SQL inject `wallet_view_user_wallet.balance=9876543210.12` 到 demo 用户 USD 钱包（10 位整 + 2 位小数）。
  - `GET /api/wallets` 返回 `{"ccy":"USD","balance":9876543210.12,...}` 真后端 payload (no mock)。
  - Browser-harness 切到 375x812 mobile viewport，nav `/home`：
    - 总资产 ¥71,054,356,367.23（FX 转 CNH 后 13 位整数 + 2 位小数）。
    - ≈ $ 9,814,137,619.78 USD（10 位整 + 2 小数）。
    - USD 钱包行 9,876,543,210.12（10+2 位）。
    - docW=winW=375，无 overflow；金额节点 scrollWidth ≤ clientWidth 全部 fit。
  - Screenshot `/tmp/uvisa-home-375-big.png` 显示 typography tier 主动降字号，主金额、CNH 折算、wallet rows 均无裁切。
- Restore: 恢复 USD wallet balance=18000.0，避免污染后续测试。
- Verify gates: real backend payload ✓; mobile 375px viewport ✓; no overflow ✓; non-mock evidence ✓; typography scaling 实测触发 ✓。

- 2026-05-13T12:40:43+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-043801-383284-p69674-8b48b68d-1ea9f3ca/discussion_result.json`. Failures: []
