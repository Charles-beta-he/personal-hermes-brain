---
name: bayesian-agent
description: "贝叶斯脑 × Agent 置信度管理 — 基于 Friston 自由能原理，将 Agent 判断建模为概率推断。维护 skill/能力的贝叶斯置信度分布，根据用户反馈持续更新。Use when evaluating skill reliability, making uncertain decisions, or calibrating Agent confidence. Triggers: '置信度', '贝叶斯', '概率更新', 'skill评分', '能力评估', '不确定性'."
license: MIT
tags: [bayesian, confidence, skill-evaluation, uncertainty, probabilistic-reasoning]
---

# Bayesian Agent — 贝叶斯置信度管理

> 大脑是贝叶斯推断机器 — Karl Friston
> Agent 的每个判断都应该是概率性的，不是二元的对/错。

## 核心原理

### 贝叶斯更新公式

```
P(H|E) = P(E|H) × P(H) / P(E)

P(H)     = 先验置信度（历史表现）
P(E|H)   = 似然（在该假设下观察到证据的概率）
P(H|E)   = 后验置信度（更新后的置信度）
```

### Agent 映射

| 贝叶斯概念 | Agent 映射 |
|-----------|-----------|
| 假设 H | "这个 skill 能有效解决这类问题" |
| 证据 E | 用户反馈、测试结果、构建状态 |
| 先验 P(H) | Skill 的历史成功率 |
| 似然 P(E|H) | 如果 skill 有效，得到这种反馈的概率 |
| 后验 P(H|E) | 更新后的 skill 置信度 |

## 置信度数据结构

每个 skill 维护一个 Beta 分布：

```python
skill_confidence = {
    "skill-name": {
        "alpha": 8,      # 成功次数 + 1 (伪计数)
        "beta": 2,       # 失败次数 + 1 (伪计数)
        "mean": 0.80,    # alpha / (alpha + beta)
        "samples": 9,    # 总使用次数
        "last_updated": "2026-04-23T20:00:00Z"
    }
}
```

Beta 分布优势：
- 共轭先验，更新简单（alpha+=成功, beta+=失败）
- 天然输出 [0,1] 区间
- 样本少时自动保守（宽分布），样本多时自动精确（窄分布）

## 更新规则

### 成功反馈
```python
alpha += 1
# 额外加成：如果用户明确好评，alpha += 2
```

### 失败反馈
```python
beta += 1
# 额外惩罚：如果失败导致用户重大纠正，beta += 2
```

### 无反馈（中性）
```python
# 不更新，或微小衰减（遗忘因子）
alpha *= 0.999
beta *= 0.999
```

## 置信度等级

| 等级 | 置信度区间 | 行为策略 |
|------|-----------|---------|
| A (高置信) | ≥ 0.85 | 默认使用，可作为其他skill的依赖 |
| B (中置信) | 0.70 - 0.84 | 使用但附加验证，逐步积累样本 |
| C (低置信) | 0.55 - 0.69 | 谨慎使用，优先尝试替代方案 |
| D (待验证) | < 0.55 | 限制使用，需要针对性测试 |

## 不确定性量化

### 认知不确定性 (Epistemic)
样本不足导致的不确定性。解决：多用。

```python
epistemic_uncertainty = 1 / sqrt(alpha + beta)
```

### 偶然不确定性 (Aleatoric)
问题本身固有的随机性。接受。

```python
aleatoric_uncertainty = sqrt(alpha * beta) / ((alpha + beta)**2 * (alpha + beta + 1))
```

### 总不确定性
```python
total_uncertainty = epistemic_uncertainty + aleatoric_uncertainty
```

**决策规则**：当 total_uncertainty > 0.3 时，主动寻求更多反馈（多问用户确认）。

## 多 Skill 组合决策

面对任务，多个 skill 都可能适用时：

```python
def select_skill(task_features, available_skills):
    candidates = []
    for skill in available_skills:
        # P(skill|task) ∝ P(task|skill) × P(skill)
        relevance = calculate_relevance(task_features, skill.triggers)
        confidence = skill.confidence.mean
        score = relevance * confidence
        candidates.append((skill, score))
    
    #  softmax 选择（探索-利用平衡）
    scores = [c[1] for c in candidates]
    temperature = 0.5  # 高=多探索，低=多利用
    probs = softmax([s/temperature for s in scores])
    
    return weighted_choice(candidates, probs)
```

## 与现有体系的集成

### 与 control-theory 集成
- 健康度 V 中的 "skill覆盖率" 使用贝叶斯加权：
  `weighted_coverage = Σ(confidence_i × coverage_i) / Σ(confidence_i)`

### 与 darwin-skill 集成
- 8维度评分中的 "实测表现" 直接输入贝叶斯更新
- 棘轮机制：后验置信度必须严格 > 先验才保留

### 与 PUA 体系集成
- PUA 的 L1-L4 压力等级可用置信度校准：
  - 高置信 skill 失败 → L2（意外，值得深究）
  - 低置信 skill 失败 → L0（正常，预期内）

## 输入输出规范

### 输入

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `skill_name` | string | 是 | 要查询或更新的 skill 名称 |
| `action` | enum | 是 | `query` / `update` / `recommend` / `list` |
| `feedback` | enum | 否 | `success` / `failure` / `praise` / `correction`（update 时必填）|
| `task_features` | string[] | 否 | 任务关键词（recommend 时必填）|

### 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| `skill` | string | skill 名称 |
| `mean` | float | 置信度均值 (0-1) |
| `grade` | enum | A/B/C/D |
| `credible_interval_95` | [float, float] | 95% 可信区间 |
| `observations` | int | 总使用次数 |
| `last_updated` | ISO8601 | 最近更新时间 |
| `recommendations` | object[] | recommend 时的排序结果 |

## 使用方式

### 查询某个 skill 的置信度
```
用户: "requesting-code-review 这个 skill 可靠吗？"
→ 输入: { action: "query", skill_name: "requesting-code-review" }
→ 输出: { skill: "requesting-code-review", mean: 0.92, grade: "A", observations: 45, ... }
→ 自然语言: "置信度 0.92 (A级, 45次使用, 最近一次成功)"
```

### 任务前的 skill 选择建议
```
用户: "我要审查代码"
→ 输入: { action: "recommend", task_features: ["code", "review", "quality"] }
→ 输出: { recommendations: [ {skill: "requesting-code-review", score: 0.89}, ... ] }
→ 自然语言: "推荐 requesting-code-review (置信度 0.89)..."
```

### 校准 Agent 过度自信
```
当 Agent 说"这一定没问题"时：
→ 输入: { action: "query", skill_name: "<当前使用的skill>" }
→ 如果 mean < 0.85，自动降级为"这很可能没问题，但建议验证"
```

## 输出物

- `~/.hermes/skills/bayesian-agent/confidence-db.json` — skill 置信度数据库
- 每次 session 结束后自动更新（如配置了 cron）
- 每日健康度报告中包含置信度变化摘要


## 约束

- 遵循项目规范
- 在 context budget 内完成
