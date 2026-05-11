---
title: Agent技能树路由矩阵
created: 2026-05-08
type: control-plane-overlay
concepts: [skill tree, route matrix, project memory, systems engineering, agent control plane]
status: current
---

# Agent技能树路由矩阵

> 目的：补上“有很多 skills，但没有显式项目路线图”的缺口。它不替代 skill graph；它把任务类型映射到可执行能力链。

## 四层技能树

| 层 | 作用 | 存放内容 | 不应存放 |
|---|---|---|---|
| L0 理论/治理 | 决定为什么这样做 | 系统工程、控制论、P10、风险路由 | 具体项目进度 |
| L1 通用领域 | 决定做哪类事 | 前端、后端、文档、MCP、研究、桌面整理 | 项目专属业务状态 |
| L2 项目工作流 | 决定这个项目如何做 | workpad、anchors、red lines、验收矩阵 | 全局用户画像 |
| L3 会话执行 | 决定现在做哪一步 | todo、临时假设、当前验证命令 | 跨会话稳定事实 |

## 前端项目默认路线

| 阶段             | 技能/能力链                                                                                               | 输出                  |
| -------------- | ---------------------------------------------------------------------------------------------------- | ------------------- |
| Intake         | requirement-clarification + source-driven-development + read-repo                                    | 目标、非目标、锚点、风险        |
| Architecture   | p10 + p9 + architecture-optimization-loop                                                            | P10/P9 任务树          |
| Implementation | test-driven-development + incremental-implementation + project modify-code                           | 小切片修改与回归测试          |
| UI Closure     | browser-harness-integration + visual-regression + uimax-audit + fixing-accessibility/motion/metadata | 交互闭环证据              |
| Verification   | requesting-code-review + post-deploy-verification + multi-model-thinking(按风险)                        | build/test/UI/多模型验证 |
| Deposition     | obsidian + project workpad + ADR/UI_TEST_CASES                                                       | 项目记忆沉淀              |

## 任务池 / 长期闭环路线

| 阶段            | 技能/能力链                                            | 输出                                               |
| ------------- | ------------------------------------------------- | ------------------------------------------------ |
| Intake        | obsidian + local-brain-task-orchestration         | canonical task note，而不是 session-local todo       |
| Reconcile     | brain_task_orchestrator reconcile + proof-check   | stale lease / expired / due retry 调和结果           |
| Safe Dispatch | brain_task_dispatch_tick + dispatch-dry-run       | 只给下一任务 hint，不自动执行、不自动 done                       |
| Execution     | p9 + loop + 项目专属 skill route                      | claim -> execute -> verify -> done/retry/release |
| Proof Gate    | proof-check + brainctl sync/reindex/search        | 结构化 evidence；done 不允许空口完成                        |
| Cadence       | no_agent cron local-brain-task-dispatch-safe-tick | 静默定时 tick；有变化/错误才输出                              |

## 外部 GitHub 项目分析 -> 技能树完善路线

| 阶段                 | 技能/能力链                                                 | 输出                                                |
| ------------------ | ------------------------------------------------------ | ------------------------------------------------- |
| Recon              | github + framework-audit + source-driven-development   | repo 结构、核心概念、可借鉴/不采纳边界                            |
| Multi-model Review | multi-model-thinking(T1/T2 按风险) + ratification gate    | scoped claims/evidence/issue ledger，不把模型共识当事实     |
| Skill Gap Mapping  | skill-ecosystem-governance + Agent技能树路由矩阵              | 新增/修改 skill 的最小必要清单                               |
| Landing            | obsidian + hermes-agent-skill-authoring                | Project/Review/Evolution/Task proof + skill patch |
| Verification       | skill-steward graph-check + py_compile/test/build(按项目) | graph 无环/深度合规，脚本和文档可检索                            |

## GUI / Computer-use agent 评估路线

| 阶段 | 技能/能力链 | 输出 |
|---|---|---|
| Recon | framework-audit + `references/gui-computer-use-agent-audit.md` + github | 固定 commit/license/entry point，读取 README/CLI/wrapper/grounding/action/local-env |
| Safety Boundary | macos-computer-use + browser-harness-integration + requesting-code-review | screen/OCR/grounding/Accessibility/clipboard/shell/log-redaction 风险矩阵 |
| Evidence Closure | multi-model-thinking(按风险) + visual-regression/browser artifacts | trajectory screenshot/trace/fact-caption/judge artifact；不把截图 smoke 当完成证明 |
| Landing | skill-ecosystem-governance + hermes-agent-skill-authoring | 只提炼 capability doctor/action contract/evaluator，不默认安装外部 GUI runtime |

## 路由规则

- 低风险单文件：L1 + L3 即可，不跑四模型。
- 跨模块业务流：L1 + L2 + browser/Playwright 验证。
- 架构/原型漂移/删除功能：必须 P10 + workpad anchors + 多模型 T2/T3。
- 任务池事实源必须是 `05-实践与项目/tasks/*.md` frontmatter；Dashboard/排序池只是 derived view。
- `done` 必须有结构化 evidence（`command:`/`file:`/`brainctl:`/`search:`/`artifact:`/`url:`），否则 proof gate FAIL；英文检索锚点：`proof-check structured evidence`。
- 外部 GitHub 项目只先做 selective extraction；除非另有决策，不采纳整套 runtime。
- 项目状态、业务流程、验收矩阵进入 Project Workpad，不进 persistent memory。
- 用户稳定偏好、职业目标、长期红线进入 memory；但必须压缩成不会过期的事实。

## 与 Skill Graph 2.0 的区别

- Skill Graph：skill 之间有没有循环、深度、依赖，属于拓扑健康。
- Skill Route Matrix：某类任务应该加载/执行哪些技能，属于语义控制面。

两者互补：前者防混乱，后者防“会很多但不会调度”。
