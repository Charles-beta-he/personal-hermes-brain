---
title: P10 - 系统工程式Agent自进化策略
created: 2026-05-08
status: active
type: strategy
---

# P10 - 系统工程式Agent自进化策略

## 战略判断

当前缺口不是“没有记忆”或“没有 skill”，而是缺少系统工程式中间层：

- memory 太全局，不能承担项目工作台。
- skill graph 只描述技能依赖，不描述项目语义路线。
- session todo 太短命，不能跨会话沉淀项目状态。
- 本地大脑有项目/模板/实践方案层级，但之前缺少把三者串起来的控制面。

## 战略原则

1. 目标先行：每个项目先有 north star 和禁改红线。
2. 锚点锁定：原型、参考仓库、API、字段展示、UI 行为都要成为 anchor。
3. 分解协调：项目拆成业务子系统、技术子系统、验收子系统。
4. 反馈稳定：每轮 loop 只能通过验证结果推进状态，不能靠主观“应该好了”。
5. 综合集成：多模型、测试、用户校正、git、文档沉淀共同形成判断。
6. 局部可逆：先 landing overlay，不动 runtime。

## P10 风险

- Goodhart：A+ 分数可能变成指标游戏，必须保留真实交互验收。
- 幽灵记忆：不能把项目临时进度写入 memory。
- 模板泛化过度：前端闭环模板可复用，但业务流程必须项目化。
- 多模型幻觉：模型只能审方案，证据来自工具。

## Stop Condition

当一个项目 workpad 同时具备：north star、anchors、red lines、skill route、business flow matrix、acceptance matrix、evidence ledger、next loop queue、done criteria，即可认为进入系统工程控制面。
