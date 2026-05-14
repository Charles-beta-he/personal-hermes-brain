# Code Review 多 Agent 并行审查与置信度过滤 — 学习路线

> 从单 Agent Review 到多 Agent 并行审查 + 置信度过滤的结构化学习路径。
> 每阶段独立可验证，失败可回退到上一阶段。

## 适用场景

- 用户想掌握多 Agent 代码审查的完整方法论
- 评估团队成员的 AI-assisted Code Review 能力等级
- 从 github-code-review 平滑过渡到 multi-agent-code-review

## 阶段总览

```
Stage 1: 单 Agent 审查基础 (Review Literacy)        → 会用 AI 做 Code Review
Stage 2: 并行调度理解 (Parallel Dispatch)            → 理解 delegate_task 并行模式
Stage 3: 置信度与聚合 (Confidence & Aggregation)     → 掌握评分、过滤、去重
Stage 4: 生产级闭环 (Production Loop)                → 反馈校准 + 历史精度 + 自动化
```

---

## Stage 1: 单 Agent 审查基础 (Review Literacy)

**目标**: 能用 AI Agent 做有效的单 Agent 代码审查

**前置知识**: Git 基础, GitHub PR 流程, CLI 工具使用

**学习内容**:

1. Code Review 核心维度 (6 维检查清单)
   - Correctness: 边界、空值、错误路径
   - Security: SQLi、XSS、硬编码密钥、认证绕过
   - Code Quality: 命名、DRY、职责单一
   - Testing: 覆盖率、边界用例、错误用例
   - Performance: N+1、O(n²)、异步阻塞
   - Documentation: API 文档、非显而易见逻辑注释

2. 单 Agent 审查工作流
   ```bash
   # 本地变更
   git diff main...HEAD --stat        # 大局观
   git diff main...HEAD               # 完整 diff
   # 逐文件读上下文 + 应用检查清单

   # PR 审查
   gh pr diff 123
   gh pr view 123
   ```

3. 输出格式: Critical → Warnings → Suggestions → Looks Good

**验证点**: 能对 100+ 行 PR 做结构化审查 | 能识别至少 3 类问题 | 输出格式规范

**关联 Skill**: `github-code-review` (基础), `requesting-code-review` (前置验证)

---

## Stage 2: 并行调度理解 (Parallel Dispatch)

**目标**: 理解为什么需要多 Agent、如何用 delegate_task 并行调度

**前置知识**: Stage 1, delegate_task 基本用法

**学习内容**:

1. 单 Agent 的局限
   - 100+ 行改动容易遗漏跨维度问题
   - 安全专家不擅长风格检查，反之亦然
   - 单 Agent 无 cross-validation，false positive 高

2. 正交分解 (Orthogonal Decomposition)
   - 将审查拆为独立关注域: Security / Logic / Performance / Style / Architecture
   - 每个 Agent 收到相同的代码、不同的 system prompt
   - Agent 之间无通信，避免 groupthink

3. delegate_task 批量模式
   ```python
   delegate_task(tasks=[
       {"goal": "Security review prompt...", "context": "<diff>"},
       {"goal": "Logic review prompt...",    "context": "<diff>"},
       {"goal": "Perf review prompt...",     "context": "<diff>"}
   ])
   # 最多 3 并发 (delegation.max_concurrent_children)
   # 5 Agent 时 2 个排队
   ```

4. Agent 数量选择
   - 2 Agent: Bugs (安全+逻辑) + Quality (风格+性能+架构) — 中等 PR
   - 3 Agent: Security + Logic + Performance — 默认推荐
   - 5 Agent: 全维度 — 关键路径代码

5. 与 agent-team-parallel 的关系
   - agent-team-parallel: 通用并行任务控制器 (envelope bus, proof-gated)
   - multi-agent-code-review: 专用于代码审查的并行模式
   - 前者是基础设施，后者是应用层

**验证点**: 能解释正交分解 | 能写 3 Agent 的 prompt | 理解并发限制

**关联 Skill**: `delegate_task` (调度), `agent-team-parallel` (并行基础设施)

---

## Stage 3: 置信度与聚合 (Confidence & Aggregation)

**目标**: 掌握置信度评分、跨 Agent 一致性、语义去重、阈值过滤

**前置知识**: Stage 2, Python 基础, JSON 处理

**学习内容**:

1. 结构化输出 Schema
   ```json
   {
     "file": "src/auth.py", "line": 42,
     "severity": "high", "confidence": 0.92,
     "finding": "...", "suggestion": "...",
     "reasoning": "..."
   }
   ```
   - confidence: Agent 自报置信度 (0.0-1.0)
   - severity: critical / high / medium / low
   - reasoning: 为什么认为是真问题

2. 复合评分公式
   ```
   final_score = (agreement × 0.6) + (avg_conf × 0.4)
   ```
   - agreement = 标记该问题的 Agent 数 / 总 Agent 数
   - avg_conf = 该问题所有 Agent 自报置信度均值
   - 0.6/0.4 权重: 一致性比自报更可靠

