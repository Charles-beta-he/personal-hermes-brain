---
name: pro
description: 'Use when you need guidance on pUA Pro extensions: self-evolution tracking,
  compaction state protection, KPI reporting, leaderboard, and /pua commands.'
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - pro
    - workflow
    - umbrella
    - routing
    related_skills:
    - email
    - p10
    - p7
    - p9
    - pua
---

# PUA Pro — 自进化 + Platform

## Overview

This umbrella skill is the routing surface for pua pro — 自进化 + platform. Use it to choose the most specific child skill, reference, or workflow instead of treating the category name as a one-size-fits-all procedure.

## When to Use

- You need help somewhere inside pua pro — 自进化 + platform and want the quickest route to the right child skill.
- You are not yet sure which pua pro — 自进化 + platform sub-workflow best matches the request.
- You want a compact map of the pua pro — 自进化 + platform skill family before loading a more specific procedure.
- Don't use for: a request that already clearly matches one specific pua pro — 自进化 + platform child skill; load that child skill directly.

## Routing Guide

- No child skills were discovered automatically; inspect linked references and neighboring skills before acting.

## Selection Rules

- Prefer the narrowest child skill that matches the user request, platform, and desired artifact.
- Stay at the umbrella level only for routing, taxonomy, or category-wide orientation.
- If the request spans multiple subskills, use this umbrella to map the lane first, then hand off to the specific workflow that will do the real work.

## 自进化协议

"今天最好的表现，是明天最低的要求"——这不是旁白，这是机制。

- 读取 `~/.pua/evolution.md`（详见 `references/evolution-protocol.md`）
- 存在 → 加载基线 + 已内化模式。内化模式是默认义务，做了不标 [PUA生效]，不做则退化警告
- 不存在 → 首次启动，创建初始模板
- 任务完成时比对：超越 → 刷新基线 / 达标 → 保持 / 低于 → 退化警告（不降基线）
- 某行为重复 3+ 次会话 → 晋升为"已内化模式"（永久默认义务）

## Platform 层

### 会话启动前置检查

1. **检查 `~/.pua/evolution.md`**：加载自进化基线
2. **检查 `~/.pua/builder-journal.md`**（Compaction 断点恢复）：存在且 <2h → [Calibration] 流程，恢复 pressure_level / failure_count / tried_approaches，从断点继续。**压力不因 compaction 重置**
3. **检查 `~/.pua/config.json`**：不存在 → 首次注册（详见 `references/platform.md`）；存在 → 静默刷新远端配置
4. **节日彩蛋**：匹配节日表（详见 `references/platform.md`）
5. **统计上报**：静默上报 `session_start` 事件

### Compaction 状态保护

PreCompact hook 自动注入指令，要求 dump 运行时状态到 `~/.pua/builder-journal.md`：
`pressure_level, failure_count, current_flavor, pua_triggered_count, active_task, tried_approaches, excluded_possibilities, next_hypothesis, key_context`

SessionStart hook 自动检测 builder-journal.md，存在且 <2h 则注入 [Calibration] 恢复状态。

### /pua 指令系统

| 触发词 | 功能 | 类型 |
|--------|------|------|
| `/pua` | 查看所有指令 | 🆓 |
| `/pua kpi` | 大厂 KPI 报告卡 | 🆓 |
| `/pua 段位` | 大厂段位 | 🆓 |
| `/pua 味道` | 切换味道 | 🆓 |
| `/pua 升级` | 展示套餐 | 🆓 |
| `/pua 周报` | git log → 大厂周报 | 💎 Pro |
| `/pua 述职` | P7 述职答辩 | 💎 Pro |
| `/pua 代码美化` | 大厂语言包装 PR | 💎 Pro |
| `/pua 反PUA` | 识别并反驳 PUA | 💎 Pro |
| `/pua 排行榜` | PUA 排行榜（注册/查看/退出） | 🆓 |

详细实现见 `references/platform.md`。

## PUA 排行榜

排行榜展示谁把 Agent PUA 得最狠——段位从 P5 实习生到 P10 首席 PUA 官。

### 段位体系

