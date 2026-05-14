---
name: p10-architecture-self-check
description: Use when the task falls under P10 Architecture Self-Check — 全栈架构自检.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - p10
    - architecture
    - self
    - check
    related_skills:
    - codex
    - impeccable
    - loop
    - p10
    - p9
    - plan
    - pua
    - pua-en
---

# P10 Architecture Self-Check — 全栈架构自检

## Overview


> 季度/事件驱动的全栈架构健康度评估。从参考模型偏差检测到 P9 任务编制。
> 核心原则: 先读模型 → 查健康 → 深挖 → 输出战略 → 委托执行 → Claude Code 外脑验证。

## When to Use

- The task falls under P10 Architecture Self-Check — 全栈架构自检

## 触发条件

- 用户说 "p10 自检架构"
- 季度 review（按 timescale-separation 每季度）
- V̇ < -0.05 连续 2 次
- 新类型任务首次出现且现有模型不适用

## 执行序列 (6 步)

### Step 1: 加载参考模型

```
skill_view("p10", file_path="references/reference-model.md")
skill_view("p10", file_path="references/p10-protocol.md")
skill_view("p10", file_path="references/stability-margin.md")
skill_view("p10", file_path="references/timescale-separation.md")
```

### Step 2: 运行健康快照

```bash
# 一体化健康评分 V(t) — 包含 self-test + route + cron + memory
bash ~/.hermes/scripts/p10-health.sh
# JSON 模式:
bash ~/.hermes/scripts/p10-health.sh --json

# 路线分数 (多口径: overall/real_only/synthetic_only/main)
python3 ~/.hermes/scripts/route_store.py summary
python3 ~/.hermes/scripts/route_store.py scores --view main
python3 ~/.hermes/scripts/route_store.py stats  # 四口径 JSON

# Eval 状态
python3 ~/.hermes/scripts/eval-harness.py --status

# Cron 状态 (优先用 cronjob 工具, 其次 jobs.json)
# cronjob(action='list')  # ← 从 Hermes 内调用
# 或者:
python3 -c "
import json, os
p=os.path.expanduser('~/.hermes/cron/jobs.json')
with open(p) as f: data=json.load(f)
for j in (data.get('jobs',data) if isinstance(data,dict) else data):
    print(j.get('name','?'), 'last_run:', j.get('last_run_at','null') or 'null')
"

# Evolve 日志
tail -20 ~/.hermes/logs/evolve.log
```

### Step 3: 深挖审计

```bash
# Skill 膨胀（原始文件数）
find ~/.hermes/skills -name 'SKILL.md' | wc -l

# Skill 治理健康（有效技能数 / alias 去重 / 相似度 / 供应链）
python3 ~/.hermes/scripts/skill-steward.py
# 重点读：
# - 总技能数（不含别名）
# - test coverage
# - 同名冲突
# - 内容重叠 → 建议合并
# - related_skills 覆盖率
# - 供应链安全扫描

# Orphan 检测: 用 Python 扫描所有 SKILL.md 的 skill_view 引用
# 输出未被引用的 skill 列表

# Cron 健康: 检查 last_run_at 全 null 的 job
cat ~/.hermes/cron/jobs.json | python3 -c "..."

# Canary 状态
grep canary_ratio ~/.hermes/config.yaml
ls -la ~/.hermes/skills-staging/
```

### Step 4: 输出 P10 战略文档

按 P10 协议输出五部分：
1. **当前状态 V(t)** — 关键指标 + 判定
2. **Top-5 风险** — P0→P2 分级, 证据 + 缓解
3. **架构审查** — 五维度 (代码架构/技术栈/可扩展性/开发体验/质量基线)
4. **决策记录** — 为什么选 A 不选 B
5. **P9 编制** — 任务分解, 不写 Prompt

写出战略文档: `~/.hermes/notes/p10-strategy-YYYY-MM-DD.md`

### Step 5: Claude Code 外脑验证

```bash
bash ~/.hermes/scripts/self-describe.sh
bash ~/.hermes/scripts/consult-claude.sh
```

读取 `/tmp/hermes-plan.json`, 评估每个 step:
- 拒绝新 cron (避免膨胀)
- 检查是否已有相同配置
- 接受低风险 config_set 和代码修复

### Step 6: P9 执行 → P10 验证

按 `p9` 协议拆解任务, 执行, 然后 P10 层最终验证。

## 常见问题与修复

