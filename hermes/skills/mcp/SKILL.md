---
name: mcp
description: "Mcp workflow skill. See references/ for detailed guides."
license: MIT
metadata:
  hermes:
    tags: [mcp, protocol, integration]
    related_skills: [pua, loop]
---

# Mcp

> Mcp 相关的工作流 Skill

## 输入

- 用户请求的具体参数
- 相关上下文或文件路径

## 输出

- 执行结果或生成的文件
- 验证报告（如适用）

## 约束

- 遵循项目规范
- 不泄露敏感信息
- 在 context budget 内完成

## 边界条件

- MCP server 不可用时，返回明确错误并提示用户检查 server 状态
- 输入参数为空或缺失时，返回错误提示而非静默失败
- 超出 context budget 时，截断输入并告知用户
- 工具调用超时时，重试一次后返回部分结果

## 检查点

- [ ] 输入参数完整
- [ ] 输出符合预期格式
- [ ] MCP server 连接正常
- [ ] 验证通过

## Skill 路由决策树

```
想连接/使用 MCP Server?
  ├─ 配置为 Hermes 持久工具 → native-mcp
  ├─ 一次性/ad-hoc 调用 → mcporter
  └─ 了解协议原理 → 阅读本 skill 的 references/

想构建 MCP Server?
  ├─ 学习路线 (四阶段) → references/mcp-builder-learning-path.md
  ├─ 从零实现 (Python stdio) → mcp-server-from-scratch skill
  ├─ 设计模式 → references/code-intelligence-mcp-patterns.md
  └─ 补强评估 → references/mcp-skill-enhancement-assessment.md
```

## Code-intelligence MCP patterns

When designing or evaluating an MCP server for codebase intelligence, use `references/code-intelligence-mcp-patterns.md`. Prefer stable resources for repo/schema/process/contract/status context, tools for query/impact/detect-changes/rename/shape-check actions, and enforce freshness + impact-before-edit + detect-changes-before-commit guardrails. Treat MCP outputs as evidence with provenance, not as automatic truth certification.

## native-mcp vs mcporter 选型

| 维度 | native-mcp | mcporter |
|------|-----------|----------|
| 用途 | 持久化配置，每次对话可用 | ad-hoc 一次性调用 |
| 配置 | config.yaml mcp_servers 节 | 无需配置 / CLI 参数 |
| 启动 | Agent 启动时自动连接 | 每次调用时启动 |
| 适合 | 高频工具 (filesystem, github) | 探索/测试/临时任务 |
| 工具名 | mcp_{server}_{tool} | {server}.{tool} |
| 认证 | env 配置传递 | mcporter auth 交互式 |
| 采样 | 支持 (sampling 配置) | 不支持 |

经验法则：用过 3 次以上的 MCP server → native-mcp；试用/探索 → mcporter。

## 示例

### 示例 1: 基本用法


```
Input:  用户请求调用 MCP 工具
Output: 工具执行结果 + 验证报告
```

### 示例 2: Server 不可用

```
Input:  MCP server 连接失败
Output: 错误提示 "MCP server 不可用，请检查 server 状态后重试"
```

## 关联 Skill

- `pua`: 核心行为基线
- `loop`: 迭代管理
