# Forgetting Factor — 记忆遗忘因子调节

> ch12 系统辨识: memory 系统支持 λ 调节，核心记忆 λ=1，临时 λ=0.9

## λ 分级体系

| 记忆类型 | λ | 衰减速度 | 适用场景 |
|---------|---|---------|---------|
| **核心原则** | 1.0 | 永不遗忘 | 控制论十大原则、用户核心价值观 |
| **项目约定** | 0.98 | 极慢 | 架构决策、API 模式、技术栈 |
| **用户偏好** | 0.95 | 慢 | 编码风格、通信方式、质量要求 |
| **技术细节** | 0.90 | 中等 | 具体实现、版本号、配置参数 |
| **临时上下文** | 0.80 | 快 | 单次任务细节、调试中间状态 |

## 衰减公式

```
memory_strength(t) = memory_strength(0) × λ^t

t = 自上次访问以来的 session 数
```

## 自动清理规则

```
每周运行时:
  for each memory entry:
    strength = initial_strength × λ^sessions_since_access
    if strength < 0.5:
      标记为 "stale"
    if strength < 0.2:
      移入 archive（不删除，可搜索但不在 active context 中）
```

## 写入时标注 λ

```
memory(action="add", target="memory", content="...", metadata={"lambda": 0.95, "category": "user_preference"})
```

## 与现有体系集成

- 贝叶斯置信度同时受遗忘因子影响: alpha *= λ, beta *= λ
- 季度审计时检查 archive 中的记忆是否有价值回升
