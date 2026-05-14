---
name: multi-model-architecture
description: Use when the task falls under Multi-Model Architecture — 多模型全栈架构.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - software
    - development
    - multi
    - model
    - architecture
    related_skills:
    - claude-code
    - incremental-implementation
    - loop
    - multi-model-thinking
    - p10-architecture-self-check
    - plan
    - router
---

# Multi-Model Architecture — 多模型全栈架构

## Overview


> L0: 模型追踪 → L1: 模型路由 → L2: Agent协议 → L3: 投票 → L4: 互相印证 → L5: 多脑自进化
> 双脑模式: self-describe → Claude Code -p 设计 → Hermes 落地 → eval gate

## When to Use

- The task falls under Multi-Model Architecture — 多模型全栈架构
- Don't use for: requests that do not need the task falls under Multi-Model Architecture — 多模型全栈架构; choose a more specific child skill or a broader routing skill that actually matches the task.
## 架构总览

```
L0: Model Traceability    record-trace.sh → route_outcomes.model_chain
L1: Model Router           ε-greedy + pricing-aware + task_tier 过滤 + select_pair
L2: Agent Protocol         agent_protocol.py v2.0.0 (可导入模块+symlink, OTel链式关联chain_id/span_id, ProtocolError/try_wrap, 灵活extract, envelope,persistence,v1→v2迁移, 新verdict:pending/skipped/timeout)
L3: Ensemble Vote          majority / weighted / arbiter (execute=True实际调用模型；必须从 pricing.models 解析 provider 并传 hermes chat --provider，避免模型名走默认 provider)
L4: Cross-Verification     cross-patch / consensus-check / consensus-plans (全protocol_emit)
L5: Multi-Brain Evolution  consult_models.py v3 (读quorum.yaml, protocol_emit, TICK_DIR清理, per-planner timeout)
LX: Model Health Monitor   agent/model_health.py — 电路断路器 + FailoverReason-aware 恢复 + 评分排序 (详见下方)
```

## 双脑设计→实施工作流 (最关键的模式)

```
Step 1: 采集状态
  写 /tmp/hermes-<topic>-state.json (紧凑 2-3KB, 含 existing_infra + constraints + question)
  
Step 2: Claude Code 设计
  cat state.json | claude -p '...' --output-format json --max-turns 20-25 --allowedTools "Read"
  关键: --output-format json 返回 wrapped 格式:
    {type: "result", result: "```json\n{actual_plan}\n```"}
  需反序列化: json.loads(response) → 从 result 字段提取 inner JSON

Step 3: 解析 plan
  python3 -c "import json,re; d=json.load(sys.stdin); r=d['result']
  m=re.search(r'```json\n(.*?)```', r, re.DOTALL); plan=json.loads(m.group(1))"

Step 4: 创建 todo → 实施 → self-test → health check → 保存 memory
Step 5: 循环直到 plan 中所有 steps 完成

Pitfalls:
  - state.json 不要 > 4KB (Claude 注意力分散)
  - --max-turns 设 20-25 (太少了设计不完整)
  - 不让 Claude 用 Bash/Write (只读 stdin, 设计 only)
```

## L0: Model Traceability

```bash
# record-trace.sh v3 捕获模型 (带 60s TTL 缓存)
MODEL_CACHE="/tmp/.hermes-model-cache"
export HERMES_TRACE_MODEL="$MODEL"
# backfill 历史数据 (不改 is_synthetic)
python3 backfill-model-traces.py
```

## L1: Model Router

model-router.py v2: cost-aware ε-greedy + task_tier + select_pair
score = pass_rate - λ_cost×effective_rate(now) - λ_time×avg_dur
冷启动 ε=1.0, min_traces=10 后降为 0.1

## L4: Cross-Verification

consensus-check.py: AST/JSON 归一化 → hash 比较
cross-patch.py (T2): Producer→Reviewer→Merger (min_patch_conf=0.7)

任务分层: T0(MiMo quick) T1(Codex/gpt-5.5 + DeepSeek) T2(Codex + DeepSeek + Claude arbiter) T3(Claude lead + Codex + DeepSeek, MiMo fallback)
用户命令: /quick /verify /3v /arch /budget

## OpenAI Codex / gpt-5.5 接入策略

Codex 已作为 OpenAI provider 接入，当前 default model 为 `gpt-5.5`，provider 为 `openai-codex`。订阅口径: **ChatGPT Plus $20/月**（含 Codex seat），边际 token 成本在 pricing 表中按 0 计，subject to `unlimited_subject_to_abuse_protection`。Plus plan: 无限制核心聊天, 2+座位按年计费, SSO/MFA, 数据不用于训练。

推荐职责分层：
- `gpt-5.5` / Codex: codegen 主力、cross-patch producer、T1/T2 实施型 planner、可做 reviewer。
- MiMo: 低成本日常推理、T0 quick、Claude skip 时的备用多样性。
- DeepSeek: 低成本独立 reviewer / sanity check / T1-T2 第二意见。(Key 已生效，可直接调用)
- Claude Opus/Sonnet: P10 架构、关键仲裁、T3 lead；预算不足时降级到 DeepSeek/MiMo。

配置落点：
- `~/.hermes/config.yaml`: `pricing.models.gpt-5.5` provider=`openai-codex`, input/output=0, candidate_groups=[chat, codegen, reviewer, hard_reasoning]。
- `~/.hermes/config.yaml`: `verification.cross_patch.producer_model=gpt-5.5`。
- `~/.hermes/config/quorum.yaml`: Phase 1 actual fan-out 已启用；T1=[gpt-5.5, mimo-v2.5-pro, deepseek-v4-pro]（DeepSeek key 已生效），T2=[gpt-5.5, mimo-v2.5-pro, claude-opus-4-7, deepseek-v4-pro]，T3=[claude-opus-4-7, gpt-5.5, deepseek-v4-pro, mimo-v2.5-pro]。

## L4.5: Evidence-First Truth Gate (consult_models.py v3)

Multi-model consensus is not factual truth. `consult_models.py` now separates model agreement from orchestrator-owned evidence:

- `build_state()` accepts `claims` and `evidence`, and marks `state_owner=main_orchestrator`.
- `build_evidence_bundle()` normalizes claims/evidence and computes per-claim grounding.
- `evaluate_truth_gate()` returns `truth_status`, `can_certify_truth`, unsupported and contradicted claim IDs.
- Planner prompts include `evidence_bundle` and `truth_assessment`; models must emit `evidence_requests` instead of pretending they verified tool facts.
- Ratification fails closed when severity>=3 claims are unsupported or contradicted.
- SPL remains opt-in (`HERMES_MULTI_BRAIN_USE_SPL=1`) so compression cannot silently drop orchestrator state.

