# Superpowers 可组合开发流程与 TDD/brainstorming 适配评估

> 评估日期: 2026-05-12
> 来源: obra/superpowers (MIT, GitHub ~186k stars)
> 方法: evidence-first, 对比分析, 最小复现实验设计

## 1. 来源与许可

- 仓库: github.com/obra/superpowers
- 许可: MIT
- 作者: Jesse (obra)
- 定位: coding agent 的完整软件开发方法论, 基于可组合 skill + bootstrap 自动触发
- 版本: v5.1.0+
- 14 个可组合 skill, 覆盖 brainstorming → plan → TDD → subagent dispatch → review → verification 全流程

## 2. 能力矩阵: Superpowers vs Hermes 现有技能

| Superpowers Skill          | Hermes 等价物                               | 覆盖度 | 差距                                    |
|----------------------------|---------------------------------------------|--------|-----------------------------------------|
| brainstorming              | idea-refine + requirement-clarification     | 70%    | 缺少 HARD-GATE (不批准不写码), visual companion, spec self-review, docs/superpowers/specs 输出 |
| test-driven-development    | test-driven-development (已适配)             | 95%    | 基本完整, 缺少 Java/Maven 特定部分       |
| writing-plans              | writing-plans (已适配)                       | 95%    | 基本完整                                |
| subagent-driven-development| subagent-driven-development (已适配)         | 95%    | 基本完整                                |
| systematic-debugging       | systematic-debugging (已适配)                | 90%    | 基本完整                                |
| requesting-code-review     | requesting-code-review (已适配)              | 85%    | 部分重叠                                |
| dispatching-parallel-agents| agent-team-parallel                         | 60%    | 缺少 isolated context 原则, 无 shared state 检测 |
| verification-before-completion| requesting-code-review (部分)              | 50%    | 缺少独立的 "证据先于声明" 铁律 skill     |
| using-superpowers          | Hermes skill loading (不同机制)              | N/A    | 机制不同, 不需要适配                     |
| writing-skills             | hermes-agent-skill-authoring                | 70%    | 缺少 adversarial pressure testing 要求   |
| executing-plans            | subagent-driven-development (部分)           | 40%    | 缺少独立的 plan execution 纪律           |
| finishing-a-development-branch| (无)                                       | 0%     | 完全缺失 - git worktree 分支完成流程     |
| receiving-code-review      | (无)                                        | 0%     | 完全缺失 - 接收他人 code review 的处理流程 |
| using-git-worktrees        | (无)                                        | 0%     | 完全缺失 - git worktree 隔离开发流程     |

## 3. Composable Flow 分析

Superpowers 的核心设计是 **skill 链式触发**:

```
using-superpowers (bootstrap)
  → brainstorming (HARD-GATE: 不批准不写码)
    → writing-plans (spec → plan)
      → subagent-driven-development (plan → code)
        → test-driven-development (每个 task 内)
        → requesting-code-review (两阶段 review)
          → verification-before-completion (证据先于声明)
```

Hermes 现有链路:
```
requirement-clarification (可选)
  → writing-plans
    → subagent-driven-development
      → test-driven-development
      → requesting-code-review
```

**关键差距:**
1. **brainstorming HARD-GATE** — Superpowers 强制在写任何代码前必须有批准的设计。Hermes 的 idea-refine 是建议性的, 不是强制门禁
2. **verification-before-completion** — Superpowers 有独立的 "证据先于声明" 铁律。Hermes 把它混在 code-review 里, 强度不够
3. **git worktree 隔离** — Superpowers 有完整的 worktree 创建/使用/完成流程。Hermes 完全没有
4. **receiving-code-review** — Superpowers 有接收他人 review 并处理的流程。Hermes 没有
5. **Visual Companion** — brainstorming 时可选的浏览器可视化伴侣。Hermes 没有

## 4. TDD 适配评估

**已适配的 TDD skill 质量: 高**

Hermes 的 test-driven-development 已从 Superpowers 完整适配, 包括:
- RED-GREEN-REFACTOR 铁律
- "删除未测试代码" 规则
- 常见合理化借口反驳表
- Hermes 工具集成 (terminal, delegate_task)
- Java/Maven 特定指南

**差距:** 仅缺少 Java/Maven multi-module 部分 (对 Hermes 用户影响小)

