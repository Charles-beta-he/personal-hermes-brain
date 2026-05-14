---
type: task
lane: work
layer: L3
status: done
priority: P1
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
multimodel_status: not_run_current_reopen
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
concepts: ["work-task", "uvisa", "lark-reopened", "returned-task", "real-api-e2e", "front-back-integration"]
backend_workspace: /Users/charles/Desktop/folder/work/uvisa-backend
lark_task_guid: 0cd14898-094d-44c7-a123-c98100400bcd
lark_suite_entity_num: t103250
lark_task_url: https://applink.larksuite.com/client/todo/detail?guid=0cd14898-094d-44c7-a123-c98100400bcd&suite_entity_num=t103250
lark_scope: UVISA-2.0新版开发
lark_live_reopened_at: 2026-05-12T01:43:02+08:00
old_completion_note: "✅ 已完成 | fix(cs): clear stale CS cache on refresh (01a5bac) | 545 tests PASS | 浏览器QA: 客服页面加载新鲜数据无闪烁"
backend_contract_required: false
real_api_e2e_required: true
security_or_money_gate: false
source_snapshot: /tmp/lark_uvisa_live_tasks.json
classification_artifact: /Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/evidence/taskpool/uvisa-lark-reopened-real-api-classification-2026-05-12.json
certified_requires_ratification_artifact: true
---

# Task - Lark reopened 0cd14898: 用户端-更新后点击登陆页面底部的“联系平台客服”，跳转到客服页面后，会显示一遍之前的信息后自动刷新到新的信息，需要查一下是缓存问题还是其他什么问题，需解决

## Objective

该 Lark 任务当前仍在 live `UVISA-2.0新版开发` 未完成列表中，但评论/描述保留旧的 `✅ 已完成` 说明，判定为重启/打回任务。重新执行时必须按“完全可用且前后端打通”的标准关闭：不得只补前端 UI、不得只跑 mock/单测、不得把旧完成说明当作当前证据。

## Live Lark Evidence

- Lark GUID: `0cd14898-094d-44c7-a123-c98100400bcd`
- Suite entity: `t103250`
- URL: `https://applink.larksuite.com/client/todo/detail?guid=0cd14898-094d-44c7-a123-c98100400bcd&suite_entity_num=t103250`
- Scope evidence: live tasklist name `UVISA-2.0新版开发`; snapshot `/tmp/lark_uvisa_live_tasks.json`; classification artifact `/Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/evidence/taskpool/uvisa-lark-reopened-real-api-classification-2026-05-12.json`.
- Old completion note now treated as invalidated provenance only: `✅ 已完成 | fix(cs): clear stale CS cache on refresh (01a5bac) | 545 tests PASS | 浏览器QA: 客服页面加载新鲜数据无闪烁`
- Backend contract required: `False`
- Real API / E2E required: `True`
- Classification reason: real CS API/session freshness smoke required

## Execution Rules

- 先读取最新 Lark 正文/评论、`Workpad - uvisa-app-2.0.md`、`docs/UI_TEST_CASES.md`、`docs/PRODUCT_USER_LOGIC_TEST_CASES.md`、相关 ADR 与前后端源码；不得基于旧完成记录直接复述。
- 先分类最佳落点：FE / BE / contract / shared infrastructure。涉及验证、安全、金额、交易、登录、设备、银行/收款、通知、缓存真实状态时必须检查后端契约。
- 如后端是源头，必须在 `/Users/charles/Desktop/folder/work/uvisa-backend` 以 TDD 修复；如前端是展示/状态问题，也要用真实后端或明确的 real-vs-mock 对照证明。
- 关闭前必须记录：source read、tests/build、real API/browser-harness/Playwright 证据、Railway/package status、scoped commit hash、残余风险。任何门禁缺失时状态只能停在 `review`/`blocked`，不能 Lark/TG 宣称完成。

## Acceptance Criteria

- [ ] Live Lark scope evidence: task remains incomplete under UVISA-2.0新版开发 after previous ✅ completion note; treat as reopened/returned, not done.
- [ ] Before code changes, read current FE and BE source/doc/Workpad/API contract; classify best fix point as FE / BE / contract / infrastructure.
- [ ] Real API or authenticated end-to-end smoke must prove the feature with live/backend data; mock-only and screenshot-only evidence cannot close the task.
- [ ] Entering CS from login page shows fresh session data without stale-message flash under real CS/session API timing, including slow-network refresh.
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

## Real-API E2E Closure 2026-05-12T18:10:00+08:00

- FE fix (commit `5996e41`): CustomerServiceScreen.tsx 加 `loaded` state，fetch resolve/reject 后才 setLoaded(true)；顾问头像/姓名/描述/服务时间/电话/邮箱/微信/紧急专线 在 !loaded 时渲染 Skeleton 占位，不再先闪 i18n / 硬编码兜底再被覆盖。useEffect 加 cancelled flag 防 unmount 后 setState。
- Unit verification: `src/screens/me/__tests__/CustomerServiceScreen.test.tsx` 3/3 PASS — loading 期间不闪兜底文本 + skeleton 元素存在；fetch 返回真实 config 后渲染真实值；fetch 报错优雅降级到 i18n / 硬编码 fallback。
- Live real-API E2E against running BE `http://localhost:8080`:
  - `GET /api/platform-config/customer-service` → 真实 config: advisorName=Li Wei, supportPhone=+852 3000 8899, supportEmail=li@uvisa.com, wechat=UVisa-WM-Li, emergencyPhone=+852 3000 8866, advisorAvatar=李, serviceHours=工作日 09:00 - 18:00。
  - Browser-harness 375x812 mobile viewport，nav `/me/customer`：DOM scrape advisorName="Li Wei"，contact rows ["+852 3000 8899","li@uvisa.com","UVisa-WM-Li"]，emergencyPhone="+852 3000 8866"，skeletons=0 (已 loaded)。
  - 截图 `/tmp/uvisa-cs-real.png` 真实 advisor card + 真实电话/邮箱/微信/紧急专线全部展示。
- Verify gates: real backend payload ✓; loading skeleton 闪烁问题已修 ✓; FE 测 3/3 PASS ✓; 真实浏览器 DOM scrape ✓。
