# Sturgeon + Price + Dunbar：三角约束

> Sturgeon's Law (1957) | Price's Law (1965) | Dunbar's Number (1992)
> 联系：[[03-理论与元认知/系统理论/Ashby-必要多样性定律|Ashby]] ｜ [[03-理论与元认知/系统理论/Prigogine-耗散结构|Prigogine]]

## 核心命题

三条经验定律组合成一个不可逃脱的物理约束：

```
Sturgeon:   90% 的 skill 是垃圾     → 161 个中 ~145 个质量低下
Price:      √161 ≈ 13 个 skill 贡献 50% 的价值
Dunbar:     150 是认知维持上限       → 161 已经超了
```

## 三定律详解

### Sturgeon's Law (Theodore Sturgeon, 1957)

> "90% of everything is crap."

在 Hermes 确认的 5 大硬伤背景下，如果 77% 的 skill 无测试、76% 无版本追踪，**Sturgeon 的比例可能更接近 95%**。

应用原则：
- 接受 90% 的 skill 不需要达到 A 级
- 但系统必须能让这 90% **不污染** 剩下 10%
- 解决方案：冷热分离 + 活跃集

### Price's Law (Derek de Solla Price, 1965)

> 在科学文献中，√N 的贡献者产出 50% 的总贡献。

```
√161 ≈ 13
→ 161 个 skill 中，约 13 个贡献 50% 的总价值
→ 系统资源（上下文预算、加载优先级）应向这 13 个倾斜
```

应用原则：
- 识别 13 个核心 skill（通过使用追踪）
- 核心 skill 始终在活跃集中
- 非核心 skill 按 LRU 淘汰

### Dunbar's Number (Robin Dunbar, 1992)

> 人类认知可维持的稳定社会关系上限 ≈ 150。

```
当前技能数 161 > 150
→ 系统已达到认知维持力的物理上限
→ 这是"为什么技能生态感觉失控"的根本原因
```

这不是巧合。Agent 的"认知"（context window、prompt 中的技能列表、选择决策）同样受限于某种形式的"邓巴数"。

应用原则：
- 活跃集上限 = 50（7±2 的扩展工作区）
- 冷存储无上限
- 每次交互只暴露活跃集

## 三角约束的实施

### 1. 活跃集机制
```
活跃集: ≤ 50 个 skill（经常使用的）
冷存储: 剩余 skill（需显式搜索或加载）

加载策略:
  1. 先用 session_search 或当前任务类型匹配活跃集
  2. 如果未命中，搜索冷存储
  3. 搜索命中后，自动将 skill 移入活跃集（LRU 替换）
```

### 2. 核心 13 识别
```
通过 cronjob 每周统计 skill_view() 调用频率：
  top-13 → 标记为 CORE（永不淘汰）
  top-14~50 → 活跃
  bottom-111 → 冷存储

核心 13 示例（推测）：
  pua, loop, p10, p9, p7, systematic-debugging,
  tdd, uimax-audit, dogfood, auto-optimize-loop,
  plan, writing-plans, software-development
```

### 3. 全局容量限制
```
总技能数上限: 200（Dunbar 的宽容区间）
超过 200 时:
  → 新创建被阻塞
  → 强制要求先 ARCHIVE N 个，N = 当前数 - 200

活跃集上限: 50（控制器容量）
超过 50 时:
  → LRU 淘汰
  → 被淘汰的自动进入冷存储
```

## 引用

> Sturgeon, T. (1957). Quoted in *Venture Science Fiction*.
> Price, D. J. de Solla (1965). *Little Science, Big Science*. Columbia University Press.
> Dunbar, R. I. M. (1992). "Neocortex size as a constraint on group size in primates". *Journal of Human Evolution*, 22(6), 469-493.

## Evidence Boundary

- 来源支持什么：该卡仅记录理论概念、经典解释或本地大脑已引用的工程化映射。
- Hermes 映射边界：Agent/多模型/技能治理映射是工程类比与设计启发，不等同于原理论在数学或社会科学意义上的严格证明。
- 不应过度推出什么：不得仅凭该理论卡宣称某项代码、流程或策略已经正确；仍需工具证据、原文证据、审计输出或运行验证。