### Cron 全部未执行 (last_run_at 全 null)

排查顺序:
```
1. hermes cron status            → 看 scheduler 状态
2. grep cron_mode config.yaml    → 必须是 approve (不是 deny)
3. hermes gateway status         → 必须 running
4. hermes gateway install        → 安装 launchd/systemd 服务
5. hermes cron tick              → 手动触发 (会跑全部到期 job, 可能超时)
```

根因组合:
- `cron_mode: deny` → 改为 `approve`
- Gateway 未安装 → `hermes gateway install`
- Gateway 已安装但未启动 → `hermes gateway start`

### 路由名截断/空值

检查 `~/.hermes/agent-hooks/record-trace.sh` 的 route 字段:
```python
# ❌ 原代码: route 硬编码空值
'route': '',

# ✅ 修复: 使用工具名作为路由标识
'route': 'hook:' + d.get('tool_name', 'unknown'),
```

注意: bash heredoc 内嵌 Python -c 不能用 f-string（引号冲突），用字符串拼接。

### 合成 trace 污染观测数据

当观测数据被人工生成的 trace 主导时，eval gate 失去意义。

检测:
```bash
python3 ~/.hermes/scripts/route_store.py summary
# 看 "Real: N traces | Synthetic: M traces" 比例
```

修复流程:
```bash
# 1. 加列
sqlite3 ~/.hermes/route_outcomes.db "ALTER TABLE route_outcomes ADD COLUMN is_synthetic INTEGER DEFAULT 0"

# 2. 更新 route_store.py: append() + CLI --synthetic flag + summary 显示 split

# 3. 回填标签
sqlite3 ~/.hermes/route_outcomes.db "UPDATE route_outcomes SET is_synthetic=1 WHERE route='' OR route='planner-'"

# 4. 未来 trace: hook 写入 is_synthetic=0，手动生成设 is_synthetic=1
```

### Cron 踩踏 (全部在 minute=0)

症状: 所有 11+ cron job 在同一分钟触发 → API rate limit + 并发竞争。

检测:
```bash
# 读 jobs.json，解析 schedule 字段，构建 24h 热力图
python3 -c "
import json
with open('$HOME/.hermes/cron/jobs.json') as f:
    jobs = json.load(f)['jobs']
hours = {h: 0 for h in range(24)}
for j in jobs:
    expr = j['schedule']['expr'] if isinstance(j['schedule'], dict) else j['schedule']
    parts = expr.split()
    h_field = parts[1] if len(parts) >= 5 else '*'
    # parse */N, comma, single values
# 找出 count>=3 的小时 → stampede
"
```

修复:
```bash
# 错开高频小时的 minute 偏移
hermes cron edit <job_id> --schedule "5 0 * * *"    # 从 0 → 5
hermes cron edit <job_id> --schedule "10 0 * * *"   # 从 0 → 10
hermes cron edit <job_id> --schedule "30 * * * *"   # hourly → minute=30
# 重型 job 从 hourly 降为 6h: "0 */6 * * *"
```

### Cron 新增但 `last_run_at` 仍是 null

不要立刻判定 scheduler 坏了。先分两类：

1. **高频 job (≤6h)**: 跨过 2+ 轮应执行窗口仍无 last_run_at → 真正故障
2. **日频 job (每天一次)**: 可能尚未到首次触发时间 — next_run_at 在今晚/明早, last_run_at null 属正常

验证方法:
```bash
# 通过 cronjob 工具获取 (推荐, 可看到完整 last_run_at)
# cronjob(action='list')

# 或解析 jobs.json
python3 -c "
import json, os
p=os.path.expanduser('~/.hermes/cron/jobs.json')
with open(p) as f: data=json.load(f)
for j in (data.get('jobs',data) if isinstance(data,dict) else data):
    last = j.get('last_run_at','null') or 'null'
    nxt = j.get('next_run_at','?')
    name = j.get('name','?')
    print(f'{name:40s} last={str(last)[:19]}  next={str(nxt)[:19]}')
"
```

判断: 3 个高频 job (脑同步/健康监控/canary) 有 recent last_run_at → scheduler 活着。日频 job null → 等待轮次即可。

### Raw skill count 与 effective skill count 不一致

`find ~/.hermes/skills -name 'SKILL.md'` 给的是**原始文件数**，会把 alias stub 也算进去。