CLI pattern:
```bash
python3 ~/.hermes/scripts/consult_models.py state 'question' \
  --claim '{"id":"C-001","text":"self-test is green","severity":4}' \
  --evidence-json '{"id":"E-001","type":"command","summary":"self-test output","supports":["C-001"]}' \
  --out /tmp/mm-state.json
python3 ~/.hermes/scripts/consult_models.py run /tmp/mm-state.json --tier T3 --quorum 4 --discussion --max-rounds 2 --keep
```

Verification:
- `python3 ~/.hermes/scripts/test_consult_models_integration.py` includes evidence/truth-gate regression tests.
- `python3 ~/.hermes/scripts/self-test.py` validates `schemas/evidence-bundle.schema.json`.

## L5: Multi-Brain Evolution

consult-models.sh + consensus-plans.py + quorum.yaml

Plan Schema v1: patch id = sha1(file|op|body) — 确定性, 跨模型可比较
4层语义 consensus: L1 诊断 (0.4) L2 patch overlap (0.3) L3 参数 (0.2) L4 置信度 (0.1)
合并: 交集优先→多数补充→少数仲裁
4阶段: Phase 0 shadow → Phase 1 N=2 → Phase 2 N=3 → Phase 3 steady

### Fan-out Certification Semantics (P1 quorum hardening)

For any tier claiming multi-model validation, `min_quorum` is the certification threshold, not merely a best-effort hint.

Current hardened rule:
```yaml
T1:
  quorum: 3
  min_quorum: 2  # T1 must not certify from a single planner
  planners: [gpt-5.5, mimo-v2.5-pro, deepseek-v4-pro]
  diversity: provider
```

`consult_models.py` should expose a structured `fanout_certification` object in `merged_plan.json`, `discussion_result.json`, phase events, and final output:

```python
def fanout_certification_status(success_count: int, planner_count: int, min_quorum: int, fail_count: int = 0) -> dict:
    if success_count <= 0:
        return {"status": "all_failed", "certified": False, ...}
    if success_count < min_quorum:
        return {"status": "degraded_not_certified", "certified": False, ...}
    return {"status": "fanout_quorum_met", "certified": True, ...}
```

Required semantics:
- `success_count == 0` → `all_failed`, `certified=false`
- `success_count < min_quorum` → `degraded_not_certified`, `certified=false`
- `success_count >= min_quorum` → `fanout_quorum_met`, `certified=true`

Pitfall: T1 with three planners and `min_quorum: 1` lets a single successful model masquerade as multi-model certification. Tests should explicitly assert `T1 min_quorum >= 2` and `fanout_certification_status(success_count=1, planner_count=3, min_quorum=2)` returns `degraded_not_certified`.

## Claude Budget

日 250K/周 800K token 上限, 60% warn 95% block
多脑模式: <$5 排除 Claude, <$20 排除 opus, arbiter $5 独立池

## 双模型架构评分工作流 (Claude Code + Codex)

触发: 用户要求"测试 Claude Code 对架构评分 / 双模型评分 / 盯 Claude token 消耗 / PUA loop 评分"。

### 单次评分

流程:
1. 生成脱敏 state: `/tmp/hermes-<topic>-score-state.json` (2-3KB, 用正则脱敏 api_key/token/password/secret)
2. Claude Code 只读评分:
   ```bash
   cat /tmp/hermes-<topic>-score-state.json | claude -p 'You are Claude Code acting as an external P10 architecture reviewer. Score ... Output ONLY valid JSON ...' \
     --output-format json --max-turns 1 --allowedTools "" > /tmp/claude-<topic>-score.json
   ```
3. 解析: `json.loads(result)` 直接得到 JSON (无需 fence 解析)
4. 报告落盘到 `~/.hermes/notes/`

### PUA Loop 迭代评分

当目标是"评分过 N"时:
1. 建立基线 → 分析最低维度
2. 每轮: fix → self-test → state → Claude Code 评分
3. 若未达标: 让 Claude Code 设计下一轮 fix (双脑模式):
   ```bash
   cat state.json | claude -p 'Design a concrete fix plan. Output JSON with plan[].{id, file, change, test, impact}' \
     --output-format json --max-turns 1 --allowedTools ""
   ```
4. 按 plan 逐个实施 → 验证 → 重新评分
5. 重复直至达标或穷尽

关键经验:
- test_coverage 最敏感: 跨 patch 只有 2 个测试会被严厉扣分 (78→90 需要 10+ 测试)
- model_diversity 需要真正不同的 auth 路径, 不只是 config 列表
- safety 看重 "fail closed + 测试证明": 必须有 rollback 测试
- state 2-3KB 最优; 6KB+ 拉低评分质量
- 评分成本 ~$0.25-0.30/轮; 设计方案 ~$0.27/轮; 5 轮总计 ~$1.66

## Pricing

pricing.py: 多模型时间感知；Codex/gpt-5.5 Plus 订阅边际成本=0但受滥用防护；MiMo off-peak 0.8x；TTS 3免费 (auto-expire)

## 关键 Pitfalls

