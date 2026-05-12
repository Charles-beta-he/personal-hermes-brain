# MCP Builder 四阶段学习路线

> 从零到生产级 MCP Server 的结构化学习路径。
> 每阶段独立可验证，失败可回退到上一阶段。

## 适用场景

- 用户想学习构建 MCP Server
- 用户已有 MCP 经验想进阶
- 评估团队成员的 MCP 能力等级

## 阶段总览

```
Stage 1: 协议理解 (Protocol Literacy)     → 理解 MCP 是什么
Stage 2: 最小实现 (Minimal Implementation) → 能跑起来
Stage 3: 实战构建 (Production Builder)     → 处理真实场景
Stage 4: 生态贡献 (Ecosystem Contributor)  → 可分享可复用
```

---

## Stage 1: 协议理解 (Protocol Literacy)

**目标**: 理解 MCP 是什么、为什么存在、协议结构

**前置知识**: HTTP/JSON 基础, CLI 工具使用

**学习内容**:

1. MCP 协议概述
   - MCP = Model Context Protocol = AI 应用与外部工具/数据的标准化接口
   - 类比: MCP 之于 AI Agent = USB 之于电脑
   - 三种原语: Tools (动作), Resources (数据), Prompts (模板)

2. 传输层
   - Stdio: 进程间通信 (stdin/stdout JSON-RPC) — 本地首选
   - HTTP/SSE: 远程服务器 (Streamable HTTP) — 远程/共享首选

3. 协议生命周期
   ```
   Client                    Server
     |-- initialize -------->|
     |<-- initialize resp ---|
     |-- initialized ------->|  (notification, no response)
     |-- tools/list -------->|
     |<-- tools list --------|
     |-- tools/call -------->|
     |<-- tool result -------|
   ```

4. JSON-RPC 2.0 核心
   - Request:  {"jsonrpc":"2.0", "id":N, "method":"...", "params":{...}}
   - Response: {"jsonrpc":"2.0", "id":N, "result":{...}}
   - Notification: {"jsonrpc":"2.0", "method":"...", "params":{...}} — 无 id, 不返回响应
   - Error: {"jsonrpc":"2.0", "id":N, "error":{"code":-32601, "message":"..."}}

**验证点**: 能画出握手流程 | 能区分 Request vs Notification | 能解释三种原语

**资源**: https://modelcontextprotocol.io | https://spec.modelcontextprotocol.io

**关联 Skill**: `mcp` (总览), `native-mcp` (客户端侧理解)

---

## Stage 2: 最小实现 (Minimal Implementation)

**目标**: 用最少代码实现一个可工作的 MCP Server

**前置知识**: Stage 1, Python 或 TypeScript 基础

### Path A: 无 SDK (推荐 — 理解原理)

**使用 Skill**: `mcp-server-from-scratch`

核心要点:
1. 读 stdin 逐行 JSON, 写 stdout 逐行 JSON
2. 三个 method 必须处理: initialize, tools/list, tools/call
3. notification (无 id) 不返回响应
4. 每条 print 后必须 flush=True

**实战练习**: 实现 `echo` MCP Server (1 tool, ~10 行核心代码)

**验证点**: mcporter 能连接并调用 | initialize 握手成功 | unknown method 返回 error

### Path B: 用 SDK (推荐 — 快速开发)

```python
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("my-server")

@server.list_tools()
async def list_tools():
    return [Tool(name="echo", description="Echo input", inputSchema={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"]
    })]

@server.call_tool()
async def call_tool(name, arguments):
    if name == "echo":
        return [TextContent(type="text", text=arguments["text"])]

server.run()
```

**验证点**: Server 启动响应 tools/list | Tool 调用返回正确结果 | 错误输入不 crash

---

## Stage 3: 实战构建 (Production Builder)

**目标**: 构建有实际价值的 MCP Server

**前置知识**: Stage 2, 能独立实现一个 tool

**学习内容**:

1. **多 Tool 设计**: 单一职责, snake_case 命名, 完整 inputSchema
2. **Resources**: 只读数据暴露 (配置/状态/schema)
3. **Prompts**: 参数化模板 (标准化分析/报告/审查)
4. **错误处理**: isError + 友好消息, 不暴露路径/凭证
5. **安全性**: 输入验证, 最小权限, 凭证隔离, 路径遍历防护
6. **HTTP Transport**: Streamable HTTP 进阶

**实战项目** (三选一):
- A: Git 操作 MCP Server (6 tools — 参见 mcp-server-from-scratch 实战案例)
- B: 数据库查询 MCP Server (read-only SQL)
- C: API 聚合 MCP Server (封装第三方 API)

**验证点**: 3+ tools 完整 schema | 错误处理正确 | Hermes 注册可用 | 安全无泄露

**关联 Skill**: `mcp-server-from-scratch` (实现), `native-mcp` (注册到 Hermes)

---

## Stage 4: 生态贡献 (Ecosystem Contributor)

**目标**: 构建可复用、可分享的 MCP Server

**前置知识**: Stage 3, 至少一个实战 MCP Server

**学习内容**:

1. **发布**: npm (`npx -y`), PyPI (`uvx`), Docker
2. **测试**: 单元 → 集成 (完整握手) → E2E (客户端调用)
3. **文档**: README (一句话 + 快速开始) + LLM 友好的 tool description
4. **高级模式**: Sampling, Dynamic tools, Streaming, Multi-repo contracts
5. **可靠性**: 幂等性, 超时设计, 资源限制, 防无限循环

**验证点**: npm/uvx 可安装 | 测试覆盖 | LLM 友好描述 | 文档完整

**关联 Skill**: `mcp` (code-intelligence-mcp-patterns)

---

## 阶段自评

| 转换 | 必须做到 |
|------|---------|
| 1→2 | 不查文档画出握手流程, 理解 id/notification 区别 |
| 2→3 | 独立实现 3+ tool Server, 在 Hermes 注册可用 |
| 3→4 | 有真实场景 Server, 理解安全边界和错误处理 |

## Skill 依赖图

```
Stage 1: mcp + native-mcp (读)
Stage 2: mcp-server-from-scratch (做)
Stage 3: native-mcp (注册) + mcp-server-from-scratch (实现)
Stage 4: mcp/code-intelligence-mcp-patterns (设计模式)
```
