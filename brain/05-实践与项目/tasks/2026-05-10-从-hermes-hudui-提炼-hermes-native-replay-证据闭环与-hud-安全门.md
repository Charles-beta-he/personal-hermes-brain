---
type: task
lane: evolution
layer: L3
status: done
priority: P1
created: 2026-05-10T17:37:59+08:00
updated: 2026-05-13T01:01:50+08:00
expires_at: 2026-06-09T17:37:59+08:00
project: hermes-agent
architecture_target: LX
capability_delta: 选择性提炼 hermes-hudui 的 Replay/receipt/export、HUD mutation safety、dashboard hygiene gate，增强 evidence-first closeout 与本地控制面可视化
anti_drift_check: 禁止整体安装/复制第三方运行时；MIT 代码仅作参考，默认 clean-room Hermes-native；任何 HUD mutation surface 必须 loopback/auth/fail-closed；多模型结果 not_certified 只能作为 advisory
acceptance_evidence: "repo b7b76d5: py_compile PASS, pytest 83 PASS, frontend build PASS, npm audit 1 moderate; consult tick /Users/charles/.hermes/tick-20260510-092912 status not_certified truth grounded"
workflow_contract: ["[08-模板/task-workflow-contract-template]"]
required_authority: budget-handoff
max_authority: autonomous-execution
permission_tier: budget-handoff
write_surfaces: ["taskpool", "hermes-scripts", "brain"]
completion_gate: ratification-or-selfcheck-review-done
lane_semantics: "self-evolution: deterministic gates plus ratification/proof before review->done"
multimodel_status: advisory_completed
multimodel_last_checked_at: 2026-05-13T00:39:22+08:00
multimodel_round_status: advisory_passed
multimodel_last_gate_status: PASS_ADVISORY_ONLY
multimodel_last_decision: CONTINUE_LOOP
multimodel_last_discussion_artifact: /Users/charles/.hermes/tick-20260512-163519/discussion_result.json
multimodel_last_state_path: /Users/charles/.hermes/state/taskpool-multimodel/2026-05-10-从-hermes-hudui-提炼-hermes-native-replay-证据闭环与-hud-安全门-state.json
multimodel_last_failures: []
claimed_by: 
claim_expires_at: 
run_id: 
retry_count: 0
next_attempt_at: 
workspace: 
parallel_boundary: 
evidence:
  - artifact:/Users/charles/.hermes/tick-20260512-163519/discussion_result.json
  - artifact:/tmp/hermes-replay-receipt-test2.json
  - proof:py_compile PASS; replay_receipts generate->verify PASS; test_replay_receipts 2 tests OK; hud safety gate detects 15 hermes-hudui findings; dashboard hygiene detects 928kB bundle budget violation; commit ad8dff2
  - proof:ratification-gate PASS; replay/HUD/dashboard gates landed; tests PASS; local commit ad8dff2
concepts: ["evolution", "hermes-hudui", "replay", "receipt", "hud-security", "dashboard-hygiene", "multi-model-advisory"]
multimodel_advisory_only: True
multimodel_certification_authority: False
multimodel_advisory_reasons: ["architecture_target", "evolution_lane"]
multimodel_certification_reasons: []
---

# Task - 从 hermes-hudui 提炼 Hermes-native Replay 证据闭环与 HUD 安全门

## Objective

把 joeynyc/hermes-hudui 的高价值能力转成 Hermes 原生小切片：P0 Replay receipt/proof verifier；P1 HUD mutation surface safety verifier；P1 dashboard frontend hygiene gate；P2 dashboard/product discovery。不得引入第二套 HUD runtime 或暴露未认证写接口。

## Acceptance Criteria

- [ ] 新增/更新 Hermes-native 脚本/测试/文档：replay receipt 能生成并验证 redacted proof artifact；HUD/API mutation verifier 覆盖 cron/plugin/gateway/profile/memory 写接口 loopback/auth/CORS；dashboard hygiene gate 覆盖 npm audit/build/chunk budget；所有改动有本地测试与 scoped commit。

## Multi-model Advisory Summary

Status: `truth_grounded_advisory / not_certified`.