1. Patch ID 必须确定性: sha1(file|op|body), 不含 model_name
2. Claude -p JSON nesting: wrapper→result→fence→inner JSON (双反序列化)
3. state.json 紧凑 (2-3KB): >4KB 分散注意力
4. Provider diversity: select_pair 必须不同 provider
5. Backfill 不改 is_synthetic: 保护 real-only 口径
6. YAML 重复 key: 最后出现覆盖 → grep 重复项
7. Memory 满: 压缩/删除过时条目, 合并重复
8. agent_protocol seq 计数器: 必须是 per-chain_id 而非 per-(chain_id, agent_id) — 否则不同 agent 在同一 chain 中 seq 都从 1 开始，无法排序。
9. agent_protocol envelope.chain_id: wrap() 中 auto-gen 的 chain_id 必须写入 envelope 块——仅当 explicitly passed 才写入的 bug 导致后续消费者丢失链式追溯。
10. model-router cold start: 只有所有候选都 cold 时才强制 epsilon=1；若 gpt-5.5 等 warm model 已有足够 trace，保留 ε-greedy，否则会因新增 cold 候选随机绕开 Codex 主力。
11. select_pair reviewer narrowing: select_model 必须支持 candidate_override；否则 reviewer 过滤 diverse_reviewers 后又被 pricing candidate_groups 覆盖，可能选回 producer 本身。
12. consult_models.py 真多模型落地: 非 shadow 模式必须通过模型专属 adapter 调用（Claude→claude-cli；Codex/MiMo→hermes chat --provider openai-codex/xiaomi），不能再用 Claude prompt 冒充所有 planner。用 `HERMES_MULTI_BRAIN_OFFLINE=1` 只做 adapter dry-run。
13. ensemble-vote execute=True 也要做 provider-aware 调用：从 pricing.models 解析 provider 后传 `hermes chat --provider`；Hermes stdout 可能带 `session_id:` 前缀，解析 verdict 时要从 stdout 中提取 JSON object，不能直接 `json.loads(stdout)`。
14. cross-patch.py 双模式: `execute` = orchestration framework (`actual_model_calls=false`); `run` = script_actual (真实 producer/reviewer), 默认 dry-run, `--apply` 才写文件, `--verify` 失败回滚。`--apply` 无 `--verify` 时 fail closed (返回 rejected), 除非显式 `--force-no-verify`。
15. provider 可用性检查: `_model_available()` 必须查三层 (shell env → .env file → CLI auth)。只查 shell env 会漏掉 .env 中的 XIAOMI_API_KEY 和 Claude CLI session。结果写入 `state/unavailable_providers.jsonl` 做审计。
16. cross-patch 安全测试必须覆盖: 非唯一匹配拒绝、--apply 无 verify 拒绝、verify pass 写入、verify failure 回滚、cost tracking。5 个测试是最低要求。
17. pricing.py promo TTL: promotion 在 7 天内到期时必须 log warning, 否则会静默回归到全价 (如 DeepSeek 2.5x 折扣到期后 4x 涨价)。
18. model-router select_model 输出应包含 `unavailable_candidates` 字段, 供可观测性追踪。
19. score_provider 短路: health=0 直接返回 0, 不计算其他维度 (避免给不可用 provider 高分)。
20. get_best_provider 兜底: 全部评分=0 时 fallback 到 get_available_providers (紧急模式)。
21. 动态降级注入: synthetic fallback entry 的 model 字段用 provider 名 (非具体模型名), 由 resolve_provider_client 解析。
22. reliability 维度: cost 权重从 0.20 降到 0.10, 避免便宜但幻觉重的模型 (如 DeepSeek V4) 过度受益。hallucination_rate > 0.5 时 reliability 归零。
23. get_dynamic_reliability 永远不超过 baseline: min(dynamic, baseline), 防止正向漂移。

## DeepSeek 特殊计费模式 (本次新增)

Promotion 模式: 限时折扣, 自动过期
```yaml
deepseek-v4-pro:
  promotion:
    active: true
    discount: 0.25           # 2.5折
    expires_at: "2026-05-05T15:59:00Z"   # 北京时间 23:59 = UTC 15:59
    promo_input: 0.20
    promo_output: 0.60
```
pricing.py effective_rate(): free > promotion > schedule > base (优先级)
过期自动恢复: datetime.isoformat → now < expires → 才生效

Cache hit: 全系列 1/10 (字段 cache_hit_input/cache_hit_output)
废弃别名: modes: {non_thinking: "deepseek-chat (deprecated)", thinking: "deepseek-reasoner"}

## 日常运维命令 (模型使用可见性)

  python3 model-usage.py              # 摘要 + 最近20条
  python3 model-usage.py --today      # 只看今天
  python3 model-usage.py --model mimo # 过滤
  python3 model-usage.py --cost       # 按花费排序
  python3 model-usage.py --timeline 50

  python3 skill-audit.py              # skill 生态审计 (未引用/stale/stub)
  python3 model-diversity-monitor.py  # per-pair 模型差异性 (趋同告警)
  python3 claude-budget-tracker.py status  # Claude 预算

## 关键 Bug 修复记录

1. main 口径未排除 synthetic: _aggregate() 漏传 synthetic=0
   → 219 main(real) vs 216 main(all) — 7条合成污染
   修复: main = _aggregate(where, params, synthetic=0, exclude_routes=...)

2. self-describe.sh state_hash: 须在 FULL_OUT 写入后计算
   SHA256=$(sha256sum "$FULL_OUT" | cut -d' ' -f1)

3. agent_protocol seq counter: per-chain 非 per-(chain,agent) — 否则不同 agent 在同一 chain 中 seq 均为 1
4. agent_protocol envelope.chain_id: auto-gen 时必须写入 envelope，不能只在 explicitly passed 时写入

## LX-Q: Model Quota Monitor (实时额度可观测性 + quota gate) — 已落地

`~/.hermes/scripts/model_quota.py` — provider quota snapshot 统一层。核心原则：exact / estimated / unobservable 必须分开，unknown 不等于额度充足；但 unknown/unobservable 默认允许路由，只有 `status=exhausted` 做 hard gate。

能力：
- `snapshot_from_headers()` 解析 OpenAI/Anthropic 风格 rate-limit headers：remaining tokens / requests / reset。
- `default_snapshot()` 对订阅/OAuth provider（如 `openai-codex`）标记 `status=unobservable`, `quota_type=subscription_cap`，不伪造剩余额度。
- `record_call()` 持久化到 `state/model_quota_state.json`，审计日志写 `logs/model-quota.jsonl`。
- `probe_deepseek_balance()` 支持 DeepSeek `/user/balance` 余额端点（低频、非 token 调用）。
- CLI：
  - `python3 ~/.hermes/scripts/model_quota.py status --model gpt-5.5 --model claude-opus-4-7`
  - `python3 ~/.hermes/scripts/model_quota.py probe --deepseek --json`

集成点：
- `consult_models.py`：fan-out 前 `filter_planners_by_quota()`，把 `model_quota_snapshot` 与 `skipped_due_to_quota` 注入 state.budget、merged_plan、discussion_result、protocol event；`status --quota` 展示 T0-T3 quota。
- `model-router.py`：`_quota_filter_candidates()` 在 availability 之后 hard-gate exhausted candidates，decision 输出 `quota_exhausted_candidates` 与 `quota_snapshot`；`status --quota` 展示路由候选额度。
- `self-test.py`：新增 `model_quota.py compiles`、`model_quota tests (4/4)`、`model-router quota tests (1/1)`，总 self-test 47/47。