治理决策（Dunbar 阈值、冲突数、系统多样性）应以 `skill-steward.py` 的 **总技能数（不含别名）** 为准。

示例:
- raw SKILL.md: 197
- effective skills (excluding aliases): 181

结论:
- P10 报告里两者都可写，但**风险判断用 effective count**。

### 同名 Skill 多副本 ≠ 可直接合并

`find ~/.hermes/skills -name 'SKILL.md'` 可能显示同一 skill 名在多个目录:
- impeccable: 12 副本 (.cursor/, .claude/, .gemini/, .trae/ 等)
- pua/pua-en/pua-ja: 各 4 副本 (root + pua/skills/ + pua/codex/ + pua/codebuddy/)

**先 diff 再决策**: `diff -q root/SKILL.md pua/skills/X/SKILL.md`
- IDENTICAL → 可 symlink 或删除副本
- DIFFER → 故意平台变体，不可安全合并 (需上游库收敛)

### Memory 去重判定: Ghost 识别口诀

读取 `~/.hermes/memories/MEMORY.md` 时，逐条问:
- **Will this fact still be true in 10 sessions?**
- 时变数字 (92 traces, PID 50599, 3kept) → ❌ ghost
- 完成式状态 (Week1→0.85, P0已解) → ❌ ghost  
- 日限定条目 (首次运行今03:00) → ❌ ghost
- 项目约定、工具清单、关键教训 → ✅ durable
- 环境事实 (路径、部署方式) → ✅ durable


配置阈值:
```yaml
# ~/.hermes/config.yaml
hermes:
  evolve:
    min_traces: 30           # 不足 30 traces 拒绝决策
    min_traces_for_action: 30
    min_traces_for_eval: 20
```

验证 trace 量达标:
```bash
python3 ~/.hermes/scripts/route_store.py summary
# 确认 Total >= 30
```

## 输出物

- `~/.hermes/notes/p10-strategy-YYYY-MM-DD.md` — 战略文档
- Memory 更新: 淘汰旧条目, 写入当前状态
- 最终报告: 任务完成度矩阵 + V 变化
- `~/.hermes/logs/health-history.jsonl` — V(t) 历史记录 (由 p10-health.sh 自动追加)

## 核心工具速查

| 工具 | 用途 | 关键命令 |
|------|------|----------|
| `p10-health.sh` | 一体化 V(t) 健康评分 | `bash ~/.hermes/scripts/p10-health.sh [--json]` |
| `route_store.py v2` | 四口径 trace 统计 | `python3 ~/.hermes/scripts/route_store.py stats` → views: overall/real_only/synthetic_only/main |
| `route_store.py v2` | Main 口径评分 | `python3 ~/.hermes/scripts/route_store.py scores --view main` |
| `self-test.py` | 组件完整性检查 | `python3 ~/.hermes/scripts/self-test.py` (隔离DB, 不污染生产) |
| `eval-harness.py` | Eval gate 状态 | `python3 ~/.hermes/scripts/eval-harness.py --status` |

### V(t) 评分公式

```
V(t) = 0.25 × self_test_pass
     + 0.30 × main_pass_rate_7d    (排除 blank/planner- 路由)
     + 0.15 × cron_health          (enabled jobs 当前健康: 非 error/failed；recent_24h 仅作观测)
     + 0.20 × real_ratio           (1 - synthetic_ratio)
     + 0.10 × gateway_running

Grade: A(≥0.90) B(≥0.75) C(≥0.60) D(<0.60)
```

### route_store.py 四口径

- **overall**: 全部 traces, 含 blank + planner- 污染
- **real_only**: is_synthetic=0 的真实施行
- **synthetic_only**: is_synthetic=1 的合成 traces
- **main**: 排除 blank("") + planner- 路由的净化口径 → **决策用此**

## Common Pitfalls
1. **`hermes cron tick` 超时**: 会跑所有到期 job, 11 jobs × 60s = 660s。用 `hermes cron status` 确认调度器在线后等自动触发，不必手跑 tick。
2. **patch 工具转义引号**: `patch(mode='replace')` 会把 `"` 转义为 `\"`。在 bash heredoc 场景下改用字符串拼接避免引号问题。
3. **Memory 2,200 字符上限**: P10 自检结果需合并为一条。优先删除 "已完成" 条目腾空间。
5. **p10-health cron_health 口径**: cron_health 应衡量 enabled jobs 当前是否不在 error/failed；weekly/monthly job 或尚未到 first-run 时间的 job 不应因为 last_run_at 非 24h 内而扣分。保留 `cron_recent_24h`、`cron_pending_first_run`、`cron_bad` 作观测字段。若改了 p10-health 输出格式，必须同步改 `usage-score.py`，优先让 usage-score 读取 `p10-health.sh --json`，不要解析易碎文本。

