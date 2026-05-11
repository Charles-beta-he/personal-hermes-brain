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

## Code-intelligence MCP patterns

When designing or evaluating an MCP server for codebase intelligence, use `references/code-intelligence-mcp-patterns.md`. Prefer stable resources for repo/schema/process/contract/status context, tools for query/impact/detect-changes/rename/shape-check actions, and enforce freshness + impact-before-edit + detect-changes-before-commit guardrails. Treat MCP outputs as evidence with provenance, not as automatic truth certification.

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
