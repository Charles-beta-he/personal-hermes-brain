---
name: mcp-server-from-scratch
description: Use when the task falls under MCP Server From Scratch.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - software
    - development
    - mcp
    - server
    - scratch
    related_skills:
    - mcp
---

# MCP Server From Scratch

## Overview


> 当 npm/uvx 上没有现成的 MCP server 时, 按协议自行实现。
> 不需要 MCP SDK — MCP 协议就是 JSON-RPC over stdio。

## When to Use

- The task falls under MCP Server From Scratch

## MCP 协议 (最小实现)

MCP (Model Context Protocol) 服务器是一个 stdio 进程, 通过 stdin/stdout 收发 JSON-RPC 2.0 消息。

### 三步握手

```
Client → Server: {"method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{}}}
Server → Client: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"xxx","version":"0.1.0"}}}

Client → Server: {"method":"notifications/initialized","params":{}}
Server → Client: (无响应 — 这是 notification, 没有 id)

Client → Server: {"method":"tools/list","id":2,"params":{}}
Server → Client: {"jsonrpc":"2.0","id":2,"result":{"tools":[...tool definitions...]}}

Client → Server: {"method":"tools/call","id":3,"params":{"name":"tool_name","arguments":{...}}}
Server → Client: {"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"output"}],"isError":false}}
```

### 关键协议细节

1. **Server 端不能主动发消息** — 只能响应. 不能在 main() 顶部 print notification
2. **initialize 只执行一次** — 用 `initialized = False` flag 保护, 后续收到忽略
3. **tools/list 和 tools/call 在 initialize 之前拒绝** — 返回 error code -32000
4. **notification (无 id) 不返回响应** — `if msg_id:` 判断
5. **错误码**: -32601 method not found, -32000 server not initialized, -32603 internal error

## 模板代码

```python
#!/usr/bin/env python3
"""
MCP <name> Server — <description>

Usage: Registered in config.yaml:
  mcp_servers:
    <name>:
      command: python3
      args:
        - ~/.hermes/scripts/mcp-<name>-server.py
      timeout: 30
"""

import json, sys, subprocess, os

# ─── Tool Definitions (JSON Schema) ───

TOOLS = [
    {
        "name": "tool_name",
        "description": "Tool description",
        "inputSchema": {
            "type": "object",
            "properties": {
                "arg1": {"type": "string", "description": "..."},
                "arg2": {"type": "integer", "description": "...", "default": 10},
            },
            "required": ["arg1"]
        }
    },
]

# ─── Tool Handlers ───

def handle_tool_call(name, args):
    """Execute tool and return {"success": bool, "output": str}"""
    if name == "tool_name":
        # implementation
        return {"success": True, "output": "result"}
    return {"success": False, "output": f"unknown tool: {name}"}

# ─── Main Loop ───

def main():
    initialized = False

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = msg.get("method")
        msg_id = msg.get("id")
        params = msg.get("params", {})

        if method == "initialize" and not initialized:
            initialized = True
            print(json.dumps({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "<name>", "version": "0.1.0"}
                }
            }), flush=True)

        elif method == "notifications/initialized":
            pass

        elif method == "tools/list" and initialized:
            print(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}), flush=True)

        elif method == "tools/call" and initialized:
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            result = handle_tool_call(tool_name, tool_args)
            print(json.dumps({
                "jsonrpc": "2.0", "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": result.get("output", "")}],
                    "isError": not result.get("success", False)
                }
            }), flush=True)

        else:
            if msg_id:
                err_code = -32000 if not initialized else -32601
                err_msg = "Not initialized" if not initialized else f"Unknown method: {method}"
                print(json.dumps({"jsonrpc": "2.0", "id": msg_id, "error": {"code": err_code, "message": err_msg}}), flush=True)

if __name__ == "__main__":
    main()
```

## 注册到 Hermes

在 `~/.hermes/config.yaml` 的 `mcp_servers:` section 添加:

```yaml
mcp_servers:
  <name>:
    command: python3
    args:
    - ~/.hermes/scripts/mcp-<name>-server.py
    timeout: 30
```

