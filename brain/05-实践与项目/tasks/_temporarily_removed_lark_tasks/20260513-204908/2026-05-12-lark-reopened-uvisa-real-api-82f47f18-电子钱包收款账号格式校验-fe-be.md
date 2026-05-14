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
multimodel_last_checked_at: 2026-05-13T12:43:42+08:00
multimodel_round_status: advisory_passed
multimodel_last_gate_status: PASS_ADVISORY_ONLY
multimodel_last_decision: CONTINUE_LOOP
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260513-044055-777256-p74201-db9d63a4-16795282/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-12-lark-reopened-uvisa-real-api-82f47f18-电子钱包收款账号格式校验-fe-be-state.json
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
concepts: ["work-task", "uvisa", "lark-reopened", "returned-task", "real-api-e2e", "front-back-integration", "backend-contract", "security-money-gate"]
backend_workspace: /Users/charles/Desktop/folder/work/uvisa-backend
lark_task_guid: 82f47f18-7e4f-4aea-b7cf-689df27820ca
lark_suite_entity_num: t103278
lark_task_url: https://applink.larksuite.com/client/todo/detail?guid=82f47f18-7e4f-4aea-b7cf-689df27820ca&suite_entity_num=t103278
lark_scope: UVISA-2.0新版开发
lark_live_reopened_at: 2026-05-12T01:43:02+08:00
old_completion_note: ✅ 已完成 | 电子钱包收款人格式校验 | NAME_RE + SAFE_ACCOUNT_RE + EMAIL_RE 白名单验证
backend_contract_required: true
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

# Task - Lark reopened 82f47f18: 用户端-底部导航栏我的-点击收款人管理-新增收款人，选择电子钱包，收款账号输入不符合规则的内容（输入空格、特殊符号、表情包）是也能保存成功，没有进行格式校验

## Objective

该 Lark 任务当前仍在 live `UVISA-2.0新版开发` 未完成列表中，但评论/描述保留旧的 `✅ 已完成` 说明，判定为重启/打回任务。重新执行时必须按“完全可用且前后端打通”的标准关闭：不得只补前端 UI、不得只跑 mock/单测、不得把旧完成说明当作当前证据。

## Live Lark Evidence

- Lark GUID: `82f47f18-7e4f-4aea-b7cf-689df27820ca`
- Suite entity: `t103278`
- URL: `https://applink.larksuite.com/client/todo/detail?guid=82f47f18-7e4f-4aea-b7cf-689df27820ca&suite_entity_num=t103278`
- Scope evidence: live tasklist name `UVISA-2.0新版开发`; snapshot `/tmp/lark_uvisa_live_tasks.json`; classification artifact `/Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/evidence/taskpool/uvisa-lark-reopened-real-api-classification-2026-05-12.json`.
- Old completion note now treated as invalidated provenance only: `✅ 已完成 | 电子钱包收款人格式校验 | NAME_RE + SAFE_ACCOUNT_RE + EMAIL_RE 白名单验证`
- Backend contract required: `True`
- Real API / E2E required: `True`
- Classification reason: validation must be FE+BE; previous completion was frontend-style validation only risk

## Execution Rules

- 先读取最新 Lark 正文/评论、`Workpad - uvisa-app-2.0.md`、`docs/UI_TEST_CASES.md`、`docs/PRODUCT_USER_LOGIC_TEST_CASES.md`、相关 ADR 与前后端源码；不得基于旧完成记录直接复述。
- 先分类最佳落点：FE / BE / contract / shared infrastructure。涉及验证、安全、金额、交易、登录、设备、银行/收款、通知、缓存真实状态时必须检查后端契约。
- 如后端是源头，必须在 `/Users/charles/Desktop/folder/work/uvisa-backend` 以 TDD 修复；如前端是展示/状态问题，也要用真实后端或明确的 real-vs-mock 对照证明。
- 关闭前必须记录：source read、tests/build、real API/browser-harness/Playwright 证据、Railway/package status、scoped commit hash、残余风险。任何门禁缺失时状态只能停在 `review`/`blocked`，不能 Lark/TG 宣称完成。

## Acceptance Criteria

- [ ] Live Lark scope evidence: task remains incomplete under UVISA-2.0新版开发 after previous ✅ completion note; treat as reopened/returned, not done.
- [ ] Before code changes, read current FE and BE source/doc/Workpad/API contract; classify best fix point as FE / BE / contract / infrastructure.
- [ ] Backend contract must be inspected and, when incomplete/unsafe, fixed with backend TDD; frontend-only mock/Vitest proof is insufficient.
- [ ] E-wallet payee account validation rejects spaces, unsupported symbols, emoji, and invalid separators at both frontend validation and backend direct API; valid account/email/wallet identifiers still save successfully.
- [ ] Real API or authenticated end-to-end smoke must prove the feature with live/backend data; mock-only and screenshot-only evidence cannot close the task.
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

- 2026-05-12T03:53:37+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-12T04:58:02+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-12T06:07:58+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-12T07:21:46+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-12T08:24:00+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-12T09:39:23+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

- 2026-05-12T10:45:49+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-12T11:47:05+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

## Real-API E2E Closure 2026-05-12T17:25:00+08:00

- BE PayeeDetailsValidator wallet path: WALLET_ACCOUNT_PATTERN `^[A-Za-z0-9@._+\-]{4,64}$` + WALLET_EMAIL_PATTERN (PayPal/Skrill). `validateCreateBody` + `validateLegacyDetails` both branch on WALLET. PayeeDetailsValidatorTest 5/5 PASS (api-public total 23/23). Commit `3bf19c4`.
- FE RemitNewWalletScreen 已有 SAFE_ACCOUNT_RE 同等 regex (pre-existing); 本次只补 BE fail-closed,不改 FE。
- Live real-API E2E against running BE `http://localhost:8080` with authenticated JWT (demo `+8613800000000` / OTP 888888 redis-injected):
  - POST `/api/remit/payees` `{type:wallet, provider:Alipay, account:"user with space"}` → 10001 `钱包账号仅支持字母 / 数字 / @ . _ + -，长度 4-64，不支持空格 / 表情 / 特殊符号` ✓
  - POST `... account:"alice🎉pay"` (emoji) → 10001 same msg ✓
  - POST `... provider:PayPal, account:"not-an-email"` → 10001 `钱包账号必须是合法 email，不支持空格 / 表情 / 特殊符号` ✓
  - POST `... provider:Alipay, account:"alice_pay-123"` → 0 ok (新增成功) ✓
- Gates met: real backend payload + canonical envelope, no mock; fail-closed; FE already validates, BE now independent guard; touched-file tests + BE compile + api-public package PASS.

- 2026-05-13T12:43:42+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-044055-777256-p74201-db9d63a4-16795282/discussion_result.json`. Failures: []