3. 严重度阈值过滤
   | Severity | Threshold | 逻辑 |
   |----------|-----------|------|
   | critical | 0.3       | 漏报代价远大于误报 |
   | high     | 0.5       | 覆盖率与噪声平衡 |
   | medium   | 0.7       | 用户忽略低置信中等问题 |
   | low      | 0.7       | 风格问题需要高置信才报告 |

4. 语义去重策略
   - Level 1: file + line + category (快速精确)
   - Level 2: embedding similarity (更准确但慢)
   - Level 3: AST proximity (最精确，实现复杂)

5. 聚合脚本 (确定性，无需 LLM)
   ```python
   from collections import defaultdict
   clusters = defaultdict(list)
   for finding in all_findings:
       key = (finding["file"], finding["line"], finding["category"])
       clusters[key].append(finding)
   # 按 key 聚合 → 计算 final_score → 过滤 → 排序
   ```

6. 变体: Noisy OR 评分
   ```
   score = 1 - (1-p1)(1-p2)...(1-pN)
   ```
   任何 Agent 高置信 → 整体高分。适合安全审查 (宁可误报)。

**验证点**: 能手写聚合脚本 | 能解释 0.6/0.4 权重含义 | 能调阈值平衡误报/漏报

**关联 Skill**: `multi-agent-code-review` (核心), references/confidence-calibration.md

---

## Stage 4: 生产级闭环 (Production Loop)

**目标**: 建立反馈循环、历史精度校准、模型特异性补偿、自动化集成

**前置知识**: Stage 3, Beta 分布基础, GitHub API

**学习内容**:

1. 反馈循环 (Feedback Loop)
   ```
   发现 → 人工审核 → 接受/拒绝 → 更新 Agent 信誉 → 调整阈值
   ```
   - 跟踪每个 finding 的 accept/reject
   - 更新 Beta(α, β) 分布: 接受 → α+=1, 拒绝 → β+=1
   - 历史精度 = α / (α + β)

2. 增强评分公式 (有历史数据时)
   ```
   final_conf = (self_conf × 0.3) + (agreement × 0.3) + (historical_precision × 0.4)
   ```
   - 无历史数据回退: final_score = (agreement × 0.6) + (avg_conf × 0.4)
   - 冷启动: Beta(2, 2) 先验 (均匀 + 轻度正则化)

3. 模型特异性补偿
   | 模型 | 置信度分布 | 特征 |
   |------|-----------|------|
   | Claude | 0.75-0.95 | 轻度过度自信 |
   | GPT-4/5 | 0.6-0.95 | 不确定性表达更好 |
   | DeepSeek/MiMo | 0.8-0.9 | 代码任务校准较弱 |
   - 跨 Agent 一致性项 (权重 0.6) 可补偿模型偏差
   - 最高可靠性: 同模型 + 正交 prompt

4. GitHub 集成
   ```bash
   # 过滤后结果发布为 PR review
   gh pr review 123 --comment --body "## Multi-Agent Review ..."
   # 或带 inline comments 的原子 review
   gh api repos/.../pulls/123/reviews -f comments='[...]'
   ```

5. 置信度校准技术
   - Temperature Scaling: T > 1 降低过度自信
   - Platt Scaling: 逻辑回归校准
   - ECE (Expected Calibration Error): 目标 < 0.05
   - Conformal Prediction: 无分布假设的覆盖保证
   - Self-Consistency: 多次采样一致性

6. 高级话题
   - Token 成本管理: 3 Agent ≈ 3x tokens, 5 Agent ≈ 5x
   - 大 Diff 分割: 1000+ 行按文件拆分审查再聚合
   - Temperature: 审查 Agent 用 0.0-0.2, 聚合器用 0.3
   - 生成代码排除: protobuf/lock 文件自动跳过

**验证点**: 能设计反馈循环 | 理解 Beta 更新机制 | 能集成到 PR workflow

**关联 Skill**: `multi-agent-code-review` (完整), `github-code-review` (PR 集成)

---

## 阶段自评

| 转换 | 必须做到 |
|------|---------|
| 1→2 | 独立完成单 Agent PR 审查, 输出规范, 理解 6 维检查 |
| 2→3 | 能写 3 个正交 prompt, 理解 delegate_task 并发限制 |
| 3→4 | 能手写聚合脚本, 理解评分公式和阈值逻辑 |
| 4→∞ | 有实际反馈数据, 能校准阈值, 集成到 CI/PR 流程 |

## Skill 依赖图

```
Stage 1: github-code-review (读+做)
         ↓
Stage 2: delegate_task (调度) + agent-team-parallel (基础设施)
         ↓
Stage 3: multi-agent-code-review (核心方法论)
         ↓
Stage 4: multi-agent-code-review/references/confidence-calibration.md (校准)
         + github-code-review (PR 集成)
```

## 实战练习建议

| 阶段 | 练习 |
|------|------|
| 1 | 对自己的一个小 PR 做完整单 Agent 审查 |
| 2 | 用 2 Agent 模式审查一个 50+ 行 PR |
| 3 | 用 3 Agent 模式审查 + 手动聚合 + 调阈值 |
| 4 | 在真实 PR 上运行完整流程 + 跟踪 accept/reject |
