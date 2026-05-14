# trigger_timing_policy_v1.md

> 目标：把 Hermes 本地脑从“事后复盘驱动多模型”切换为
> “事件驱动、分级触发、闭环认证、自收敛循环”。

## 1. Policy Overview

本策略适用于：
- local-brain taskpool
- PUA-loop 式迭代推进
- multimodel intervention 自动触发
- post-session autopsy / iteration budget doctor / orchestrator 协同

核心原则：
1. Deterministic gates first
2. Model agreement is not evidence
3. Advisory ≠ Closeout
4. Structural signals > Keywords
5. Fail-closed for done/certification

---

## 2. Session-Level Authorization

当用户在当前会话明确要求：
- “继续”
- “推进”
- “loop”
- “pua-loop 落地”
- “多模型分析穷尽”

则当前会话应放行为：

### Allowed (会话级放行)
- 继续 loop 推进
- 自动收集证据
- 自动触发 T1/T2 advisory
- 自动重跑 unresolved issue
- 自动写回 latest discussion artifact
- 自动写回 not_certified / continue_loop / round status

### Conditionally Allowed (条件放行)
- T3 certification 继续执行：允许
- T3 closeout 自动 PASS：仅当 gate PASS
- 自动写入 done：仅当 gate PASS + evidence bound

### Denied (不放行)
- 跳过 evidence binding
- 跳过 4/4 required participant panel
- unresolved severity>=3 时标 LOOP_DONE
- advisory 当作 closeout
- provider 降级时伪造 certified

---

## 3. Trigger Timing Model

系统触发点分为 5 层：

### 3.1 pre-action
目标：高风险动作前置拦截。

触发条件：
- blast_radius 高
- 可逆性低
- 接近 done/closeout/certification/ratification
- uncertainty 高

输出：
- phase=pre_action
- recommended_tier=T0/T1_advisory
- advisory_only=true

---

### 3.2 mid-loop
目标：最早自我修正点。

触发条件：
- corrections >= 2
- repeat_signature >= 2
- iteration_budget_used >= 0.70
- 同工具连续低效重复
- 不可分类失败首次出现

输出：
- phase=mid_loop
- recommended_tier=T1_advisory/T2_advisory
- advisory_only=true

---

### 3.3 post-failure
目标：把失败转为结构化分类证据。

失败分类：
- tool_error
- verifier_gap
- requirement_mismatch
- schema_mismatch
- quota_or_timeout
- router_skew
- unknown

触发条件：
- first low-risk failure -> T0/T1
- same failure class 24h >= 2 -> T2
- unknown/high severity/closeout-related failure -> T3 advisory / certification path

输出：
- phase=post_failure
- failure_class
- repeat_count
- recommended_tier

---

### 3.4 post-session
目标：由“总结报告”降格为“证据生产器”。

输出字段：
- correction_count
- tool_failures
- iteration_budget_count
- repeat_signatures
- failure_class_counts
- recommended_tier

规则：
- autopsy 不再只是结果展示
- 它必须产出 orchestrator 可直接消费的 tier 建议

---

### 3.5 periodic governance
目标：双环学习层。

触发条件：
- 每 50 个 task event
- 或每 24h

治理指标：
- trigger_rate
- advisory_count
- confirm_rate
- post_session_only_detect_rate
- late_intervention_rate

调参规则：
- trigger 高 but confirm 低 -> 降噪
- post_session_only 高 -> 提前 mid-loop 阈值
- repeat unresolved T3 issue 高 -> 改走 evidence request loop

---

## 4. Tier Routing Model

### T0
- deterministic / readonly / sanity
- 成本最低

### T1 advisory
- 早介入
- 可建议 retry/replan/evidence collection
- 不能 done

### T2 advisory
- 分歧审查 / repeat failure / mid risk
- 仍不能 done

### T3 advisory
- 高风险或关键转折点前的多模型审查
- 仍然不是 closeout authority

### T3 certification
- 最终 closeout
- 必须 4/4 canonical participants
- 必须 evidence bound to task
- unresolved severity>=3 不能通过

---

## 5. Advisory vs Certification Split

