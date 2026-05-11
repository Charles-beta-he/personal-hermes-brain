# GSD ↔ Hermes Workflow Mapping

> T25: GSD Bridge 实际映射验证 — 概念层面对齐

## 核心工作流映射

| GSD Workflow | Hermes Skill | 说明 |
|-------------|--------------|------|
| `plan-phase.md` | `p9` | 任务规划与拆解 |
| `execute-phase.md` | `p7/p8` | 代码执行与交付 |
| `verify-phase.md` | `post-deploy-verification` | 部署后验证 |
| `discuss-phase.md` | `requirement-clarification` | 需求澄清与讨论 |
| `code-review.md` | `github-code-review` | 代码审查 |
| `audit-fix.md` | `uimax-audit` | 质量审计与修复 |
| `health.md` | `agent-health-monitor` | 健康度检查 |
| `session-report.md` | `loop-report-template` | 迭代报告 |
| `stats.md` | `darwin-skill` | 统计分析 |
| `sync-skills.md` | `bayesian-agent` | Skill 同步与置信度更新 |
| `diagnose-issues.md` | `systematic-debugging` | 问题诊断 |
| `spike.md` | `optimal-control-modes` (探索模式) | 技术调研 |
| `ship.md` | `semantic-release-monorepo` | 发布上线 |
| `forensics.md` | `session-history-analyzer` | 历史分析与根因 |

## 调用路径（概念验证）

```
Hermes 用户输入:
  "帮我审查这段代码"
    ↓
  Hermes 匹配 `github-code-review` skill (高置信度)
    ↓
  如需 GSD 增强:
    读取 GSD `code-review.md` 作为参考模板
    提取 GSD 的审查 checklist 补充到 Hermes 流程
    ↓
  输出: Hermes 标准输出 + GSD 审查点覆盖
```

## 差异点

| 维度 | GSD | Hermes |
|------|-----|--------|
| 运行方式 | CLI + SDK | Agent 对话 |
| 状态管理 | 文件系统 (workspaces/) | Memory + Session |
| 技能发现 | `sync-skills` 命令 | `skills_list` tool |
| 迭代报告 | `session-report` 生成文件 | `loop-report` 对话输出 |
| 健康监控 | `health` 命令 | `agent-health-monitor` 脚本 |

## 集成建议

1. **单向引用**: Hermes 读取 GSD workflows 作为参考，不反向调用
2. **模板补充**: GSD 的 checklist/templates 可补充到 Hermes references/
3. **概念对齐**: 统一术语（phase = task, workspace = project, skill = skill）

## 验证状态

✓ GSD workflows 目录可读取（85 个 workflows）
✓ 概念映射建立（15 个核心 workflow 对齐）
⚠ 运行时集成受限（SDK 版本冲突，采取文档级引用策略）
