---
name: requirement-clarification
description: Use when a new task, feature request, or bug report arrives and you must clarify goals, acceptance criteria, scope, risks, and priorities before execution.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - requirements
    - planning
    - clarification
    - acceptance-criteria
    related_skills:
    - writing-plans
    - source-driven-development
    - test-driven-development
---

# Requirement Clarification — 需求澄清与验收定义

## Overview

接任务时先对齐再动手。理解错了就做错了——先对齐再动手。. In practice, load it when a new task, feature request, or bug report arrives and you must clarify goals, acceptance criteria, scope, risks, and priorities before execution. It defines the expected execution lane, scope boundaries, and verification shape for this class of work.
## When to Use

- 收到新需求/功能请求
- 接到 bug 报告
- 任务描述模糊或缺少验收标准
- 用户说"帮我做个 XXX"但没有细节
- Don't use for: requests that do not need a new task, feature request, or bug report arrives and you must clarify goals, acceptance criteria, scope, risks, and priorities before execution; choose a more specific child skill or a broader routing skill that actually matches the task.
## 核心原则

**不澄清不动手。** 任务描述越短，澄清工作越重要。

## 五步澄清法

### Step 1: 复述需求

用自己的话复述用户要做什么，确保理解一致。

输出格式：
```
我理解的你的需求是：
[一句话目标]

涉及的范围：
- [范围1]
- [范围2]

是这样吗？
```

### Step 2: 定义验收标准 (AC)

每个需求必须有可验证的验收标准。

**好的 AC：**
- [ ] 用户在 375px 和 1280px 视口下都能正常提交表单
- [ ] 提交后显示成功 toast，3 秒后自动消失
- [ ] 表单验证错误时，对应字段边框变红并显示错误文案

**差的 AC：**
- [ ] 表单能正常工作（无法验证）
- [ ] UI 好看（主观，无法验证）

如果用户没给 AC，主动补充并确认。

### Step 3: 明确边界

定义**在范围内**和**不在范围内**：

```
### IN SCOPE（做）
- 功能 A
- 功能 B

### OUT OF SCOPE（不做）
- 功能 C（建议后续迭代）
- 功能 D（超出当前资源）
```

### Step 4: 识别依赖与风险

- 依赖：需要哪些外部资源/接口/权限？
- 风险：哪些因素可能导致延期或失败？
- 假设：基于哪些假设在做这个方案？

### Step 5: 确认优先级

- P0: 阻塞发布，必须做
- P1: 重要，尽量做
- P2: 锦上添花，有时间做

## 输出物

澄清完成后，产出 `.claude/requirements/{task-id}.md`：

```markdown
# 需求澄清 — [Task 标题]

## 需求复述
[一句话 + 详细描述]

## 验收标准 (AC)
- [ ] AC1: [可验证标准]
- [ ] AC2: [可验证标准]

## 边界定义
### IN SCOPE
- [ ]
### OUT OF SCOPE
- [ ]

## 依赖与风险
- 依赖: [ ]
- 风险: [ ]
- 假设: [ ]

## 优先级
- [ ] P0 / P1 / P2

## 下一步
- [ ] 进入 writing-plans / 直接执行
```

## 快速澄清清单

简单任务（< 30 分钟）可以跳过文档，但必须口头确认：
- [ ] 我理解的目标对吗？
- [ ] 验收标准是什么？
- [ ] 有什么不能碰的？

## 与 PUA 体系的集成

- P10: 在战略层面定义需求价值
- P9: 在任务拆解前确保需求澄清完成
- P8/P7: 执行前阅读需求澄清文档

## 反模式

- ❌ 不问清楚就开始写代码
- ❌ 假设用户想要的是 X，实际用户想要的是 Y
- ❌ 验收标准模糊，做完后用户说"不是我要的"
- ❌ 范围蔓延——做着做着加了新功能

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

