# Hermes MCP Skill 补强评估

> 评估日期: 2026-05-12
> 评估范围: mcp, native-mcp, mcporter, mcp-server-from-scratch
> 评估标准: 覆盖度, 实用性, 一致性, 缺口

---

## 现有 Skill 矩阵

| Skill | 定位 | 覆盖阶段 | 质量 |
|-------|------|---------|------|
| `mcp` | 总览/入口 | 全阶段路由 | ★★★☆☆ |
| `native-mcp` | Hermes 内置 MCP 客户端 | Stage 1 (理解), Stage 3 (注册) | ★★★★★ |
| `mcporter` | CLI ad-hoc MCP 调用 | Stage 1 (探索), Stage 2 (测试) | ★★★★☆ |
| `mcp-server-from-scratch` | 从零构建 MCP Server | Stage 2, Stage 3 | ★★★★☆ |

---

## 逐项评估

### 1. `mcp` (总览 Skill)

**优势**:
- 有 code-intelligence-mcp-patterns 参考 (设计模式)
- 边界条件和检查点定义清晰

**不足**:
- references/skill-overview.md 内容过于泛化, 无实操价值
- references/README.md 为空
- 缺少: 协议版本对照表, 传输层选型决策树
- 缺少: 与 native-mcp/mcporter 的使用场景路由

**补强建议**:
- [x] 添加 mcp-builder-learning-path.md (已完成)
- [x] 更新 SKILL.md 添加学习路线路由入口 (已完成)
- [ ] 添加协议版本兼容性参考

### 2. `native-mcp` (Hermes MCP 客户端)

**优势**:
- 文档完整度极高: 配置参考、安全、故障排除全覆盖
- 传输层 (stdio/HTTP) 双支持
- Sampling 配置详尽
- 环境变量过滤和凭证脱敏

**不足**:
- 无 references/ 子目录, 所有内容集中在 SKILL.md (447 行, 偏长)
- 缺少: 与 mcporter 的对比选型指南
- 缺少: config.yaml 的完整示例模板

**补强建议**:
- [ ] 拆分 Troubleshooting 到 references/troubleshooting.md
- [ ] 添加 "native-mcp vs mcporter" 选型决策

### 3. `mcporter` (CLI MCP 工具)

**优势**:
- 覆盖完整: list/call/auth/config/daemon/generate
- ad-hoc 模式 (无需配置即可调用)
- code generation 能力

**不足**:
- 缺少: 实际使用示例 (从发现到调用的完整流程)
- 缺少: 与 native-mcp 的使用场景对比
- 缺少: OAuth 流程的非交互式处理

**补强建议**:
- [ ] 添加 "从发现到调用" 的端到端示例
- [ ] 添加 native-mcp vs mcporter 选型表

### 4. `mcp-server-from-scratch` (构建 MCP Server)

**优势**:
- 实战导向: 有完整模板代码和 Git Server 案例
- Pitfalls 部分从真实调试中总结, 价值高
- 测试代码模板实用

**不足**:
- 仅覆盖 Python stdio, 缺少 TypeScript 实现
- 缺少: HTTP Transport 实现指南
- 缺少: Resources 和 Prompts 的实现示例
- 缺少: SDK 方式 (Path B) 的详细指南
- Pitfalls 第 7/8 条缺失 (编号跳到 9)

**补强建议**:
- [ ] 添加 TypeScript 版本模板
- [ ] 添加 Resources/Prompts 实现示例
- [x] 修复 Pitfalls 编号 (7, 8 已补全)
- [ ] 添加 SDK Path B 的完整示例

---

## 关键缺口分析

### 缺口 1: 学习路线缺失 (严重)
**状态**: 已补强 — `references/mcp-builder-learning-path.md` 已创建

### 缺口 2: Skill 间路由缺失 (中等)
**现状**: 用户不知道何时用哪个 skill
**建议**: 在 mcp SKILL.md 添加决策树:
```
想连接/使用 MCP Server?
  ├─ 配置为 Hermes 工具 → native-mcp
  ├─ 一次性/ad-hoc 调用 → mcporter
  └─ 了解协议原理 → mcp (references/)

想构建 MCP Server?
  ├─ 从零实现 → mcp-server-from-scratch
  ├─ 学习路线 → mcp (references/mcp-builder-learning-path.md)
  └─ 设计模式 → mcp (references/code-intelligence-mcp-patterns.md)
```

### 缺口 3: TypeScript MCP Server 模板缺失 (低)
**现状**: mcp-server-from-scratch 仅 Python
**建议**: 添加 TypeScript SDK 模板到 references/

### 缺口 4: 测试模式未标准化 (低)
**现状**: mcp-server-from-scratch 有测试代码但未形成模式
**建议**: 提取 MCP Server 测试模式到独立参考

---

## 优先级排序

| 优先级 | 补强项 | 影响 | 工作量 |
|--------|--------|------|--------|
| P0 | 学习路线参考 | ★★★★★ | 已完成 |
| P1 | Skill 间路由决策树 | ★★★★☆ | 已完成 |
| P1 | native-mcp vs mcporter 选型 | ★★★★☆ | 已完成 |
| P2 | TypeScript MCP Server 模板 | ★★★☆☆ | 中 |
| P2 | Resources/Prompts 实现示例 | ★★★☆☆ | 中 |
| P3 | MCP Server 测试模式 | ★★☆☆☆ | 小 |

---

## 总结

Hermes MCP skill 生态覆盖了 "使用 MCP" 和 "构建 MCP Server" 两大方向,
核心能力完整 (native-mcp 文档质量极高, mcp-server-from-scratch 实战性强)。

主要缺口:
1. 学习路线 — 已通过 mcp-builder-learning-path.md 补强
2. Skill 间路由 — 已在 mcp SKILL.md 添加决策树
3. native-mcp vs mcporter 选型 — 已添加对比表
4. Pitfalls 编号 — 已修复 mcp-server-from-scratch #7/#8
5. TypeScript 模板 — 低优先级, Python 路径已足够入门

生态成熟度: ★★★★☆ (4/5) — 核心能力完整, 路由已补, 进阶内容 (TS模板/Resources/Prompts) 待补
