# Chunk Success Rate — 复杂任务分解成功率评估

> T15d: >90% 的复杂任务成功分解为 ≤7 chunks，无 context 溢出

## 分解标准

```
简单任务: 1 个 chunk（单文件修改，<20 行）
中等任务: 2-3 个 chunks（多文件，有依赖关系）
复杂任务: 4-7 个 chunks（架构调整，跨模块）
超复杂任务: >7 个 chunks → 必须上报 P10 重新拆分战略
```

## 评估维度

| 维度 | 目标 | 测量方法 |
|------|------|---------|
| 分解成功率 | >90% | 任务成功拆分为 chunks 且全部完成 |
| chunk 边界清晰度 | 100% | 每个 chunk 有明确的输入/输出/验收标准 |
| 无溢出率 | 100% | 执行过程中无 context 超限 |
| 平均 chunk 数 | 3-5 | 按任务复杂度分组统计 |

## Context 溢出检测

```
溢出信号:
  - "我需要更多上下文"
  - 重复询问同一信息
  - 输出质量突然下降
  - 工具调用失败率上升

应对措施:
  1. 立即停止当前 chunk
  2. 将已完成的中间结果固化（写入文件/memory）
  3. 以"已完成的中间结果 + 剩余任务"重新启动
  4. 记录溢出事件，用于后续优化分解策略
```

## 数据存储

`~/.hermes/notes/engineering-cybernetics/chunk-stats.jsonl`

```json
{
  "task_id": "uuid",
  "task_complexity": "simple|medium|complex",
  "planned_chunks": 4,
  "actual_chunks": 4,
  "overflow_events": 0,
  "success": true,
  "timestamp": "2026-04-23T..."
}
```

## 季度目标

```
Q1 基线: 复杂任务分解成功率 85%
Q2 目标: 90%
Q3 目标: 93%
Q4 目标: 95%

无 context 溢出事件: 0（硬指标）
```
