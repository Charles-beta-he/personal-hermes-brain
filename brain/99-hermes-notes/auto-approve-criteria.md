# Auto-Approve Criteria — 自进化自主决策标准

> Week 1 产出。定义双脑自进化何时可免人工审核。

## 当前状态: disabled

`auto_approve.enabled: false` — 所有变更仍需人工审批。
启用前需验证 canary 通道稳定运行 ≥ 7 天。

## 自主放行条件

当 `auto_approve.enabled: true` 时，满足 ALL 以下条件自动放行：

| # | 条件 | 阈值 | 来源 |
|---|------|------|------|
| 1 | eval_pass_rate_delta ≥ +2% | eval_delta_min: 0.02 | eval-after-apply.sh |
| 2 | 无 P0 回归 | require_p0_free: true | route_scores + eval harness |
| 3 | Canary 24h 无异常 | canary_clean_hours: 24 | canary-evaluator.sh |
| 4 | 变更风险 ≤ med | max_risk_level: med | Claude Code plan step risk |
| 5 | 非敏感变更 | require_human 白名单 | schema/mcp/auth 仍需人工 |

## 始终需人工审批的操作

- Schema 变更 (route_outcomes 表结构、config schema)
- MCP 配置变更 (新增/删除/修改 MCP server)
- Auth 相关变更 (credential、pairing、gateway auth)
- 内存 schema 变更

## 启用流程

```
1. Canary 通道稳定 ≥ 7 天 (canary_ratio=0.1, 0 次异常回滚)
2. min_real_traces_for_eval ≥ 20 连续 7 天
3. 手动运行 3 次 dry-run auto-approve → 全部正确分类
4. 设置 evolve.auto_approve.enabled: true
5. 观察 72h，误放行率 = 0 → 正式启用
```

## 回滚信号

- 误放行 > 0: 立即回滚 enabled=false
- Canary 异常 > 1 次/周: 暂缓启用
- eval_delta 不稳定 (连续 3 次 -/+ 跳变): 增加 min_real_traces
