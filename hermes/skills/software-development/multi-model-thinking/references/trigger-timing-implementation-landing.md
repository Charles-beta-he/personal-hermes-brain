# Trigger Timing Implementation Landing — 实现落地记录

> 2026-05-12 落地的事件驱动触发时机改造。记录实际代码变更、脚本路径、新增 schema。

## 变更清单

| 文件 | 行数 | 功能 |
|------|------|------|
| `post-session-autopsy.py` | +56 | classify_failure_group, recommend_autopsy_tier, failure_class_counts, recommended_tier |
| `brain_task_orchestrator.py` | +56 | advisory/certification split, budget signal consumption, advisory done blocking |
| `iteration_budget_doctor.py` | +35 | --emit-signal, budget_signals.jsonl output |
| `brain_task_dispatch_tick.py` | +14 | tier routing fields in multimodel_summary |
| `test_brain_task_dispatch_tick.py` | +9 | run() 适配 ERROR spine |

总计: +170 行, 5 文件

## 新增 Schema: local_brain_trigger_signal_v1

```json
{
  "schema": "local_brain_trigger_signal_v1",
  "ts": "ISO8601",
  "source": "iteration_budget_doctor|post_session_autopsy|orchestrator|validator",
  "phase": "pre_action|mid_loop|post_failure|post_session|periodic_governance",
  "severity": "info|warn|high|critical",
  "signal_type": "iteration_budget_saturation|correction_repeat|tool_failure_repeat|...",
  "recommended_tier": "T0|T1_advisory|T2_advisory|T3_advisory|T3_certification",
  "advisory_only": true,
  "confidence": 0.0-1.0,
  "rationale": "short text"
}
```

信号写入路径: `~/.hermes/state/budget_signals.jsonl`

## 新增函数

### post-session-autopsy.py

- `classify_failure_group(group)` → timeout_or_quota|schema_mismatch|permission_or_auth|missing_dependency|tool_error|unknown
- `recommend_autopsy_tier(*, corrections_count, iteration_budget_count, tool_failures_count, repeat_signature_count, failure_class_counts, high_signal_count)` → T0|T1_advisory|T2_advisory

### brain_task_orchestrator.py

- `task_multimodel_advisory_reasons(task)` → 非强触发原因列表
- `task_multimodel_certification_reasons(task)` → 强触发原因列表 (p0_evolution_blast_radius, loop_non_convergence, stale_claim)

## 阈值

| 条件 | Tier |
|------|------|
| high_signal_count >= 3 | T2 |
| iteration_budget_count >= 2 or tool_failures >= 3 | T2 |
| corrections >= 3 or repeat_signature >= 3 | T2 |
| timeout_or_quota or schema_mismatch in failure classes | T1 |
| any signal present | T1 |
| no signals | T0 |

## Advisory Done Blocking 机制

当 task 只有 advisory_reasons（无 certification_reasons）时：
- 即使 gate 返回 PASS + LOOP_DONE，也会被降级为 PASS_ADVISORY_ONLY
- decision 改为 continue_loop
- advisory_block 字段标记原因
- 结果写入 task frontmatter: multimodel_advisory_only=true, multimodel_certification_authority=false

这确保了 advisory-only 任务不能通过多模型认证关闭。

## Budget Signal Consumption

orchestrator 的 task_multimodel_intervention_reasons 现在会检查 `~/.hermes/state/budget_signals.jsonl`：
- 读取最近 20 条信号
- 如果有 severity=high/critical 且 recommended_tier >= T2 的信号
- 且当前 task 没有强触发原因
- 则注入 `iteration_budget_signal` 作为额外触发原因
- 这会把弱触发升级到 >= 2 信号门槛

## 文件路径

- 触发时机规格文档: `~/.hermes/docs/trigger_timing_policy_v1.md`
- 预算信号文件: `~/.hermes/state/budget_signals.jsonl`
- doctor --emit-signal: `python3 ~/.hermes/scripts/iteration_budget_doctor.py --emit-signal`
