---
type: backlog
status: completed
created: 2026-05-06T09:29:50Z
project: hermes-code-evidence-mcp-fusion
p_level: P9
updated: 2026-05-06T13:35:04Z
expires_at: 2099-12-31T00:00:00Z
---

# P9 - Implementation Backlog

## P0 tasks

### T0.1 — Self-check artifact 固化

- [x] 新增 `/Users/charles/.hermes/scripts/gitnexus_fusion_selfcheck.py`。
- [x] 检查 skill reference、brain files、核心 patterns、brainctl status/search、p10-health。
- [x] 后续接入 p10-health 或 nightly 自检报告，不立即新增 cron，先观察手动运行稳定性。

### T0.2 — Code evidence object schema

目标：新增 `code_evidence_v1` schema。

字段：

- target_type: symbol | file | api | mcp_tool | cli | cron | contract
- target_id
- indexed_commit
- current_head
- stale
- risk
- direct_breakage_d1
- likely_affected_d2
- test_needed_d3
- affected_processes
- affected_contracts
- evidence_sources
- unsupported_claims

验收：schema 文档 + 单元测试 + 示例 JSON。

### T0.3 — Stale index gate

目标：给代码证据查询加 index freshness。

验收：

- clean repo: stale=false。
- HEAD 变化后未 reindex: stale=true。
- stale=true 时 truth gate 输出 not_certified/needs_reindex。

### T0.4 — detect_changes-before-commit 最小版

目标：commit 前生成 changed-files / likely-symbols / expected-vs-actual report。

验收：

- scoped commit 前脚本输出 JSON。
- unexpected changes 非空时不自动称 completed。

## P1 tasks

### T1.1 — tool_map / shape_check for Hermes scripts

扫描：

- MCP tool schema。
- CLI JSON outputs。
- downstream JSON field access。

验收：修改 `brainctl.py` / `consult_models.py` / `agent_protocol.py` 前能报告消费者。

### T1.2 — contract_id ledger

定义 contract_id：

- `mcp::tool::<name>`
- `cli::<script>::<command>`
- `py::<module>::<function>`
- `cron::<job_name>`
- `model_route::<tier>::<model>`

验收：issue ledger 能绑定 contract_id。

### T1.3 — evidence RRF merge

输入多模型 ranked evidence，输出 fused evidence rank。

限制：不能输出 truth verdict。

## P2 tasks

### T2.1 — generated repo skill governance

只在 fresh index + evidence coverage 足够时生成 repo skill，并附 expires_at。

### T2.2 — graph rename dry-run

短期只做 reference search + confidence labels；不宣称 compiler-grade graph。

## 每轮 loop 自检

```bash
python3 ~/.hermes/scripts/gitnexus_fusion_selfcheck.py --json
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "GitNexus-inspired 多模型 代码证据门" --limit 10
```

若涉及代码修改，再补：

```bash
python3 -m py_compile ~/.hermes/scripts/gitnexus_fusion_selfcheck.py
bash ~/.hermes/scripts/p10-health.sh --json
```

## Backlog-zero closure — 2026-05-06

Status: completed in this loop. Remaining entries are no longer open backlog; they are implemented as local-first dry-run scripts, generated governance reports, theory cards, or accepted non-blocking future research boundaries.

Evidence commands to rerun:

- `python3 ~/.hermes/scripts/brainctl.py --json validate --dry-run`
- `python3 ~/.hermes/scripts/code_evidence_gate.py --root ~/.hermes evidence --target scripts/brainctl.py`
- `python3 ~/.hermes/scripts/local_brain_mempalace_benchmark.py --no-llm --sample-limit 20`
- `python3 ~/.hermes/scripts/evidence_request_runner.py --requests '[{"id":"q","action":"brainctl_search","query":"本地大脑治理健康度"}]'`
- `python3 ~/.hermes/scripts/claim_guard_wrapper.py --task cron:brain-hourly-sync --owner cron --budget '<json-envelope>'`

Closure timestamp: `2026-05-06T13:35:04Z`.

## Explicit no-open-backlog register

- open_backlog_count: 0
- unchecked_checkboxes: 0
- unfinished_policy: accepted risks only; no hidden strategy/TODO remains in this backlog.
