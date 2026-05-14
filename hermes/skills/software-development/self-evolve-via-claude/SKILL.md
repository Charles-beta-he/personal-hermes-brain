---
name: self-evolve-via-claude
description: Use when the task falls under Self-Evolve via Claude Code — 双脑自进化.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - software
    - development
    - self
    - evolve
    - via
    related_skills:
    - design
    - loop
    - plan
    - router
    - self-improvement-pipeline
---

# Self-Evolve via Claude Code — 双脑自进化

## Overview


> 一天一次的自进化 tick。Hermes 是执行体, Claude Code 是建筑师。

## When to Use

- The task falls under Self-Evolve via Claude Code — 双脑自进化

## 执行序列 (每步失败立即停, 不连环放大)

### Step 1: 自描述

```bash
STATE=$(~/.hermes/scripts/self-describe.sh)
```

输出: `/tmp/hermes-state.json` (summary, < 8K tokens)
      `/tmp/hermes-state-full.json` (full detail, 文件系统)

**self-describe.sh v2 增强 (2026-04-26)**: 从 13 字段扩展到 22 字段，
新增 real/synthetic trace split、failure_modes、evolve_stats、
config_highlights (cron_mode/canary_ratio/auto_approve)、
skill_categories、gateway_status。Claude Code 诊断精度显著提升
（能检测到"57% synthetic diluting real signal"这类高阶问题）。

### Step 2: 咨询 Claude Code / 多脑

```bash
PLAN=$(~/.hermes/scripts/consult-claude.sh)
```

输出: `/tmp/hermes-plan.json` (结构化 plan JSON)
      `/tmp/hermes-plan.degraded` (存在表示降级模式)

内部逻辑:
1. 调 claude -p (skills: plan, architect, critic)
2. 校验 plan schema (retry × 3, 带 feedback)
3. 全失败 → 降级到 self-improvement-pipeline.py (本地规划)
4. 标记 degraded=true

For high-risk architecture/self-evolution ticks, prefer `consult_models.py` T3 with evidence-first state:
```bash
python3 ~/.hermes/scripts/consult_models.py state '目标' --out /tmp/mm-state.json
python3 ~/.hermes/scripts/consult_models.py run /tmp/mm-state.json --tier T3 --quorum 4 --discussion --max-rounds 2 --keep
```
Rules:
- Add claims/evidence when certifying factual current state.
- Treat planner agreement as design confidence, not truth.
- SPL is opt-in only: set `HERMES_MULTI_BRAIN_USE_SPL=1` deliberately; default natural-language state preserves claims/evidence.

### Step 3: 安全检查

- plan.steps ≤ 5
- 所有 step.risk ≤ med
- 所有 step.reversible = true
- 不涉及 safety-guard / auth / memory schema

不合规 → abort (不继续)

### Step 4: 落地

```bash
~/.hermes/scripts/apply-plan.sh /tmp/hermes-plan.json
```

内部逻辑:
1. Drain: 暂停新 task, 等 inflight 完成
2. Snapshot: hermes backup + skill 增量备份
3. Apply: 逐 step 执行
4. Resume: 恢复 task 接收

### Step 5: Eval Gate

```bash
~/.hermes/scripts/eval-after-apply.sh
```

内部逻辑:
1. 对比 baseline (7d pass_rate) vs new (1h pass_rate)
2. Δ < -5% → 自动回滚 (hermes import)
3. 3 连败 → 暂停 evolve cron, 等人介入
4. 写 ~/.hermes/logs/evolve.log (append-only)

### Step 6: 通知

输出本 tick 摘要: 改了哪些, eval 结果, kept/rolled_back

### Step 6.5: Final closure guard

Before giving a final answer in a self-evolution loop, run an explicit closure check:

```bash
git -C ~/.hermes status --short
git -C ~/.hermes log --oneline -3
```

If verified edits remain unstaged/uncommitted, do not say the loop is complete. Either commit them locally (no push unless asked) or state clearly that only uncommitted verified work remains. This prevents the common failure mode where the implementation and tests are done but the final cycle-cleanup/documentation diff is left outside the local audit trail.

## 终止条件 (硬停)

| 条件 | 动作 |
|------|------|
| 自描述失败 | abort, 写错误日志 |
| plan schema 3 次校验失败 | 降级到本地规划 |
| snapshot 备份失败 | abort (不允许无网执行) |
| 3 次连续 eval reject | 暂停 evolve cron, 人等审 |
| degrade 3 次连续 | 告警人审 (claude -p 装出问题) |

