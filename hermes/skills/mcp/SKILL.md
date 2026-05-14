---
name: mcp
description: Use when you need the Mcp workflow umbrella. See references/ for detailed
  guides.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - mcp
    - protocol
    - integration
    - umbrella
    - routing
    related_skills:
    - mcporter
    - native-mcp
---

# Mcp

## Overview

This umbrella skill is the routing surface for mcp. Use it to choose the most specific child skill, reference, or workflow instead of treating the category name as a one-size-fits-all procedure.

## When to Use

- You need help somewhere inside mcp and want the quickest route to the right child skill.
- You are not yet sure which mcp sub-workflow best matches the request.
- You want a compact map of the mcp skill family before loading a more specific procedure.
- Don't use for: a request that already clearly matches one specific mcp child skill; load that child skill directly.

## Routing Guide

- `mcporter` — you need to use the mcporter CLI to list, configure, auth, and call MCP servers/tools directly (HTTP or stdio), including ad-hoc servers, config edits, and CLI/type generation.
- `native-mcp` — you need guidance on built-in MCP (Model Context Protocol) client that connects to external MCP servers, discovers their tools, and registers them as native Hermes Agent tools.

## Selection Rules

- Prefer the narrowest child skill that matches the user request, platform, and desired artifact.
- Stay at the umbrella level only for routing, taxonomy, or category-wide orientation.
- If the request spans multiple subskills, use this umbrella to map the lane first, then hand off to the specific workflow that will do the real work.

## 边界条件

- MCP server 不可用时，返回明确错误并提示用户检查 server 状态
- 输入参数为空或缺失时，返回错误提示而非静默失败
- 超出 context budget 时，截断输入并告知用户
- 工具调用超时时，重试一次后返回部分结果

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

## MCP Server minimal template / test checklist

When evaluating or building a new MCP server, use the minimal server contract and test ladder captured in `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/mcp-server-minimal-template-test-checklist-2026-05-13.md`: stdout JSON-RPC only, stderr logs, initialize/initialized/tools-list/tools-call coverage, complete inputSchema, unknown method/tool errors, secret redaction, path traversal rejection, bounded timeout/output, and unit → stdio transcript → mcporter/native-mcp smoke → malicious input tests.

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

## Common Pitfalls

1. Using the mcp umbrella as the full procedure even though a more specific child skill already fits.
2. Reading the routing map but never loading the referenced child skill or support material that contains the actual execution steps.
3. Choosing a child skill without checking that its platform, tools, and expected artifacts match the current task.

## Verification Checklist

- [ ] The request was mapped to the best-fitting child skill or explicitly kept at umbrella level for routing only.
- [ ] The selected child skill descriptions, references, and prerequisites were checked before substantive execution.
- [ ] Any claimed handoff, output, or route decision was read back against the specific child workflow before completion.