## 5. Brainstorming 适配评估

**现有覆盖: 70%, 关键缺失: HARD-GATE**

| 维度 | Superpowers brainstorming | Hermes idea-refine + req-clarification |
|------|--------------------------|----------------------------------------|
| 强制门禁 | HARD-GATE: 不批准不写码 | 建议性, 不强制 |
| 一次一问 | 强制 | 要求但不强制 |
| 2-3 方案对比 | 强制 | 要求 5+ 方案 |
| 设计文档输出 | docs/superpowers/specs/ | .claude/requirements/ |
| Spec self-review | 4 项检查 (placeholder/一致性/范围/歧义) | 无 |
| 用户 review 门禁 | 必须用户批准 spec 才继续 | 无 |
| Visual Companion | 可选浏览器可视化 | 无 |
| YAGNI 强调 | 每个设计环节都强调 | 仅在 idea-refine 提及 |

## 6. 最小复现实验设计

### 实验 1: Brainstorming HARD-GATE 效果测试

**场景:** 用户说 "帮我做个 React todo list"

**Superpowers 预期行为:**
1. 触发 brainstorming skill
2. 不写任何代码
3. 问 1 个澄清问题 → 等回答
4. 提出 2-3 个方案 → 用户选
5. 分段展示设计 → 用户逐段批准
6. 写 spec 文档 → self-review → 用户 review
7. 只有用户批准后才进入 writing-plans

**Hermes 当前预期行为:**
1. 可能触发 idea-refine 或 requirement-clarification (取决于 skill 加载)
2. 也可能直接开始写代码 (无 HARD-GATE)
3. 如果触发 idea-refine, 会生成 5+ 方案但不强制用户批准

**验证方法:** 对比两种配置下的 agent 行为, 记录是否跳过设计直接写码

### 实验 2: TDD 铁律执行测试

**场景:** 实现一个简单的 retry 函数

**预期行为 (两者相同):**
1. 写失败测试
2. 运行确认失败
3. 写最小代码通过
4. 运行确认通过
5. 重构

**验证方法:** 给 subagent 任务, 观察是否遵守 RED-GREEN-REFACTOR

## 7. 决策

### Adopt (直接采用): 0 个
不需要直接安装 Superpowers — Hermes 已有 5/14 个 skill 的高质量适配。

### Borrow (借鉴模式): 5 个

1. **brainstorming HARD-GATE** → 增强 requirement-clarification, 添加强制门禁
   - 在 requirement-clarification 中添加 `<HARD-GATE>` 规则
   - 不批准设计 = 不写代码

2. **verification-before-completion** → 创建独立 skill
   - 从 Superpowers 提取 "证据先于声明" 铁律
   - 独立于 code-review, 作为完成前的最后门禁

3. **brainstorming spec self-review** → 合并到 requirement-clarification
   - 添加 4 项 spec 检查: placeholder/一致性/范围/歧义

4. **brainstorming Visual Companion** → 参考设计, 未来可实现
   - 浏览器可视化伴侣, 用于 UI mockup 展示
   - 优先级低, 可以后续迭代

5. **git worktree 隔离流程** → 参考设计, 考虑适配
   - finishing-a-development-branch + using-git-worktrees
   - 对 Hermes 的 agent-team-parallel 有参考价值

### Reject (不采纳): 2 个

1. **using-superpowers** — 机制不同 (Superpowers 用 Skill tool, Hermes 用 skill_view), 不需要适配
2. **receiving-code-review** — Hermes 的 requesting-code-review 已包含部分, 且 Hermes 主要作为 reviewer 而非被 review 方

## 8. 结论

Superpowers 是一个高质量的可组合开发方法论, 其 14 个 skill 形成完整的开发链路。Hermes 已适配其中 5 个核心 skill (TDD/plans/subagent/debugging/review), 覆盖约 60% 的能力。

**最大差距在 brainstorming 阶段:** 缺少 HARD-GATE 强制门禁, 导致 agent 可能跳过设计直接写码。这是最值得借鉴的模式。

**整体决策: BORROW 模式** — 不安装 Superpowers, 选择性借鉴 5 个模式增强现有 skill。预计 2-3 个工作项可完成核心差距填补。