Pitfalls：
1. 不要让模型自己报告额度；额度只能来自 headers / balance endpoint / local tracker / error inference。
2. 不要把 `unknown` 当 `ok`；输出必须保留 observability/source/confidence。
3. 测试中 `model_quota` 会被多个模块 import，`HERMES_HOME` 是 import-time constant；隔离测试需从 `sys.modules` pop 掉旧 `model_quota` 后再导入 router。
4. 传入的 partial quota snapshot 必须 merge `default_snapshot()` 补全 schema，否则输出会缺 `observability` 等字段。
5. `agent/model_health.py` 测试不要用真实 `~/.hermes`: 持久化的 `rate_limits/model_health_state.json` 会让 fresh monitor 从 `HALF_OPEN` 等状态开始。运行相关测试用 `TMP=$(mktemp -d); HERMES_HOME="$TMP" python -m pytest tests/test_model_health.py ...; rm -rf "$TMP"`。

验证：
- `python3 -m unittest test_model_quota.py test_consult_models_integration.py test_model_router_quota.py -v` → 16/16 passed。
- `python3 ~/.hermes/scripts/self-test.py` → 47/47 passed。
- `bash ~/.hermes/scripts/p10-health.sh` → V(t)=0.951 Grade A。

## LX: Model Health Monitor (电路断路器 + 评分策略) — Phase 1+2+3 完成

agent/model_health.py — 基于电路断路器的 provider 健康追踪，FailoverReason-aware 恢复策略。已全栈集成。

```
4 状态电路断路器:
  CLOSED    → 正常使用
  OPEN      → 跳过 provider
  HALF_OPEN → 允许 1 个探测请求 (锁定防并发)
  DISABLED  → 永久失败 (auth/billing), 需手动 reset

触发条件:
  连续失败 >= 3  → 立即开路 (failure_threshold 可配)
  错误率 >= 40%  → 滑窗20次, 最低5次后才计算
  延迟尖峰 > 3x  → 告警 (不触发断路)

FailoverReason-aware 恢复策略 (agent/error_classifier.py 15类):
  rate_limit     60s base, 2x backoff, cap 3600s (优先用 Retry-After header)
  server_error   30s base, 2x backoff, cap 600s
  overloaded     30s base, 2x backoff, cap 600s
  timeout        15s base, 2x backoff, cap 120s
  auth/billing   → DISABLED (不自动恢复)

紧急模式: 全部 provider 挂掉 → 强制 least-recently-failed 进入探测

持久化:
  rate_limits/model_health_state.json  (快速加载, 每30s刷新)
  logs/model-health.jsonl              (审计日志)
  状态 >1h 未更新 → 自动重置为 fresh

线程安全: threading.Lock + atomic write (tmpfile+rename, 同 nous_rate_guard.py)

7/7 + 4/4 测试通过 (tests/test_model_health.py, 共 11 tests)

Phase 2 集成点 (全部完成):
  ✅ run_agent.py:10371  record_success (API 成功后, latency_ms=api_duration*1000)
  ✅ run_agent.py:11433  record_failure (FailoverReason 分类后, 带 reason)
  ✅ run_agent.py:6969   _try_activate_fallback 循环跳过 OPEN/DISABLED provider
  ✅ run_agent.py:7186   _restore_primary_runtime 检查 primary 健康, 不恢复降级 provider
  ✅ config.yaml:7       model_health 配置段 (9 参数)
  ✅ commands.py:176     /health 命令注册 (Info 类别)
  ✅ cli.py:6251+7146    /health 处理: 无参=健康表, reset <provider>=手动重置

Phase 3 集成点 (评分策略 + 可靠性维度, 全部完成):
  ✅ agent/model_health.py  score_provider() + get_best_provider() + get_provider_scores()
  ✅ agent/model_health.py  record_hallucination() + get_dynamic_reliability() (幻觉追踪)
  ✅ run_agent.py:6980   _try_activate_fallback 动态降级 (静态穷尽后 get_best_provider)
  ✅ cli.py:7170         /health scores 子命令 (评分排序表)
  ✅ tests/test_model_health.py  4 新增测试 (scoring/get_best/latency/task_type)

配置 (config.yaml):
  model_health:
    enabled: true
    failure_threshold: 3
    error_rate_threshold: 0.4
    min_calls_for_rate_check: 5
    latency_spike_threshold: 3.0
    recovery_timeout: 60
    max_recovery_timeout: 3600
    window_size: 20
    flush_interval: 30

多模型设计验证: MiMo(主设计) → Claude Code(8条验证, 全AMEND无REJECT) → 合并
Claude 关键修正: 遵循 nous_rate_guard.py 模式, 集成 FailoverReason, all_open 紧急模式, 探测锁
```

## Model Switch Strategy (多维度加权评分排序 + 可靠性维度)

agent/model_health.py 中的 `score_provider()` + `get_best_provider()` — 当 provider 遇到 rate limit 时，动态选择最佳替代。

```
评分公式 (5 维度, sum=1.0):
  score = health(0.35) + capability(0.25) + reliability(0.20) + cost(0.10) + latency(0.10)

权重变更历史:
  v1: health=0.40, capability=0.30, cost=0.20, latency=0.10 (4维)
  v2: health=0.35, capability=0.25, reliability=0.20, cost=0.10, latency=0.10 (5维, 加入幻觉维度)

Provider Profiles (PROVIDER_PROFILES dict):
  openai-codex  cost_tier=1  caps=code,reasoning,chat,codegen,tool_calling,structured_output  reliability=0.90
  anthropic     cost_tier=2  caps=reasoning,code,chat,analysis,long_context                   reliability=0.95
  xiaomi        cost_tier=0  caps=chat,code,speed,cost_efficiency                              reliability=0.75
  deepseek      cost_tier=0  caps=code,reasoning,cost_efficiency                               reliability=0.60 (V4 幻觉较重)

健康评分: CLOSED→1.0, HALF_OPEN→0.5, OPEN/DISABLED→0.0 (短路返回0)
能力评分: task_type → required_caps 匹配率 (code/reasoning/chat/default)
可靠性评分: static baseline from PROVIDER_PROFILES + dynamic hallucination adjustment
  get_dynamic_reliability(): baseline * (1 - hallucination_rate * 2)
  hallucination_rate = hallucination_count / success_count
  hallucination_rate=0 → baseline, 0.1 → baseline*0.8, 0.5 → 0
成本评分: cost_tier 0→1.0, 1→0.65, 2→0.30 (降权到 0.10 避免便宜但幻觉重的模型受益)
延迟评分: <500ms→1.0, <2s→0.5, <5s→0.25, >5s→0.1, unknown→0.7

记录幻觉:
  monitor.record_hallucination("deepseek") → hallucination_count++ → reliability 动态下降
  用途: multi-model cross-check 发现输出不准确时调用
```

