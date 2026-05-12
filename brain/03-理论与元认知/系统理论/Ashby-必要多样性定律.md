# Ashby：必要多样性定律

> W. Ross Ashby, *Introduction to Cybernetics* (1956)
> 联系：[[03-理论与元认知/控制论基础/01-反馈回路与稳定性|反馈回路]] ｜ [[03-理论与元认知/系统理论/Prigogine-耗散结构|耗散结构]]

## 核心命题

**只有多样性才能吸收多样性** (Only variety can destroy variety)

对于一个控制系统，控制器的状态数必须 ≥ 被控系统的状态数。否则控制必然失效。

## 数学表述

```
R_controller ≥ R_system
```

其中 R = 可能状态数的对数（信息论中的多样性度量）。

## 问题诊断：Hermes Skills

```
R_system = 161（每个 skill 是一个可能状态）
R_controller ≈ ?

当前控制器 = prompt 语义匹配 → R_controller ≈ 1~3
失控必然。差距：2 个数量级。
```

## 解决方案

### 1. 降低系统多样性（R_system 降维）
- 冷热分离：top-13 热 skill 进入活跃集，其余冷存储
- 合并重复：12 个 pua 副本 → 1 个标准 + 平台适配器
- 骨架清理：删除空壳 skill（如 incident-response）

### 2. 提升控制器多样性（R_controller 升维）
- 构建使用先验分布：P(load|skill) = frequency(skill) / Σf
- 贝叶斯更新：每次 load 后更新先验
- 输入分类器：按任务类型（dev/ops/research/creative）预分类

### 3. 有效多样性公式

```
R_effective = min(R_controller, R_system)
```

目标：R_effective ≥ 20（Miller 7±2 的扩展工作集）

## 实践指标

| 指标     | 当前值  | 目标值       |
| ------ | ---- | --------- |
| 总技能数   | 161  | ≤ 50（活跃集） |
| 控制器候选数 | ~1-3 | ≥ 20      |
| 活跃集命中率 | 未知   | ≥ 90%     |

## 引用

> Ashby, W. R. (1956). *An Introduction to Cybernetics*. Chapman & Hall.

## Evidence Boundary

- 来源支持什么：该卡仅记录理论概念、经典解释或本地大脑已引用的工程化映射。
- Hermes 映射边界：Agent/多模型/技能治理映射是工程类比与设计启发，不等同于原理论在数学或社会科学意义上的严格证明。
- 不应过度推出什么：不得仅凭该理论卡宣称某项代码、流程或策略已经正确；仍需工具证据、原文证据、审计输出或运行验证。
