---
type: theory-note
layer: cybernetics-foundation
status: active
created: 2026-05-06T08:24:00Z
concepts: [engineering-cybernetics, agent-loop, proof-of-work, control-plane]
primary_sources:
  - Qian Xuesen, Engineering Cybernetics, 1954
local_sources:
  - 99-hermes-notes/engineering-cybernetics/ch01-introduction.md
  - 99-hermes-notes/engineering-cybernetics/ch03-stability-feedback.md
  - 99-hermes-notes/engineering-cybernetics/AGENT-EVOLUTION-HANDBOOK.md
---

# 07 - 工程控制论到 Agent 闭环

## 核心迁移

工程控制论把控制系统抽象为可建模、可分析、可验证的工程对象。迁移到 Agent 系统时，关键不是照搬公式，而是保留工程约束：

```text
目标明确 → 状态可观测 → 控制动作有边界 → 反馈可验证 → 稳定性可审计
```

## Hermes Agent 闭环

```text
用户目标 / cron trigger
  ↓
P10/P9 framing / task contract
  ↓
skill/router/model selection
  ↓
tool execution / subagent / code or note changes
  ↓
verification: test/build/search/reindex/evidence
  ↓
review: self-check / multi-model / user feedback
  ↓
local brain + skill + memory routing
  ↓
next iteration
```

## 控制面组件

| 控制论角色 | Hermes 组件                                           |
| ----- | --------------------------------------------------- |
| 控制器   | main agent, P10/P9, router, skills                  |
| 被控对象  | codebase, local brain, cron jobs, notes             |
| 传感器   | terminal/read_file/search/browser/brainctl          |
| 估计器   | session_search, brainctl search, multi-model review |
| 执行器   | tools, scripts, patch, git commit                   |
| 监督器   | self-test, verify-evolution-event, p10-health       |
| 记忆    | Obsidian vault, Hermes memory, skills, logs         |

## Proof-of-work

工程控制论要求输出可验证。对 Hermes：

- 写笔记后：`brainctl sync` + `brainctl reindex` + `brainctl search`。
- 改脚本后：`py_compile` + 单测。
- 改项目后：test + build。
- 自进化后：evolution note + event stream + verifier + local commit。

## 设计启示

1. Agent 是动态控制系统，不是一次性问答系统。
2. 本地大脑是长期状态估计器，不只是笔记仓库。
3. 多模型是调节器多样性，不是事实来源。
4. 自进化必须闭环到日志、验证和本地大脑检索。

## 相关链接

- [[01-反馈回路与稳定性]]
- [[05-稳态-内稳态与自适应]]
- [[06-一阶与二阶控制论]]
- [[Hermes Local Brain Memory Hierarchy]]

## Evidence Boundary

- 来源支持什么：该卡仅记录理论概念、经典解释或本地大脑已引用的工程化映射。
- Hermes 映射边界：Agent/多模型/技能治理映射是工程类比与设计启发，不等同于原理论在数学或社会科学意义上的严格证明。
- 不应过度推出什么：不得仅凭该理论卡宣称某项代码、流程或策略已经正确；仍需工具证据、原文证据、审计输出或运行验证。
