---
type: proof
lane: evolution
status: accepted
created: 2026-05-14T17:42:00+08:00
source_task: 2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略
concepts: ["budget-exhaustion", "auto-handoff", "continuation-packet", "fallback-policy", "quota-observability", "relay-ordering"]
inputs:
  - /Users/charles/Documents/brain/05-实践与项目/tasks/2026-05-14-fallback-threshold-policy-brief.md
  - /Users/charles/Documents/brain/05-实践与项目/tasks/2026-05-14-quota-observability-policy-brief.md
  - /Users/charles/Documents/brain/05-实践与项目/tasks/2026-05-14-relay-ordering-policy-brief.md
---

# Hermes 预算耗尽后的自动接力与回退策略：最终方案

## 0. Verdict

本方案把父任务拆出的三层策略合成为可落地的最小控制面：

1. quota observability：识别 quota_state 与 confidence。
2. fallback threshold：把 quota/context/side-effect 风险映射为 GREEN / AMBER / RED / BLACK。
3. relay ordering：按风险等级执行 checkpoint → task transition → handoff/retry/resume。

目标不是立即实现完整自动调度，而是先建立可验证、可回退、不会丢状态的 budget-handoff 状态机。

## 1. 状态机

```text
START
  ↓
OBSERVE_QUOTA
  ↓
DECIDE_THRESHOLD
  ├─ GREEN → CONTINUE → VERIFY → DONE/LOOP
  ├─ AMBER → NARROW_SCOPE → LOCAL_CHECK → DECIDE_THRESHOLD
  ├─ RED → CHECKPOINT → TRANSITION_TASK → HANDOFF_OR_RETRY → RESUME_FROM_PACKET
  └─ BLACK → EMERGENCY_CHECKPOINT → BLOCK_OR_RETRY_OR_MANUAL → RESUME_FROM_PACKET
```

### State: OBSERVE_QUOTA

输入：provider/tool errors、Hermes result envelope、gateway/runtime status、local command evidence、human/session observation。

输出：

- quota_state: healthy | degraded | limited | exhausted | unknown
- confidence: high | medium | low | unknown
- evidence_ref: file path / tool output hash / command log

### State: DECIDE_THRESHOLD

把 quota_state、confidence、context pressure、side-effect risk、taskpool dependency risk 映射为：

- GREEN：正常继续。
- AMBER：收窄范围，优先 local deterministic check。
- RED：停止探索，写 continuation packet，再 transition/handoff。
- BLACK：停止非 checkpoint 副作用，紧急保存状态，block/retry/manual。

### State: CHECKPOINT / EMERGENCY_CHECKPOINT

生成 continuation packet，至少包含：

```yaml
continuation_packet:
  task_id: "..."
  parent_id: "..."
  fallback_band: RED
  quota_state: limited
  confidence: high
  authority: budget-handoff
  completed: []
  pending: []
  modified_files: []
  verification:
    passed: []
    missing: []
  next_atomic_action: "..."
  blocked_reason: "..."
  resume_instructions: "..."
```

### State: TRANSITION_TASK

根据状态选择：

- review：当前 slice 完成，等待验收/复核。
- retry：同一任务可在 cooldown 后恢复。
- blocked：缺权限、依赖、配额或不可安全继续。
- child task：只有当 scope 必须拆分，且 parent/dependency/evidence 明确时创建。
- done：只有 acceptance evidence 满足时使用。

### State: HANDOFF_OR_RETRY

动作顺序必须是：

1. checkpoint durable；
2. task status/claim durable；
3. 再切换模型/session/provider 或释放 claim；
4. 新 session 只从 continuation packet 恢复。

## 2. 触发条件

### GREEN

- quota_state=healthy；
- 没有明显 context pressure；
- 当前剩余步骤可在本 session 完成；
- 无未验证高风险副作用。

动作：继续执行，不创建 continuation packet。

### AMBER

任一成立：

- quota_state=degraded；
- 第一次 rate-limit/429/latency spike；
- context 明显压缩但仍可完成一个小验证；
- 剩余步骤多于安全预算；
- side effect 可逆但尚未完全验证。

动作：收窄范围，优先 local check，准备 continuation facts，但不急于切 session。

### RED

任一成立：

- quota_state=limited；
- repeated 429 / cooldown / circuit-open；
- 一次额外探索可能丢失可恢复状态；
- parent/child 依赖不 checkpoint 会变得不清楚；
- pending side effect 需要验证或 rollback 记录。

动作：必须先 checkpoint，再 transition，再 handoff/retry。

### BLACK

任一成立：

- quota_state=exhausted；
- required authority tier 全部不可用；
- current session 无法安全完成 checkpoint 以外操作；
- partial external side effect 无法验证。

动作：紧急 checkpoint；停止新副作用；blocked/retry/manual。

### UNKNOWN

unknown 不能当 healthy。

规则：

