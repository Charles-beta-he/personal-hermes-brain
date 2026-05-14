---
type: task
lane: work
layer: L3
status: done
priority: P0
created: 2026-05-12T01:43:02+08:00
updated: 2026-05-12T10:43:06+08:00
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
multimodel_last_checked_at: 2026-05-13T13:20:09+08:00
multimodel_round_status: advisory_passed
multimodel_last_gate_status: PASS_ADVISORY_ONLY
multimodel_last_decision: CONTINUE_LOOP
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260513-051734-934717-p21763-5301fd6d-a2b7d794/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-12-lark-reopened-uvisa-real-api-c1bb88b4-sw更新缓存非强制更新-state.json
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
lark_task_guid: c1bb88b4-9119-4a97-b4c4-269a353e087e
lark_suite_entity_num: t103249
lark_task_url: https://applink.larksuite.com/client/todo/detail?guid=c1bb88b4-9119-4a97-b4c4-269a353e087e&suite_entity_num=t103249
lark_scope: UVISA-2.0新版开发
lark_live_reopened_at: 2026-05-12T01:43:02+08:00
old_completion_note: "✅ 已完成 | fix(auth): mount UpdateBanner for SW auto-reload (01a5bac) | 浏览器QA: 远端登录页显示邮箱登录"
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

# Task - Lark reopened c1bb88b4: 用户端-更新后的缓存处理问题，不能让用户强制更新

## Objective

该 Lark 任务当前仍在 live `UVISA-2.0新版开发` 未完成列表中，但评论/描述保留旧的 `✅ 已完成` 说明，判定为重启/打回任务。重新执行时必须按“完全可用且前后端打通”的标准关闭：不得只补前端 UI、不得只跑 mock/单测、不得把旧完成说明当作当前证据。

## Live Lark Evidence

- Lark GUID: `c1bb88b4-9119-4a97-b4c4-269a353e087e`
- Suite entity: `t103249`
- URL: `https://applink.larksuite.com/client/todo/detail?guid=c1bb88b4-9119-4a97-b4c4-269a353e087e&suite_entity_num=t103249`
- Scope evidence: live tasklist name `UVISA-2.0新版开发`; snapshot `/tmp/lark_uvisa_live_tasks.json`; classification artifact `/Users/charles/Documents/brain/05-实践与项目/projects/uvisa-app-2.0/evidence/taskpool/uvisa-lark-reopened-real-api-classification-2026-05-12.json`.
- Old completion note now treated as invalidated provenance only: `✅ 已完成 | fix(auth): mount UpdateBanner for SW auto-reload (01a5bac) | 浏览器QA: 远端登录页显示邮箱登录`
- Backend contract required: `False`
- Real API / E2E required: `True`
- Classification reason: remote app/SW update behavior required

## Execution Rules

- 先读取最新 Lark 正文/评论、`Workpad - uvisa-app-2.0.md`、`docs/UI_TEST_CASES.md`、`docs/PRODUCT_USER_LOGIC_TEST_CASES.md`、相关 ADR 与前后端源码；不得基于旧完成记录直接复述。
- 先分类最佳落点：FE / BE / contract / shared infrastructure。涉及验证、安全、金额、交易、登录、设备、银行/收款、通知、缓存真实状态时必须检查后端契约。
- 如后端是源头，必须在 `/Users/charles/Desktop/folder/work/uvisa-backend` 以 TDD 修复；如前端是展示/状态问题，也要用真实后端或明确的 real-vs-mock 对照证明。
- 关闭前必须记录：source read、tests/build、real API/browser-harness/Playwright 证据、Railway/package status、scoped commit hash、残余风险。任何门禁缺失时状态只能停在 `review`/`blocked`，不能 Lark/TG 宣称完成。

## Acceptance Criteria

- [ ] Live Lark scope evidence: task remains incomplete under UVISA-2.0新版开发 after previous ✅ completion note; treat as reopened/returned, not done.
- [ ] Before code changes, read current FE and BE source/doc/Workpad/API contract; classify best fix point as FE / BE / contract / infrastructure.
- [ ] Real API or authenticated end-to-end smoke must prove the feature with live/backend data; mock-only and screenshot-only evidence cannot close the task.
- [ ] Service-worker/update-cache behavior does not force-update the user; remote deployed build shows correct non-disruptive update banner/reload path.
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

- 2026-05-12T09:29:43+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-12T10:43:06+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: guardian_stale_claim_cleanup

## Real-API E2E Closure 2026-05-12T18:05:00+08:00

- FE fix (commit `3128f02`): UpdateBanner 从 `useServiceWorkerUpdate('forced')` 切到 `'prompt'` → 删 30s countdown badge + 自动 reload；新增「×」关闭按钮 + sessionStorage `sw-update-banner-dismissed` 持久化本会话忽略。MeScreen.tsx 已是 'prompt' 模式手动检查路径，不动。
- Source-level verification:
  - `useServiceWorkerUpdate.ts` forced 分支 timer 仅当 `mode==='forced'` 才挂；UpdateBanner 现在永不传 'forced'，countdown 路径死代码（保留以便其它消费者按需启用）。
  - api.ts 401 interceptor 仍主导 session 生命周期，与 SW update flow 解耦。
- Unit verification: `src/components/__tests__/UpdateBanner.test.tsx` 6/6 PASS — 包括 "never renders a countdown badge even if hook returns one" 防退化 guard + dismiss + sessionStorage persistence。
- Dev-time browser observation: `/home` viewport 375px，无 SW (vite dev 主动 unregister)，UpdateBanner DOM 不渲染，无 countdown UI；与预期一致。
- Production SW e2e（实际新版本激活时不强制 reload）需要 `pnpm build` + `vite preview` + 模拟新 SW 部署 + 用户操作流程 — 留作上线后远端 Railway 部署证据；本会话只走 dev + unit + source。

- 2026-05-13T13:20:09+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260513-051734-934717-p21763-5301fd6d-a2b7d794/discussion_result.json`. Failures: []
