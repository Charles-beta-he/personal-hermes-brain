---
type: implementation-playbook
status: active
created: 2026-05-06T09:29:50Z
project: hermes-code-evidence-mcp-fusion
concepts: [GitNexus, MCP, multi-model-thinking, code-evidence, truth-gate]
---

# GitNexus-inspired 多模型代码证据门落地方案

## 一句话

把“多模型讨论”升级为“多模型围绕同一套代码证据对象讨论”。

## Loop 流程

### Round 0 — Framing

- 明确任务是否涉及 code/MCP/API/CLI/cron/contract。
- 如果是，必须启用 code-evidence gate。
- 生成 state_hash。

### Round 1 — Evidence collection

收集：

- repo_context。
- index_status。
- impact_evidence。
- tool_map / route_map / shape_check。
- contract_id ledger。

### Round 2 — Multi-model fanout

每个模型只能基于 evidence_bundle 提案或质疑。

必须输出：

- claim。
- cited evidence id。
- missing evidence request。
- risk severity。
- proposed experiment。

### Round 3 — Issue ledger

所有 dissent 进入 issue ledger，尤其少数意见不能被模型名/模型数量压制。

### Round 4 — Patch / action

只有当：

- stale=false。
- impact_evidence 存在。
- severity>=3 issue 有处理。
- expected verification 明确。

才允许进入实现。

### Round 5 — Detect changes

实现后运行 detect_changes-before-commit。

必须比较：

- expected_changed_files vs actual_changed_files。
- expected_contracts vs affected_contracts。
- expected_flows vs affected_flows。

### Round 6 — Ratification

truth gate 认证顺序：

1. deterministic evidence。
2. tests/build/static checks。
3. detect_changes report。
4. 多模型 review。

模型一致排在最后；不能覆盖前面失败。

## 停机条件

- 自检脚本 PASS 或 warning 已进入 accepted risk。
- brainctl sync/reindex/search 可检索本方案。
- 本轮新增文件无断链、无 secret pattern。
- 若 discussion timeout/dissent，最终只能写 fanout/self-check，不写 certified consensus。

## 关联

- [[05-实践与项目/projects/hermes-code-evidence-mcp/Project - Hermes Code Evidence MCP Fusion]]
- [[05-实践与项目/projects/hermes-code-evidence-mcp/P10 - Long-term Strategy]]
- [[05-实践与项目/projects/hermes-code-evidence-mcp/P9 - Implementation Backlog]]
- [[04-知识原子/atoms/model-agreement-is-not-evidence]]
- [[04-知识原子/atoms/minority-opinion-and-model-authority]]
