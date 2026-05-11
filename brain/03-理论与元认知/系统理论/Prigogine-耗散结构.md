# Prigogine：耗散结构与熵债

> Ilya Prigogine, *Self-Organization in Non-Equilibrium Systems* (1977), Nobel Prize 1977
> 联系：[[03-理论与元认知/系统理论/Ashby-必要多样性定律|Ashby]] ｜ [[03-理论与元认知/系统理论/Sturgeon-Price-Dunbar-三角约束|三角约束]]

## 核心命题

开放系统远离热力学平衡时，可以通过向环境输出熵来维持内部有序。

```
dS_total = dS_internal + dS_output
有序状态的条件: dS_output < 0 且 |dS_output| ≥ dS_internal
```

## Hermes Skills 的熵分析

### 当前状态（无淘汰）
```
每次会话: dS_internal = +1（创建/残留信息）
           dS_output   =  0（无淘汰机制）
           dS_total    = +1/会话 → 持续熵增
```

### 目标状态（有淘汰）
```
每次创建: dS_internal = +1（新 skill）
           dS_output   = -k*1（清理同等体量的旧技能）
           dS_total    ≈ 0 → 稳态循环
```

## 熵债机制

**每个创建操作自动产生一张"熵债票"**，必须在 48 小时内偿还：

| 创建动作 | 熵债 | 偿还方式 |
|---------|------|---------|
| 新增 skill | SKILL.md 文件大小（KB） | 删除等量 KB 的过时 skill |
| 新增测试 | test 行数 | 合并可合并的重复测试 |
| 新增引用 | 引用文件数 | 清理断裂引用 |

## 检测：当前熵债计算

| 类别 | 数量 | 每项熵值 | 总熵债 |
|------|------|---------|-------|
| 骨架 skill（无 SKILL.md 或空） | ≥1 (incident-response) | 高 | 需要偿还 |
| 重复 skill（pua 家族） | 12 个同名 | 极高（冲突熵） | 合并到 1+适配器 |
| 断裂引用（sync-to-obsidian 等） | ≥2 | 中 | 修复或删除 |
| 无测试 skill | 124/161 (77%) | 低 | 批量标记 DEPRECATED |
| 无 CHANGELOG skill | 122/161 (76%) | 低 | 同上 |

## 实施步骤

1. 批量清理：所有在过去 90 天未被查看过的 skill → 标记 DEPRECATED
2. 创建门禁：任何 `skill_manage('create')` 必须先执行一次 `skill_manage('audit')`
3. cronjob：每日凌晨扫描熵债，输出 `entropy-debt-report.md`
4. 阈值告警：总熵债超过 1000（任意单位）→ 阻止创建

## 引用

> Prigogine, I., & Stengers, I. (1984). *Order Out of Chaos*. Bantam Books.

## Evidence Boundary

- 来源支持什么：该卡仅记录理论概念、经典解释或本地大脑已引用的工程化映射。
- Hermes 映射边界：Agent/多模型/技能治理映射是工程类比与设计启发，不等同于原理论在数学或社会科学意义上的严格证明。
- 不应过度推出什么：不得仅凭该理论卡宣称某项代码、流程或策略已经正确；仍需工具证据、原文证据、审计输出或运行验证。