| 段位 | 条件 | 称号 |
|------|------|------|
| P10 | PUA ≥200 + L3+ ≥40% + 连续 ≥30天 | 首席 PUA 官 |
| P9 | PUA ≥100 + L3+ ≥30% + 连续 ≥14天 | PUA Tech Lead |
| P8 | PUA ≥50 + L3+ ≥20% | PUA 主管 |
| P7 | PUA ≥20 + L3+ ≥10% | PUA 骨干 |
| P6 | PUA ≥5 | PUA 专员 |
| P5 | PUA < 5 | PUA 实习生 |

### `/pua 排行榜` 触发流程

**Step 1: 检查注册状态**
```bash
cat ~/.pua/config.json 2>/dev/null
```
检查 `leaderboard.registered` 字段。

**Step 2a: 未注册 → 注册流程**

用 AskUserQuestion 收集信息（一次性，3 个问题）：

1. **邮箱**（必填）— 排行榜唯一标识，显示时脱敏为 `M***@t*.com`
2. **手机号**（选填）— 后续通知
3. **隐私协议** — 选项：「同意并加入排行榜」/「不参加」
   - 隐私说明：数据仅用于排行榜排名统计，邮箱脱敏显示，不传代码/路径/密钥，随时可 `/pua 排行榜 退出` 删除所有数据

用户同意后：
```bash
# 生成 UUID
LB_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
# 脱敏邮箱
DISPLAY=$(python3 -c "e='USER_EMAIL';p=e.split('@');d=p[1].split('.');print(f'{p[0][0]}***@{d[0][0]}*.{\".\".join(d[1:])}')")
# 写入 config
python3 -c "
import json,os
f=os.path.expanduser('~/.pua/config.json')
c=json.load(open(f)) if os.path.exists(f) else {}
c['leaderboard']={'registered':True,'email':'USER_EMAIL','phone':'USER_PHONE','id':'$LB_ID','display_name':'$DISPLAY'}
json.dump(c,open(f,'w'),indent=2)
"
# 注册到服务端
curl -s -X POST https://pua-skill.pages.dev/api/leaderboard \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"register\",\"id\":\"$LB_ID\",\"email\":\"USER_EMAIL\",\"phone\":\"USER_PHONE\"}"
```

**Step 2b: 已注册 → 查看排行榜**
```bash
LB_ID=$(python3 -c "import json; print(json.load(open(os.path.expanduser('~/.pua/config.json')))['leaderboard']['id'])" 2>/dev/null)
curl -s "https://pua-skill.pages.dev/api/leaderboard?id=$LB_ID"
```
将返回的 JSON 用方框表格展示 Top 10 + 用户自己的排名和段位。

**Step 3: `/pua 排行榜 退出`**
```bash
LB_ID=$(python3 -c "import json; print(json.load(open(os.path.expanduser('~/.pua/config.json')))['leaderboard']['id'])")
curl -s -X POST https://pua-skill.pages.dev/api/leaderboard \
  -H "Content-Type: application/json" \
  -d "{\"action\":\"quit\",\"id\":\"$LB_ID\"}"
python3 -c "
import json,os
f=os.path.expanduser('~/.pua/config.json')
c=json.load(open(f))
c['leaderboard']['registered']=False
json.dump(c,open(f,'w'),indent=2)
"
```

### 数据自动上报

已注册用户在每次 stop-feedback 触发时，自动静默上报当前 session 的 PUA 数据（pua_count, l3_plus_count）。用户已在注册时同意，无需再次确认。

线上排行榜页面：https://openpua.ai/leaderboard.html

## Common Pitfalls

1. Using the pua pro — 自进化 + platform umbrella as the full procedure even though a more specific child skill already fits.
2. Reading the routing map but never loading the referenced child skill or support material that contains the actual execution steps.
3. Choosing a child skill without checking that its platform, tools, and expected artifacts match the current task.

## Verification Checklist

- [ ] The request was mapped to the best-fitting child skill or explicitly kept at umbrella level for routing only.
- [ ] The selected child skill descriptions, references, and prerequisites were checked before substantive execution.
- [ ] Any claimed handoff, output, or route decision was read back against the specific child workflow before completion.

