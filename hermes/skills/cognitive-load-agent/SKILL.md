---
name: cognitive-load-agent
description: "认知负荷理论 × Agent Context 管理 — 基于 Sweller 认知负荷理论，将 Agent context window 建模为工作记忆。通过 Chunk 化分解、外在负荷最小化、相关负荷最大化来优化推理质量。Use when task is complex, context is long, or reasoning quality degrades. Triggers: 'context管理', 'chunk化', '任务分解', '认知负荷', '工作记忆', 'context溢出', '任务太大'."
license: MIT
tags: [cognitive-load, context-management, chunking, task-decomposition, working-memory]
---

# Cognitive Load Agent — 认知负荷管理

> 工作记忆的容量是 7±2 个 chunk — George Miller
> Agent 的 context window 同理，超限则推理质量必然下降。

## 三类认知负荷

| 类型 | 定义 | Agent 映射 | 优化策略 |
|------|------|-----------|---------|
| **内在负荷 (Intrinsic)** | 任务本身的复杂度 | 问题的本质难度 | 分解为子任务 |
| **外在负荷 (Extraneous)** | 无关信息占用资源 | 冗余prompt、重复上下文 | 精简、去重、按需加载 |
| **相关负荷 (Germane)** | 促进理解的信息 | skill 中的原理说明、示例 | 保留并强化 |

**目标**：最小化外在负荷，最大化相关负荷，将内在负荷控制在 chunk 容量内。

## Chunk 容量规则

### 基础规则
```
Context Window ≈ 工作记忆
Chunk 容量 ≈ 7 ± 2

每个 chunk 可以是：
- 一个 skill 的核心概念
- 一个子任务的目标
- 一个文件的关键信息
- 一个验证步骤的结果
```

### Agent 专用 chunk 定义
```
1 chunk = 约 200-400 tokens 的有效信息
（不是 raw tokens，是「可被独立理解和操作」的信息单元）
```

### 任务分解阈值
| 当前 chunk 数 | 行动 |
|--------------|------|
| ≤ 5 | 可直接执行，无需分解 |
| 6-7 | 建议分解，但可尝试直接执行 |
| 8-9 | 必须分解，否则推理质量下降 |
| ≥ 10 | 严重超载，必须分层分解 |

## Context 预算制

每个 session 开始前，按任务类型分配 context tokens 预算：

### 标准预算（128K context）
```
系统指令 + 环境信息    : 15%  (~20K)  — 固定开销
战略分析 (P10)         : 15%  (~20K)  — 方向校准
核心上下文（代码/需求） : 35%  (~45K)  — 主要工作区
验证输出 + 测试结果    : 20%  (~25K)  — 反馈回路
缓冲（应对意外）       : 15%  (~18K)  — 安全余量
```

### 紧急模式预算（快速修复）
```
战略分析 : 5%
核心上下文: 60%
验证输出 : 25%
缓冲     : 10%
```

### 探索模式预算（新领域研究）
```
战略分析 : 25%
核心上下文: 30%
验证输出 : 20%
缓冲     : 25%  — 不确定性高，需要更多余量
```

## Chunk 化分解策略

### 分解原则
1. **功能内聚**：每个 chunk 只做一件事
2. **接口最小化**：chunk 间交换最少信息
3. **可独立验证**：每个 chunk 有明确的完成标准

### 分解模板
```markdown
## Chunk N: [功能描述]
**输入**: [需要什么前置信息]
**输出**: [交付什么结果]
**预算**: [大约多少 tokens]
**验证**: [如何确认完成]
```

### 分层分解示例
原始任务："重构整个前端架构"

```
第一层 (P10):
  Chunk 1: 现状分析（技术债务识别）
  Chunk 2: 目标定义（理想架构蓝图）
  Chunk 3: 迁移策略（分阶段计划）

第二层 (P9):
  Chunk 3.1: 第一阶段：组件抽象
  Chunk 3.2: 第二阶段：状态管理迁移
  Chunk 3.3: 第三阶段：路由重构

第三层 (P8):
  Chunk 3.1.1: 提取共享 UI 组件
  Chunk 3.1.2: 建立组件文档
  Chunk 3.1.3: 替换旧组件引用
```

每层不超过 7 个 chunk，超则继续分层。

