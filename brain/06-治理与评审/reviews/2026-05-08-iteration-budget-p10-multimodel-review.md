---
type: review
layer: L6
status: current
created: 2026-05-08T18:36:00+08:00
updated: 2026-05-08T18:36:00+08:00
project: hermes-automation-budget
concepts: [iteration-budget, multi-model-advisory, p10-strategy, pua-loop]
models:
  - gpt-5.5
  - claude-opus-4-7
  - mimo-v2.5-pro
artifacts:
  - /Users/charles/.hermes/tick-20260508-101930
  - /tmp/iteration_budget_verify_20260508183533
---

# Iteration Budget P10 多模型审查与落地记录

## 问题

自动化任务出现 `Iteration budget reached (60/60) — response may be incomplete` 时，旧策略容易落入两个坏结果：

1. 只调大 `agent.max_turns`，把一个 Hermes session 变成无界 daemon。
2. 预算耗尽时输出半成品，任务池没有 handoff/proof，后续无法 resume。

## 证据摘要

- 当前 `agent.max_turns = 60`。
- 当前 `delegation.max_iterations = 50`。
- `cli.py` 在 `api_calls >= max_iterations` 且 `completed=false` 时输出 iteration budget warning。
- `brain_task_dispatch_tick.py` 是 control-plane tick，不执行任务 Markdown。
- `long_evolution_guard.py` 已有 budget-check 和 claim ledger 原语，但没有面向 iteration cap 的 doctor/runner/handoff。

## 多模型结果

artifact: `/Users/charles/.hermes/tick-20260508-101930`

- gpt-5.5: 建议 budget doctor、bounded task tick、handoff template、policy skill update、proof wrapper。
- claude-opus-4-7: 建议 diagnostic script、bounded runner、taskpool landing、policy skill update，不改默认 config。
- mimo-v2.5-pro: JSON parse/invoke failed。
- merged consensus: weak_consensus。
- discussion_result 缺失：本轮不是完整 ratification。

结论：采用 multi-model advisory + deterministic gates。P10 策略不得声称 full certification。

## P10 issue ledger

| Issue | Severity | Status | Resolution |
|---|---:|---|---|
| I-001 单纯调大 max_turns 会掩盖无界 daemon 风险 | 5 | resolved | 默认保留 bounded cap，增加 handoff/tick |
| I-002 cron/自动任务不应把机械循环交给 LLM | 4 | resolved | script_first_no_agent / tiny_summarizer 分层 |
| I-003 task pool 执行必须 claim/release/retry/done/proof | 5 | resolved | bounded tick 默认只准备，不执行；执行前仍需 claim |
| I-004 多模型本轮未完整认证 | 3 | accepted_risk | 标注 advisory，最终以 deterministic tests/selfcheck 为 gate |
| I-005 doctor 不得泄露 session/log 中 secret | 5 | resolved | warning hit 不输出 snippet，只输出 path/counters/source_kind |

无 severity>=4 unresolved blocker。

## 落地文件

- `/Users/charles/.hermes/scripts/iteration_budget_doctor.py`
- `/Users/charles/.hermes/scripts/brain_task_budget_tick.py`
- `/Users/charles/.hermes/scripts/iteration_budget_handoff_template.md`
- `/Users/charles/.hermes/scripts/test_iteration_budget_guard.py`
- `/Users/charles/.hermes/skills/autonomous-ai-agents/hermes-agent/references/tool-budget-and-permission-gates.md`
- `/Users/charles/Documents/brain/05-实践与项目/实践方案/Hermes自动化任务IterationBudget闭环策略.md`

## 验证

verification dir: `/tmp/iteration_budget_verify_20260508183533`

- py_compile: PASS
- test_iteration_budget_guard.py: 3 tests PASS
- iteration_budget_doctor.py: status OK, warnings 20, cron_jobs 22, at_risk_tasks 4
- brain_task_budget_tick.py: status OK, budget_action stop_and_handoff, p10_gate PASS
- brain_task_orchestrator selfcheck: PASS
- brain_task_orchestrator proof-check: PASS, only legacy warning
- skill-steward graph-check: status OK, cycles=0, depth_max=4
- brainctl sync: exit_code 0
- brainctl reindex: indexed_blocks 2359, skipped_secret_blocks 18
- brainctl search: 命中本任务与策略页

## P10 verdict

当前策略无 P10 blocker：

- 单会话有界：保留。
- 控制面和执行面：分离。
- cron 风险：script-first/no_agent 分层。
- task pool 执行：claim/proof/handoff。
- 多模型不完整：明确降级为 advisory，不冒充 full certification。

剩余后续增强：将 `brain_task_budget_tick.py` 与 idle-runner 的 claim/run/retry 自动执行阶段合并；当前版本先作为安全准备器，不自动执行任务内容。

## Evidence Boundary

Model agreement is provenance only; status promotion requires command/file/search proof recorded in this note or linked artifacts.