必须硬拆：

### advisory result
可写：
- recommended_tier
- round_status
- last_gate_status
- last_decision
- last_failures
- latest discussion artifact

不可写：
- done
- closeout authority
- certified status as final user-facing completion

### certification result
可写：
- multimodel_status=certified
- multimodel_ratification_artifact
- LOOP_DONE
- done transition

前提：
- ratification gate PASS
- evidence bound to exact task
- canonical participant panel complete

---

## 6. Signal Schema

推荐统一信号 schema：`local_brain_trigger_signal_v1`

字段：
- task_id
- source: autopsy | doctor | orchestrator | validator | dispatch_tick
- phase: pre_action | mid_loop | post_failure | post_session | periodic_governance
- severity: info | warn | high | critical
- signal_type:
  - correction_repeat
  - tool_failure_repeat
  - iteration_budget_saturation
  - verifier_failure
  - unknown_failure
  - blast_radius_high
  - closeout_surface_touch
  - repeat_signature_hit
  - stale_evidence
- recommended_tier: T0 | T1_advisory | T2_advisory | T3_advisory | T3_certification
- advisory_only: true/false
- evidence_refs: []
- window: string
- confidence: 0-1
- rationale: string

---

## 7. Threshold Defaults

### Mid-loop T1
- corrections >= 2
- repeat_signature >= 2
- iteration_budget_used >= 0.70

### Mid-loop T2
- corrections >= 3
- repeat_signature >= 3
- iteration_budget_used >= 0.85
- verifier_failure >= 1

### Post-failure T2
- same failure class in 24h >= 2

### Post-session promotion
- autopsy recommended_tier >= T2
- 或 >= 2 个强信号同时出现

### Governance trigger
- 50 events / 24h
- 评估 trigger vs confirm 率

---

## 8. Loop Economy Rules

避免 pua-loop 白烧模型：

### cheap pass
- 风险低
- deterministic gate 明确
- 优先 T0/T1

### mid audit
- 有分歧但不确定
- 走 T2 advisory
- 收集 evidence

### closeout gate
- 最终 done/closeout
- 走 T3 certification
- 必须 4/4 + evidence binding

### anti-burn rules
1. 同一 task 连续多轮 unresolved severity>=3：
   - 暂停 full T3
   - 改 evidence request loop
2. provider quota confidence 低：
   - advisory 偏 cheap route
   - T3 仅必要时触发

---

## 9. Governance Ratchet

建议实现 `trigger_effectiveness_v1`

字段：
- window
- trigger_count
- advisory_count
- escalation_count
- certified_count
- confirm_rate
- repeat_trigger_rate
- post_session_only_detect_rate
- late_intervention_rate
- recommended_adjustment

自动规则：
- trigger_rate > 0.30 && confirm_rate < 0.10 -> 降噪
- post_session_only_detect_rate > 0.20 -> 提前介入阈值
- unresolved T3 repeat 空转 -> 改 evidence request loop

---

## 10. Implementation Phases

### P0
- autopsy 输出 recommended_tier / repeat_signature / failure_class_counts
- orchestrator 拆 advisory / certification
- advisory results 不能 done

### P1
- doctor --emit-signal
- orchestrator mid-loop accumulator
- post_failure classifier
- dispatch/dynamic step 支持 advisory-tier routing

### P2
- trigger_effectiveness ratchet
- loop economy mode
- governance auto-tuning

---

## 11. Done Conditions

### LOOP continue
- gate FAIL
- unresolved severity>=3 > 0
- evidence request pending
- governance ratchet 标记空转

### LOOP_DONE
- deterministic gates pass
- ratification gate PASS
- evidence bound to exact task
- canonical 4/4 panel satisfied
- no actionable unresolved blocker

### LOOP abort
- provider blocked
- external dependency missing
- requirement fundamentally changed

---

## 12. Current Recommendation

当前应落地为：

- 会话级用户要求可放行自动推进
- advisory 自动推进：放行
- certification 执行推进：放行
- closeout 自动通过：条件放行
- done 写入：条件放行

即：
用户授权执行推进，但完成判定仍由 gate 控制。