## 补充模式: 前端项目完整性审计 (Frontend Completeness Audit)

当需要对 React/TS 前端项目做完整性审查时，使用以下检查流程：

### 子代理委派原则

- **每个子代理最多 5-10 个文件** — MiMo 模型在读取大量文件后容易"沉默"（返回空回复）
- **每个子代理一个维度** — 不要混合"审计认证安全"和"修复 i18n"
- **显式文件列表** — 不要说"检查所有屏幕"，而是"检查这 7 个文件"
- **始终包含 tsc 验证** — 每个子代理任务结束时运行 `node node_modules/typescript/bin/tsc --noEmit`

### 死代码扫描 (Dead UI Scanner)

```python
import os
issues = []
for root, dirs, files in os.walk("src/screens"):
    for f in files:
        if not f.endswith('.tsx'): continue
        fp = os.path.join(root, f)
        content = open(fp).read()
        rel = os.path.relpath(fp, "src")
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # 按钮无 onClick
            if '<button' in line and 'onClick' not in line:
                ctx = '\n'.join(lines[max(0,i-2):i+3])
                if 'onClick' not in ctx and 'type=' not in line:
                    issues.append(f"{rel}:{i} — button without onClick")
            # 硬编码密钥
            if '"888888"' in line or '"123456"' in line:
                if 'import.meta.env' not in line:
                    issues.append(f"{rel}:{i} — hardcoded secret")
            # 硬编码版本号
            if 'v1.0.0' in line and 'version.ts' not in rel and 'package.json' not in rel:
                issues.append(f"{rel}:{i} — hardcoded version")
            # 硬编码 placeholder
            if 'placeholder="' in line:
                ph = line.split('placeholder="')[1].split('"')[0]
                if ph and 't(' not in ph and len(ph) > 3:
                    issues.append(f"{rel}:{i} — hardcoded placeholder")
```

### 未接线组件检测

```bash
# 创建但未使用的组件
for f in src/components/*.tsx src/hooks/*.ts; do
  name=$(basename "$f" .tsx); name=$(basename "$name" .ts)
  count=$(grep -rl "$name" src/ --include="*.tsx" --include="*.ts" | wc -l)
  [ "$count" -le 1 ] && echo "UNUSED: $f"
done
```

### i18n 差距分析

```bash
# 屏幕中未使用 useTranslation 的文件数
grep -rl "useTranslation" src/screens/ --include="*.tsx" | wc -l
# 总屏幕数
find src/screens -name "*.tsx" | wc -l
```

### 版本号集中管理

创建 `src/lib/version.ts`:
```typescript
export const APP_VERSION = '1.0.0';
export const BUILD_NUMBER = '24042701';
export const FULL_VERSION = `v${APP_VERSION} (build ${BUILD_NUMBER})`;
```

在 AboutScreen、MeScreen 等引用版本号的地方使用 `APP_VERSION` 或 `FULL_VERSION`。

### 常见陷阱

1. **Button vs 组件包装器**: UI 组件 (Button.tsx, BottomSheet.tsx) 内的 `<button>` 是包装器 — onClick 通过 prop 传入，不在 JSX 上
2. **placeholder="0.00"**: 数字输入默认值可以硬编码 — 不是用户可见文本
3. **"即将上线"**: 作为功能开发中的空状态文案是可接受的
4. **sed 替换过于宽泛**: 使用精确匹配，不要全局替换可能误中其他行的模式
5. **i18n 嵌套 key**: `t('update.available')` 支持扁平 key 和嵌套对象两种 JSON 格式

## 补充模式: 多模型架构填充 Loop (Multi-Model Architecture Fill)

当需要对前端项目做全量架构填充时，使用以下 loop 模式:

### Loop 结构

```
Round 1: 基础架构 (services + stores + mock server + API client)
Round 2: 屏幕迁移 (connect screens to stores, 28/55 done)
Round 3: 多模型审查 (3 parallel agents: API/屏幕/安全)
Round 4: 修复所有差距
Round 5: P10 自检 → 如有差距回到 Round 3
Repeat until: 0 差距, tsc PASS, 所有测试通过
```

