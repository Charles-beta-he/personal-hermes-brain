---
name: gsd-bridge
description: "Hermes → GSD Bridge — 在 Hermes Agent 中调用 GSD (get-shit-done) 的 agents 和 workflows。用于项目级开发任务，与现有 skill 生态互补。Triggers: 'gsd', 'get-shit-done', '项目开发', 'phase规划', 'new-project', '代码构建', '/gsd'"
license: MIT
tags: [gsd, project-development, phase-planning, claude-code, bridge]
---

# GSD Bridge — Hermes ↔ GSD 集成

> GSD (get-shit-done) 已全局安装到 ~/.claude/
> 本 skill 提供 Hermes 调用 GSD 资源的统一入口。

## 架构关系

```
Hermes Agent (当前)          GSD (Claude Code 生态)
    │                              │
    ├── skill 管理 ←───────────────┤ (独立生态)
    ├── Agent 进化 ←───────────────┤ (独立生态)
    └── 项目开发 ──→ gsd-bridge ──→ ├── agents/ (33个)
                                      ├── workflows/ (87个)
                                      └── sdk/
```

**原则**: Hermes 负责 skill 管理和 Agent 进化，GSD 负责具体项目开发。
两者互补，不重叠。

## 可用资源

### GSD Agents (33个)

| Agent | 功能 | 触发场景 |
|-------|------|---------|
| gsd-planner | 创建可执行 phase 计划 | 需要拆任务时 |
| gsd-executor | 执行计划，波次并行 | 编码实现时 |
| gsd-verifier | 验证工作成果 | 交付前检查 |
| gsd-debugger | 系统调试 | 顽固 bug 时 |
| gsd-code-reviewer | 代码审查 | PR 级改动 |
| gsd-roadmapper | 创建路线图 | 新项目初始化 |
| gsd-phase-researcher | 研究 phase 实现方案 | 技术选型时 |

完整列表: `ls ~/.claude/get-shit-done/agents/`

### GSD Workflows (87个)

| Workflow | 功能 | 触发命令 |
|---------|------|---------|
| do.md | 智能命令路由 | /gsd:do |
| new-project.md | 新项目初始化 | /gsd:new-project |
| plan-phase.md | Phase 规划 | /gsd:plan-phase |
| execute-phase.md | Phase 执行 | /gsd:execute-phase |
| verify-work.md | 工作验证 | /gsd:verify-work |
| debug.md | 调试工作流 | /gsd:debug |

完整列表: `ls ~/.claude/get-shit-done/workflows/`

## 使用方式

### 方式 1: 直接调用 GSD CLI

```bash
# 新项目初始化
gsd-sdk query state.init --path ./my-project

# 查看当前状态
gsd-sdk query state.load

# 执行 phase
gsd-sdk execute phase --number 1
```

### 方式 2: 读取 GSD Agent 定义

```
需要深度规划时:
→ 读取 ~/.claude/get-shit-done/agents/gsd-planner.md
→ 按 agent 定义执行规划流程
```

### 方式 3: 读取 GSD Workflow

```
需要执行特定工作流时:
→ 读取 ~/.claude/get-shit-done/workflows/{workflow}.md
→ 按 workflow 定义的步骤执行
```

## 与现有体系的集成

### 与 control-theory 集成
- GSD 的 phase 执行 → 参考模型中的 [3] 编码实现阶段
- GSD 的 verify-work → 参考模型中的 [5] 验证测试阶段
- GSD 的 wave execution → 自适应采样中的波次并行

### 与 darwin-skill 集成
- GSD skill 的 Darwin 评分: 单独评估，不影响 Hermes skill 生态
- GSD 优化后的 skill → 可考虑迁移到 Hermes 生态

### 与 bayesian-agent 集成
- GSD agent 的置信度: 单独维护，不与 Hermes skill 混用
- 项目成功率同时计入 Hermes 健康度 V

## 限制

1. GSD 的 hooks 只在 Claude Code 运行时生效，Hermes 中不可用
2. GSD 的 context monitor、statusline 等需要 Claude Code 环境
3. GSD SDK 的完整功能需要 `gsd-sdk` CLI 在 PATH 中

## 安装检查

```bash
# 检查 GSD 是否已安装
ls ~/.claude/get-shit-done/

# 检查 SDK
ls ~/.claude/get-shit-done/sdk/dist/cli.js

# 检查 agents
ls ~/.claude/agents/ | grep gsd- | wc -l
```
