---
name: ooda-agent
description: "OODA环 × Agent 迭代速度优化 — 基于 John Boyd 的军事决策理论，将每个 Agent 交互建模为 Observe→Orient→Decide→Act 循环。优化目标是比问题演化更快完成 OODA，在对抗性任务中取得优势。Use when iterating on complex tasks, debugging stubborn bugs, or optimizing response speed. Triggers: 'OODA', '迭代速度', '响应速度', '快速迭代', '对抗性任务', '顽固bug', '决策循环'."
license: MIT
tags: [ooda, iteration-speed, decision-cycle, debugging, rapid-response]
---

# OODA Agent — 迭代速度优化

> 在对抗中，不是装备更好的一方获胜，而是 OODA 循环更快的一方。
> — John Boyd, USAF Colonel

## OODA 四阶段

```
Observe (观察)  ──► Orient (定向) ──► Decide (决策) ──► Act (行动)
     ▲                                                              │
     └──────────────────── Feedback ◄───────────────────────────────┘
```

| 阶段 | 控制论映射 | Agent 映射 | 典型耗时 |
|------|-----------|-----------|---------|
| **Observe** | 传感器读取 | 读取当前状态：git diff、test结果、文件内容 | 10-20% |
| **Orient** | 状态估计 | 分析根因、定位问题、理解上下文 | 40-60% |
| **Decide** | 控制器计算 | 选择方案、评估风险、制定计划 | 15-25% |
| **Act** | 执行器输出 | 代码修改、工具调用、交付输出 | 10-20% |

**瓶颈通常在 Orient（分析）阶段。**

## 速度优化策略

### 1. Observe 加速 — 减少状态读取时间

| 技术 | 实现 | 效果 |
|------|------|------|
| **状态缓存** | 缓存常用文件状态，避免重复读取 | -30% |
| **增量观测** | 只读取变化的部分，不重新加载全量 | -40% |
| **预处理摘要** | 执行前输出当前状态摘要，减少中途查询 | -20% |
| **并行观测** | 同时读取多个独立信息源 | -25% |

**Agent 实践**：
```python
# 好的：一次读取全部需要的状态
files_to_read = ["src/app.py", "tests/test_app.py", "package.json"]
contents = read_multiple_files(files_to_read)

# 差的：分多次读取，每次都要重新定位
content1 = read_file("src/app.py")
# ... 分析 ...
content2 = read_file("tests/test_app.py")
# ... 分析 ...
```

### 2. Orient 加速 — 缩短分析时间

| 技术 | 实现 | 效果 |
|------|------|------|
| **诊断模板** | 预设常见问题的诊断流程 | -50% |
| **模式匹配** | 根据错误类型直接跳转对应分析路径 | -40% |
| **假设排序** | 按先验概率排序假设，优先验证最可能的 | -30% |
| **快速排除** | 设计 cheap test 快速排除大量假设 | -35% |

**诊断模板示例（Build 失败）**：
```
Step 1: 读取最后 20 行错误输出
Step 2: 识别错误类型（语法/类型/依赖/配置/测试）
Step 3: 按类型匹配预设方案库
Step 4: 验证最可能方案（≤ 2 分钟）
Step 5: 如果失败，启动深度分析
```

### 3. Decide 加速 — 快速选择方案

| 技术 | 实现 | 效果 |
|------|------|------|
| **方案库** | 常见问题的预设方案（带成功率） | -40% |
| ** satisficing** | 不求最优，求「够好且快」 | -30% |
| **决策树** | 结构化决策，减少自由思考 | -25% |
| **默认方案** | 无明确证据时，使用历史最优方案 | -20% |

**Simon 有限理性**：
```
全局最优 = 需要探索所有可能 → Orient 极长
满意解 (satisficing) = 找到第一个超过阈值的就执行 → Orient 短

Agent 策略：
- 常规任务 → satisficing（快速决策）
- 关键架构 → 全局最优（深度分析）
- 紧急修复 → 默认方案 + 快速验证
```

### 4. Act 加速 — 提高执行效率

| 技术 | 实现 | 效果 |
|------|------|------|
| **代码模板** | 常用代码模式的预生成片段 | -30% |
| **批量操作** | 一次修改多个相关文件 | -25% |
| **自动化脚本** | 重复操作脚本化 | -50% |
| **safe defaults** | 预设安全参数，减少决策 | -15% |

## OODA 计时与监控