### 子代理超时回退: 程序化批量迁移

当子代理在批量迁移任务上超时（例如 "迁移 40 个屏幕到 i18n"），切换到程序化批量迁移:

```python
# execute_code 批量 i18n 迁移模式
for file_path in remaining_screens:
    content = open(file_path).read()
    if 'useTranslation' in content: continue
    # 在最后一个 import 后添加 useTranslation import
    # 在组件函数体开头添加 const { t } = useTranslation()
    # 替换中文字符串为 t() 调用
    open(file_path, 'w').write(content)
```

这种方法处理机械性工作；子代理处理创造性/分析性工作。

### Zustand persist + devtools 模板

所有 store 使用统一中间件栈:

```typescript
import { create } from 'zustand';
import { persist, devtools, createJSONStorage } from 'zustand/middleware';

export const useXxxStore = create<XxxState>()(
  devtools(
    persist(
      (set, get) => ({ /* state & actions */ }),
      {
        name: 'xxx-store',
        storage: createJSONStorage(() => sessionStorage),
        partialize: (state) => ({ /* 只持久化关键字段 */ }),
      }
    ),
    { name: 'XxxStore' }
  )
);
```

### PWA 更新模式 (registerType: 'prompt')

```typescript
// useServiceWorkerUpdate hook
// - 检查更新: reg.update() (mount + 每 60 分钟 + 手动)
// - 强制倒计时: 30 秒后自动 skipWaiting
// - 手动检查: checkForUpdate() 接入 MeScreen 版本卡片
// - 状态: 'idle' | 'checking' | 'available' | 'up-to-date'
```

### 版本号集中管理

创建 `src/lib/version.ts` 避免硬编码:

```typescript
export const APP_VERSION = '1.0.0';
export const BUILD_NUMBER = '24042701';
export const FULL_VERSION = `v${APP_VERSION} (build ${BUILD_NUMBER})`;
```

### 构建验证

每次修改后必须验证:
- [ ] `node node_modules/typescript/bin/tsc --noEmit` → 0 errors
- [ ] `npx vitest run` → all tests pass
- [ ] `node node_modules/vite/bin/vite.js build` → PWA files generated (sw.js, manifest.webmanifest)
- [ ] `grep -rn '"888888"' src/` → 0 hardcoded secrets
- [ ] `grep -rn 'from.*data/mock' src/screens/` → 0 mock imports
- [ ] `grep -rl 'useTranslation' src/screens/ | wc -l` → 55/55 screens

## Related

- `p10` — CTO 战略层协议
- `self-improvement-pipeline` — L0-L5 自进化架构
- `self-evolve-via-claude` — 双脑进化流程
- `stuck-diagnosis` — 卡顿排查（含 cron 调试模式）
- `skill-ecosystem-governance` — Skill 生态治理

## 补充模式: 多模型基础设施自检 (Multi-Model Infrastructure Self-Check)

当需要对 L0-L5 多模型架构做健康审计时，使用以下检查流程。触发词: "多模型自检", "multi-model self-check", "多模型架构修复", "circuit breaker 检查"。

### 七维检查清单

1. **Quorum 截断**: quorum.yaml 中 T2/T3 的 quorum < planners 数量 → 某些模型永远被截断
   ```bash
   python3 ~/.hermes/scripts/consult_models.py status
   # 检查每个 tier: quorum vs len(planners)
   ```

2. **Cold Start 死循环**: model-router 中某模型 0 traces → score=None → exploit 跳过 → 永远 0 traces
   ```bash
   sqlite3 ~/.hermes/route_outcomes.db "SELECT model_chain, COUNT(*) FROM route_outcomes WHERE model_chain != '' GROUP BY model_chain ORDER BY 2 DESC"
   # 任何 quorum.yaml 中列出的模型, 0 调用 = cold start 死循环
   ```

3. **Stale Circuit Breaker**: model_health_state.json 中 circuit=open 但 recent_outcomes 全 true
   ```bash
   python3 -c "
   import json, time
   with open('$HOME/.hermes/rate_limits/model_health_state.json') as f:
       state = json.load(f)
   now = time.time()
   for name, info in state.get('providers', {}).items():
       c = info.get('circuit', 'unknown')
       recent = info.get('recent_outcomes', [])
       sr = sum(1 for x in recent if x) / len(recent) if recent else 0
       opened = info.get('opened_at', 0)
       timeout = info.get('recovery_timeout', 60)
       if c in ('open','half_open') and (now-opened) > timeout and sr > 0.7:
           print(f'STALE: {name} — {c}, success={sr:.0%}, stale={now-opened:.0f}s')
   "
   ```