注意缩进: `mcp_servers:` 是顶层 key, 与 `plugins:` 同级。

## 测试方法

```python
import subprocess, json, time, os, fcntl

proc = subprocess.Popen(
    ['python3', '/path/to/mcp-server.py'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, bufsize=0
)

def send(proc, msg):
    proc.stdin.write(json.dumps(msg) + '\n')
    proc.stdin.flush()

def read(proc, timeout=1):
    time.sleep(timeout)
    fl = fcntl.fcntl(proc.stdout, fcntl.F_GETFL)
    fcntl.fcntl(proc.stdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    try:
        return proc.stdout.read()
    except:
        return ''
    finally:
        fcntl.fcntl(proc.stdout, fcntl.F_SETFL, fl)

# Test initialize
send(proc, {"method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test"}}})
resp = read(proc)
assert "serverInfo" in resp, f"Init failed: {resp[:200]}"

# Test tools/list
send(proc, {"method":"notifications/initialized","params":{}})
time.sleep(0.3)
send(proc, {"method":"tools/list","id":2,"params":{}})
resp = read(proc)
tools = json.loads(resp.split(chr(10))[0]).get("result",{}).get("tools",[])
print(f"{len(tools)} tools loaded")

# Test tool call
send(proc, {"method":"tools/call","id":3,"params":{"name":tools[0]["name"],"arguments":{...}}})
resp = read(proc)

proc.terminate()
```

## 实战案例: Git MCP Server

本次实战实现的 `mcp-git-server.py` (6 tools) 参见:
- `~/.hermes/scripts/mcp-git-server.py` — 完整实现
- `~/.hermes/config.yaml` — `mcp_servers.git` 注册

## Pitfalls (从真实调试中总结)

1. **不要在 main() 顶部 print 任何内容** — MCP 客户端期望第一条消息是 initialize 的响应。如果提前 print 了 notification, 客户端会尝试解析第一条消息为 initialize response 并失败
2. **notification 无 id, 不返回响应** — MCP 客户端发送 `notifications/initialized` 后, server 不能回任何消息。用 `if msg_id:` 判断是否该回复。notification 的 id 是 null, 不是 0
3. **initialize 只处理一次** — 客户端可能发送多次 (重连场景), 用 `initialized` flag 保护。后续 initialize 应忽略或用 error 拒绝
4. **Stdout 必须 flush** — `flush=True` 在每条 print 后必须加, 否则 MCP 客户端读不到响应
5. **测试时使用非阻塞读** — subprocess.stdout.readline() 在无数据时会阻塞。用 `fcntl` 设置 NONBLOCK + time.sleep
6. **Tool 参数名注意** — `tools/call` 的 params 结构是 `{"name":"...", "arguments":{...}}`, 不是直接 `tool_name` 和 `args`
7. **Tool inputSchema 必须是合法 JSON Schema** — `type:"object"` 必须有 `properties`, `required` 是数组不是布尔。缺少 `properties` 会导致客户端 schema 验证失败但不报错，tool 调用时参数丢失
8. **stderr 用于调试日志，不要写 stdout** — 如果需要 debug 输出，写到 stderr (`print("debug", file=sys.stderr)`)，stdout 是 MCP 协议通道，任何非 JSON-RPC 内容都会导致客户端解析失败
9. **initialize 时序问题** — 有些 MCP 客户端在初始化时先发 `initialize` 再发 `notifications/initialized`。但极少数客户端 (如自定义 wrapper) 会在 initialize 之后直接发 `tools/list` 而不发 notifications/initialized。如果你的 server 被 tools/list 和 tools/call 的 `and initialized` 条件挡住, 确保不要漏掉这种 "跳过 notification" 的客户端模式。解决方案: 在 initialize 响应后立即设置 `initialized = True`, 不等待 `notifications/initialized` — 客户端发不发的差异可通过检查: 如果初始化后第一条消息是 `tools/list` 而非 `notifications/initialized`, 允许通过但不响应 notification。

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

