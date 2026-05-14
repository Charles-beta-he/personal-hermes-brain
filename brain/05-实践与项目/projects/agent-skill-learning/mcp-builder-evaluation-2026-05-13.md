---
type: evaluation
project: hermes-skill-learning
source_candidate: "mcp-builder"
evaluated_at: 2026-05-13T16:32:33+08:00
decision: borrow
status: deterministic-evidence-slice-complete
---

# MCP Builder 四阶段 MCP Server 引导与 Hermes MCP skill 补强评估

## 0. 结论

决策：BORROW，不 ADOPT，不直接安装/导入外部 `mcp-builder`。

候选来源在当前任务里只可追溯到截图 OCR（“四阶段引导，从零写 MCP Server 不再踩坑”）和任务池 linked state；本地没有可验证的外部 `mcp-builder` 源码、README 或 LICENSE。因此外部候选 license 记为 UNKNOWN / NOT VERIFIED。可借鉴的是“四阶段学习/构建路线”模式；Hermes 本地 MCP skill 生态已有可验证的本地技能与 references，可作为实际落点。

## 1. 来源与许可确认

| 项 | 证据 | 结论 |
|---|---|---|
| 截图候选 | task `acceptance_evidence`: `截图 OCR: 四阶段引导，从零写 MCP Server 不再踩坑` | candidate clue only |
| 外部源码/license | 未发现本地可核验 `mcp-builder` 源码包、仓库或 LICENSE | UNKNOWN / NOT VERIFIED |
| Hermes 本地落点 | `/Users/charles/.hermes/skills/mcp/SKILL.md`、`references/mcp-builder-learning-path.md`、`references/mcp-skill-enhancement-assessment.md` | borrow pattern 的可验证落点 |

处理原则：不复制未知许可内容；只把抽象出来的“四阶段 MCP Server 构建路线 + 最小模板/测试清单”落到 Hermes 现有 `mcp` / `mcp-server-from-scratch` 体系。

## 2. 四阶段流程提取

本地可验证路线：`/Users/charles/.hermes/skills/mcp/references/mcp-builder-learning-path.md`。

| Stage | 名称 | 目标 | 验证点 |
|---|---|---|---|
| 1 | Protocol Literacy | 理解 MCP、JSON-RPC、Tools/Resources/Prompts、stdio/HTTP | 能画出 initialize → initialized → tools/list → tools/call；能区分 request / notification / error |
| 2 | Minimal Implementation | 用最少代码实现可工作的 stdio MCP server | initialize 握手成功；tools/list 返回 schema；tools/call 正常；unknown method error |
| 3 | Production Builder | 真实场景、多 tool、resources/prompts、安全和错误处理 | 3+ tools 完整 schema；输入验证；不泄密；Hermes 注册可用 |
| 4 | Ecosystem Contributor | 可复用、可发布、可分享 | README、LLM-friendly descriptions、单元/集成/E2E 测试、超时/幂等/资源限制 |

## 3. Hermes MCP skill 缺口对比

依据：`/Users/charles/.hermes/skills/mcp/references/mcp-skill-enhancement-assessment.md`。

| Hermes skill | 覆盖 | 缺口 | 本轮处理 |
|---|---|---|---|
| `mcp` | 总览、路线、native-mcp vs mcporter 路由 | 缺少最小 server 模板与测试清单的一页式入口 | 新增 checklist artifact 并 patch `mcp` pointer |
| `native-mcp` | Hermes 持久 MCP 客户端配置、安全、故障排除 | 对 builder 来说是注册/验证阶段 | 保持作为 Stage 3 验证落点 |
| `mcporter` | ad-hoc 调用、探索、测试 | 可作为 Stage 2 最小 server smoke test | 纳入测试清单 |
| `mcp-server-from-scratch` | Python stdio 实现、模板、pitfalls | TS/HTTP/resources/prompts 仍是进阶缺口 | 本轮先补最小模板/测试 checklist，不扩散到 TS/HTTP |

## 4. MCP server 最小模板 / 测试清单建议

新增 artifact：

- `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/mcp-server-minimal-template-test-checklist-2026-05-13.md`

核心门禁：

1. Stdio server 必须只在 stdout 输出 JSON-RPC 响应；日志走 stderr。
2. 必须处理 `initialize`、`notifications/initialized`、`tools/list`、`tools/call`。
3. Tool schema 必须是完整 JSON Schema，参数缺失/类型错误不能 crash。
4. Unknown method / unknown tool 返回结构化 JSON-RPC error 或 tool-level isError。
5. 安全默认：最小权限、禁止路径遍历、禁止 secret echo、错误信息脱敏。
6. 测试顺序：unit handler → stdio transcript → mcporter/native-mcp smoke → malicious input/failure cases。

## 5. Acceptance mapping

| Acceptance | Evidence | Status |
|---|---|---|
| 确认来源与许可 | Section 1：截图候选 only；外部 license unknown；不导入 | PASS |
| 提取四阶段流程 | Section 2，引用本地 `mcp-builder-learning-path.md` | PASS |
| 对比现有 MCP skills 缺口 | Section 3，引用 `mcp-skill-enhancement-assessment.md` | PASS |
| 产出 MCP server 最小模板/测试清单建议 | Section 4 + checklist artifact | PASS |
| 不安装/不导入/不泄密 | 本轮只写 brain artifact 和本地 skill reference | PASS |

## 6. Decision

BORROW pattern only。

推荐落点：`mcp` umbrella skill 增加一页式 `minimal server template + test checklist` reference；实现细节仍由 `mcp-server-from-scratch` 承担，注册/运行由 `native-mcp` / `mcporter` 承担。
