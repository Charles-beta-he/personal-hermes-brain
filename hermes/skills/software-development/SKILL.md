---
name: software-development
description: "Meta-skill for software development workflows. Contains sub-skills for TDD, debugging, architecture optimization, UI audit, visual regression, and more. Use as a directory to discover specific development skills."
license: MIT
---

# Software Development — 软件开发工作流集合

> 元 Skill：包含所有软件开发相关的专项 Skill

## 子 Skill 列表

| Skill | 用途 | 触发条件 |
|-------|------|---------|
| `test-driven-development` | TDD 执行规范 | 实现功能或修复 bug 前 |
| `systematic-debugging` | 调试方法论 | 遇到 bug 或测试失败 |
| `requesting-code-review` | 预提交验证 | 准备提交代码 |
| `post-deploy-verification` | 部署后验证 | 代码上线后 |
| `uimax-audit` | UI 质量审计 | 前端改动后 |
| `visual-regression` | 视觉回归检测 | UI 变更后 |
| `color-contrast-checker` | WCAG 对比度检查 | 前端样式修改 |
| `browser-harness-integration` | 浏览器验证 | 需要端到端测试 |
| `architecture-optimization-loop` | 架构优化 | 系统重构或性能优化 |
| `subagent-driven-development` | Sub-agent 开发 | 复杂多模块任务 |
| `auto-optimize-loop` | 自循环优化 | 代码库持续优化 |
| `animation-system-optimization` | 动效系统优化 | 动画相关优化 |
| `hermes-workflow-orchestrator` | 工作流编排 | 构建自动化流程 |
| `arc-dispatch-executor` | 任务执行 | Lark 任务自动执行 |
| `requirement-clarification` | 需求澄清 | 接任务时 |
| `writing-plans` | 计划编写 | 多步骤任务规划 |
| `plan` | Plan 模式 | 需要详细规划 |
| `theory-driven-evolution` | 理论驱动进化 | 引入新理论框架 |
| `skill-eval` | Skill 评估 | 评估 skill 质量 |
| `workflow-ecosystem-audit` | 生态审计 | 审计工作流覆盖 |
| `incident-response` | 事故响应 | 线上问题 |

## 使用方式

不要直接调用 `software-development`，而是根据具体场景选择上述子 Skill。

## 输入

- 开发任务描述
- 当前技术栈信息

## 输出

- 根据选择的子 Skill 输出对应交付物

## 约束

- 始终先选择最具体的子 Skill，而非使用此元 Skill
- 如不确定，调用 `requirement-clarification` 先澄清

## 关联 Skill

- `p9`: 任务拆解（复杂开发任务先拆解）
- `p7`: 代码执行（子 Skill 的下游）
- `loop`: 迭代优化


## 约束

- 遵循项目规范
- 在 context budget 内完成


## 约束

- 遵循项目规范
- 在 context budget 内完成


## 检查点

- [ ] 输入参数完整
- [ ] 输出符合预期格式


## 示例

```bash
# 示例: 使用本 skill 执行开发任务
```