任务类型对评分的影响 (实测数据, 全健康时):
  default:   openai-codex(0.915) > xiaomi(0.837) > deepseek(0.723) > anthropic(0.807)
  code:      openai-codex 最强 (codegen+tool_calling 独有)
  reasoning: anthropic 反超 (analysis+reasoning 独有, reliability 最高)
  chat:      xiaomi 登顶 (cost=0 最便宜, 3/3 caps 全中)
  DeepSeek:  reliability=0.60 拉低分数, 排名从并列第2降至第4

动态降级流程 (run_agent.py _try_activate_fallback):
1. 先走静态 fallback_chain，跳过 OPEN/DISABLED
2. 静态 chain 穷尽 → get_best_provider() 从已知 provider 动态选择
3. 排除当前 provider，按综合评分选最优
4. 注入为 synthetic fallback entry 继续降级

/health 命令:
  /health          → 健康状态表 (circuit/err_rate/latency)
  /health scores   → 评分排序表 (score/health/cap/cost/lat)
  /health reset X  → 手动重置 provider

测试: 11/11 passed (7 原有 + 4 新增: scoring/get_best/latency/task_type)

## SPL (Structured Protocol Language) — Token 优化通讯协议

agent/spl.py (1025行) — 用结构化 JSON 替代自然语言 prompt，减少多模型通讯 token 开销。

5 大压缩技术:
  ① 头部压缩: {"hdr":{"role":"vr","op":"vf"}} 替代 "You are a second brain..."
  ② 上下文哈希: {"ctx":{"ref":"sha256:abc123"}} 替代重复发送完整 state
  ③ 响应模板: {"rsp":{"schema":"v1","fields":["verdict","reasoning"]}} 替代 300 词格式描述
  ④ 缩写字典: pl=planner, vr=validator, A=agree, R=reject, rl=rate_limit (40+ 术语)
  ⑤ 分层上下文: T0(50tok) T1(200tok) T2(400tok)

API:
  SPLEncoder().encode_planner_call(model, state, tier, state_hash)
  SPLEncoder().encode_vote_call(task, model)
  SPLEncoder().encode_arbiter_call(model, task, verdicts)
  SPLDecoder().decode(spl_msg)
  spl_prompt_for_model(model, question, tier)
  SPLTier.T0 / SPLTier.T1 / SPLTier.T2

Token 节省:
  Planner fan-out: ~1700tok → ~760tok (56%)
  Vote batch:      ~320tok  → ~300tok (6%)
  Compaction:      ~570tok  → ~120tok (79%)
  典型 session:    ~2602tok → ~1177tok (55%)

集成 (已完成):
  ✅ consult_models.py — planner call 前尝试 SPL 编码, 失败回退自然语言
  ✅ ensemble-vote.py  — vote call 前尝试 SPL 编码, 失败回退自然语言

## Claude 访问方式变更 / 当前口径

当前 `consult_models.py` 对 Claude 模型优先走 Claude Code CLI，而不是 Hermes Anthropic adapter：
  当前: `claude -p prompt --model <claude-model> --max-turns 1 --output-format json`
  fallback: 非 Claude / 无 `claude` CLI 时才走 `hermes chat -q ... --provider <provider>`；DeepSeek 仍走 direct API fallback。

原因: Claude Code CLI 使用用户 Claude Max/OAuth session，能避开部分本地 Hermes Anthropic adapter 的 provider/model misroute；同时与“Claude Code 作为多脑 P10 设计/仲裁参与者”的实际决策路径一致。

验证口径:
  - `claude --version` + `claude auth status --text` 确认 CLI/auth。
  - `printf 'ping' | claude -p 'Reply exactly: CLAUDE_CODE_OK' --max-turns 1 --allowedTools ""` 确认 Claude Code print mode 可用。
  - `consult_models.py run <state> --tier T3 --quorum 1 --keep` 后检查 `tick-*/plans/claude-*.json.meta.adapter == "claude-code"`。
  - Discussion/ratification 路径可直接通过 `call_discussion_model('claude-opus-4-7', ...)` 或完整 `--discussion` tick 验证；只有 planner fan-out 不等于完整认证。

双脑工作流中的 Claude Code 调用 (Step 2) 仍用 `claude -p` (需要完整 Claude Code 能力)

## DeepSeek V4 幻觉验证 (2026-04-28)

基础测试 (3题): HTTP 429/RFC 6585 ✅, Python flatten ✅, 概率 2/5 ✅
进阶测试 (7题): 多跳推理 ✅, 逻辑谬误 ✅, 代码调试陷阱 ✅, 认知偏差 ✅, Python版本 ✅, 2024大选 ✅, JSON输出 ✅
总计 10/10 通过

结论: 基础+进阶任务表现正常, 但保持 reliability=0.60 (用户反馈实际使用中幻觉较重)
幻觉高发区: 长上下文窗口、工具调用链、项目级代码生成 (难以用单题测试覆盖)

## 关联脚本

model-router.py pricing.py claude-budget-tracker.py cross-patch.py
consensus-plans.py consensus-check.py agent-protocol.py ensemble-vote.py
consult-models.sh record-trace.sh route_store.py backfill-model-traces.py
self-describe.sh config/quorum.yaml
model-usage.py skill-audit.py model-diversity-monitor.py   (NEW: 运维工具)
agent/model_health.py tests/test_model_health.py           (NEW: 电路断路器+评分策略)
agent/spl.py                                                (NEW: SPL 通讯协议)

## Round 1 硬化 (2026-04-27)

1. cross-patch.py `apply_file_patches` 增加唯一命中检查：`before.count(original)` 必须等于 1，否则报 ambiguous conflict。
2. `cross-patch.py run --apply` 默认要求 `--verify`；无 verify 时 fail closed 返回 `rejected`。可显式 `--force-no-verify` 覆盖。
3. Producer prompt 新增 `patch_id` 字段（sha1(file+original+suggested)）。Reviewer prompt 新增 `approved_patch_ids`。run_cross_patch_actual 用 approved_patch_ids 做交叉验证。
4. 默认 reviewer 不再硬编码，改为 `_select_reviewer_via_router()` 调用 model-router select-pair 动态选择 diverse reviewer。
5. self-test.py 从 24 tests 扩展到 39 tests。

## Round 2-3 (2026-04-27)

