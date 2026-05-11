# Confidence-Driven Skill Selection — 高置信优先，低置信慎用

> T20c: 任务成功率提升至 95% 的关键机制

## 选择策略

### Step 1: 候选 Skill 检索

```
用户输入 → 关键词匹配 → 候选 skill 列表（通常 2-5 个）
```

### Step 2: 置信度排序

```python
def select_skill(candidates, context_budget, urgency):
    """
    candidates: [(skill_name, confidence, complexity)]
    context_budget: 剩余 token 预算 (0-1)
    urgency: 紧急程度 (0-1)
    """
    
    for skill in candidates:
        # 基础分 = 置信度
        score = skill.confidence
        
        # 紧急模式: 优先选择简单、高置信 skill（即使不是最优匹配）
        if urgency > 0.7:
            score += (1 - skill.complexity) * 0.3
        
        # Context 紧张: 优先选择低消耗 skill
        if context_budget < 0.3:
            score += (1 - skill.complexity) * 0.2
        
        # 低置信 skill 惩罚
        if skill.confidence < 0.5:
            score -= 0.3  # 慎用
        
        skill.selection_score = score
    
    return max(candidates, key=lambda s: s.selection_score)
```

### Step 3: 执行与监控

```
执行选中的 skill:
  - 记录实际表现（成功/失败/用户纠正）
  - 更新置信度（贝叶斯 + 卡尔曼）
  - 如失败: 尝试次优候选（fallback chain）
```

## Fallback Chain

```
首选 skill (置信度最高)
  → 失败 → 次选 skill (置信度次高)
    → 失败 → 通用 skill (保底)
      → 失败 → 人工介入标记
```

## 禁忌清单

```
confidence < 0.3: 禁止使用，直接人工介入
confidence < 0.5: 允许使用但需额外验证
confidence < 0.7: 常规使用
confidence > 0.9: 优先使用，可跳过部分验证
```

## 与任务成功率的关联

```
目标: 任务成功率 95%

计算:
  假设每次任务平均使用 3 个 skill
  每个 skill 的独立成功率需要: 0.95^(1/3) ≈ 0.983
  
  即: 平均每个 skill 的置信度需要 ≥ 0.98
  
  当前状态:
    40 个 skill，平均置信度 ~0.67
    需要持续优化至 0.98
```