1. 优先不耗模型预算的 deterministic local check。
2. 只允许一次 bounded retry，前提是 idempotent 且无 pending side effect。
3. retry 后仍 unknown，则按 degraded/AMBER 规划。
4. 非幂等或高风险任务，unknown 直接要求 checkpoint。

## 3. 自动 / 人工边界

### 可自动执行

- 生成 continuation packet。
- 写 proof log / evidence refs。
- 将 pending/claimed/running 转为 review/retry/blocked。
- 创建明确 parent link 的 child task。
- cooldown 后恢复 retry。
- 切换到同权限或更高权限的模型/provider，且任务无高风险副作用。

### 必须人工或更高权限确认

- 购买/扩容/付费提升 quota。
- 降级到低权限模型执行高风险操作。
- 对外部系统产生不可逆副作用。
- 自动关闭长期 blocked P1/P2 主线。
- 删除/覆盖用户项目代码、发布、部署、资金/账号相关操作。
- 无 evidence 时强行 done。

### 禁止

- 隐式 auto-purchase。
- 无上限 retry。
- 无 parent/evidence 的重复任务创建。
- quota unknown 时假装 healthy。
- checkpoint 未落盘就 release claim 或切 session。

## 4. 失败回退策略

| Failure | Fallback |
| --- | --- |
| provider quota/rate-limit | checkpoint → retry with cooldown or switch same-authority provider |
| model circuit open | checkpoint → retry after cooldown; if repeated, blocked with evidence |
| context pressure | checkpoint → new session resume from packet |
| unknown quota | local deterministic check → one bounded retry → AMBER checkpoint |
| partial side effect | stop new work → verify/rollback note → blocked/review |
| taskpool transition failed | keep local packet artifact; do not release claim until transition succeeds |
| handoff session failed | mark retry/blocked with packet path and resume instructions |

## 5. 观测指标

最小指标：

- budget_handoff_trigger_count
- quota_state distribution
- fallback_band distribution
- continuation_packet_created_count
- resume_success_count
- retry_after_handoff_count
- blocked_due_to_quota_count
- duplicate_task_prevented_count
- noop_decision_count
- change_decision_count
- evidence_missing_block_count

每次 RED/BLACK 至少记录：

- task_id / parent_id；
- quota_state / confidence；
- fallback_band；
- source signal；
- evidence_ref；
- next_atomic_action；
- selected transition；
- resume result。

## 6. 最小落地方案

### Phase 1: 手动控制面落地

- 在 task proof log 中采用 continuation_packet schema。
- 在 blocked/retry/review transition 时强制引用 evidence_ref。
- 对 P1/P2 evolution 任务使用 GREEN/AMBER/RED/BLACK 标签作为 reviewer 语言。

验收：父任务能从三份 brief 形成稳定 handoff strategy，且 taskpool selfcheck PASS。

### Phase 2: 脚本化 helper

新增或扩展一个 helper，例如：

```text
brain_task_orchestrator.py budget-handoff-check \
  --task TASK_ID \
  --quota-state limited \
  --confidence high \
  --signal "circuit open" \
  --next-action "resume from packet"
```

输出：recommended_band、required_packet_fields、recommended_transition。

验收：同一输入 deterministic 输出同一 transition 建议，不自动执行高风险动作。

### Phase 3: 自动化但 default-safe

- 仅 RED/BLACK 自动生成 packet；
- 不自动购买、不自动部署、不自动删除；
- high-risk action 仍需 authority gate；
- all automation fail-soft。

验收：post-update/selfcheck 不破坏现有任务池；重复触发不创建 duplicate task。

## 7. 父任务 Acceptance Mapping

- 状态机：已定义 START → OBSERVE_QUOTA → DECIDE_THRESHOLD → CONTINUE/NARROW/CHECKPOINT/BLACK → TRANSITION → HANDOFF/RESUME。
- 触发条件：GREEN/AMBER/RED/BLACK + UNKNOWN handling 已定义。
- 自动/人工边界：可自动、需人工、禁止动作已定义。
- 失败回退：按 provider quota、circuit、context、unknown、partial side effect、transition failure、handoff failure 定义。
- 观测指标：10 个最小指标已定义。
- 最小落地方案：Phase 1/2/3 已定义。

## 8. Noop-vs-change 总规则

NOOP：状态真实、证据充分、无 recoverability 风险、无 pending side effect、无 taskpool dependency ambiguity。

CHANGE：状态可能丢失、quota/circuit repeated、RED/BLACK、pending side effect、parent/child dependency 会误导、unknown 且无法安全 bounded retry。

## 9. Final Recommendation

父任务可从 `blocked(loop_non_convergence)` 推进到 `review`：前置三层已经收敛，最终方案已具备 acceptance evidence。下一步不是继续拆子任务，而是进行 ratification/certification；若多模型仍因 economy_pause 无法运行，应以该最终方案作为 human review artifact，解除 loop_non_convergence。