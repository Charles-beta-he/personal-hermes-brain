---
title: Agent Team 并行任务池方案
created_at: 2026-05-10T20:30:50+08:00
updated_at: 2026-05-10T23:45:00+08:00
status: fully_implemented_and_ratified
ratification: 4_model_certified (Claude + GPT + DeepSeek + MiMo)
source_tick: /Users/charles/.hermes/tick-20260510-121817
---

# Agent Team 并行任务池方案

## 当前判定

**已全栈落地并经多模型认证。**

- Phase 1-5 全部实施完成
- 动态 N 调度 + 任务分类 + 冲突避免 + 任务续接
- 4 模型认证通过 (Claude Opus 4.7 + GPT-5.5 + DeepSeek V4 Pro + MiMo v2.5 Pro)

## 架构总览

```
┌─────────────────────────────────────────────────┐
│              P10 Strategy Layer                  │
│  OKR 定义 → KR 分解 → appetite 分配             │
└─────────────┬───────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────┐
│           Dynamic N Scheduler                    │
│  N = min(ceil(dispatchable/7), groups, 3)       │
│  平滑: 连续 2 轮确认才变更 N                     │
└─────────────┬───────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────┐
│          Task Classifier                         │
│  boundary → conflict_group 映射                  │
│  同组串行, 跨组并行                              │
└─────────────┬───────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────┐
│       Agent Team Controller                      │
│  claim → delegate_task → proof → review          │
│  kill switch + lease TTL + human escape          │
└─────────────┬───────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────┐
│      Task Continuation Manager                   │
│  检测 budget exhaustion → checkpoint → resume    │
│  max_continuations=3, 注入已完成进度             │
└─────────────┬───────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────┐
│  Envelope Bus (SQLite) + Pipeline Tick (cron)    │
│  PENDING→RUNNING→DONE→FAILED→SKIPPED→BLOCKED    │
└─────────────┬───────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────┐
│  Brain Task Orchestrator (source-of-truth)       │
│  + Kanban Bridge (observability mirror)          │
└─────────────────────────────────────────────────┘
```

## 已落地组件

### 1. Brain Task Orchestrator
- 路径: `~/.hermes/scripts/brain_task_orchestrator.py`
- 自检: PASS (34 tasks, 22 dispatchable)
- 命令: list, claim, release, done, proof-check, selfcheck, parallel-dispatch-dry-run, boundary-check

### 2. Dynamic N Scheduler
- 路径: `~/.hermes/scripts/dynamic_n.py`
- 公式: `N = min(ceil(dispatchable/7), conflict_groups, 3)`
- 平滑: 连续 2 轮确认才变更 N (防震荡)
- 当前: raw=3, applied=3

### 3. Task Classifier
- 路径: `~/.hermes/scripts/task_classifier.py`
- 确定性规则: boundary → conflict_group
- 分组: evolution-lane, hermes-core, uvisa-frontend, hermes-router 等
- 同组串行, 跨组并行

### 4. Agent Team Controller
- 路径: `~/.hermes/scripts/agent_team_controller.py`
- Cron: 286f7b115fa5 (every 1h)
- 功能: 动态 cycle, conflict group 调度, claim, proof 收集
- 安全: kill switch, lease TTL, human escape

### 5. Task Continuation Manager
- 路径: `~/.hermes/scripts/task_continuation.py`
- 检测: 5 种 budget exhaustion 信号
- Checkpoint: completed/remaining steps, files changed
- Resume: 注入已完成进度, 跳过已完成步骤
- 限制: max_continuations=3

### 6. Envelope Bus
- 路径: `~/.hermes/scripts/envelope_bus.py`
- DB: `~/.hermes/state/envelope_bus.db`
- 状态: PENDING→RUNNING→DONE→FAILED→SKIPPED→BLOCKED

### 7. Pipeline Tick
- 路径: `~/.hermes/scripts/pipeline_tick.py`
- Cron: 6bc821b4743e (every 1h)
- 功能: brain tasks → envelopes, timeout 处理, escape 检查

### 8. Kanban Bridge
- 路径: `~/.hermes/scripts/kanban_bridge.py`
- Cron: 9e30cb4804db (every 2h)
- 功能: brain → Kanban 单向同步 (观测性)

## 数字护栏

| 参数                 | 值                   | 说明                     |
| ------------------ | ------------------- | ---------------------- |
| appetite_timeout   | 30min (默认)          | 可配置 15/60/120min       |
| max_retry          | 3                   | 超过 escalate+block      |
| max_continuations  | 3                   | budget exhaustion 续接上限 |
| human_escape       | 2 block / 3 crash   | 自动暂停+通知                |
| state_source       | SQLite envelope bus | 唯一状态源                  |
| max_runtime        | 3600s/task          | 单任务最大运行时间              |
| lease_ttl          | 900s                | worker claim 有效期       |
| heartbeat_interval | 120s                | worker 心跳间隔            |
| N_max              | 3                   | 最大并行 agent 数           |
| N_smoothing        | 2 cycles            | N 变更确认轮数               |

## 冲突组 (当前)

| 组名 | 任务数 | 说明 |
|------|--------|------|
| evolution-lane | 13 | 技能进化类任务 |
| hermes-core | 4 | Hermes 核心修改 |
| uvisa-frontend | 2 | uvisa 前端修改 |
| hermes-router | 1 | 能力路由分析 |

## Cron 全景

| Job | ID | Schedule | 说明 |
|-----|-----|----------|------|
| agent-team-cycle | 286f7b115fa5 | every 1h | 动态并行调度 |
| pipeline-tick | 6bc821b4743e | every 1h | envelope bus 同步 |
| kanban-bridge | 9e30cb4804db | every 2h | brain→Kanban 镜像 |
| 8 个旧 jobs | ... | 各异 | 已修复为 MiMo |

## 安全机制

- ✓ Kill switch (controller + bridge)
- ✓ Lease TTL (60min default)
- ✓ Human escape (2 block / 3 crash → auto-pause)
- ✓ Proof artifacts (dir + schema + sha256)
- ✓ Worker 禁止 self-done
- ✓ Conflict group 隔离
- ✓ Task continuation (budget exhaustion resume)
- ✓ N smoothing (防震荡)

## 多模型认证记录

| 轮次      | 方向                                  | 结果                            |
| ------- | ----------------------------------- | ----------------------------- |
| Round 1 | Dir1 Agent Team + Dir2 Kanban Watch | 4/4 approve                   |
| Round 2 | Dir3 Missions Task Pool (amend)     | 4/4 approve                   |
| Round 3 | 合并确认                                | 4/4 confirm = FINAL_CERTIFIED |
| Phase 3 | Agent Team Controller               | GPT+MiMo verified             |
| Phase 4 | Dynamic N + Classifier              | GPT+MiMo verified             |
| Phase 5 | Task Continuation                   | GPT+MiMo verified             |

## 核心方法论书籍

| 书籍                   | 作者          | 应用                        |
| -------------------- | ----------- | ------------------------- |
| Shape Up             | Ryan Singer | appetite 控制, 6 周周期        |
| Measure What Matters | John Doerr  | OKR 目标追踪                  |
| Working Backwards    | Amazon      | PRD 逆向拆解                  |
| Team Topologies      | Skelton     | 团队拓扑, specialist profiles |

## 产物清单

```
~/.hermes/scripts/agent_team_controller.py
~/.hermes/scripts/dynamic_n.py
~/.hermes/scripts/task_classifier.py
~/.hermes/scripts/task_continuation.py
~/.hermes/scripts/envelope_bus.py
~/.hermes/scripts/pipeline_tick.py
~/.hermes/scripts/kanban_bridge.py
~/.hermes/state/envelope_bus.db
~/.hermes/state/task_checkpoints/
~/.hermes/state/proof_artifacts/
~/.hermes/state/dynamic_n_state.json
~/.hermes/memory/docs/adr/long-running-task-pool-design-v1.md
~/.hermes/memory/docs/adr/mm-ratification-final-v1.json
```