6. test_ensemble_vote_integration.py: 6 tests (majority/unanimous/split/weighted/single voter)
7. test_consult_models_integration.py: 6 tests (provider resolution, quorum config, T1 diversity)
8. model-router.py `_model_available()`: preflight provider check, 不可用 provider 自动从候选过滤
9. cross-patch.py: per-run cost cap (max_cost_per_run_usd), cost tracking (latency_ms)
10. cross-patch.py: fuzzy whitespace fallback (exact miss + normalized match → hint)

## Round 4 (2026-04-27, Claude Code 设计方案)

11. test_cross_patch_safety.py: 5 tests (非唯一匹配/apply guard/verify pass/rollback/cost tracking)
12. pricing.py: promo TTL 7 天告警 (PROMO_EXPIRING_SOON logging)
13. model-router.py: `_log_unavailable_provider()` → state/unavailable_providers.jsonl

## Round 5 (2026-04-27, 最终 91 分)

14. _model_available 三层检查: shell env → .env file → Claude CLI auth
15. 正确识别 3 个活跃 provider: openai-codex (OAuth), xiaomi (.env API key), anthropic (Claude CLI)
16. self-test: 44/44 passed, V(t)=0.9682 Grade A

## Round 6 (2026-04-28, 多模型架构系统审计 + 修复)

触发: 用户要求"检查多模型架构, 是否存在未填充或硬编码功能"。

### 9 类常见缺陷 (审计 checklist)

按优先级排查多模型基础设施:

**P0 硬编码与配置脱节**
- H1 arbiter 模型字面量: `arbiter_model = "claude-sonnet-4-6"` 应改为 `resolve_arbiter_model(tier)` 读 quorum.yaml
- H2 producer/reviewer 默认值在多处不一致 (line 91 vs line 508)
- H3 fallback 链字面量数组 `["mimo-v2.5-pro", "gpt-5.5", "claude-sonnet-4-6"]` 绕开 router/health/pricing

**P1 配置启用但未真正落地**
- U1 模型在 quorum.yaml 列表中但 route_outcomes 调用次数 = 0 (检查: `sqlite3 route_outcomes.db "SELECT model_chain, COUNT(*) FROM route_outcomes WHERE model_chain != '' GROUP BY model_chain"`)
- U2 multi-brain 流程从未跑过 (检查: `ls ~/.hermes/eval/` 无 tick 输出)
- U3 ensemble-votes.jsonl 中 verdict=null / votes_count=null
- U4 测试 fixture (producer="p"/reviewer="r") 写入生产 logs/DB

**P2 软问题**
- S1 eval-harness method='dry_run' 仍计入 pass_rate
- S2 status 命令不显示 OFFLINE 模式

### 修复模式

**1. 测试隔离 env-var 模式** (P0 必须先做, 否则后续清理白做)
```python
# 在生产代码中 (cross-patch.py / agent_protocol.py / ensemble-vote.py):
LOG_FILE = os.environ.get("CROSS_PATCH_LOG_FILE",
    os.path.join(HERMES_HOME, "logs", "cross-patch.jsonl"))
db = (db_path
    or os.environ.get("HERMES_PROTOCOL_DB_PATH")
    or os.environ.get("HERMES_ROUTE_DB_PATH")
    or os.path.expanduser("~/.hermes/route_outcomes.db"))

# 在测试中 (TestCase 基类):
class _IsolatedTestEnv(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._iso_dir = tempfile.mkdtemp(prefix="cross-patch-test-")
        cls._saved_env = {}
        for k, v in {
            "CROSS_PATCH_LOG_FILE": os.path.join(cls._iso_dir, "cross-patch.jsonl"),
            "HERMES_PROTOCOL_DB_PATH": os.path.join(cls._iso_dir, "protocol.db"),
        }.items():
            cls._saved_env[k] = os.environ.get(k)
            os.environ[k] = v
        # rebind module-level constants (read at import time)
        cross_patch.LOG_FILE = os.environ["CROSS_PATCH_LOG_FILE"]
```

**2. arbiter quorum.yaml 三级解析**
```yaml
multi_brain:
  default_arbiter: claude-opus-4-7   # 必须新增字段
tiers:
  T2: { arbiter: claude-opus-4-7 }   # tier-level 优先
  T1: { arbiter: null }              # 走 default
```
```python
def resolve_arbiter_model(tier: Optional[str]) -> Optional[str]:
    q = load_quorum()
    if tier:
        v = (q.get("tiers", {}).get(tier, {})).get("arbiter")
        if v: return v
    return q.get("multi_brain", {}).get("default_arbiter")
# None 返回时调用方必须 verdict='unknown' reason='no_arbiter_configured', 不能 fall through 到字面量
```

**3. selector accessor chain (无字面量)**
```python
def select_producer_reviewer(tier="T2", requested_producer=None, requested_reviewer=None):
    # 1. 显式 caller 提供
    # 2. model-router select-pair (注意: 返回 dict 含 model 字段, 不是字符串!)
    # 3. quorum.yaml.tiers.<tier>.planners 顺序遍历, 跳过 unavailable
    # 全失败 → raise CrossPatchUnavailable (NOT silent string return)

# 在 CLI 处 catch:
try:
    result = run_cross_patch_actual(...)
except CrossPatchUnavailable as e:
    result = {"verdict": "skipped", "status": "unavailable", "reason": str(e)}
    sys.exit(2)
```

**4. probe subcommand + dedup snapshot**
```python
# model-router.py 加 probe 子命令: 不消耗 token, 只做 auth check
def probe_all_providers() -> dict:
    pt = _get_pricing()
    available, unavailable = [], []
    for model, info in pt.models.items():  # 注意: pt.models, 不是 pt.config["pricing"]["models"]
        ok = _model_available(model)
        ...
    return {"available": available, "unavailable": unavailable}

# _log_unavailable_provider 改为去重:
# - state/provider_availability.json: snapshot keyed by (provider::model), atomic write
# - state/unavailable_providers.jsonl: 仅状态转换写入 (available→unavailable, unavailable→available)
# 避免 _model_available 在每次路由决策中调用 N 次 → jsonl 爆炸
```

**5. schema-enforced ensemble logging**
```python
ENSEMBLE_LOG_SCHEMA_VERSION = 1
def _log_and_emit(result, ...):
    required = ("ts", "task", "strategy", "verdict", "votes_count", "models")
    missing = [f for f in required if log_entry.get(f) is None]
    if missing:
        print(f"[ensemble-vote] WARN: missing {missing}; fail-closed skip write", file=sys.stderr)
        return  # NOT write polluted entry
# vote() 必须强制写: result["votes_count"] = sum(1 for r in results if r.get("verdict") not in (None, "unknown", "timeout"))
```