- Repo: `https://github.com/joeynyc/hermes-hudui`
- Pinned commit: `b7b76d573263afdfadf667b5eb98d348c1921182`
- GitHub snapshot: MIT, 1433 stars, 175 forks, 9 open issues, pushed `2026-05-09T13:30:14Z`
- Consult artifact: `/Users/charles/.hermes/tick-20260510-092912/discussion_result.json`
- Models attempted: `claude-opus-4-7`, `gpt-5.5`, `deepseek-v4-pro`, `mimo-v2.5-pro`
- Truth gate: grounded, evidence coverage `1.0`, verified claims `6/6`
- Certification: `not_certified`; agreement matrix `0.65/0.65/0.65`, unresolved severity>=3 blockers, Claude discussion 403, MiMo adapter rejected `xiaomi`, implementation patches only appeared from gpt-5.5.

## Evidence Collected

- `README.md:1-35,45-64,83-99` — browser-based Hermes monitor, 18 tabs, Replay redacted proof artifacts, TUI relation, MIT.
- `pyproject.toml:5-30` — Python package `hermes-hudui`, FastAPI/Uvicorn/watchfiles/Pillow/cryptography, CLI entrypoint.
- `frontend/package.json:6-39` — React/Vite/TypeScript frontend and build scripts.
- `backend/main.py:76-81,95-109,143-166` — wildcard CORS, unauthenticated WebSocket, CLI default host `127.0.0.1`.
- `backend/api/cron.py:55-97,105-134` — cron create/control endpoints shell out to Hermes CLI; localhost trust boundary comment.
- `backend/api/gateway.py:21-45` — gateway restart and Hermes update mutation endpoints.
- `backend/api/plugins.py:36-97` — plugin install/enable/disable/show/hide/update mutation endpoints.
- `backend/services/replay_redactor.py:13-28,116-140,143-188` — token/path/raw-field redaction and receipt redaction metadata.
- Deterministic gates: `py_compile` PASS; backend `pytest` PASS `83 passed`; frontend `npm ci --ignore-scripts && npm run build` PASS; `npm audit` reports one moderate PostCSS advisory `GHSA-qx2v-qp2m-jg93`; Vite warns main chunk `950.53 kB`.

## Decision

选择性提炼，不整体引入。

Reasoning:
- 高价值：Replay/receipt/export 与 Hermes 的 evidence-first closeout、任务池 proof log、review artifact 非常契合。
- 直接采用风险：该 HUD 是 localhost-trusted 写接口聚合器，cron/profile/memory/plugin/gateway/hermes-update 均有 mutation surface；如果未来进入 Hermes 官方/个人控制面，必须先有 loopback/auth/CORS/fail-closed 认证。
- 工程健康度不错：测试与构建通过；但依赖安全与前端 bundle 需要进入 hygiene gate。
- 多模型结论不能当 full certification：本次只能作为 grounded advisory，因为 ratification 未通过。

## P0/P1/P2 Implementation Slices

P0 — Hermes-native Replay Receipt / Proof Verifier
- [ ] 设计 `replay_receipts.py` 或融入现有 evidence/closeout 脚本：生成 redacted proof artifact、receipt hash、可选签名验证。
- [ ] 与任务池 `Proof Log` / `acceptance_evidence` 对接：done/review 状态必须能引用 receipt/hash。
- [ ] 测试：redaction 覆盖 token、env、auth URL、local path、raw tool stdout/stderr/reasoning；receipt hash mismatch fail-closed。

P1 — HUD/API Mutation Surface Safety Verifier
- [ ] 新增 local HUD/API safety gate：枚举 cron/plugin/gateway/profile/memory/hermes-update 等 mutation endpoints。
- [ ] 验证 host 非 loopback 时拒绝 wildcard CORS / unauthenticated mutation；loopback-only 也必须显式标注 RCE-equivalent threat model。
- [ ] 测试：新增写接口缺少 trust boundary metadata 时 fail-closed。

