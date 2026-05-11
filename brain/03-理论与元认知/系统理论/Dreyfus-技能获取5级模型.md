# Dreyfus：技能获取 5 级模型

> Stuart & Hubert Dreyfus, *Mind Over Machine* (1986)
> 联系：[[03-理论与元认知/系统理论/Ashby-必要多样性定律|Ashby]] ｜ [[06-治理与评审/技能生态/skill-steward角色定义|Steward]]

## 核心命题

技能获取不是"知道更多"，而是 "感知方式的变化"——从依赖规则到依赖直觉。

## 5 级模型

| 级别 | 名称 | 特征 | Hermes Skill 映射 |
|------|------|------|------------------|
| 1 | Novice | 依赖无上下文规则，无法判断优先级 | 仅有 SKILL.md 骨架，无 test-prompts |
| 2 | Advanced Beginner | 能识别情境特征，但无法自主决策 | 有 test-prompts，无 CHANGELOG |
| 3 | Competent | 能制定计划并执行，有责任感 | 有测试 + 日志 + 边界条件 |
| 4 | Proficient | 能从全局视角判断，直觉辅助决策 | 有 cross-ref + 多场景覆盖 |
| 5 | Expert | 直觉驱动，无需分析直接行动 | 有 Darwin 评分 ≥ 90 + 实测验证 |

## 在 steward 中的应用

```python
def grade_skill(skill):
    """按 Dreyfus 5 级给 skill 打分"""
    score = 1  # 默认 Novice

    if skill.has_tests:
        score = 2  # Advanced Beginner
    if skill.has_changelog and skill.has_tests:
        score = 3  # Competent
    if (skill.has_tests and skill.has_changelog and
        skill.ref_count >= 2 and len(skill.description) > 50):
        score = 4  # Proficient
    if (score >= 4 and has_darwin_score(skill) and
        get_darwin_score(skill) >= 90):
        score = 5  # Expert

    return score
```

## 生态目标

| 等级           | 当前占比               | 目标占比         |
| ------------ | ------------------ | ------------ |
| 5 Expert     | 0%                 | ≥ 10% (核心技能) |
| 4 Proficient | 未知                 | ≥ 20%        |
| 3 Competent  | ~24% (有 CHANGELOG) | ≥ 50%        |
| 2 Advanced   | ~23% (有 tests)     | ≥ 70%        |
| 1 Novice     | 剩余                 | < 30%        |

## 引用

> Dreyfus, H. L., & Dreyfus, S. E. (1986). *Mind Over Machine: The Power of Human Intuition and Expertise in the Era of the Computer*. Free Press.

## Evidence Boundary

- 来源支持什么：该卡仅记录理论概念、经典解释或本地大脑已引用的工程化映射。
- Hermes 映射边界：Agent/多模型/技能治理映射是工程类比与设计启发，不等同于原理论在数学或社会科学意义上的严格证明。
- 不应过度推出什么：不得仅凭该理论卡宣称某项代码、流程或策略已经正确；仍需工具证据、原文证据、审计输出或运行验证。
