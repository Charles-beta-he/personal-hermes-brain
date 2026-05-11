---
type: p9-backlog
layer: L2
status: completed
created: 2026-05-06T12:56:02Z
updated: 2026-05-06T13:35:04Z
project: hermes-local-brain
review: 2026-05-06-local-brain-remaining-strategy-audit
source: pua_loop_local_brain_audit
canonical_vault: /Users/charles/Documents/brain
expires_at: 2099-12-31T00:00:00Z
---

# P9 - Outstanding Optimization Backlog

本页是本地大脑剩余优化策略的唯一调度入口：把分散在 task、review、evolution、dashboard、project 中的“后续建议/待完成”收敛为可治理 backlog。它不表示这些事项都应立即执行；它表示本地大脑已经知道这些策略、边界与优先级，未来 loop 不再靠零散搜索重复发现。

## P10 方针

- Canonical truth：`/Users/charles/Documents/brain` Markdown vault 是权威源；SQLite、FTS、WAL、向量库、MemPalace/GitNexus/Ruflo 类索引都是 derived/cache，必须可重建。
- Evidence boundary：工具证据、原文、命令输出、结构审计优先；多模型 fanout/review 是 provenance，不是事实证明。
- Ghost prevention：L3 task 必须有 `expires_at` 或 terminal state；已完成事项必须同步 checklist，避免未来 session 误当 WIP。
- P10/P9/Loop 路由：P10 只定方向与风控；P9 拆成可验收切片；Loop 每轮必须 sync/reindex/search/audit，不空口完成。

## Current stop-gate snapshot

- Structure gate source：`~/.hermes/scripts/local_brain_exhaustive_audit.py`。
- Latest observed before this backlog：empty_dirs=[], top_level_no_index=[], parent_no_direct_md_top=[], broken_wikilinks_count=0, secret_pattern_hits=0。
- 本页处理的不是结构 P0 缺陷，而是“剩余策略散落/状态滞后/闭环弱”的治理缺口。

## P0 — 必须先收敛，防 ghost 与假闭环

### P0.1 Brainctl governance gates 最小落地

- Source：[[01-系统与偏好/system/Hermes Local Brain Memory Hierarchy]] lines on `brainctl validate/promote/expire/review record`。
- Rationale：没有 validate/expire/promote/review record，L3 过期、review 晋升、证据边界只能靠人工记忆，容易产生 ghost。
- Acceptance：
  - `brainctl validate --dry-run` 或等价脚本能报告 frontmatter/layer/schema、L3 expiry、review caveat/evidence boundary。
  - `brainctl expire --dry-run` 能报告过期或无 expiry 的 L3，不自动删除。
  - `brainctl promote --dry-run` 能报告哪些 task/review 可晋升到 atom/project/skill，哪些因证据不足拒绝。
  - 输出写入 [[07-仪表盘/本地大脑治理健康度]]。
- Status：done — `brainctl validate/expire/promote/review record` 已落地为 dry-run/local-first 命令并有 unittest。

### P0.2 Dashboard factual freshness

- Source：[[07-仪表盘/技能生态健康度]]、[[07-仪表盘/理论覆盖矩阵]]。
- Problem：旧 dashboard 与后续 evolution/proof 存在状态滞后；例如 Skill Graph cycles 已为 0，但测试覆盖、同名冲突、规则活性仍需实时刷新；理论矩阵仍有“待自检 Loop 发现”占位。
- Acceptance：dashboard 分成 `current snapshot`、`historical snapshot`、`accepted risks`、`open actions`，每个 open action 链接本 backlog。
- Status：done — `brainctl validate --write-dashboard` 可刷新 current snapshot / historical snapshot / accepted risks / open actions。

### P0.3 GitNexus checklist ghost 修正

- Source：[[05-实践与项目/tasks/2026-05-06-gitnexus-fusion-long-term-landing-log]]、[[06-治理与评审/reviews/2026-05-06-gitnexus-fusion-multimodel-selfcheck]]。
- Problem：原 checklist 保留 `scoped commit` 未勾选；git log 已观察到 `62e05b3 docs(brain): land GitNexus code-evidence fusion`。
- Acceptance：相关 task/review 记录 commit，避免未来 loop 误判为未完成。
- Status：done in this loop；见本页 Closure。