### 记录格式
```json
{
  "session_id": "20260423_213000",
  "task": "修复 build 失败",
  "ooda_cycles": [
    {
      "cycle": 1,
      "observe_ms": 1200,
      "orient_ms": 8500,
      "decide_ms": 2100,
      "act_ms": 1800,
      "total_ms": 13600,
      "bottleneck": "orient"
    }
  ],
  "iterations": 3,
  "total_time_ms": 40800
}
```

### 瓶颈分析
```
如果 observe > 30%: 状态读取效率低 → 优化缓存/并行
如果 orient > 50%: 分析效率低 → 优化诊断模板/模式匹配
if decide > 25%: 决策困难 → 优化方案库/决策树
if act > 25%: 执行效率低 → 优化模板/批量操作
```

## 对抗性 OODA

面对「顽固问题」（反复修复反复失败）：

### 传统思路（慢）
```
问题稳定 → Agent 也稳定地以相同方式应对 → 陷入僵局
= 双方 OODA 同步，无优势
```

### 对抗性思路（快）
```
1. 改变观测维度（从不同角度收集信息）
2. 改变定向框架（换一套假设体系）
3. 引入外部变量（改变环境条件）
4. 加速执行频率（小步快跑，快速试错）
```

**Boyd 的破坏性 OODA**：
> 不是更快地做同样的事，而是做不同的事让对手无法定向。

Agent 应用：当同一类修复连续 3 次失败，强制切换策略：
- 从「局部修复」切换到「全局重构」
- 从「自动化」切换到「人工确认每一步」
- 从「增量修改」切换到「回滚到稳定基线重新开始」

## 与现有体系的集成

### 与 control-theory 集成
- ch03 稳定性：快速 OODA = 高增益反馈，需要足够稳定裕度支撑
- ch05 采样：OODA 频率 = 采样频率，需满足香农定理

### 与 cognitive-load 集成
- Orient 阶段消耗最多认知资源 → Chunk 化分解 Orient 过程

### 与 bayesian-agent 集成
- 高置信 skill → OODA 可更快（Orient 缩短）
- 低置信 skill → OODA 需更谨慎（Orient 延长）

## 输入输出规范

### 输入

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `action` | enum | 是 | `record` / `analyze` / `disrupt` / `benchmark` |
| `cycle_data` | object | 否 | 计时数据（record 时必填）|
| `failure_count` | int | 否 | 连续失败次数（disrupt 时必填）|
| `task_type` | enum | 否 | `simple` / `normal` / `complex` / `stubborn` / `strategic`（benchmark 时必填）|

### 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| `bottleneck` | enum | 瓶颈阶段：observe/orient/decide/act |
| `optimization` | string[] | 优化建议列表 |
| `target_time_ms` | int | 目标耗时（毫秒）|
| `actual_time_ms` | int | 实际耗时（毫秒）|
| `is_within_target` | bool | 是否达标 |
| `disrupt_strategy` | string | 破坏性策略（disrupt 时）|

## 使用方式

### 任务前速度评估
```
用户: "这个 bug 很顽固"
→ 输入: { action: "benchmark", task_type: "stubborn" }
→ 输出: { target_time_ms: 900000, optimization: ["启用对抗性 OODA"], ... }
→ 自然语言: "启用对抗性 OODA 模式。前 2 次尝试用标准流程，第 3 次起自动切换策略维度。"
```

### 迭代中速度监控
```
每轮 loop 结束后：
→ 输入: { action: "record", cycle_data: { observe_ms: 1200, orient_ms: 8500, ... } }
→ 输出: { bottleneck: "orient", optimization: ["使用诊断模板"], ... }
→ 下轮针对性优化
```

### 顽固问题协议
```
连续 3 轮同类型失败：
→ 输入: { action: "disrupt", failure_count: 3 }
→ 输出: { disrupt_strategy: "改变定向框架", ... }
→ 强制改变一个维度（观测/定向/决策/行动）
→ 记录哪种改变有效，固化为模式
```

## 速度目标

| 任务类型 | 目标 OODA 周期 | 迭代次数上限 |
|---------|---------------|-------------|
| 简单修改 | < 2 分钟 | 1-2 轮 |
| 常规功能 | < 5 分钟 | 3-5 轮 |
| 复杂重构 | < 10 分钟 | 5-8 轮 |
| 顽固 Bug | < 15 分钟 | 8-10 轮（对抗模式） |
| 战略设计 | < 30 分钟 | 2-3 轮 |

超过上限 → 触发升级/求助/暂停


## 约束

- 遵循项目规范
- 在 context budget 内完成
