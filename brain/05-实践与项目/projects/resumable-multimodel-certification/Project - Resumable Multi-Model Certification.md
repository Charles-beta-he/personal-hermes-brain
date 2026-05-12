---
type: project
status: active
created: 2026-05-07
project: resumable-multimodel-certification
priority: P0-foundation
certification_status: fanout_dissent_not_certified
---

# Project - Resumable Multi-Model Certification

## North Star

把 Hermes 的多模型认证从“前台同步脚本 + 最后一次性写 discussion_result.json”升级为“artifact-first、可恢复、可审计、后台可跑、fail-closed 的认证状态机”。

目标不是让某次 `consult_models.py --discussion` 跑得更久，而是让多模型认证成为长期可维护的基础设施：任何高风险决策都能被拆成证据、讨论、checkpoint、恢复、审计和最终 certification manifest。

## Current Problem

近期多次多模型 discussion 在前台 600s 限制内超时，留下：

- `plans/*.json`
- `merged_plan.json`

但没有：

- `discussion_result.json`
- 完整 issue ledger ratification
- 可证明的 certification manifest

因此按 fail-closed 语义只能视为 weak consensus / not certified。

## Scope

本项目只覆盖 Hermes multi-model certification 基础设施：

1. discussion checkpoint；
2. resume-discussion；
3. audit-certification；
4. background-safe runner；
5. certification_manifest；
6. evidence-first split/ratification workflow；
7. quota/budget/heartbeat observability。

## Explicitly Deferred

`TaskCreate -> 下一轮 ralph 入口自动串联` 暂停等待本项目完成后再做。原因：它是 hook/state/continuation 高风险功能，必须依赖可恢复多模型认证系统来完成 evidence-first gate 与最终 ratification。

Deferred marker: `TASKCREATE_RALPH_DEFERRED_UNTIL_RESUMABLE_CERT_READY`。

## Non-goals

- 不把 `merged_plan.json` 升级为认证产物。
- 不把延长 foreground timeout 当长期解法。
- 不在第一阶段做 per-round parallel model calls。
- 不让 hook/cron/ralph 消费 partial discussion。
- 不记录 API key、token、password、auth header 或 connection string。

## Success Criteria

Future complete certification artifact: `certification_manifest.json`.

- `partial_runs_marked_uncertified_rate = 100%`。
- `certified_runs_have_discussion_result_rate = 100%`。
- `certified_runs_have_certification_manifest_rate = 100%`。
- forced timeout 后 `resume_success_rate >= 95%`。
- `secret_leak_count = 0`。
- background job 永远输出非空 status JSON。
- `audit-certification <tick_dir>` 可在不调用模型的情况下给出认证状态。

## Related Notes

- [[05-实践与项目/projects/resumable-multimodel-certification/P10 - Long-term Strategy]]
- [[05-实践与项目/projects/resumable-multimodel-certification/P9 - Implementation Backlog]]
- [[05-实践与项目/实践方案/10-可恢复多模型认证系统Playbook]]
- [[06-治理与评审/reviews/2026-05-07-resumable-multimodel-certification-multimodel-selfcheck]]