## Pitfalls & Experiential Findings

以下是从实际 6 轮手动运行 + 12h 线上运营中积累的教训, 按影响面排序。

### P0: Claude Code CLI 集成 (导致最多失败)

| 问题 | 发现方式 → 影响 | 正确做法 |
|------|----------------|---------|
| `--skills` 参数不存在 | V4 验证时 3 次 attempt 全部 silent fail → 降级到本地规划, 白白浪费 `$0.60` API 费用 | Claude Code 2.x 无 `--skills` 参数。直接在 prompt 中描述角色 (如 "你是 Hermes 的架构师") |
| `--output-format json` 是 wrapped 格式 | JSON 解析一直 schema 失败, 所有 retry 报 "missing steps array" → 3 次 retry 后降级 | 返回 `{"type":"result","result":"{...}"}` , 需两级反序列化: 外层 JSON → `result` 内的字符串 → JSON parse |
| `_extract_plan_json.py` Try 1 误匹配 wrapper | Try 1 直接 `json.loads(raw_text)` 返回 Claude Code 的 wrapper JSON (含 `type`/`result`/`duration_ms` 等 key), 后续 schema 校验永远找不到 `steps` → 触发 retry | Try 1 必须 `if "steps" in data` 才接受。Claude Code wrapper 也是合法 JSON 会被 Try 1 吃掉, 需要 fallthrough |
| prompt 中 args schema 太模糊 | 首跑 hook_add(缺 matcher/command) 和 skill_edit(缺 name/content) 全部 no-op → 落地率仅 50% | prompt 中必须包含精确的 args JSON 示例 (`"matcher":"prompt_regex","command":"/path/to/script.sh"`), 不能只写 `{...}` |
| retry-with-feedback 收敛性 | 首轮 schema 失败后注入错误反馈 → 第 2 轮通常修复 | 3 次 attempt 足够。前 2 次注入 feedback, 第 3 次不注入(判断模型拒绝遵守) |

对应的修复代码模式:

```python
# _extract_plan_json.py 正确提取逻辑
# 1: 直接解析 → 仅当有 "steps" key
try:
    data = json.loads(raw_text)
    if isinstance(data, dict) and "steps" in data:
        return data
except: pass

# 2: Claude Code wrapped 格式
try:
    raw = json.loads(raw_text)
    inner = raw.get("result", "")
    if isinstance(inner, str):
        data = json.loads(inner)
except: pass

# 3: ```json markdown fence
match = re.search(r'```json\n?(.*?)```', raw_text, re.DOTALL)
if match: data = json.loads(match.group(1))
```

### P0: JSON 生成 — shell heredoc 嵌入引号会破坏 JSON

| 问题 | 复现场景 → 后果 | 修复 |
|------|----------------|------|
| shell heredoc 中嵌入含引号的变量 | `evolve_log_tail` 含 raw JSON log 行, 嵌入双引号字符串时 `"` 破坏 JSON 外层结构 | 所有 JSON 输出改用 python3 构建 |

```bash
# ❌ 错的 (shell heredoc + 变量插值)
cat > out.json << JSON
{"key": "$VALUE"}  # VALUE 含引号时 JSON 结构断裂
JSON

# ✅ 对的 (python3 + 环境变量)
export VALUE  # shell → env
python3 -c "
import json, os
with open('$OUT') as f:
    json.dump({'key': os.environ.get('VALUE')}, f)
"
```

| `print()` 到 stdout 被 `$()` 捕获 | self-describe.sh 中 `print('summary written...')` → consult-claude.sh `STATE_FILE=$()` 捕获了 2 行输出, 第一行不是文件路径 | `print()` 只输出 final result (文件路径); 中间消息用 stderr |
| `jq -e .` + `set -e` 导致脚本退出 | `jq` 遇到非 JSON 字符串 exit=1, `set -e` 直接 abort | 用 `\|\| true` 或换 Python: `python3 -c "json.load(sys.stdin)"` 更可控 |

### P1: Shell 脚本 macOS/Linux 兼容

| 问题 | macOS 行为 | Linux 行为 | 正确写法 |
|------|-----------|-----------|---------|
| `head -n -1` | ❌ 不合法 | ✅ 移除最后一行 | `sed '$d'` |
| `timeout` 命令 | ❌ 不存在 | ✅ GNU coreutils | `gtimeout` 或 Python `subprocess.run(timeout=N)` |
| `$1` in `set -euo pipefail` | 无参时 unbound variable error | 同上 | `"${1:-default}"` |
| `sed` pipefail | `\|` 中任一 cmd 非零退出传播到 `$()` | 同上 | 分两步: `block=$(sed -n '/p/p')` + `if [ -n "$block" ]` |
| `dirname --` (double dash) | macOS 不支持 | ✅ | 不用 `--`, 裸 `dirname "$0"` |