4. **Gateway 误报**: macOS pgrep -f 不能匹配完整路径 → health 脚本报 down 但 gateway 实际在跑
   ```bash
   # 不能只靠 pgrep -f, 必须同时检查 ps aux
   pgrep -f "hermes.*gateway" || ps aux | grep -q "[h]ermes.*gateway"
   ```

5. **Model Diversity**: 单模型占比 >90% = 多模型印证机制名存实亡
   ```bash
   python3 ~/.hermes/scripts/model-diversity-monitor.py
   ```

6. **Memory 膨胀**: >2200 chars → 需压缩, 先删"已完成"条目
   ```bash
   # 用 memory(action='remove') 逐条清理
   ```

7. **Provider 可用性三层检查**: 只查 shell env 会漏掉 .env 和 CLI session
   ```bash
   python3 ~/.hermes/scripts/model-router.py probe
   ```

### 冷启动修复模式

当某模型 0 traces 陷入死循环时:

1. **Quorum 修复**: 确保模型在 T1/T2/T3 planners 列表中, 且 quorum >= len(planners)
2. **评分预热**: 在 model-router.py score_model() 中加入冷启动 bonus:
   ```python
   # Bonus decays linearly: 0 traces → +0.25, min_traces → +0
   if count < min_traces:
       warmup_bonus = 0.25 * (1.0 - count / max(min_traces, 1))
       base += warmup_bonus
   ```
3. **验证**: `for i in $(seq 1 100); do model-router.py select; done | sort | uniq -c`

### Stale Circuit 修复模式

```python
# 读取 state → 检测 stale → 修复 → 写回
for name, info in state['providers'].items():
    if circuit in ('open','half_open') and time_in_state > recovery_timeout and success_rate > 0.7:
        info['circuit'] = 'closed'
        info['consecutive_failures'] = 0
        info['opened_at'] = 0.0
        info['probe_in_progress'] = False
```

### 多模型思考修复流程

当自检发现多个问题时, 使用多模型思考协议生成修复方案:

1. 准备 state.json (问题列表 + 约束 + 验收标准)
2. 三模型并行: GPT-5.5(工程方案) + DeepSeek(红队) + MiMo(极简审查)
3. Claude 交叉质疑 → 合成最终方案
4. 按依赖顺序执行修复
5. self-test 验证 44/44 保持

### 本地大脑 × 多模型自动化 readiness 审计补充

当用户问“多模型分析自检架构与本地大脑中未自动化的部分”或类似问题时，不要只读 `p10-health` 的 A 分。必须同时区分：核心健康、readiness-gated advisory、fully certified autonomous execution。

最小证据采集：
```bash
bash ~/.hermes/scripts/p10-health.sh --json
python3 ~/.hermes/scripts/self-test.py
python3 ~/.hermes/scripts/consult_models.py status
python3 ~/.hermes/scripts/model-router.py probe
python3 ~/.hermes/scripts/model-diversity-monitor.py --json
python3 ~/.hermes/scripts/model-router.py readiness --json
python3 ~/.hermes/scripts/brainctl.py --json status
python3 ~/.hermes/scripts/brainctl.py --json validate --write-dashboard
python3 ~/.hermes/scripts/local_brain_exhaustive_audit.py --sample-limit 50
python3 ~/.hermes/scripts/local_brain_main_hierarchy_migration_selfcheck.py --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py eligibility-check --json
python3 ~/.hermes/scripts/brain_task_idle_runner.py --json --write-state
python3 ~/.hermes/scripts/brain_task_dispatch_tick.py --print-always --no-state
```

