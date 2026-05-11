---
type: atom
status: evergreen
created: 2026-05-08T02:05:00+08:00
updated: 2026-05-08T02:05:00+08:00
concepts: [hermes-tool-budget, permission-gates, agent-orchestration]
---

# Agent 单会话工具预算与权限门

## Principle

长任务不能依赖单个聊天会话无限调用工具。单会话工具预算是工程边界，不是认知边界。可靠 agent 系统应把工作拆成可恢复 tick，并把状态、证据、权限决策外置到 durable artifacts。

## Tool Budget Pattern

- Batch: 多个机械检查合并进一个脚本或 `execute_code`。
- Checkpoint: 每轮写 task state、evidence bundle、issue ledger、verification result。
- Resume: 新会话只需读取 artifact，不需要完整聊天历史。
- Delegate: 独立探索交给 subagent/background/cron；父会话验证 handle。
- Certify: 多模型认证必须基于 linked claims/evidence，不基于口头一致。

## Permission Gate Pattern

- Read-only 默认允许。
- Derived write scoped allowlist。
- Canonical task mutation 只能通过 typed command + atomic write + lease。
- External side effect 必须 dry-run first。
- Destructive/secrets 默认拒绝。

## Local-Brain Application

`~/Documents/brain` 保持 Markdown canonical。`brain_task_orchestrator.py` 是 typed local controller：它降低 LLM 工具调用消耗，同时限制写入面，避免 subagent 直接用任意 shell 修改 vault。

## Symphony Insight

OpenAI Symphony 文章中的 Codex App Server / dynamic tool calls 提供了同一个原则：高权限工具留在宿主侧 proxy，agent 只调用受控接口；不要把 token 或无限权限环境暴露给工作 agent。
