---
name: router
description: "多臂老虎机路线选择器 — 基于 route_outcomes 历史数据用 e-greedy 策略选最优执行路线。触发词：路线选择, router, bandit, 选路线, route selection, 路径选择"
license: MIT
---

# Router — 多臂老虎机路线选择器

> 基于历史 outcomes 实时选最优路线。e-greedy: 90% exploit, 10% explore。

## 流程

### Step 1: 任务分类 (Triage)

读用户请求, 分类为 task_class:

| 模式 | task_class |
|------|-----------|
| 前端 UI/UX 类, 复杂交互 | feature.frontend |
| 后端 API/数据类 | feature.backend |
| Bugfix 类 | bugfix |
| 代码审查/重构类 | refactor |
| 研究/文档类 | research |
| DevOps/部署类 | devops |
| 配置/工具类 | config |
| 计划/设计类 | planning |
| 其他 | general |

分类规则: 优先匹配具体分类, 最后 fallback 到 general。

### Step 2: 查询历史分数

```bash
python3 ~/.hermes/scripts/route_store.py scores --task-class <task_class> --hours 168
```

输出示例:
```
route=planner>impl>ver: count=45 pass=0.82 dur=180s score=0.77
route=explorer>planner>impl>ver: count=12 pass=0.91 dur=240s score=0.85
```

如果查询结果为空 (新 task_class), 用默认路线:
```
default -> planner > implementer > verifier
```

### Step 3: e-greedy 选择

- 生成随机数 r = random()
- r < 0.9: 选 score 最高的路线 (exploit)
- r >= 0.9: 从所有候选路线中随机选一条 (explore)

记录选择到 route_outcomes:
```bash
python3 ~/.hermes/scripts/route_store.py append \
  --skill router --task-class <class> --route <selected> \
  --verdict pending --task_id <session_id>
```

### Step 4: 输出执行路线

输出格式:
```
[Router] task_class=<分类>
[Router] 候选路线:
  route A: <描述> (pass=<rate>, dur=<s>, score=<s>)
  route B: <描述> (pass=<rate>, dur=<s>, score=<s>)
[Router] 选择: <路线> (e-greedy, exploit/explore)
[Router] 执行技能:
  1. <skill-1>
  2. <skill-2>
```

然后按选中的路线启动执行。

## Triage 误分类反馈机制

发现 triage 误分类时, 将案例追加到:
```
~/.hermes/skills/software-development/router/triage-examples.json
```

格式:
```json
[{"input": "用户请求摘要", "expected": "正确分类", "actual": "误分类", "timestamp": "ISO时间"}]
```

累计 10 条误分类后触发 L3 分支 D (分类器细化, 自动更新 few-shot 示例)。
active 状态: router 的 e-greedy 选择由 `python3 ~/.hermes/scripts/route_store.py scores --task-class <class>` 提供。

## Bandit Score 计算

score = pass_rate - lambda_cost * avg_cost - lambda_time * avg_duration/60

- lambda_cost = 0.1
- lambda_time = 0.01

少于 5 条记录的路线自动视为无数据, 用默认路线。

## 默认候选路线

当 route_outcomes 中无数据时, 按 task_class 的默认路线:

| task_class | 默认路线 | 说明 |
|-----------|---------|------|
| feature.* | planner > implementer > verifier | 标准三阶段 |
| bugfix | diagnose > fix > verify | 诊断优先 |
| research | explore > synthesize > present | 探索优先 |
| config | research > implement > verify | 先调研后实施 |
| general | plan > implement > verify | 通用三阶段 |

## Pitfalls

- 新 task_class 无数据时用默认路线
- e 不超过 10%
- 不要在单次任务中多次调用 router
