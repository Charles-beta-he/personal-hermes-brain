# PUA Loop 多模型架构迭代报告
日期: 2026-04-27

## 评分轨迹

| Round | Score | Δ  | 关键动作 |
|-------|-------|-----|---------|
| Baseline | 78 | — | Codex 接入后首次评分 |
| R1 | 86 | +8 | 修复 5 个 P1: patch-id binding / self-test 纳入 / --apply 强制 verify / 动态路由 / 唯一命中 |
| R2 | 86 | 0 | 集成测试扩展 (ensemble 6 + consult 6) |
| R3 | 86 | 0 | 可观测性增强 (provider 预检 / cost cap / fuzzy fallback) |
| R4 | 89 | +3 | Claude Code 设计 4 fix: safety tests 5 / promo TTL / self-heal manifest |
| R5 | **91** | +2 | _model_available 修复: .env + Claude CLI auth 识别 |

## 最终维度评分 (Round 5)

| Dimension | Score |
|-----------|-------|
| correctness | 92 |
| safety | 93 |
| observability | 92 |
| model_diversity | 84 |
| automation | 91 |
| test_coverage | 90 |
| operability | 90 |
| cost_control | 88 |
| **overall** | **91** |

## 5 轮迭代改动汇总

### 脚本修改
1. cross-patch.py — 唯一命中检查 + fuzzy fallback / --apply 强制 verify / patch_id binding / 动态路由 reviewer / per-run cost cap
2. model-router.py — _model_available() 三层检查 (shell env → .env → Claude CLI) / unavailable_candidates 输出 / self-heal manifest
3. pricing.py — promo TTL 7 天警告
4. self-test.py — 24 → 44 tests
5. consult_models.py — 之前已改 (adapter fan-out)
6. ensemble-vote.py — 之前已改 (provider-aware)
7. agent_protocol.py — 之前已改 (v2.0.0)
8. consensus-check.py — 之前已改 (bare except)

### 新增测试文件
1. test_cross_patch_safety.py (5 tests)
2. test_ensemble_vote_integration.py (6 tests)
3. test_consult_models_integration.py (6 tests)
4. test_cross_patch_real_execution.py (2 tests, 之前已有)

### 新增数据文件
1. state/unavailable_providers.jsonl — provider 可用性审计日志

## Claude Code 成本

| Round | Cost USD |
|-------|----------|
| R1 设计 | $0.28 |
| R2 评分 | $0.28 |
| R3 评分 | $0.30 |
| R4 设计+评分 | $0.55 |
| R5 评分 | $0.25 |
| **总计** | **~$1.66** |

## 剩余 P1 (非阻塞)

1. T2/T3 config 仍含 DeepSeek 但 router 自动过滤 — 需显式 degraded flag
2. Anthropic 依赖 Claude CLI session token — 需定期 auth probe
3. Provider N=3 是最低可行 quorum — 任一失败即降级到 N=2
4. MiMo 质量未与 gpt-5.5/claude-opus 做 parity 测试