判定规则：
- `p10-health` A + `self-test` PASS 只证明核心健康，不证明自治执行可认证。
- `model-diversity-monitor gate_failed=true` 或 `model-router readiness ok=false` 时，T2/T3 只能输出 `readiness-gated advisory` / `not_certified_for_autonomous_execution`，即使 quorum.yaml 配了 4 个模型。
- `brainctl validate passed=false`、`local_brain_exhaustive_audit stop_gate_pass=false`、或主层级 selfcheck FAIL 时，禁止把本地大脑任务自动 promotion/done；只允许检测、dashboard 标红、修复建议。
- `brain_task_multimodel_loop_runner --dry-run` PASS 只证明 verifier 可验证合成 artifact；未拿到真实 `discussion_result.json` 前，不得称生产级多模型闭环。
- `local-brain-task-dispatch-safe-tick` 若 cron `last_status=error` 但手动运行 exit=0/空输出，优先查 `~/.hermes/cron/jobs.json` 的 `last_error`、`~/.hermes/logs/brain_task_dispatch_tick.jsonl`、以及 no_agent/空输出语义；常见根因包括 cron runtime `[Errno 24] Too many open files`，不是任务池逻辑失败。
- 任务池 `eligibility mode=deny`、`allowlist_empty`、`autorun_disabled`、`kill_switch=true` 通常是正确 fail-closed 姿态，不要当 bug 修成自动执行。

多模型 consult 超时处理：
- 如果 `consult_models.py run ... --discussion` timeout，先按 state 内容/问题文本/`state_hash` 找目标 tick，不要盲目使用最新 tick（可能已有别的并发任务生成更新 tick）。
- 只有 fan-out + `merged_plan.json` 而缺 `discussion_result.json` 时，报告为 weak consensus / not certified；读取 `discussion/round_*/round_summary.json` 提取 unresolved issue ledger。
- 若 round summary 显示 `certification_intent=implementation_required` 但 `patches=[]` 或 severity>=3 unresolved，必须保持 `not_certified`，不能把“问题被证实”升级为“方案已认证”。

输出优先级模板：
- P0：堵假认证/假健康（diversity gate blocker、brain validate/audit stop gate、dispatch cron 可观测性）。
- P1：补真实闭环（certify-only real consult artifact、proof hash 固定路径、resume/timeout verifier、router diversity enforcement）。
- P2：保持 fail-closed 自动推进（idle-runner 只读、autorun 需 allowlist+kill-switch+budget+proof+lease）。

### macOS Pitfalls

- `pgrep -f` 不能匹配 Python 进程的完整路径 → 用 `ps aux | grep` 回退
- `grep -q "a\|b"` 在 macOS BRE 中 `\|` 行为不一致 → 用 `grep -E "a|b"` 或拆两行
- `cat -A` 不存在 → 用 `od -c` 检查字节

## 补充模式: 代码级健壮性审计 (Code Robustness Audit)

当需要对各层代码质量做深度审计（不仅是健康指标）时，使用以下五维检查清单 + 双脑 gap/fix 流程：

### 五维检查清单

对每个层文件逐条检查：

1. **协议集成**: 是否有 `from agent_protocol import...`？关键事件是否 `protocol_emit()` ？
2. **异常处理**: `grep -rn 'except:'` 和 `grep -rn 'except Exception'` 检查裸异常
3. **Stub 检测**: 函数是否只返回占位符？注释中是否有"待实现"/"requires delegate_task"？
4. **Shell 健壮性** (bash 脚本): 检查 `2>/dev/null` 掩蔽、硬编码 fallback、TICK_DIR 泄漏、fragile 字符串拼接
5. **数据层连接**: route_outcomes 与 protocol_messages 是否可 JOIN？record-trace 是否传递 chain_id？

### 采集命令

```bash
grep -rn 'except:' ~/.hermes/scripts/*.py ~/.hermes/agent-hooks/*.sh
grep -rn 'protocol_emit\|protocol_wrap\|from agent_protocol' ~/.hermes/scripts/*.py
grep -rn '2>/dev/null' ~/.hermes/scripts/*.sh
python3 ~/.hermes/scripts/route_store.py stats  # 四口径
```

### 双脑 gap/fix 流程

1. 构建 compact state.json (<4KB)，包含每层文件/状态/观察到的 gap
2. 送 Claude: `cat state.json | claude -p '...' --output-format json --max-turns 10 --allowedTools Read`
3. 解析 wrapped JSON → `plan['gaps']` 和 `plan['fixes']`
4. 按 severity 排序 (critical > high > medium > low)，按 effort 估算工期 (S/M)
5. 子Agent并行执行 (不同文件不冲突)
6. 跨层验证: 编译 + 功能测试 + protocol_messages 计数 + chain_id 列检查

### 签收标准

- 全栈 0 bare except
- 每层至少一个关键事件 protocol_emit
- 0 个 stub 函数
- L5 不再有 hardcoded fallback

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