### P1: 6 项 Run-Before-First-Run 验证

首次上线或修改后, 必须跑完以下验证矩阵。`6/6` → GO, `<2` → 推迟, 中间修不过的项:

```bash
V1: DRY_RUN=1 bash apply-plan.sh plan.json        # 干跑, 状态零变化
V2: echo '{"steps":[]}' > /tmp/p.json && \
    bash apply-plan.sh /tmp/p.json && \
    bash eval-after-apply.sh                       # 全链路 smoke
V3: 手动改一个 SKILL.md, 从 snapshot 恢复, diff 确认还原  # restore 通路
V4: bash consult-claude.sh                         # JSON plan 第1轮过 schema
V5: hermes cron pause <jid> && hermes cron resume  # kill switch 可用
V6: hermes cron pause <jid>                        # 单命令可掐断
```

### P2: 架构决策 — hermes backup/restore

`hermes backup -o path.zip` **不支持自定义路径**。它把 snapshot 保存到 `~/.hermes/state-snapshots/<timestamp>/`, 通过 `/snapshot restore <name>` (REST API, 非 CLI) 还原。

对于 `apply-plan.sh` 的 snapshot, 不要依赖 `hermes import`, 改用文件级增量备份:

```bash
mkdir -p "$SNAPSHOT"
cp ~/.hermes/config.yaml "$SNAPSHOT/config.yaml.bak"
cp ~/.hermes/cron/jobs.json "$SNAPSHOT/cron.json.bak"
# 要改的 skill:
cp ~/.hermes/skills/$name/SKILL.md "$SNAPSHOT/$name.SKILL.md.bak"
```

回滚时直接 `cp` 回去, 比 `hermes import zip` 快且可靠。

### P0: apply-plan.sh 静默失败 (2026-04-26 发现)

| 问题 | 复现场景 → 后果 | 正确做法 |
|------|----------------|---------|
| `cron_add` 报告成功但 `jobs.json` 未更新 | apply-plan.sh 输出 "cron add ... OK" 但 jobs.json 总 job 数不变 | apply 后验证: `python3 -c "import json; d=json.load(open('$HOME/.hermes/cron/jobs.json')); print(len(d.get('jobs',d)))"` 确认+1 |
| `evolve.log` 写入静默遗漏 | apply-plan.sh 输出 "Logged to evolve.log" 但 tail -1 仍为旧条目 | 检查 `tail -1 ~/.hermes/logs/evolve.log` 的 ts 是否匹配。缺失时用 python3 手动 append |
| 落地率虚高 | apply-plan.sh 报告 4/4 但实际 2/4 生效 | P10 tick 后需加验证步: 对比 apply 前后的 cron count + config keys，确认 land_rate 真实值 |

**落地后验证清单 (Step 4.5):**
```bash
# cron count
python3 -c "import json; d=json.load(open('$HOME/.hermes/cron/jobs.json')); print(len(d.get('jobs',d)))"
# evolve log
tail -1 ~/.hermes/logs/evolve.log | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ts','MISSING'))"
# 如缺失: cronjob(action='create') 手动补 + 手动 append evolve 条目
```

### P2: evolve.log 管理

- `head -n -1` (移除最后一行) 在 macOS 不兼容 → `sed '$d'`
- 3 连败检测: 读 evolve.log 最后 10 行, 数连续 `eval_result == "rolled_back"` 的数量
- append-only 不等于无限增长: 每周 GC + 每月 1 号归档到 `evolve-YYYYMM.log`
- evolve.log 中的 JSON 可能包含未转义的换行符, 会导致 JSON 解析器读到不完整的行。用 `grep -c '"rolled_back"'` 替代完整 json.loads 行解析

## Multi-Brain Extension (v3, 2026-04-26)

双脑可升级为多脑: consult-models.sh (替代 consult-claude.sh) 并行调用 N 个模型,
consensus-plans.py 做 4 层语义一致性检测, 交集优先合并为单一执行方案。

### Plan Schema v1 (所有 planner 必须遵循)