## 外在负荷消除清单

执行任务前检查：

- [ ] **冗余 skill 卸载**：当前任务不需要的 skill 不加载
- [ ] **历史会话压缩**：超过 3 轮的历史，只保留关键结论（摘要）
- [ ] **文件按需读取**：不一次性 cat 整个大文件，只读相关部分
- [ ] **输出模板预置**：在 prompt 中给出输出格式，减少 Agent "想格式"的负担
- [ ] **术语统一**：同一概念用同一术语，避免同义词认知消耗

## 相关负荷强化策略

促进理解的元素应该保留并强化：

- **类比**：用已知概念解释新概念
- **可视化**：用表格、流程图、代码块替代纯文本
- **示例优先**：先给例子，再给规则
- **原理说明**：解释"为什么"而不仅是"怎么做"

## 过载检测与恢复

### 过载信号
- Agent 开始重复已确认的信息
- 输出中出现与任务无关的内容
- 对简单问题给出过度复杂的回答
- 遗忘前文已确认的关键约束

### 恢复协议
```
1. 暂停当前工作
2. 输出当前已完成的 chunk 摘要
3. 压缩上下文：保留摘要，丢弃细节
4. 重新确认剩余目标
5. 继续执行
```

## 与现有体系的集成

### 与 control-theory 集成
- 采样频率（ch05）根据认知负荷调整：高负荷任务 → 更频繁检查（防止迷失）
- 能控性（ch04）验证：Agent 能否通过 chunk 分解改变任意复杂状态

### 与 bayesian-agent 集成
- 高认知负荷任务的 skill 选择：优先选择置信度高、chunk 数少的 skill

### 与 PUA 体系集成
- PUA 的 L3 压力（3.25 考核）可加入认知负荷维度：
  "连续 3 次任务因 chunk 超载而失败 → 需要改进任务分解能力"

## 量化指标

| 指标 | 计算方法 | 目标值 | 监控频率 |
|------|---------|--------|---------|
| **Chunk 化成功率** | 成功分解的任务数 / 总复杂任务数 | > 90% | 每次任务 |
| **平均 Chunk 数** | 所有任务的 chunk 总数 / 任务数 | ≤ 6 | 每周 |
| **Context 溢出率** | 溢出触发次数 / 总 session 数 | < 5% | 每日 |
| **外在负荷消除率** | 执行清单的任务数 / 总任务数 | 100% | 每次任务 |
| **Orient 耗时占比** | Orient 时间 / 总 OODA 时间 | < 45% | 每次迭代 |

## 输入输出规范

### 输入

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_description` | string | 是 | 任务描述 |
| `action` | enum | 是 | `assess` / `decompose` / `compress` / `cleanup` |
| `current_chunks` | int | 否 | 当前 chunk 数（assess 时必填）|
| `context_usage_pct` | float | 否 | 当前 context 使用百分比（compress 时必填）|
| `available_skills` | string[] | 否 | 当前加载的 skill 列表（cleanup 时必填）|

### 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| `intrinsic_load` | int (1-10) | 内在负荷评分 |
| `chunk_count` | int | 预估 chunk 数 |
| `should_decompose` | bool | 是否需要分解 |
| `decomposition` | object[] | 分解方案（decompose 时）|
| `budget` | object | 推荐的 context 预算分配 |
| `warnings` | string[] | 预警信息 |

## 使用方式

### 任务开始前评估
```
用户: "帮我重构这个项目"
→ 输入: { action: "assess", task_description: "重构整个前端架构" }
→ 输出: { intrinsic_load: 9, chunk_count: 12, should_decompose: true, ... }
→ 自然语言: "建议分解为 3 个阶段，每阶段 3-4 个子任务。是否继续？"
```

### Context 溢出预警
```
当 context 使用 > 80% 时：
→ 输入: { action: "compress", context_usage_pct: 0.82 }
→ 输出: { warnings: ["Context 即将溢出，已压缩历史记录"], ... }
```

### 子任务交接
```
Chunk N 完成后：
→ 输入: { action: "handoff", current_chunk: N }
→ 输出: { handoff_summary: "<200 tokens 的交接摘要", ... }
```


## 约束

- 遵循项目规范
- 在 context budget 内完成
