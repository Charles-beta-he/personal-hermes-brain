# OODA Timer — 迭代阶段计时基线

> T15c: 记录所有任务的 Observe/Orient/Decide/Act 耗时，建立速度基线

## 阶段定义

| 阶段 | 开始标记 | 结束标记 | 说明 |
|------|---------|---------|------|
| **Observe** | 用户发送消息 | Agent 开始回复 | 信息接收 + 上下文加载 |
| **Orient** | 开始分析 | 确定方案 | 理解需求 + 选择 skill + 制定计划 |
| **Decide** | 确定方案 | 开始执行 | 最终决策 + 资源分配 |
| **Act** | 开始执行 | 输出结果 | 工具调用 + 代码编写 + 验证 |

## 记录格式

```json
{
  "session_id": "uuid",
  "task_type": "feature|bugfix|refactor|explore",
  "phases": {
    "observe_ms": 1200,
    "orient_ms": 8500,
    "decide_ms": 2100,
    "act_ms": 15600
  },
  "total_ms": 27400,
  "orient_ratio": 0.31,
  "success": true,
  "rounds": 3
}
```

## 基线目标

```
Orient 时间占比目标: < 45%
当前观察: 通常 Orient 占 30-50%，主要取决于任务复杂度

优化方向:
  - skill 快速匹配（减少 Orient 时间）
  - 预加载常用 skill（减少上下文加载）
  - 标准化 Task Prompt（减少决策时间）
```

## 与 Loop 的集成

每次 loop 结束时:
1. 估算本轮各阶段耗时
2. 如 Orient 占比 > 50% → 告警（可能 skill 选择不当）
3. 如 Act 占比 < 20% → 告警（可能过度分析）

## 数据存储

`~/.hermes/notes/engineering-cybernetics/ooda-baseline.jsonl`

季度分析:
  - 平均 Orient 时间趋势
  - 按 task_type 分组对比
  - 识别慢 Orient 的 skill（需要优化）