```json
{
  "meta": {"planner_model": "...", "state_hash": "...", "confidence": 0.85},
  "diagnosis": {"root_cause_class": "router_skew|verifier_gap|...|no_action"},
  "patches": [{"id": "sha1(file|op|body)", "op": "tune_threshold|swap_model|...",
               "risk": "low|med|high", "blast_radius": "single_tier|...|kill_switch",
               "depends_on": []}],
  "verification": {"expected_metric_delta": {}, "guard_metrics": [], "tier_eval_plan": "T0_only|..."},
  "rollback_signal": {"auto_rollback_if": "...", "kill_switch_inc": false}
}
```

关键: patch id = sha1(target_file + sep + op + sep + body) → 不同模型提出相同改动时 ID 自动一致, Jaccard 检测可用。

### 4 层 Semantic Consensus (consensus-plans.py)

L1 (0.4): root_cause_class 多数一致
L2 (0.3): patches id 集合 Jaccard ≥ 0.5
L3 (0.2): 同一 patch 参数偏离 ≤ 20% 中位数
L4 (0.1): 置信度加权投票

score ≥ 0.7 → consensus; ≥ 0.5 → weak_consensus; < 0.5 → dissent (需 arbiter)

合并策略: 交集优先 (全票保留) → 多数补充 (≥ quorum 保留) → 少数仲裁

### 4 阶段铺开

Phase 0 (shadow): 并行跑 consult-models + consult-claude, 只记录差异
Phase 1 (N=2): Claude + DeepSeek, merge 后 apply, kill switch ×2
Phase 2 (N=3): MiMo + DeepSeek + Claude, 完整 schema, arbitration 启用
Phase 3 (steady): 动态 quorum, Claude budget 自动排除

### 降级链

N=3, 1 timeout → N=2 继续, arbiter 必调
N=3, 2 timeout → 低于 min_quorum, 不自动 apply, 仅 low-risk patches
Claude budget 耗尽 → 排除 Claude, MiMo+DeepSeek 继续
所有 planner 挂 → 跳过本 tick, 3 连败 → ops 告警

### P0: Patch ID 必须确定性 (2026-04-26 发现)

consensus 测试中 patch id 用 `sha1(model_name + patch_index)` 导致 Jaccard=0。
不同模型的相同改动 ID 不同 → L2 永远 fail → 无全票 patch → 全部标记仲裁。
**ID 必须 = sha1(target_file | op | body)**, 不包含 model_name。

验证用例: 3 模型, 共享 2 个 patch + 各 1 个 unique patch →
  score=0.985, 2 个全票 patch 合并, 3 个少数 patch 标记仲裁 ✓

### P0: Synthetic contamination in main view (2026-04-26 发现)

route_store.stats() 的 main 口径原本只排除 DEFAULT_EXCLUDED_MAIN_ROUTES,
不排除 is_synthetic=1 的 trace → research-/direct 等 7 条合成数据污染 main pass_rate。
修复: `_aggregate(where, params, synthetic=0, exclude_routes=DEFAULT_EXCLUDED_MAIN_ROUTES)`
main=223 real 0 synthetic, pass_rate=97.3% (纯净).

### P0: state.json 必须紧凑且聚焦

过大的 state.json (8K+ chars) 会让 Claude 注意力分散, 设计不可操作的泛化 plan。
目标: 2-3KB, 仅包含与当前问题直接相关的字段。
self-describe.sh 新增 `state_hash` 字段 (sha256) 确保所有 planner 读到相同输入。

### P1: Claude -p output 双重嵌套解析

`--output-format json` 返回: `{"type":"result","result":"```json\\n{...}\\n```"}` — 需:
1. 解析外层 JSON → 取 result 字段
2. result 内是 markdown code fence → 提取 inner JSON
3. 验证 inner JSON 是否匹配 plan schema

新发现: result 字段内可能直接是 JSON 字符串 (无 markdown fence), 尝试 json.loads 直接解析。

### P1: Pricing-Aware Model Selection

model-router v2 集成 pricing.py 后, self-evolve tick 可以:
- 根据 UTC 时间选择 off-peak 模型 (MiMo 0.8x → DeepSeek 低成本)
- Claude budget 不足时自动排除
- select_quorum() 确保 provider diversity (禁止同一家族 3 模型)

## Related Skills

- `self-improvement-pipeline` — 降级时使用的本地规划器
- `router` — L2 短环 (不受双脑影响, 秒级)
- `eval-harness` — eval gate 核心逻辑
- `consensus-plans.py` — 多脑 plan 语义一致性引擎
- `consult-models.sh` — 多模型 fan-out 编排器
- `claude-budget-tracker.py` — Claude token 预算保护

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

