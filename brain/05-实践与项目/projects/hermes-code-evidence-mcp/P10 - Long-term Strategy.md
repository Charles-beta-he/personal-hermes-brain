---
type: strategy
status: active
created: 2026-05-06T09:29:50Z
project: hermes-code-evidence-mcp-fusion
p_level: P10
---

# P10 - Long-term Strategy

## 当前健康快照

来自 `p10-health.sh --json`：

```json
{
  "timestamp": "2026-05-06T09:29:50Z",
  "V": 0.9892,
  "grade": "A",
  "main_pass_rate": 0.964,
  "cron_health": 1.0,
  "real_ratio": 1.0,
  "gateway": 1.0,
  "warnings": ["memory file > 2.2KB, may have ghosts"]
}
```

判定：系统健康足够承载一个长期治理项目；主要非阻断风险是 memory ghost 膨胀。

## 战略判断

GitNexus 的价值不是替代 Hermes，而是提供一组可迁移控制原语：

1. code graph 让模型发言前先看结构证据。
2. MCP tools/resources 让证据访问协议化。
3. guardrails 把“应该查影响”升级为“未查不得认证”。
4. Contract Bridge 让跨 repo/API/tool 影响可追踪。
5. detect_changes 把实际 diff 和预期影响面闭环。

## 架构原则

- Local-first：所有核心证据来自本地 repo、本地 brain、本地脚本。
- Evidence-first：模型只做 reasoning；事实证据由 orchestrator/tool 收集。
- Fail-closed：stale index、missing impact、unsupported severity>=3 claim 都不能 certified。
- No runtime dependency：先做 Hermes-native 小切片，不把 GitNexus runtime 纳入关键路径。
- Scoped evolution：每轮只推进一个可验证 slice，并提交本地 git。

## 路线图

### Phase A — Governance landing（已启动）

- 写入本地大脑项目、P10/P9、实践方案、自检报告。
- skill reference 接入 multi-model-thinking。
- 自检脚本验证核心 pattern 是否仍存在。

### Phase B — Evidence object schema

- 定义 `code_evidence_v1`。
- 定义 risk levels 与 truth_gate 阻断规则。
- 定义 stale-index verdict。

### Phase C — Minimal detectors

- `hermes_index_status`：repo HEAD vs indexed_commit。
- `hermes_detect_changes`：git diff → changed files/symbol hints。
- `hermes_tool_map`：MCP/CLI/script JSON outputs 与 downstream parser references。

### Phase D — Workflow gates

- `consult_models.py state` 自动识别 code/MCP/API task 并要求 code-evidence。
- `cross-patch.py` 应用 patch 前后写入 evidence bundle。
- local commit 前运行 detect_changes 自检。

### Phase E — Contract Bridge

- 为 MCP tool、CLI command、HTTP route、cron、Python API 生成 canonical contract_id。
- issue ledger 绑定 contract_id。
- 多模型 dissent 必须指向 contract_id + evidence。

## Top risks

| 风险 | 等级 | 缓解 |
|---|---:|---|
| 把 GitNexus runtime 当依赖引入，产生 license/supply-chain 风险 | P0 | 只提取方法论；代码复用需单独 review |
| 伪装代码图谱能力，实际只有关键词搜索 | P0 | 输出中区分 graph_confident 与 text_search_low_confidence |
| stale index 仍被模型当证据 | P0 | stale=true 一票否决 certified |
| 自动生成 skill 污染生态 | P1 | generated skill 必须有 commit、evidence、expires_at |
| RRF 被误用为投票/真理认证 | P1 | 明文规则：RRF only ranks evidence |

## P10 stop condition

长期项目每轮 loop 只有满足以下条件才算阶段完成：

- 自检脚本 PASS 或 warning 已记录 accepted risk。
- 本地大脑 sync/reindex/search 通过。
- 新增文档无断链、无敏感模式命中。
- 多模型自检若未 ratified，必须写明 fanout/dissent/not_certified caveat。
- scoped local commit 完成。
