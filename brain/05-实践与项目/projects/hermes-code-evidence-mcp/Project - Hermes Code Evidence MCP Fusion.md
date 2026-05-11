---
type: project
status: active
created: 2026-05-06T09:29:50Z
project: hermes-code-evidence-mcp-fusion
horizon: long-term
source_reference: GitNexus MCP/code-intelligence methodology
---

# Project - Hermes Code Evidence MCP Fusion

## 北极星

把 GitNexus 的 code-intelligence MCP 设计融合成 Hermes-native 长期能力：

> 任何多模型代码决策都必须绑定可复现代码证据；模型一致、模型名、模型数量都不能替代 impact/context/contract/shape/staleness/test 证据。

## 为什么做

当前 Hermes 已有多模型思考、truth gate、本地大脑、P10/P9/Loop、自进化日志，但代码变更链路还需要更硬的结构化 evidence plane：

- 变更前：知道会影响哪些 symbol、API、MCP tool、cron、contract。
- 变更中：模型 dissent 绑定 contract_id 与 evidence，而不是泛泛而谈。
- 变更后：detect_changes 映射实际 diff 到预期影响面。
- commit 前：HIGH/CRITICAL 影响必须阻断或显式 caveat。

## 借鉴范围

借鉴 GitNexus 的方法论：

- impact-before-edit。
- detect_changes-before-commit。
- stale-index gate。
- tool_map / shape_check。
- canonical contract_id / Contract Bridge。
- structured MCP resources。
- RRF-like evidence ranking。

不借鉴/暂不采用：

- 不整体引入 GitNexus runtime。
- 不复制 GitNexus 代码。
- 不在生产链路使用 `npx -y ...@latest`。
- 不把 Cypher 裸暴露给所有模型。
- 不把 RRF 当真理认证。

## 当前本地落地点

- Skill reference: `/Users/charles/.hermes/skills/software-development/multi-model-thinking/references/gitnexus-code-evidence-mcp-pattern.md`
- Self-check script: `/Users/charles/.hermes/scripts/gitnexus_fusion_selfcheck.py`
- 本项目目录：`/Users/charles/Documents/brain/05-实践与项目/projects/hermes-code-evidence-mcp/`

## 成功标准

### L0 文档/知识层

- 本地大脑可检索：GitNexus-inspired、多模型、代码证据门、impact-before-edit、detect_changes、stale-index、Contract Bridge、shape_check。
- 相关 skill reference 存在并被 multi-model-thinking 引用。
- 自检脚本 PASS 或只剩明确 warning。

### L1 协议层

- 定义 Hermes code-evidence object schema。
- 定义 contract_id 命名规范。
- 定义 `hermes://repo/...` 与 `hermes://model-run/...` resource vocabulary。

### L2 工具层

- `hermes_index_status` / `hermes_detect_changes` / `hermes_tool_map` / `hermes_shape_check` 的最小可用版本。
- 本地 index freshness 检查接入 truth gate。

### L3 工作流层

- `consult_models.py` 对 code/MCP/API 任务生成 state 时自动要求 code-evidence gate。
- `cross-patch.py` / commit loop 接入 detect_changes-before-commit。
- PUA-loop 完成条件加入 code-evidence proof。

## 状态边界

当前是长期项目起点：文档、skill reference、自检脚本已经落地；完整 runtime gate 还未全部实现。历史 GitNexus 多模型 fanout 产物可作为 provenance，但不是 ratified consensus。
