# MCP Server 最小模板 / 测试清单（2026-05-13）

## Minimal stdio server contract

- stdout: JSON-RPC responses only; no debug logs.
- stderr: logs/debug/error diagnostics.
- Required methods:
  - `initialize` returns protocol/server capabilities.
  - `notifications/initialized` is accepted as notification and returns no response.
  - `tools/list` returns tools with complete `inputSchema`.
  - `tools/call` validates name and arguments, then returns content or structured error.
- Unknown method returns JSON-RPC error.
- Unknown tool returns tool-level error content, not process crash.

## Minimal security gates

- Use allowlists for tools and filesystem/API surfaces.
- Validate path arguments against allowed roots; reject `..` traversal and symlink escape when relevant.
- Do not echo secrets, raw tokens, or full environment variables.
- Bound timeouts and output size; return partial/error response rather than hanging.
- Keep credentials in env/config; never embed in tool descriptions or examples.

## Test ladder

1. Pure handler unit tests: method routing, schema validation, unknown method/tool.
2. Stdio transcript tests: send JSON lines, assert exact JSON-RPC ids/results/errors.
3. mcporter smoke: list tools and call the minimal echo/read-only tool.
4. native-mcp smoke: register in Hermes config in a disposable environment, verify discovered tools.
5. Negative tests: malformed JSON, missing args, wrong types, malicious paths, oversized output, timeout.

## Done definition

- [ ] initialize handshake passes.
- [ ] tools/list has stable names, descriptions, inputSchema.
- [ ] tools/call happy path passes.
- [ ] malformed/unknown/error paths pass without crash.
- [ ] no secrets in stdout/stderr/report.
- [ ] README has install/run/test examples and security boundary.
