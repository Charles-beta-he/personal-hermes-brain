---
type: evolution_log
layer: L6
status: current
created: 2026-05-08T18:36:00+08:00
updated: 2026-05-08T18:36:00+08:00
project: hermes-automation-budget
concepts: [iteration-budget, self-evolution, pua-loop]
---

# 2026-05-08 Iteration Budget 自进化记录

## Change

为 Hermes 自动化任务补齐 iteration-budget P10 闭环：

- 新增 read-only doctor。
- 新增 bounded task budget tick。
- 新增 handoff template。
- 更新 Hermes tool-budget skill。
- 写入本地大脑策略页、review、proof。
- 创建并完成 canonical task note。

## Why

自动化任务出现 `Iteration budget reached (60/60)` 时，旧处理方式只有人工解释和调参建议，缺少：

- 预算诊断 artifact。
- 自动任务 handoff artifact。
- P10 策略分层。
- PUA-loop 接近预算时的强制收尾规则。
- 本地大脑 proof gate。

## Safety

- 不修改 vendor runtime。
- 不读取/输出 secret value。
- doctor 不输出 session/log snippet。
- budget tick 默认不 claim、不执行、不 done。
- 高风险任务分类为 manual。

## Verification

见：

- `/Users/charles/Documents/brain/05-实践与项目/tasks/2026-05-08-iteration-budget-pua-loop-proof.md`
- `/Users/charles/Documents/brain/06-治理与评审/reviews/2026-05-08-iteration-budget-p10-multimodel-review.md`

## Evidence Boundary

Model agreement is provenance only; status promotion requires command/file/search proof recorded in this note or linked artifacts.

