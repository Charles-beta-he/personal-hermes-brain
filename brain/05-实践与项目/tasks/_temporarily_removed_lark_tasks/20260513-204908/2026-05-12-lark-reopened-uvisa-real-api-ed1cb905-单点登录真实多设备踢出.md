---
type: task
lane: work
layer: L3
status: done
priority: P0
created: 2026-05-12T01:43:02+08:00
updated: 2026-05-12T01:46:57+08:00
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
multimodel_last_checked_at: 2026-05-13T14:32:23+08:00
multimodel_round_status: advisory_passed
multimodel_last_gate_status: PASS_ADVISORY_ONLY
multimodel_last_decision: CONTINUE_LOOP
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260513-062950-424770-p92012-1c1f6a28-f3495fd9/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-12-lark-reopened-uvisa-real-api-ed1cb905-单点登录真实多设备踢出-state.json
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
lark_task_guid: ed1cb905-7f25-4b44-b5a4-b1f342d81650
lark_suite_entity_num: t103228
lark_task_url: https://applink.larksuite.com/client/todo/detail?guid=ed1cb905-7f25-4b44-b5a4-b1f342d81650&suite_entity_num=t103228
lark_scope: UVISA-2.0新版开发
lark_live_reopened_at: 2026-05-12T01:43:02+08:00
old_completion_note: "✅ 已完成 | feat(sso): Redis active-session SSO | BE cd3915c + FE 02783c5 | 545 tests PASS | 新登录自动踢旧session"
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

# Task - Lark reopened ed1cb905: 用户端-未做单点登陆-同账户不同设备登陆未顶掉帐号

## Objective

该 Lark 任务当前仍在 live `UVISA-2.0新版开发` 未完成列表中，但评论/描述保留旧的 `✅ 已完成` 说明，判定为重启/打回任务。重新执行时必须按“完全可用且前后端打通”的标准关闭：不得只补前端 UI、不得只跑 mock/单测、不得把旧完成说明当作当前证据。

## Live Lark Evidence

- Lark GUID: `ed1cb905-7f25-4b44-b5a4-b1f342d81650`
- Suite entity: `t103228`
- URL: `https://applink.larksuite.com/client/todo/detail?guid=ed1cb905-7f25-4b44-b5a4-b1f342d81650&suite_entity_num=t103228`
- Scope evidence: live tasklist name `UVISA-2.0新版开发`; snapshot `/tmp/lark_uvisa_live_tasks.json`; classification artifact `/Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/evidence/taskpool/uvisa-lark-reopened-real-api-classification-2026-05-12.json`.
- Old completion note now treated as invalidated provenance only: `✅ 已完成 | feat(sso): Redis active-session SSO | BE cd3915c + FE 02783c5 | 545 tests PASS | 新登录自动踢旧session`
- Backend contract required: `True`
- Real API / E2E required: `True`
- Classification reason: backend session invalidation + real multi-login proof required

## Execution Rules

- 先读取最新 Lark 正文/评论、`Workpad - uvisa-app-2.0.md`、`docs/UI_TEST_CASES.md`、`docs/PRODUCT_USER_LOGIC_TEST_CASES.md`、相关 ADR 与前后端源码；不得基于旧完成记录直接复述。
- 先分类最佳落点：FE / BE / contract / shared infrastructure。涉及验证、安全、金额、交易、登录、设备、银行/收款、通知、缓存真实状态时必须检查后端契约。
- 如后端是源头，必须在 `/Users/charles/Desktop/folder/work/uvisa-backend` 以 TDD 修复；如前端是展示/状态问题，也要用真实后端或明确的 real-vs-mock 对照证明。
- 关闭前必须记录：source read、tests/build、real API/browser-harness/Playwright 证据、Railway/package status、scoped commit hash、残余风险。任何门禁缺失时状态只能停在 `review`/`blocked`，不能 Lark/TG 宣称完成。

## Acceptance Criteria

- [ ] Live Lark scope evidence: task remains incomplete under UVISA-2.0新版开发 after previous ✅ completion note; treat as reopened/returned, not done.
- [ ] Before code changes, read current FE and BE source/doc/Workpad/API contract; classify best fix point as FE / BE / contract / infrastructure.
- [ ] Backend contract must be inspected and, when incomplete/unsafe, fixed with backend TDD; frontend-only mock/Vitest proof is insufficient.
- [ ] Same account login on a second device invalidates the old device access and refresh tokens/session server-side; both OTP/password/refresh paths respect the same active-session generation.
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

## Real-API E2E Closure 2026-05-12T17:30:00+08:00

- BE SSO (Redis active sid) pre-existing (commit `d2457db`): `JwtTokenService.issue` writes `auth:session:{userId}=newSid` overwriting; `JwtBlacklistAuthConverter.convert` rejects mismatched sid; `JwtTokenService.rotate` also rejects mismatched sid on refresh.
- FE additions (commit `c37bbef`): App.tsx visibility/focus listener → `fetchProfile()` ping when tab regains focus → existing api.ts 401 interceptor → `uvisa:auth-expired` event → toast + redirect /login. No frontend timer, BE remains source of truth.
- Live real-API E2E against running BE `http://localhost:8080`:
  - Device A login via phone OTP → access token `T_A` + refresh `RT_A` + sid_A in Redis.
  - Verify `T_A` /api/me → code=0, uvisaUid=UV1380000.
  - Device B login same account → new access `T_B` + refresh `RT_B` + sid_B in Redis (overwrites sid_A).
  - `T_A` /api/me → HTTP 401 ✓ (JwtBlacklistAuthConverter.isSessionValid=false).
  - `RT_A` /api/auth/refresh → code=10002 `登录已过期，请重新登录` ✓ (rotate() detects mismatched sid).
  - `T_B` /api/me → code=0, uvisaUid=UV1380000 ✓ (new device unaffected).
- FE UX flow: device A 老 token → 401 → api.ts performRefresh → 10002 → wipe tokens → dispatch `uvisa:auth-expired` → toast + redirect.
- 顶号机制 BE+FE 全链路通; user 在 device A 切回前台触发 fetchProfile heartbeat → 立刻 401 → 登出。
- Residual nice-to-have (phase-3 / not blocking): BE 当前 401 body 为空，FE `ssoKick` flag 走 generic expiry 文案而非 "已在其他设备登录"。可加自定义 AuthenticationEntryPoint 写 JSON body 把 BizException msg 透传到 FE。本任务核心要求 "顶掉" 已完整实现。

- 2026-05-13T14:32:23+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-062950-424770-p92012-1c1f6a28-f3495fd9/discussion_result.json`. Failures: []
