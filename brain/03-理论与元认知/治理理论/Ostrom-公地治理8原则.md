# Ostrom：公共池资源治理 8 原则

> Elinor Ostrom, *Governing the Commons* (1990), Nobel Prize 2009
> 联系：[[03-理论与元认知/治理理论/Conway-逆定律-组织决定系统|Conway 逆]] ｜ [[03-理论与元认知/治理理论/Havel-无权力者的权力|Havel]]

## 核心命题

公共池资源（Common Pool Resource）在无治理时必然走向"公地悲剧"。但通过 8 条设计原则，社区可以自治且可持续。

Hermes Skills 系统本质是一个 CPR：
- **非排他性**：谁都能创建 skill
- **竞用性**：每个 skill 占用 agent 上下文预算

## 8 原则对照检查

### 原则 1：清晰边界
- 什么能进入资源池？
- **现状**：❌ 无边界 —— `skill_manage('create')` 无条件放行
- **对策**：定义 skill 生命周期状态机 → 创建时需指定 state = BETA

### 原则 2：收益与成本对等
- 创建者是否承担维护成本？
- **现状**：❌ 创建后归零（0 维护成本）
- **对策**：每个创建附带"熵债"——必须标记一个旧 skill 为 DEPRECATED

### 原则 3：集体选择
- 规则由参与者制定？
- **现状**：❌ 无治理委员会，无制度
- **对策**：创建 `skill-governance` 技能（本系统的宪法）

### 原则 4：监控
- 使用情况被监控？
- **现状**：❌ 完全无追踪
- **对策**：增加 skill_view() 调用计数器 + 热力图

### 原则 5：梯度制裁
- 从警告到驱逐？
- **现状**：❌ 无任何制裁
- **对策**：BETA → ACTIVE → DEPRECATED → ARCHIVED → DELETED

### 原则 6：冲突解决机制
- 低成本仲裁？
- **现状**：❌ 无冲突检测
- **对策**：`skill-conflict-report` 每周自动生成

### 原则 7：组织权力被认可
- 自治权合法？
- **现状**：⚠️ 技能系统存在但无管理机构
- **对策**：skill-steward cronjob 作为执行机构

### 原则 8：嵌套层级
- 多层治理？
- **现状**：⚠️ 有目录结构但无对应治理层级
- **对策**：类别级 + 生态级 + 跨生态级三级治理

## Ostrom 宪章（一页纸规则）

```
① 新技能 BETA 标签，3 个月无人用 → DEPRECATED，6 个月 → ARCHIVED
② 创建新技能必须标记一个 DEPRECATED 或 ARCHIVED
③ 每个技能必须有 test-prompts 才能升 ACTIVE
④ skill-steward cron 每周扫描并报告违规
⑤ 违反规则 → 警告 → 30 天未处理 → 自动 ARCHIVE
```

## 引用

> Ostrom, E. (1990). *Governing the Commons: The Evolution of Institutions for Collective Action*. Cambridge University Press.

## Evidence Boundary

- 来源支持什么：该卡仅记录理论概念、经典解释或本地大脑已引用的工程化映射。
- Hermes 映射边界：Agent/多模型/技能治理映射是工程类比与设计启发，不等同于原理论在数学或社会科学意义上的严格证明。
- 不应过度推出什么：不得仅凭该理论卡宣称某项代码、流程或策略已经正确；仍需工具证据、原文证据、审计输出或运行验证。