P1 — Dashboard Frontend Hygiene Gate
- [ ] 为未来 Hermes dashboard/frontend 工作加 `npm audit` / build / bundle budget gate。
- [ ] 策略：moderate+ 且 fixAvailable 的 advisory 进入 blocker 或 accepted-risk；chunk budget 必须显式配置，不能只忽略 Vite warning。

P2 — Product Discovery / Dashboard UX Ideas
- [ ] 只吸收产品形态：health/action items、gateway/provider visibility、plugin status、model analytics、live capability matrix、language/theme/keyboard UX。
- [ ] 不复制运行时；作为 Hermes TUI/Gateway/Obsidian dashboard 的需求池。

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
| clone + repo facts | pass | `/tmp/hermes-hudui-audit`, commit `b7b76d5` |
| python compile | pass | `python3 -m py_compile $(git ls-files '*.py')` |
| backend tests | pass | `.venv` + `python -m pytest -q` -> `83 passed in 13.27s` |
| frontend build | pass | `npm ci --ignore-scripts && npm run build` |
| npm audit | warn | one moderate PostCSS advisory, fixAvailable |
| multi-model consult | advisory | tick `20260510-092912`, truth grounded, ratification not certified |

## Proof Log

- 2026-05-10T17:37:59+08:00: Task created from local-brain control point.
- 2026-05-10T17:40:00+08:00: Evidence-first repo audit and T3 multi-model discussion completed; task updated as `truth_grounded_advisory`, not certified.

## Blockers / Confusions

- Multi-model certification unresolved: discussion result has `status=not_certified`; do not execute implementation patches solely from this consult.
- Direct runtime adoption blocked until local HUD mutation safety and dependency/bundle hygiene gates exist.

## Final Handoff

- Status:
- Evidence:
- Residual risk:

- 2026-05-11T00:42:51+08:00: Lifecycle transition `pending` -> `claimed` by `agent-team-controller`. Reason: Phase 4 dynamic parallel dispatch

- 2026-05-11T01:39:48+08:00: Lifecycle transition `claimed` -> `pending` by `hermes`. Force: true. Reason: deadlock_fix_release

- 2026-05-12T02:54:26+08:00: Permission taxonomy defaults applied by `permission-migrate --apply`. Changes: {"required_authority": "budget-handoff", "max_authority": "autonomous-execution", "permission_tier": "budget-handoff", "write_surfaces": ["taskpool", "hermes-scripts", "brain"], "completion_gate": "ratification-or-selfcheck-review-done", "lane_semantics": "self-evolution: deterministic gates plus ratification/proof before review->done"}

- 2026-05-13T00:35:18+08:00: Lifecycle transition `pending` -> `claimed` by `hermes`.

- 2026-05-13T00:39:22+08:00: Multimodel PUA-loop round `advisory_passed`. Gate `PASS_ADVISORY_ONLY`, decision `CONTINUE_LOOP`. Discussion `/Users/charles/.hermes/tick-20260512-163519/discussion_result.json`. Failures: []

- 2026-05-13T01:01:50+08:00: Lifecycle transition `claimed` -> `running` by `hermes`. Reason: implemented and verified Hermes-native replay/HUD/dashboard evidence gates

- 2026-05-13T01:01:50+08:00: Lifecycle transition `running` -> `review` by `hermes`. Reason: ratification_gate_PASS plus deterministic script tests PASS Evidence: artifact:/Users/charles/.hermes/tick-20260512-163519/discussion_result.json, artifact:/tmp/hermes-replay-receipt-test2.json, proof:py_compile PASS; replay_receipts generate->verify PASS; test_replay_receipts 2 tests OK; hud safety gate detects 15 hermes-hudui findings; dashboard hygiene detects 928kB bundle budget violation; commit ad8dff2

- 2026-05-13T01:01:50+08:00: Lifecycle transition `review` -> `done` by `hermes`. Reason: review closeout after target-bound ratification PASS and scoped local commit ad8dff2 Evidence: artifact:/Users/charles/.hermes/tick-20260512-163519/discussion_result.json, artifact:/tmp/hermes-replay-receipt-test2.json, proof:ratification-gate PASS; replay/HUD/dashboard gates landed; tests PASS; local commit ad8dff2
