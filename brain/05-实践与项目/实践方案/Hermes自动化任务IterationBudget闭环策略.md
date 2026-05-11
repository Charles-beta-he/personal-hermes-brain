---
type: practice
layer: L5
status: current
created: 2026-05-08T18:35:00+08:00
updated: 2026-05-08T18:35:00+08:00
project: hermes-automation-budget
concepts: [iteration-budget, bounded-tick, pua-loop, proof-gate, task-pool]
---

# Hermes 自动化任务 Iteration Budget 闭环策略

## P10 决策

`Iteration budget reached (N/N) — response may be incomplete` 是控制系统饱和信号，不是单纯“把 max_turns 调大”的配置问题。

策略：

1. 默认保持单会话有界。
2. 机械/控制面 cron 优先 `script_first_no_agent`。
3. 需要 LLM 的 cron 使用 script + tiny summarizer。
4. 长任务必须拆成 bounded tick：plan -> execute slice -> verify -> proof/handoff。
5. 接近预算时必须写 handoff，不允许声称 done。
6. done 必须走结构化 evidence gate。

## 落地组件

- `~/.hermes/scripts/iteration_budget_doctor.py`
  - read-only doctor。
  - 输出 agent/delegation cap、近期 warning hit、cron 风险形态、任务池自动化相关任务。
  - 不输出 secret value；`.env` 只检查 key presence。

- `~/.hermes/scripts/brain_task_budget_tick.py`
  - bounded task tick。
  - 默认不 claim、不执行、不 done。
  - 从 canonical task pool 选一项或接受 `--task`。
  - 分类 risk / execution_mode。
  - 计算 safety margin 后的剩余预算。
  - 写 `~/.hermes/artifacts/iteration-budget/*/handoff.md`。

- `~/.hermes/scripts/iteration_budget_handoff_template.md`
  - 固化 handoff 字段、resume 规则和 proof gate。

## Execution modes

| Mode | 用途 | 默认策略 |
|---|---|---|
| `script_first_no_agent` | deterministic cron / watchdog / control-plane | no_agent=True，不烧 LLM 迭代 |
| `tiny_summarizer` | 脚本输出需要人类摘要 | LLM 只摘要，不执行循环 |
| `bounded_agent_tick` | 本地大脑任务执行 | claim 一项，做一片，proof 或 handoff |
| `single_shot_capped` | 小型一次性任务 | 硬 cap，无递归 fanout |
| `manual` | P0/high-risk/destructive/external | 人工触发，不自动跑 |

## PUA-loop 约束

Loop 不允许以“预算耗尽”为借口输出半成品：

- 预算 80% 后停止开新方向。
- 写 handoff artifact。
- 明确 next bounded command。
- 若任务已 claim，必须 release/retry/done 之一。
- 无 proof 不得 done。

## 多模型审查结果

本轮 T2 fan-out artifact：

- `/Users/charles/.hermes/tick-20260508-101930`

状态：

- gpt-5.5 与 claude-opus-4-7 均建议：doctor + bounded tick + handoff template + policy landing。
- MiMo JSON parse/invoke failed。
- consensus_verdict: weak_consensus。
- discussion 未完成，不能称完整 ratification。

因此本次状态是：multi-model advisory + deterministic gates，不是 full certification。

## P10 issue ledger

| Issue | Severity | Status | Resolution |
|---|---:|---|---|
| I-001 单纯调大 max_turns 会掩盖无界 daemon 风险 | 5 | resolved | 默认保留 bounded cap，增加 handoff/tick |
| I-002 cron/自动任务不应把机械循环交给 LLM | 4 | resolved | script_first_no_agent / tiny_summarizer 分层 |
| I-003 task pool 执行必须 claim/release/retry/done/proof | 5 | resolved | bounded tick 默认只准备，不执行；执行前仍需 claim |
| I-004 多模型本轮未完整认证 | 3 | accepted_risk | 标注 advisory，最终以 deterministic tests/selfcheck 为 gate |
| I-005 doctor 不得泄露 session/log 中 secret | 5 | resolved | warning hit 不输出 snippet，只输出 path/counters/source_kind |

## Verification commands

```bash
python3 -m py_compile ~/.hermes/scripts/iteration_budget_doctor.py ~/.hermes/scripts/brain_task_budget_tick.py ~/.hermes/scripts/test_iteration_budget_guard.py
python3 ~/.hermes/scripts/test_iteration_budget_guard.py -v
python3 ~/.hermes/scripts/iteration_budget_doctor.py --json
python3 ~/.hermes/scripts/brain_task_budget_tick.py --spent-tool-calls 50 --max-tool-calls 60 --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "iteration-budget bounded-tick pua-loop" --limit 10
```
