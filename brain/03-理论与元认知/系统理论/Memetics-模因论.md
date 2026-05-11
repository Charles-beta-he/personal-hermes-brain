# Memetics：技能作为模因的复制与变异

> Richard Dawkins, *The Selfish Gene* (1976), Ch. 11 "Memes: the new replicators"
> Susan Blackmore, *The Meme Machine* (1999)
> 联系：[[03-理论与元认知/系统理论/Darwin-技能进化|Darwin Skill]] ｜ [[06-治理与评审/技能生态/skill-steward角色定义|Steward]]

## 核心命题

**模因**（Meme）是文化传播的基本单位，像基因一样复制、变异、被选择。

Hermes Skills 就是**模因池**——每个 skill 是一个模因复合体，包含方法论、触发词、步骤序列、输出格式。

## 3 条模因定律

### 1. 复制（Copying）
技能被加载 → 被使用 → 被改进 → 新版本替换旧版本

```python
# 技能复制的 3 种方式
复制类型 1: 继承 — 新技能复制旧技能的结构并修改内容
复制类型 2: 变异 — 同一技能出现多个版本（如 pua 的 12 个副本）
复制类型 3: 重组 — 两个技能合并产生新技能
```

### 2. 变异（Variation）
每次 skill_view() 后的使用都可能产生改进，改进应回流到原始 skill。

```python
# 当前：技能是静态的
# 优化：每次成功使用后，记录使用上下文作为改进建议

def after_successful_use(skill_name, context):
    """使用后改进建议"""
    changelog_path = f"~/.hermes/skills/{skill_name}/CHANGELOG.md"
    append_to_file(changelog_path, f"- {date}: 成功用于 {context}")
```

### 3. 选择（Selection）
模因的"适应度"由使用频率和成功率决定。

## 应用：技能间的知识传递

### 当前问题
```
Skill A 学会了更好的 prompt 技巧 → Skill B 不知道
Skill C 修复了一个 bug → Skill D 的同样 bug 还在
= 技能孤岛
```

### 解决方案：模因流

```python
# 当 skill_view('skill-A') 被调用时：
# 1. 加载 skill-A 的内容
# 2. 同时检查 skill-A 的 "related_skills" 字段
# 3. 如果有同类的 skill，建议检查它们是否需要相同的更新
# 4. 输出："Skill-B 和 Skill-C 是同类技能，建议同步更新"

def meme_flow(skill_name):
    """技能间的模因流动"""
    skill = load_skill(skill_name)
    related = skill.get("related_skills", [])

    for rel in related:
        if has_same_pattern(skill_name, rel):
            print(f"ℹ️ 建议检查 {rel} 是否需要相同的变更")
```

## 模因健康度指标

| 指标     | 定义         | 健康范围      |
| ------ | ---------- | --------- |
| 复制保真度  | 同类技能的内容一致性 | > 80%     |
| 变异速度   | 技能改进的频率    | 每季度至少 1 次 |
| 适应度    | 使用频率 × 成功率 | 每月至少 3 次  |
| 模因池多样性 | 不同类别的技能数   | 10-20 类别  |

## 引用

> Dawkins, R. (1976). *The Selfish Gene*. Oxford University Press. Chapter 11.
> Blackmore, S. (1999). *The Meme Machine*. Oxford University Press.

## Evidence Boundary

- 来源支持什么：该卡仅记录理论概念、经典解释或本地大脑已引用的工程化映射。
- Hermes 映射边界：Agent/多模型/技能治理映射是工程类比与设计启发，不等同于原理论在数学或社会科学意义上的严格证明。
- 不应过度推出什么：不得仅凭该理论卡宣称某项代码、流程或策略已经正确；仍需工具证据、原文证据、审计输出或运行验证。
