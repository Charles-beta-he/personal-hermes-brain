---
title: Agent系统工程控制面
created: 2026-05-08
status: active_overlay
source: 钱学森《论系统工程》系统工程思想重构 + Hermes 多模型证据
multi_model_tick: /Users/charles/.hermes/tick-20260508-074429
truth_status: grounded
verified_claim_count: 5/5
type: project
---

# Project - Agent系统工程控制面

## 北极星

把 Hermes 从“全局 memory + 一堆 skills + 当前 session todo”升级为系统工程式控制面：

- 全局技能树：知道什么类型任务该走哪条能力链。
- 项目工作记忆：不同项目拥有独立 north star、红线、锚点、验收矩阵和证据账本。
- 跨项目领域模板：前端闭环验收、UI 测试、代码修改流程可复用。
- 反馈闭环：每轮执行后把证据、验收、偏差、沉淀写回 brain/模板/skill，而不是只留在会话压缩里。

## 非目标

- 不重写 Obsidian 主层级。
- 不把所有项目细节塞进 persistent memory。
- 不把多模型当作唯一真理来源；多模型只做方案审查，事实由工具证据认证。
- 不改 Hermes runtime，先以可逆 Markdown overlay + self-check 落地。

## 钱学森系统工程映射

| 系统工程概念 | Agent 控制面落点 |
|---|---|
| 总体设计 | P10 北极星、项目目标、禁改红线 |
| 分解协调 | P9 任务树、skill route matrix、子系统接口 |
| 定性到定量 | 用户判断 + 测试用例、覆盖率、truth gate、build/test 结果 |
| 综合集成 | 多模型 + deterministic gate + 本地大脑证据汇总 |
| 人机结合 | 用户校正优先，Agent 执行/检索/验证 |
| 反馈闭环 | loop 结束后更新 workpad、UI_TEST_CASES、ADR、memory/skill |
| 知识沉淀 | brain atoms/templates/playbooks/project workpads |

## 分层模型

1. Memory：只放跨会话仍然稳定的用户偏好和极少数路径事实。
2. Skill Tree：放任务类型→能力链路，不放具体项目状态。
3. Project Workpad：放项目专属目标、锚点、红线、业务流程、证据账本。
4. Session Todo：放当前会话短期执行状态。
5. Evidence Artifacts：放验证报告、multi-model tick、测试日志、manifest。

## 成功标准

- brain 能搜到“技能树 项目工作记忆 前端闭环验收”。
- 新前端项目可复制 `项目工作记忆模板` 初始化 workpad。
- 前端项目 loop 可调用 `前端闭环验收标准` 形成统一验收口径。
- self-check 脚本 PASS。