### P0.4 Coverage Contract 模板化

- Source：本轮内容质量审计。
- Requirement：长期 landing 至少形成 project/P10/P9 + task proof + review + evolution + validation query 的闭环。
- Acceptance：新增或更新长期项目时加入 `Closure Links`、`Evidence Boundary`、`Validation Queries`。
- Status：done — backlog-zero proof/task/review/evolution 均加入 Closure Links / Evidence Boundary / Validation Queries。

## P1 — 下一轮工程化补齐

### P1.1 GitNexus code-evidence runtime gate

- Source：[[05-实践与项目/projects/hermes-code-evidence-mcp/P9 - Implementation Backlog]]。
- Scope：`code_evidence_v1` schema、stale-index gate、detect_changes-before-commit、tool_map/shape_check、contract_id ledger、RRF evidence ranking。
- Boundary：不整体采用 GitNexus runtime；先做 read-only/dry-run，证据对象服务多模型讨论而不是替代工具验证。
- Status：done。

### P1.2 MemPalace derived-index benchmark

- Source：[[05-实践与项目/projects/local-brain-mempalace-derived/P9 - Implementation Backlog]]。
- Scope：隔离 5-20 篇非敏感样本，比较 brainctl FTS 与 derived closet/tunnel/temporal facts 的中英查询表现。
- Boundary：derived only；不写回 canonical vault，除非生成审计报告。
- Status：done。

### P1.3 Multi-model communication budget runner

- Source：本地多模型治理笔记与通信预算实践方案。
- Scope：allowlisted evidence-request runner、tier-specific token budget、telemetry 写入 dashboard。
- Boundary：其他模型只能请求证据；事实采集仍由 orchestrator/tool gate 完成。
- Status：done。

### P1.4 Ruflo claim ledger 接入 wrappers

- Source：Ruflo 长期治理 landing。
- Scope：cron/subagent wrappers 的 claim ledger、typed mailbox envelope、provider-level budget accounting。
- Boundary：先接只读/低风险任务，不引入高风险外部 checkpoint。
- Status：done。

### P1.5 理论卡 evidence-boundary 段落补厚

- Source：内容质量审计发现系统理论/治理理论多有引用但边界段落不均匀。
- Scope：给系统理论/治理理论核心卡统一增加：`来源支持什么`、`Hermes 映射只是类比/工程解释`、`不应过度推出什么`。
- Status：done。

## P2 — 已收敛为非阻塞研究边界

- 控制论数学卡：已新增 Lyapunov、Kalman、observability/controllability、optimal/adaptive control 基础卡。
- Skill ecosystem：已保留在技能生态治理 dashboard/skill-steward audit 中，不再作为本地大脑内容 backlog。
- Provider token/cost accounting：已由 `claim_guard_wrapper.py` typed mailbox envelope 记录 provider_accounting 字段。
- External checkpoint/tamper evidence：accepted risk；仅强不可篡改需求触发，不构成当前 backlog。

## Completion interpretation

本页完成后，“本地大脑内容完善”含义是：结构 gate 清零，剩余策略不再散落，P0/P1/P2 均有单一调度入口、证据边界、验收标准与状态。仍 open 的工程任务不构成内容缺失；它们是已登记、可执行、可审计的 backlog。

## Validation queries

- `本地大脑 剩余优化策略 P0 P1 P2 brainctl validate expire promote`
- `ghost prevention scoped commit GitNexus checklist 62e05b3`
- `Coverage Contract task review evolution validation query`
- `canonical vault derived index evidence boundary multi-model provenance`

## Closure Links

- Review：[[06-治理与评审/reviews/2026-05-06-local-brain-remaining-strategy-audit]]
- Task proof：[[05-实践与项目/tasks/2026-05-06-local-brain-remaining-strategy-loop-log]]
- Evolution：[[06-治理与评审/进化日志/2026-05-06-本地大脑剩余优化归并]]
- Dashboard：[[07-仪表盘/本地大脑治理健康度]]

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
