---
type: theory-note
layer: L1
status: active
created: 2026-05-06T13:35:04Z
concepts: [control-theory, agent-governance, evidence-boundary]
---

# Lyapunov 稳定性与 Agent 回归边界

把系统稳定性理解为状态偏离后仍能回到可接受区域；Agent 工程中对应回归测试、健康度阈值、错误预算和停止门。

## Hermes mapping

- 用于 P10/P9/Loop 自检时判断反馈、稳定性、置信度与工具边界。
- 与 [[07-工程控制论到Agent闭环]]、[[08-控制论基础参考书目与证据]] 互相印证。

## Evidence Boundary

- 来源支持什么：经典控制理论为状态、反馈、估计、控制目标提供形式化语言。
- Hermes 映射边界：这里是工程治理类比，不是对 Agent 行为的数学稳定性证明。
- 不应过度推出什么：不得仅凭本卡宣称多模型结论正确；必须结合本地工具证据、运行结果与审计输出。

关键词：Lyapunov Kalman observability controllability optimal control adaptive control 可观测性 可控性 最优控制 自适应控制。
