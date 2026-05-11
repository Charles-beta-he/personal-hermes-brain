# Parnas：信息隐藏与模块分解

> David Lorge Parnas, *On the Criteria to Be Used in Decomposing Systems into Modules* (1972)
> 联系：[[03-理论与元认知/控制论基础/02-大系统理论-分解与协调|大系统理论]] ｜ [[06-治理与评审/技能生态/冲突检测与合并协议|冲突检测与合并协议]]

## 核心命题

模块分解的标准不应是"功能相似"，而应是 **"变更原因相同"**。

两个模块应该独立（没有共享秘密），当且仅当它们因不同原因而变更。

## 当前错误分解分析

### PUA 家族的分解谬误

```
错误分解（按部署平台）:
  ~/.hermes/skills/pua/              → 根层 PUA
  ~/.hermes/skills/pua/codex/pua     → Codex 版
  ~/.hermes/skills/pua/codebuddy/pua → CodeBuddy 版
  ~/.hermes/skills/pua/skills/pua    → Skills 版
  ~/.hermes/skills/pua-en/           → 英文版
  ~/.hermes/skills/pua-ja/           → 日文版
  (加上每个下面的 codex/codebuddy/skills 版本)
  = 12 个副本
```

**这些副本的变更原因完全相同**（PUA 方法论的迭代）。它们不应该被分开——每次改 pua 都要同步到 12 个位置，违反了 Parnas 的核心准则。

### 正确分解（按变更原因）

```
pua-core/SKILL.md  ← 方法论本身（变更原因：方法论迭代）
pua-platform/      ← 部署适配层（变更原因：平台 API 变化）
pua-evals/         ← 测试用例（变更原因：覆盖场景增加）
```

### post-deploy-verification 的分解谬误

```
~/.hermes/skills/post-deploy-verification/SKILL.md   ← 英文版
~/.hermes/skills/software-development/post-deploy-verification/SKILL.md  ← 中文版
```

**这两个的变更原因完全相同。** 合并为一个，语言差异用 frontmatter language 字段处理。

## 冲突检测算法

```
1. 扫描所有 SKILL.md 的 name: 字段
2. 找到同名或语义相似的技能组
3. 对每组计算"变更原因一致性得分"：
   - 如果 description 和 tags 高度重合 → 高冲突 → 要求合并
   - 如果 description 不同但 name 相同 → 中冲突 → 要求改名
4. 输出冲突报告
```

## 分解质量指标

| 指标 | 定义 | 当前值 | 目标值 |
|------|------|-------|-------|
| 模块内聚度 | 同类变更聚集度 | 低（pua 分散在 12 处） | 高（每变更原因 1 模块） |
| 跨模块耦合度 | 同步变更代价 | 高（改 pua 要改 12 处） | 低（改 1 处） |
| 同名冲突率 | 同名技能占比 | ~8% (12/161) | 0% |

## 引用

> Parnas, D. L. (1972). "On the criteria to be used in decomposing systems into modules". *Communications of the ACM*, 15(12), 1053-1058.

## Evidence Boundary

- 来源支持什么：该卡仅记录理论概念、经典解释或本地大脑已引用的工程化映射。
- Hermes 映射边界：Agent/多模型/技能治理映射是工程类比与设计启发，不等同于原理论在数学或社会科学意义上的严格证明。
- 不应过度推出什么：不得仅凭该理论卡宣称某项代码、流程或策略已经正确；仍需工具证据、原文证据、审计输出或运行验证。