### 关键 Pitfall 24-28

24. **model-router select-pair 返回 nested dict, 不是字符串**:
    ```python
    p = data.get("producer")  # ❌ 是 dict {"model": ..., "reason": ..., "score": ...}
    p = data.get("producer", {}).get("model")  # ✅
    ```
    cross-patch._select_reviewer_via_router 旧版用 `data.get("reviewer", "")` 直接当字符串, fail silently.

25. **DeepSeek 0 调用真因 ≠ auth 缺失**:
    实测: DEEPSEEK_API_KEY 在 .env 中 (probe 报告 available), 但 5 次 select-pair 全部 (gpt-5.5, mimo-v2.5-pro). 根因是 ε-greedy cold start: deepseek 历史 trace=0 → score=None → exploit 时跳过. 解决: 让 multi-brain cron 主动调用 T1 (含 deepseek), 7 天累积 ≥10 trace 后自动进入评分循环. 不要强行修改 router 给 cold model 倾斜评分 (会污染 baseline).

26. **测试 fixture 写入生产路径** (本次发现 59 行污染):
    `producer_model="p" reviewer_model="r"` 这类 fixture 名直接出现在 protocol_messages 和 cross-patch.jsonl 中. 修复前必须先做 env-var 隔离 (Pitfall 修复模式 #1), 否则清理后下次 test 又会污染. 验证方法: 跑测试前后比 mtime+line count, 完全相等才算隔离生效.

27. **quorum.yaml 字段缺失静默退化**: 如果 multi_brain.default_arbiter 不存在, T1 (arbiter=null) 调用 arbiter 会返回 None, 调用方若不检查会 fall through 到字面量 fallback. 修复: 必须在 quorum.yaml 显式加 default_arbiter, 调用方在 None 时返回 verdict='unknown' reason='no_arbiter_configured'.

28. **PricingTable 属性名**: `pt.models` 不是 `pt.config["pricing"]["models"]` (pricing.py:32 `self.models = raw.get("models", {})`). 写 probe_all_providers 时容易踩.

29. **eval-harness init_baseline() 不能依赖虚构 skill 名**:
    旧版调用 `evaluate_skill("current_production")` → "Skill not found" 然后静默返回空 baseline。
    正确实现: 遍历 baseline-prompts.json 中的 85 个 prompt，逐个调 API 评估，结果写入 eval-baseline.json。
    已修复: `~/.hermes/scripts/eval-harness.py` 的 `init_baseline()` 函数。

30. **`hermes chat -q` 不能用于 eval baseline 批量评估**:
    非 PTY 环境下返回 CLI 界面（Available Tools 列表）而非模型输出；subprocess 调用 120s 超时。
    正确方案: 直接用 API（DeepSeek/Xiaomi/Anthropic）通过 `requests` 库调用。
    `fill-baseline-parallel.py` 使用 ThreadPoolExecutor(max_workers=4) 并行填充，85 prompts 约 2 分钟完成。
    当前可用 API: DEEPSEEK_API_KEY (.env), XIAOMI_API_KEY (.env), ANTHROPIC_TOKEN (Claude CLI session)。

31. **Phase 6 consult-models nightly cron 必须显式注册，且必须使用新版 CLI 子命令**:
    multi-brain fan_out_merge 无内置调度，需 cron job 触发。
    Job: `multi-brain-consult-models-nightly`, schedule `0 1 * * *`
    旧命令 `python3 ~/.hermes/scripts/consult_models.py --keep --global` 已失效；新版必须先 `state` 再 `run`：
    ```bash
    STATE=/tmp/hermes-nightly-mm-state.json
    python3 ~/.hermes/scripts/consult_models.py state \
      'Nightly actual-usage self-evolution: inspect usage-score.json and propose one low-risk update-safe action.' \
      --context-json '{"scope":"Hermes ~/.hermes/scripts and cron only"}' \
      --constraint 'update-safe changes only' \
      --accept 'discussion_result emitted or explicit timeout recorded' \
      --out "$STATE"
    python3 ~/.hermes/scripts/consult_models.py run "$STATE" \
      --tier T1 --quorum 3 --discussion --max-rounds 1 --keep
    python3 ~/.hermes/scripts/usage-score.py
    ```
    经验: T1 真实 fan-out 可成功调用 planner，但 consensus 阶段可能 >420s 超时；cron prompt 必须把 timeout 当显式结果记录，并始终补跑 `usage-score.py`。

32. **consult_models.py 讨论能力落地边界**:
    `consult_models.py` 已具备 state builder、`--discussion`、issue_ledger、ratification gate、`discussion_result.json`、DeepSeek direct API fallback。
    运行方式：
    `python3 ~/.hermes/scripts/consult_models.py state '目标' --out /tmp/mm-state.json`
    `python3 ~/.hermes/scripts/consult_models.py run /tmp/mm-state.json --tier T3 --quorum 4 --discussion --max-rounds 5 --keep`
    注意 quorum 截断：T2/T3 虽列出 4 个 planners，但默认 quorum=3 只取前三个；要求 Claude Code+Codex+DeepSeek+MiMo 全参加时必须 `--quorum 4` 或新增专用 tier。
    如果 Hermes CLI 不接受 `--provider deepseek`，不要误判 DeepSeek 不可用；`consult_models.py` 对 `provider: deepseek` 使用 DeepSeek direct API fallback。
    当前在线讨论循环已落地 cross-critique + ratification gate：模型可提交 novel severity>=3 critique 并写入 issue_ledger；未解决 blocker 会 fail-closed 输出 `not_certified`。复杂多轮自动 issue resolution/revision diff 仍可继续增强。

### 审计执行流程 (本次实测)

1. **静态扫描** (找硬编码 + stub):
   ```bash
   # 扫所有核心脚本
   for f in model-router.py pricing.py cross-patch.py consult_models.py ensemble-vote.py consensus-{check,plans}.py agent_protocol.py eval-harness.py; do
     grep -nE 'TODO|FIXME|STUB|NotImplementedError|placeholder' ~/.hermes/scripts/$f
     # 函数体只有 pass / return None 的疑似 stub
     # if/elif 中字面量模型名 (claude-opus-4-7, gpt-5.5, mimo-v2.5-pro)
     # shadow_mode/dry_run 默认 = False
   done
   ```

2. **配置一致性** (quorum.yaml ↔ 代码):
   ```bash
   # quorum.yaml 中的 arbiter 是否被代码读取
   grep -n 'arbiter' ~/.hermes/config/quorum.yaml
   grep -n 'arbiter_model.*=' ~/.hermes/scripts/*.py  # 找硬编码
   ```

3. **真实落地数据** (路由 + 协议):
   ```bash
   sqlite3 route_outcomes.db "SELECT model_chain, COUNT(*) FROM route_outcomes WHERE model_chain != '' GROUP BY model_chain ORDER BY 2 DESC"
   # 任何 quorum.yaml 中列出的模型, 0 调用 = 红旗
   sqlite3 route_outcomes.db "SELECT id, agent_id, payload_json FROM protocol_messages ORDER BY id DESC LIMIT 5"
   # 看是否有 producer="p" 这类 test 残留
   ```

4. **多模型思考协议执行修复**: Claude 主设计 → gpt-5.5 13 条逐条验证 (全 amend, confidence=0.78) → 合并 13 个 phase → 按依赖图实施.

5. **依赖排序**: Phase 0 preflight → 1 测试隔离 → 2 隔离验证 → 3 清理 → 4 H1 → 5 H2/H3 → 6 探针 → 7 schema → 8 eval-harness → 9 出口 → 10 self-check.
   关键: **隔离 (Phase 1-2) 必须在清理 (Phase 3) 之前**, 否则下次测试又污染.

### Round 6 修改清单

- `agent_protocol.py`: emit/query 加 HERMES_PROTOCOL_DB_PATH + HERMES_ROUTE_DB_PATH env
- `cross-patch.py`: LOG_FILE env-var, select_producer_reviewer accessor chain, CrossPatchUnavailable 异常, _load_quorum_safe, load_config 默认值从 quorum 派生
- `ensemble-vote.py`: load_quorum + resolve_arbiter_model, vote() 加 tier 参数, schema-enforced _log_and_emit, ENSEMBLE_LOG_SCHEMA_VERSION=1, CLI --tier
- `model-router.py`: probe subcommand + probe_all_providers(), _log_unavailable_provider 去重 (snapshot + transition jsonl)
- `consult_models.py`: status 显示 OFFLINE/ACTUAL + default_arbiter + 每 tier skipped planners
- `quorum.yaml`: 加 multi_brain.default_arbiter
- `test_cross_patch_*.py`: _IsolatedTestEnv 基类, setUpClass tmpdir env
- `test_cross_patch_safety.py`: _FakeQuorumTempDirMixin — 临时 quorum.yaml 隔离 + mock select_producer_reviewer 3-stage（14 test: explicit/router/quorum/tier/integration, 用 @patch.object 而不是 @patch("string.path")）
- `eval-harness.py`: classify_infra_failure() 5类(ok/timeout/auth_fail/unavailable/dry_run), infra failure 不计入 pass_rate, 全部 infra → status=infrastructure_failure → compare 返回 skip

### Round 6 验证

- self-test: 44/44 保持
- 测试隔离: 跑 7 个测试后 prod log_lines 不变, pm_rows 不变
- 清理: protocol_messages 删 59 行, jsonl 删 53 行 (备份在 backups/multimodel-fix-2026-04-28/)
- arbiter 解析: T1/T2/T3 全部 = claude-opus-4-7 (T2/T3 走 tier, T1 走 default)
- probe: 11/11 provider available (含 deepseek 三个变体)
- selector: select_producer_reviewer(tier='T2') 返回 (gpt-5.5, mimo-v2.5-pro)

## PUA Loop 评分迭代工作流 (78→91 in 5 rounds)

触发: 用户要求"PUA loop 直至 Claude Code 评分过 90"。

流程:
1. 建立基线评分 (Claude Code --max-turns 1 --allowedTools "")
2. 分析最低维度 → 聚焦修复
3. 每轮: 修复 → self-test → 更新 state (2-3KB) → Claude Code 评分
4. 若 <90: 让 Claude Code 设计下一轮 fix plan (双脑模式)
5. 重复直至 ≥90

关键经验:
- Claude Code 评分对 test_coverage 最敏感: 跨 patch 只有 2 个测试会被严厉扣分
- model_diversity 需要真正不同的 auth 路径 (OAuth/API key/CLI session), 不只是 config 列表
- 安全维度看重"fail closed + 测试证明": --apply requires --verify 必须有测试覆盖 rollback
- state.json 2-3KB 最优; 6KB+ 会拉低评分质量
- Claude Code 评分成本 ~$0.25-0.30/轮; 设计方案 ~$0.27/轮

## Provider 可用性三层检查

`_model_available()` 必须检查三层, 不能只看 shell env:
1. `os.environ.get(env_var)` — shell 环境变量
2. `~/.hermes/.env` 文件解析 — hermes 启动时加载
3. CLI 工具认证 — `shutil.which("claude")` 检测 Claude CLI session

已知 provider auth 路径:
- openai-codex: OAuth device code (hermes auth)
- xiaomi: API key in .env
- anthropic: Claude CLI session (独立于 ANTHROPIC_API_KEY)
- openrouter: OPENROUTER_API_KEY (当前未设置 → 自动过滤)

## Verification Checklist
- [x] self-test 44/44
- [x] test_cross_patch_safety 19/19 (原有5 + Phase 4.5 selector mock 14)
- [x] eval-harness classify_infra_failure: 5 类全部已验证 (ok/timeout/auth/unavailable/dry_run)
- [x] eval-harness baseline: 85/85 prompts 已填充 (DeepSeek API, pass_rate=100%, keyword_hit=93.2%)
- [x] Phase 6 cron registered: multi-brain-consult-models-nightly (01:00 daily)
- [x] Claude Code 严格评分 91/100 (2026-04-27, 5轮 PUA loop: 78→86→86→89→91)
- [ ] model_stats total = stats.overall total (口径一致)
- [ ] main view = 0 synthetic (纯 real-only)
- [ ] model-router candidates 全, pricing 加载
- [ ] Claude budget ok, 日 250K/周 800K
- [ ] consensus exact/dissent 双向通过 (确定性 patch ID)
- [ ] cross-patch merge (高置信应用, 低置信拒绝)
- [ ] promotion 有效期内/外双场景验证
- [ ] V(t) > 0.8, V̇ > 0

## 关联 Skill

- multi-model-thinking: 多模型思考协议 (设计→验证→合并，避免单模型盲信)
- p10-architecture-self-check: P10 架构自检
- incremental-implementation: 增量实施策略

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

