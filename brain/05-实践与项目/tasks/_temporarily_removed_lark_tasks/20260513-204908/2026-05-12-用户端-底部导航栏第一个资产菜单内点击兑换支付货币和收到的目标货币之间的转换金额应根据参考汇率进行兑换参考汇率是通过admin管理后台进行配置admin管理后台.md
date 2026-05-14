---
type: task
lane: work
layer: L3
status: pending
priority: P2
created: 2026-05-12T17:21:15+08:00
updated: 2026-05-12T17:21:15+08:00
expires_at: 2026-06-11T17:21:15+08:00
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
lark_task_guid: "fe3b1bff-405d-4045-ba74-f385d63ef6b0"
lark_suite_entity_num: "t103407"
lark_task_url: "https://applink.larksuite.com/client/todo/detail?guid=fe3b1bff-405d-4045-ba74-f385d63ef6b0&suite_entity_num=t103407"
lark_scope: "UVISA-2.0新版开发"
lark_assignee_open_id: "ou_156c85ee34f5f5a7faf039e86d246afb"
lark_assignee_name: "贺程"
lark_collected_at: "2026-05-12T22:20:17+08:00"
status: blocked
blocker: "Admin-config / BE-scope: 换汇汇率从 admin 管理后台「换汇配置」录入, FE 经 /exchange/quote 实时拉取 — 当前 admin 后台未配置有效汇率规则, 需 admin/BE owner 接手"
proof_log:
  - 2026-05-13T00:14:00+08:00 Out-of-scope for FE. ExchangeScreen 已经走 exchangeService.getQuote(from,to,amount) → BE /exchange/quote 拿 rate, ExchangeConfirm/Finish 都用 quoteId. BE 又从 admin 后台「换汇配置」读取汇率规则; admin 没配规则就没有可用 rate. 修代码不能解决配置缺失, 转 admin/BE owner.
---

# Task - 用户端-底部导航栏第一个资产菜单内，点击兑换，支付货币和收到的目标货币之间的转换金额，应根据参考汇率进行兑换，参考汇率是通过admin管理后台进行配置，admin管理后台内的“换汇配置”就是配置这里的汇率规则，当前后台配置未有效汇率配置，说

## Objective

用户端-底部导航栏第一个资产菜单内，点击兑换，支付货币和收到的目标货币之间的转换金额，应根据参考汇率进行兑换，参考汇率是通过admin管理后台进行配置，admin管理后台内的“换汇配置”就是配置这里的汇率规则，当前后台配置未有效汇率配置，说


## Live Lark Evidence

- Collected: `2026-05-12T22:20:17+08:00`
- Scope: `UVISA-2.0新版开发`
- Assignee: `贺程` / `ou_156c85ee34f5f5a7faf039e86d246afb`
- Lark GUID: `fe3b1bff-405d-4045-ba74-f385d63ef6b0`
- Suite entity: `t103407`
- URL: `https://applink.larksuite.com/client/todo/detail?guid=fe3b1bff-405d-4045-ba74-f385d63ef6b0&suite_entity_num=t103407`
- Comments snapshot: [unknown] [Image]

## Closeout Gates

- [ ] Re-read current task/comment evidence before execution; screenshots/comments may contain prototype deltas.
- [ ] Classify FE/BE/contract/infrastructure landing point before coding.
- [ ] Run scoped tests/build and record evidence.
- [ ] Commit scoped changes, follow UVISA push/remote monitor policy, and report result.

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

- 2026-05-12T17:21:15+08:00: Task created from local-brain control point.

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:
