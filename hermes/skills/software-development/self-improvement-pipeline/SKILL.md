---
name: self-improvement-pipeline
description: Use when the task falls under Self-Improvement Pipeline — 自进化优先调度层 (L0-L5).
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - software
    - development
    - self
    - improvement
    - pipeline
    related_skills:
    - darwin-skill
    - design
    - devops
    - loop
    - mcp
    - p10
    - p7
    - p9
---

# Self-Improvement Pipeline — 自进化优先调度层 (L0-L5)

## Overview


> 自动挖取改进需求、按 bandit score 选最优路线、eval 准入门。
> 核心原则: **不重造轮子 — 用 Hermes 原生能力 (hooks/cron/sqlite/skills/config) 填补缺口。**

## When to Use

- The task falls under Self-Improvement Pipeline — 自进化优先调度层 (L0-L5)

## Architecture

```
L0 执行层:  拉源 → triage → router(选skill) → exec → verify
L1 观测层:  shell hook 自动写入 trace → route_outcomes SQLite
L2 短环层:  router skill (多臂老虎机, e-greedy 90/10)
            score = pass_rate - 0.1*cost - 0.01*duration/60
L3 中环层:  离线分析: 路线全灭检测 + 工具模式挖掘 + skill 退化修复
L4 准入门:  eval-harness — 85条基线, 三维比较(pass_rate/cost/duration), 5%阈值
L5 灰度层:  config.yaml canary_ratio + skills-staging/ 目录
```

### Architecture Alignment Gate — 自进化必须跟随总体架构方向

自进化不是随机堆功能或看到外部框架就照搬；每个 evolution 版本/任务必须声明它提升了总体架构的哪一层或哪条控制面。默认 north star 是：L0-L5+LX 多模型架构、local-brain taskpool、evidence-first、bounded autonomy、work/evolution 分道、fail-closed closeout。

每个自进化任务进入执行前必须回答并记录：
- `lane`: `work` / `evolution` / `advisory`；work 交付优先，不被 evolution 占用。
- `architecture_target`: L0/L1/L2/L3/L4/L5/LX/local-brain/skill-graph/provider-quota/taskpool 等。
- `capability_delta`: 具体能力提升，例如更准的路由、更低误报、更强证据门、更稳的 cron、更少 ghost signal。
- `anti_drift_check`: 是否违背现有总体方向；是否重复造轮子；是否绕过 evidence gate 或 fail-closed gate。
- `acceptance_evidence`: 测试/自检/usage-score/graph-check/ratification artifact，而不是“模型觉得更好”。

如果无法映射到总体架构方向，默认降级为 `advisory`，不得自动落地为 runtime 改动。

## Double-Brain 模式 (Hermes ↔ Claude Code)

> Hermes 是执行体 (24/7), Claude Code 是架构师 (强规划)。通过结构化 JSON 通道互通。

### 核心数据流

```
Hermes (执行体)                    Claude Code (架构师)
  │                                      │
  ├─ self-describe.sh → state.json       │
  │  (summary <8K + details file)        │
  │                                      │
  │             state.json ──────────────┤
  │                                      ├─ claude -p --skills plan,architect,critic
  │                                      │   retry×3 with schema feedback
  │    JSON plan (5 steps max) ←─────────┤
  │                                      │
  ├─ apply-plan.sh                       │
  │  drain in-flight → snapshot → apply  │
  │                                      │
  ├─ eval-after-apply.sh                 │
  │  baseline(7d) vs new(1h) →           │
  │  delta < -5%→rollback                │
  │  3连败→暂停cron                      │
  │                                      │
  └─ evolve.log (append-only)            │
```

### 4 个关键补丁 (实战发现, 必须外加)

| # | 补丁 | 触发条件 | 动作 |
|---|------|---------|------|
| 1 | **Degradation path** | claude -p 失败或不可用 | 降级到 self-improvement-pipeline.py 本地规划, 标记 degraded=true |
| 2 | **Retry-with-feedback** | JSON plan schema 不合规 | 注入具体错误信息 (哪个字段缺了), 重试最多 3 次 |
| 3 | **Summary mode** | state.json 超 8K tokens | 输出 summary (<8K) + details_pointer (文件系统), 非原始 dump |
| 4 | **Drain phase** | apply 时 inflight tasks 未完成 | 拒收新 task → wait max 600s → 超时则 abort |

降级模式 key 设计:
- degraded=true → eval 不计入 baseline (不污染统计)
- 3 次连续 degraded → 告警人审 (claude -p 装出问题)
- 降级时 consult-claude.sh 自动 fallback, 调用栈透明

Schema retry feedback 示例:
```
FEEDBACK from previous attempt 1:
- missing 'steps' array
- steps missing required field 'expected_gain'
- step risk must be 'low' or 'med', not 'high'
Re-output JSON plan. Fix ALL of the above errors.
```

Drain 实现关键:
```bash
hermes config set scheduler.accept_new false  # 立即拒新
sleep 30                                        # 给 inflight 缓冲
while [ $(sessions_running) -gt 0 ] && [ $waited -lt 600 ]; do
    sleep 5; waited+=5
done
[ $waited -ge 600 ] && { echo "ABORT: drain timeout"; exit 1; }
# ... apply changes ...
hermes config set scheduler.accept_new true   # 恢复
```

### 终止条件 (写死在编排 skill 中)

| 条件 | 动作 |
|------|------|
| 自描述失败 | abort, 写错误日志, 跳过本轮 |
| plan schema 3 次校验失败 | 降级路径 (#1) |
| snapshot 备份失败 | abort (不允许无网执行) |
| 3 次连续 eval reject | 暂停 evolve cron, 人等审 |
| 3 次连续 degraded | 告警人审 (claude -p 装出问题) |

## Cron 时序链 (12 jobs, 已错开分钟)

```
00:05  每日健康度监控 (V函数)
00:10  自循环优化扫描
00:30  brain-hourly-sync (每小时 :30)
01:00  multi-brain-consult-models-nightly (Phase 6)
02:00  夜间自主进化审计
02:15  skill-steward-daily-audit
03:00  双脑自进化 ← 核心: describe → consult → apply → eval
04:15  Sun snapshot-GC + evolve.log月归档
05:00  */6h 自进化健康监控告警 (错开至 :05)
09:00 Mon 每周失败模式分析
23:00  PA每日进化触发
*/6h   canary灰度评估 (降频 1h→6h, 省 75% 周期)
```

**关键教训**: 所有 job 默认 minute=0 导致整点踩踏 (00:00 曾有 5 job 并发)。
必须错开到 :05/:10/:15/:30。`hermes cron edit <id> --schedule "5 0 * * *"` 可改。

## 核心经验 (从实战中总结)

### 关于 Hermes 原生能力

| 设计需求 | Hermes 原生 | 实际方案 |
|---------|-------------|---------|
| 持久化 route outcomes | `hermes memory append --table` (不存在) | SQLite route_outcomes.db + WAL mode |
| 自定义 metrics 查询 | `hermes insights --metric` (只读固定指标) | route_store.py CLI (stats/scores/summary) |
| 实时 trace 写入 | shell hook (存在) | record-trace.sh, 需 hooks_auto_accept: true |
| 灰度放量 | config.yaml skills section (存在) | 扩展 skills.canary_ratio |
| 技能版本管理 | 无 staging 概念 | skills-staging/ 目录 + promote 脚本 |

### 采样率策略

Shell hook 接收所有匹配的工具调用, 需要采样避免数据爆炸:
- 启动阶段: 30% 足够训练 bandit
- 稳定阶段: 50% 提供充足统计置信度
- 采样通过 `$RANDOM % 100` 实现, 无需外部依赖

### hooks_auto_accept

非 TTY 环境 (cron/gateway) 必须设置为 true, 否则 hook 即使注册也无法执行:
```yaml
hooks_auto_accept: true
```

### SQLite WAL 模式

route_outcomes.db 被多个进程并发读写:
- shell hook (cron 或每次工具调用)
- route_store.py CLI 查询
- router skill 读取 scores
- WAL mode + synchronous=NORMAL 防止写锁阻塞读

## 脚本清单 (13 个)

| 脚本 | 层 | 位置 | 功能 |
|------|----|------|------|
| `route_store.py` | L1 | `~/.hermes/scripts/` | SQLite 存储 + bandit 评分 CLI |
| `post-session-autopsy.py` | L0 | `~/.hermes/scripts/` | 从 session JSON 挖改进信号 |
| `self-improvement-pipeline.py` | L0 | `~/.hermes/scripts/` | 聚合信号 + 优先级排序 |
| `eval-harness.py` | L4 | `~/.hermes/scripts/` | 85条基线, 三维比较, promote/reject |
| `self-test.py` | 测试 | `~/.hermes/scripts/` | 全组件自动验证 (24项) |
| `l3-route-collapse.py` | L3-B | `~/.hermes/scripts/` | 检测路线全灭 → 提案新 skill |
| `l3-tool-patterns.py` | L3-C | `~/.hermes/scripts/` | 挖掘重复 bash/API → 提案 MCP |
| `record-trace.sh` | L1 | `~/.hermes/agent-hooks/` | shell hook, 50% 采样写入 trace |

## Eval Baseline

位置: `~/.hermes/eval/`
- `baseline-prompts.json` — 85 条测试用例, 12 个 task_class
- `eval-baseline.json` — 基线版本 v2
- `promote-log.jsonl` — 所有 promote 记录

覆盖的 task_class:
feature.frontend(10) | feature.backend(10) | bugfix(5) | refactor(5)
research(5) | devops(5) | config(5) | planning(5)
code_review(5) | testing(5) | documentation(5) | security(5)
data(5) | general(10)

## Gray/Canny 配置

```yaml
# ~/.hermes/config.yaml
evolve:
  canary_ratio: 0.1    # 10% 流量走 staging skills
  canary_log: ~/.hermes/notes/canary-log.jsonl
  auto_approve:
    enabled: false       # 需 real≥50 + canary 7d clean 才能开启
    criteria:
      eval_delta_min: 0.02
      canary_clean_hours: 24
      max_risk_level: med
    guard:
      require_p0_free: true
      require_human: schema_changes,mcp_config,auth_changes
```

## MCP 提案自动审核流水线 (L3-C 实践经验)

当 L3-C 工具模式挖掘生成 MCP 提案后, 完整的审核流程:

```bash
# Step 1: 扫描所有 skill 中的 bash 模式
python3 ~/.hermes/scripts/l3-tool-patterns.py --threshold 15

# Step 2: 读取每份提案
cat ~/.hermes/mcp/proposals/mcp-proposal-*.md

# Step 3: 逐份评估 (三条标准):
#   a. 该模式是否有 Hermes 原生工具已覆盖? (例如 search_files 已存在 → 驳回)
#   b. 是否只是单行 shell 命令? (例如 npm install, pip install → 驳回, terminal 足够)
#   c. 是否值得 MCP 封装的复杂度? (高频 + 多 skills + 结构化操作 → 实施)

# Step 4: 对通过评估的: 编写 MCP server + 注册 config.yaml
# Step 5: 对驳回的: 写 ASSESSMENT.md 留存决策理由
```

### 实际审核案例 (本轮 5 份提案的决策)

| 提案 | 评估维度 | 决策 | 依据 |
|------|---------|------|------|
| git_operations (56x/11skills) | a=未覆盖, b=否(非单行), c=是(高频结构化) | ✅ 实施 | 6-tool MCP server |
| http_requests (38x/13skills) | a=已覆盖(web_search), c=否 | ❌ 驳回 | 重复造轮子 |
| package_manager (16x/11skills) | b=是(单行命令) | ❌ 驳回 | terminal 足够 |
| python_packages (53x/24skills) | b=是(单行命令) | ❌ 驳回 | terminal 足够 |
| file_searching (51x/20skills) | a=已覆盖(search_files) | ❌ 驳回 | 提案自身也说无需封装 |

评估原则:
- 数量多不等于值得 MCP。53 次 pip install 就是 53 个单行命令, MCP 封装反而增加延迟
- 真正需要 MCP 的是**结构性操作**(git commit 带多个参数, 状态检查)而非自动化无关的 shell 单行
- 实施前必须确认提案的 suggestion 是否合理

## Verification Checklist

```bash
# 全组件自测
python3 ~/.hermes/scripts/self-test.py

# 查看路线分数 (含 Real/Synthetic 分拆)
python3 ~/.hermes/scripts/route_store.py summary

# Cron 健康一键诊断
hermes cron status && hermes gateway status

# 检查系统健康
python3 ~/.hermes/scripts/eval-harness.py --status
python3 ~/.hermes/scripts/route_store.py summary

# 手动跑一次完整管线
python3 ~/.hermes/scripts/post-session-autopsy.py --recent 10 --write
python3 ~/.hermes/scripts/self-improvement-pipeline.py --write --auto-exec
```

### Manual trigger runbook (gateway/Telegram request)

Use when the user says “触发自进化 loop”, “run self-evolution now”, or asks to prove a self-improvement tick happened now rather than waiting for the nightly cron.

1. Locate the existing job and scripts before triggering:
   ```bash
   hermes cron list
   test -f ~/.hermes/scripts/self-improvement-pipeline.py
   test -f ~/.hermes/scripts/post-session-autopsy.py
   tail -5 ~/.hermes/logs/evolve.log
   ```
2. Trigger the scheduled self-evolution job by job id (usually the job named `双脑自进化 (Hermes→ClaudeCode→落地→Eval)`):
   ```bash
   hermes cron run <job_id>
   ```
   If using the Hermes cronjob tool, `run` may only move `next_run_at` to “now”. Wait for the scheduler, then re-list until `last_run_at` changes and `last_status=ok`; do not treat `next_run_at` movement alone as proof of execution.
3. Run the deterministic local pipeline as additional evidence and to force fresh signals/action-plan artifacts:
   ```bash
   python3 ~/.hermes/scripts/post-session-autopsy.py --recent 10 --write
   python3 ~/.hermes/scripts/self-improvement-pipeline.py --write --auto-exec
   python3 ~/.hermes/scripts/self-improvement-pipeline.py --preview
   ```
   `--auto-exec` can legitimately record a `kept` evolution closure while saying `No high-ROI actions to execute`; that means the loop generated/updated the queue but did not apply a risky patch.
4. Verify operational health after the tick:
   ```bash
   python3 ~/.hermes/scripts/usage-score.py
   python3 ~/.hermes/scripts/cron-health-quarantine.py
   python3 ~/.hermes/scripts/cron-missed-run-guard.py
   python3 ~/.hermes/scripts/self-test.py
   ```
   Healthy closure target: cron bad_count=0, missed_count=0, self-test all pass. Usage grade can be B if known non-blocking components such as ensemble/ratification corpus are intentionally empty; report the components rather than inflating the grade.
5. If the loop wrote auditable artifacts, commit only scoped evidence files (no push unless explicitly asked):
   ```bash
   cd ~/.hermes
   git add -- logs/evolve.log notes/improvement-action-plan.json notes/improvement-signals.jsonl
   git diff --cached --check
   git diff --cached --unified=0 -- logs/evolve.log notes/improvement-action-plan.json notes/improvement-signals.jsonl  # scan added lines for secrets
   git commit -m "chore(evolve): trigger self-improvement loop"
   git status --short -- logs/evolve.log notes/improvement-action-plan.json notes/improvement-signals.jsonl
   ```
- [ ] Preconditions, scope, and tool availability were checked before following this workflow.
- [ ] The key output artifacts, commands, or side-effects were verified by read-back or direct inspection.
- [ ] The final result still matches the trigger and acceptance shape of this skill.
## Post-trigger audit: distinguish “ran” from “evolved”

Use this when a user asks to analyze a just-triggered self-evolution loop, especially after manual `hermes cron run <self-evolve-job>` or `self-improvement-pipeline.py --write --auto-exec`.

Core class of issue: a self-evolution tick can execute successfully and still fail to produce useful evolution. Treat scheduler success, queue generation, action execution, and performance improvement as separate facts.

Audit checklist:

```bash
# 1. Prove scheduler/script completion only
hermes cron list | grep -A12 -B2 'self-improvement\|自进化\|双脑'

# 2. Prove local queue/action-plan generation
python3 ~/.hermes/scripts/post-session-autopsy.py --recent 10 --write
python3 ~/.hermes/scripts/self-improvement-pipeline.py --write --auto-exec
cat ~/.hermes/notes/improvement-action-plan.json

tail -5 ~/.hermes/logs/evolve.log

# 3. Prove operational health separately
python3 ~/.hermes/scripts/usage-score.py
python3 ~/.hermes/scripts/cron-health-quarantine.py
python3 ~/.hermes/scripts/cron-missed-run-guard.py
python3 ~/.hermes/scripts/self-test.py
```

Interpretation rules:
- `last_status=ok` means the cron script completed; it is not proof that a useful improvement happened.
- `eval_result=kept` in `evolve.log` may only mean the priority queue had items. Check whether any item was actionable/executed.
- If `baseline/new/delta` are constant zeros, do not claim measured improvement. Report this as an observability/verifier gap.
- A HIGH item can be skipped if `roi < actionable_threshold` (currently `roi >= 2.0 and impact >= 4`). This is a triage/gating design issue, not automatically a runtime failure.
- `fix_tool_config` should not auto-edit config based on vague failure aggregates. First generate read-only diagnostics: exact tool, error signature, count, first/last seen, stale status, and current operational health.
- Usage grade can be B even when runtime is green if ensemble/ratification corpus components are missing. Separate `operational_health_grade` from `evidence_readiness_grade` in reports.

Recommended low-risk next implementation slice after this audit:
1. Add action-state ledger fields to closure events: `generated_count`, `actionable_count`, `executed_count`, `pending_review_count`, `skipped_below_threshold_count`, `top_item_roi`, `top_item_impact`, `skipped_reason`, `useful_evolution`.
2. Add read-only `tool-failure-diagnostic-<ts>.json` generation for `fix_tool_config` rather than changing config or thresholds first.
3. Improve autopsy aggregation from detail strings to structured `tool_name`, `error_signature`, `exit_code`, `count`, `first_seen`, `last_seen`, `stale_status`, `suppression_reason`.

When landing this slice, treat it as a governance-code change and close the loop with TDD + evidence-first ratification:
1. Add/extend regression tests before or alongside implementation:
   - `scripts/test_self_improvement_pipeline.py` for action-state ledger and read-only diagnostic schema.
   - `scripts/test_post_session_autopsy.py` for structured `tool_name + error_signature + exit_code` aggregation.
   - `scripts/test_usage_score.py` for `semantic_grades.operational_health` vs `evidence_readiness`, and for certified `tick-*/discussion_result.json` artifacts counting as ratification corpus when `status` is certified, truth gate allows certification, and 2+ models participated.
   - `scripts/test_consult_models_integration.py` for grounding aliases such as `claims_supported` / `supported_claim_ids` and raw unlinked evidence -> `needs_link_review`.
   - `scripts/test_ensemble_vote_integration.py` for executed ensemble votes persisting `execute=true`; without this log field, `usage-score.py` will continue reporting `ensemble_executed` missing even after real model calls.
2. Run deterministic gates before multi-model ratification:
   ```bash
   cd ~/.hermes
   python3 -m py_compile scripts/self-improvement-pipeline.py scripts/post-session-autopsy.py scripts/consult_models.py scripts/usage-score.py scripts/self-test.py
   python3 -m unittest scripts/test_self_improvement_pipeline.py scripts/test_post_session_autopsy.py scripts/test_consult_models_integration.py scripts/test_usage_score.py -v
   python3 scripts/usage-score.py
   python3 scripts/self-improvement-pipeline.py --write --auto-exec
   python3 scripts/cron-health-quarantine.py
   python3 scripts/cron-missed-run-guard.py
   python3 scripts/self-test.py
   ```
   Run `usage-score.py` before `self-improvement-pipeline.py --write --auto-exec` so the diagnostic can include fresh `semantic_grades` health context.
3. Build a `consult_models.py` evidence-first state for acceptance, not just a prose summary. Put each acceptance assertion in `state.claims` and deterministic outputs/diff summaries in `state.evidence` using explicit `claims_supported` links. Locally verify `build_evidence_bundle(state)` and `evaluate_truth_gate(bundle)` report `verified_claim_count == claim_count`, `truth_status=grounded`, and no `unsupported` / `needs_link_review` high-severity claims before running T3.
4. Full multi-model acceptance requires the ratification artifact, not just truth-gate precheck:
   ```bash
   python3 scripts/consult_models.py run /tmp/<state>.json --tier T3 --quorum 4 --discussion --max-rounds 5 --keep --timeout 180
   ```
   If the command times out after planner fan-out or lacks `discussion_result.json`, report weak consensus / not fully ratified and inspect the tick directory rather than claiming certification.
5. Before committing, stage only scoped scripts/tests/runtime evidence, run `git diff --cached --check`, scan staged added lines for secret-like patterns, verify `git diff --cached --name-only`, then local commit only; do not push unless explicitly asked.

## Pitfalls (实战发现)

1. **Shell hook 仅在非 TTY 需要 auto_accept**: cron/gateway 环境需要提前设置 hooks_auto_accept: true, 否则 hook 静默不执行
2. **SQLite lastrowid 在 Python 3.12+ 行为不同**: `conn.execute().lastrowid` 报错. 改用 `cursor = conn.execute(...); cursor.fetchone()[0]`
3. **YAML frontmatter 中 description 含引号/冒号会解析失败**: 避免在 SKILL.md 的 frontmatter description 中使用双引号、单引号或冒号
4. **工具失败检测误报**: 工具返回 JSON 含 "error": null 作为 key name. 必须解析 JSON 后判断 exit_code 而非正则匹配 raw string
5. **hook 的 matcher 正则影响性能**: 匹配范围过大会每工具调用触发, 消耗 5ms/hook. 用具体 tool_name 限制
6. **ε-greedy 的 ε 不宜超过 10%**: 过高探索导致服务品质波动, 过低导致策略锁死

7. **Cron 全部静默不执行 → 先查 cron_mode 而非进程**:
   - `hermes cron status` 显示 "Gateway is not running — cron jobs will NOT fire"
   - 根因 99% 是 `approvals.cron_mode: deny` (默认值), 不是 scheduler 故障
   - 修复: `cron_mode: approve` + `hermes gateway install` (macOS launchd) + `hermes gateway status` 验证
   - `hermes cron tick` 会同步跑所有到期 job, 11 个 job 超 60s 超时 — 不要用它调试

8. **合成 trace 必须先打标再写入 — 否则污染 eval gate**:
   - 生成合成 trace 提升样本量 → pass_rate 虚高 → eval gate 放行回归 → 恶性循环
   - 正确流程: ALTER TABLE 加 `is_synthetic` → route_store.py 支持 `--synthetic` flag → summary 显示 Real/Synthetic 分拆
   - eval gate 必须用 `min_real_traces` (默认 20) 而非 total traces
   - Claude Code 在 2026-04-26 审计中直接指认为 P0 风险

9. **route_outcomes schema 迁移必须同步更新 4 处**:
   - (a) SQL ALTER TABLE 加列
   - (b) `_ensure_schema()` 的 CREATE TABLE IF NOT EXISTS (新安装用)
   - (c) `append()` 的 INSERT 语句
   - (d) CLI `--synthetic` flag + `append` 传参
   - 遗漏任一处 → 静默失败, 无报错

10. **Auto-approve 标准应写为 config 而非代码判断**:
    - config.yaml `evolve.auto_approve` section: criteria (eval_delta_min, canary_clean_hours, max_risk_level) + guard (require_p0_free, require_human 白名单)
    - 启用前置条件: real_traces≥50, canary 7d clean, dry-run 复现历史决策
    - 当前 enabled=false — 避免过早自动化

11. **`hermes chat -q` 不能用于 eval baseline 批量评估**:
    - 非 PTY 环境下返回 CLI 界面（Available Tools 列表）而非模型输出
    - subprocess 调用 120s 超时，且实际耗时 26-110s/prompt
    - 正确方案: 直接用 API（DeepSeek/Xiaomi/Anthropic）通过 `requests` 调用
    - `fill-baseline-parallel.py` 使用 ThreadPoolExecutor(max_workers=4) 并行填充
    - 85 prompts 约 2 分钟完成（vs hermes chat -q 串行 30+ 分钟）

12. **eval-harness init_baseline() 不能依赖虚构 skill 名**:
    - 旧版调用 `evaluate_skill("current_production")` → "Skill not found"
    - 正确实现: 直接遍历 prompts 列表，逐个调 API，结果写入 baseline
    - 已修复: `~/.hermes/scripts/eval-harness.py` 的 `init_baseline()` 函数

13. **Phase 6 consult-models nightly cron 必须显式注册，且必须 bounded-wrapper 化**:
    - multi-brain fan_out_merge 无内置调度，需 cron job 触发
    - Job: `multi-brain-consult-models-nightly`, schedule `0 1 * * *`
    - 旧命令 `python3 ~/.hermes/scripts/consult_models.py --keep --global` 已失效；新版 consult_models 需要 `state` → `run` 子命令
    - cron 中不要直接依赖长 prompt 或裸 `consult_models.py run`：T1 discussion/consensus 可能超时，导致 cron agent 空响应或 last_run_at 不刷新
    - 正确模式：创建 `~/.hermes/scripts/multi-brain-nightly-safe.py` 这类 wrapper，执行 `consult_models.py state` → bounded `consult_models.py run ... --tier T1 --quorum 3 --discussion --max-rounds 1 --keep` → 无论成功/timeout 都写 JSONL → 始终补跑 `usage-score.py`
    - wrapper 返回 0 并显式记录 `status=ok|timeout_recorded|degraded_recorded`，让 cron 健康不被静默空响应污染，同时保留审计证据

14. **Cron error/空响应治理优先 wrapper 化，不要只改 prompt**:
    - 症状: `hermes cron list` 中 job `last_status=error`，`last_delivery_error=null`，错误类似 "Agent completed but produced empty response"；或长任务 idle timeout 后没有可读产物。
    - 根因常见不是脚本坏，而是 prompt-only cron 让 LLM 负责执行/总结，长输出或超时后产生空回复；另一个常见根因是父脚本 timeout 后子进程仍占住 pipe，导致 wrapper 自己也被拖死。
    - 修复流程:
      1. `cronjob(action='list')` + `python3 ~/.hermes/scripts/cron-health-quarantine.py` 定位 bad jobs
      2. 先独立运行对应脚本，确认脚本能编译/执行: `python3 -m py_compile ...` + `python3 script.py`
      3. 对没有脚本的 prompt-only job，新增 `~/.hermes/scripts/<job>.py` wrapper，输出结构化 JSON/JSONL
      4. 长任务 wrapper 必须使用 `subprocess.Popen(..., start_new_session=True)`，`communicate(timeout=...)` 超时后 `os.killpg(proc.pid, signal.SIGTERM)`，必要时 SIGKILL；不要只用 `subprocess.run(timeout=...)`，否则 child process 可能继续占管道
      5. wrapper 应始终输出非空 JSON；对底层 partial failure 记录 `partial_fail_recorded`/`degraded_recorded`/`timeout_recorded` 并写 JSONL，wrapper 自身可 exit 0 让 cron 保留可总结产物
      6. 更新 cron 时优先使用**无参数 wrapper 脚本**，例如 `script='multi-model-smoke-hourly-wrapper.py'`，把参数写进 wrapper 内部；不要假设 `script='wrapper.py --flag value'` 会被 shell 拆分。已观察到 cron pre-run injector 会把 `multi-model-smoke-safe.py --timeout 210 ...` 当成单个文件路径并报 `Script not found`。
      7. 如果必须在 cron `script` 字段携带参数，先用 `cronjob(action='run')` 做一次验证，并检查 `~/.hermes/cron/output/<job_id>/...md` 是否出现 `Script not found: /path/script.py --arg`。出现则立即改回 no-arg wrapper。
      8. 对 script-first job，prompt 只做 2-3 行摘要；不要让 prompt 再运行 `p10-health.sh`、创建/删除 cron、或加载长 skill。否则脚本已成功但 LLM 摘要阶段仍可能 idle timeout。
      9. `cronjob(action='run')` 手动触发，等待 scheduler 消化后复查 `last_status`；不要把 `next_run_at` 变化误判为已执行完成
      10. 验证: wrapper 单测覆盖 timeout kill process tree、partial failure JSON、参数转发；`cron-health-quarantine.py` bad_count=0，`p10-health.sh --json` cron_bad=0 或 safe wrapper timeout_recorded 可审计，`usage-score.py` grade 保持 A
    - 对日频/周频 job 的 `last_run_at=null` 不要直接当故障；先看 `next_run_at` 是否尚未到首次触发窗口。

15. **自进化优先级队列要防幽灵信号，不要让旧基线永远排队**:
    - 症状: `self-improvement-pipeline.py --preview` 在 `usage-score.py` 已是 A、`cron_bad=0` 后仍输出 HIGH 工具失败；或 p10/p9/p7 已有 accepted 高分记录，却仍因旧 Darwin baseline 显示 `<60`。
    - 根因: priority 聚合读取历史 JSONL/TSV 时只聚合旧信号，不检查当前 operational health；Darwin `results.tsv` 可能有 8 列记录，解析器若要求 `len(cols) >= 9` 会跳过后续 accepted 修复行，只保留旧低分行。
    - 修复模式:
      1. 先跑当前事实: `python3 ~/.hermes/scripts/usage-score.py`, `python3 ~/.hermes/scripts/cron-health-quarantine.py`, `python3 ~/.hermes/scripts/self-improvement-pipeline.py --preview`
      2. 若 usage Grade A 且 cron `bad=0`，超过治理窗口的旧 `tool_failures` 信号应视为 stale transient，不再生成 HIGH priority；不要删除原始 audit log。超过 7 天的 tool failure 即使 usage 暂时不是 A 也应 suppress，因为真实问题会被新 autopsy 在 7d 窗口内重新发出。
      3. Darwin priority 必须按 skill 取**最新记录**，不能遍历所有历史低分；`results.tsv` 解析要兼容 8 列与 9 列。
      4. 给 `self-improvement-pipeline.py` 加回归测试: stale tool failure suppression + latest-score-per-skill。
      5. 把测试接入 `self-test.py`，让优先级队列 ghost 不再回归。
    - 验证目标: `self-improvement-pipeline.py --preview` 输出“无待办改进项”或只剩真实当前问题；`usage-score.py` Grade A；`cron-health-quarantine.py bad_count=0`；`self-test.py` 全绿。

16. **usage-score 不要把“24h 无非 hook 调用”误判成系统 D 级**:
    - 症状: self-test 59/59、route 7d pass≈96%、多模型 smoke 7d 有真实记录，但 `usage-score.py` 因 24h 只有 hook rows，model_breadth/real_call_integrity/route_diversity 全为 0，最终 Grade D。
    - 根因: 个人 Agent 的真实多模型调用是低频批任务，24h 窗口可能天然稀疏；hook rows 被正确排除后 denominator=0，不能等价为健康失败。
    - 修复模式:
      1. 24h 仍是主窗口；若非 hook call_rows < 10，则对 breadth/integrity/diversity 使用 7d fallback。
      2. fallback 分数必须 capped（建议 0.7×7d score），保留新鲜度压力，避免靠历史数据长期躺平。
      3. 输出中显式标注 `fallback_used`, `fallback_hours`, 以及 7d evaluated rows，避免把 fallback 当实时绿灯。
      4. p10-health 的 self-test 必须用 exit-code + bounded subprocess，不要 `grep -q ALL PASS` 管道；`set -euo pipefail` 下 grep -q 早退可能 SIGPIPE 上游，制造 false negative。
      5. 旧 cron `last_status=error` 如果是 >24h 的 transient wrapper/interpreter shutdown 且已有 future retry，可标记 stale 而非 live bad；真正清除仍要手动或定时重跑该 job。
    - 验证目标: `bash ~/.hermes/scripts/p10-health.sh --json` Grade A 且 warnings=[]；`python3 ~/.hermes/scripts/usage-score.py` Grade A/B（fallback_used 可审计）；`python3 ~/.hermes/scripts/cron-health-quarantine.py` bad_count=0；`python3 ~/.hermes/scripts/cron-missed-run-guard.py` missed_count=0。
17. **usage/self-improvement evidence readiness 修复要同时检查“证据存在”和“日志语义可被计分器识别”**:
    - 症状: 已有真实 multi-model/ensemble 调用，`usage-score.py` 仍输出 `semantic_grades.evidence_readiness.missing=['ensemble_executed']` 或 `ratification_corpus` 缺失。
    - 根因常见有两类：
      1. `consult_models.py` 已写 `tick-*/discussion_result.json`，但 usage-score 只读 `logs/ratify.jsonl` / `cross-patch.jsonl`，未把 certified discussion artifacts 视为 ratification corpus。
      2. `ensemble-vote.py --execute` 真实调用了模型，但日志没有持久化 `execute: true`，导致 usage-score 过滤条件不命中。
    - 修复模式：
      1. 对 certified `tick-*/discussion_result.json` 建一等 evidence reader：要求 `status in {certified, certified_with_minor_risks}`、truth gate 不为 `can_certify_truth=false`、2+ models participated、mtime 在 7d 窗口内；component 输出 `sources` 便于诊断来自 `discussion_result` 还是 jsonl bridge。
      2. `ensemble-vote.py` 的 executed path 必须在 result/log entry 中写 `execute: true`，并用回归测试 mock `_call_model()` 验证 log 文件实际落字段。
      3. 刷新真实 ensemble evidence 时可用最小 smoke，但要预期部分 provider 可能失败；只要 log schema 可计数，usage-score 应如实展示 `count_7d` 与 missing 状态。
    - 验证目标: `python3 ~/.hermes/scripts/usage-score.py` 输出 Grade A，`semantic_grades.evidence_readiness.missing=[]`，`components.ensemble_executed.count_7d>=1`，`components.ratification_corpus.sources` 非空。

18. **独立 code review 对治理脚本特别容易发现“计数语义”与“分类顺序”漏洞，必须按 fail-closed 修复后复审**:
    - 典型 blocker：`pending_review_count` 把同一 `fix_tool_config` diagnostic 同时按 executed action 与 diagnostic path 双计数；或 `_error_signature()` 先匹配 generic `not_found`，导致更具体的 `module_not_found` 分支不可达。
    - 修复模式：先加 failing regression test（例如 actionable `fix_tool_config` 只计 1 个 pending review；`ModuleNotFoundError: No module named ...` 分类为 `module_not_found`），再改最小逻辑，再重新跑目标 tests + self-test + 独立 reviewer。
    - commit 前顺序：显式 pathspec stage → `git diff --cached --check` → added-lines secret scan → independent reviewer JSON verdict → reviewer 如 fail 则修复+复审 → `[verified]` scoped local commit。

19. **Skill Graphs 2.0 应作为审计门，而不是先改运行时 loader**:
    - 症状: skill 数量增长后，related_skills 形成深链或循环；agent 运行时不稳定地跳过依赖。
    - 正确分层:
      - atom: 单一原语，0 skill 依赖；
      - molecule: 1-10 个 atom 的显式工作流；
      - compound: 驱动 molecules 的高级 playbook/orchestrator。
    - 落地模式:
      1. `python3 ~/.hermes/scripts/skill-steward.py --graph-check --json --warn-only` 生成 `skills/steward/skill-graph-report.json`
      2. 严格 gate 用 `--graph-check --json`，发现 cycle/excessive_depth/typed_violations exit 2
      3. 本轮只做审计和迁移建议，不直接清理旧 skill，不改 runtime loader
      4. self-test 必须含 valid fixture 与 invalid fixture，证明 fail-closed 行为
    - 验证目标: `self-test.py` 全绿；`skill-graph-audit.schema.json` parseable；steward full report 含 `audits.skill_graph`。

20. **Advisory-only multimodel PASS 要“消费弱触发”，但不能变成认证权威**:
    - 症状: taskpool multimodel 对弱触发（如 `P0_priority`/`closeout_ratification`/`architecture_target`/`accuracy_keyword`）跑出 advisory-only PASS 后，任务仍以 `not_certified` 反复进入队列，浪费模型预算并遮挡真正需要认证的任务。
    - 修复模式: advisory-only plan 若 gate 返回 `PASS + LOOP_DONE`，持久化为 `PASS_ADVISORY_ONLY` + `decision=continue_loop`，写 `multimodel_status: advisory_completed`、`multimodel_round_status: advisory_passed`、`multimodel_advisory_only: true`、`multimodel_certification_authority: false`。
    - 关键边界: 不写 `multimodel_ratification_artifact`，`task_multimodel_passed()` 仍必须为 false；只消费弱 advisory trigger，不得屏蔽 `stale_claim`、`p0_evolution_blast_radius`、`loop_non_convergence` 等强认证触发。
    - 回归测试: 构造 weak-only P1 evolution task，写入 `PASS_ADVISORY_ONLY` 后验证不再重复触发；再设置 `retry_count >= 2` 验证强触发仍恢复。
    - 详细 runbook: `references/advisory-only-multimodel-pass-consumption.md`。
- `pro` — PUA Pro 自进化追踪 (依赖 evolution.md)
- `darwin-skill` — 单个 skill 优化
- `skill-ecosystem-governance` — 生态治理
- `loop` — 迭代执行

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

