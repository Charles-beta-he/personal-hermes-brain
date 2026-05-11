---
type: review
status: final
created: 2026-05-08T02:05:00+08:00
updated: 2026-05-08T02:16:00+08:00
source: https://openai.com/zh-Hans-CN/index/open-source-codex-orchestration-symphony/
concepts: [openai-symphony, local-brain-task-orchestration, hermes-tool-budget, permission-gates]
---

# OpenAI Symphony 文章对本地大脑任务规划的补充评审

## Verdict

有帮助，但帮助点不是把 Symphony 作为第二任务系统接入，而是进一步确认：本地大脑的待完成任务规划应从“会话管理”升级为“任务/目标控制面”。

本地结论保持不变：`~/Documents/brain` 的 Markdown task notes 是唯一事实源；Symphony、Linear、Codex App Server、dashboard、SQLite index、任务池排序都只能是派生控制面或执行层。

## Article Evidence Highlights

- 文章明确指出交互式 coding agents 的上限是 human context switching：人通常只能舒服地管理 3-5 个会话，再多就会忘记哪个会话在做什么。
- Symphony 的核心转向是：不要围绕 session / PR 管理工作，而是围绕 deliverable / issue / task / milestone 管理工作。
- Symphony 把 issue tracker 变成 control plane：每个未关闭任务映射到独立 agent workspace，持续运行，崩溃/卡住后重启，新任务出现后接手。
- 复杂工作先生成 implementation plan，再生成 task tree，定义阶段与依赖；未被 block 的任务才执行，从而形成自然并行 DAG。
- 文章强调 workflow 被写入 `WORKFLOW.md`：把人类过去隐式执行的步骤文档化，让 agents 按契约执行。
- 文章也提示不要把 agents 绑死在刚性状态机里；更好的方向是给 objectives、tools、context，并保留验证与 review packet。
- Codex App Server 的价值在于用 JSON-RPC / dynamic tool calls 程序化管理 agent，而不是在 tmux/CLI 里人工盯会话；dynamic tools 还可以避免把 Linear token 暴露给 subagents。

## Local-Brain Mapping

| Article idea | 本地大脑采用方式 |
|---|---|
| issue tracker as control plane | Obsidian 控制台 + Markdown task notes as canonical control plane |
| open task -> agent workspace | task note frontmatter + claim/lease + optional workspace |
| task tree / dependencies | inbox -> decomposition -> sorted pool，后续可扩展 blocked_by/dependency frontmatter |
| workflow in WORKFLOW.md | `08-模板/task-workflow-contract-template.md` + task note proof/evidence contract |
| always-on orchestrator | Hermes cron/background session 可作为 derived executor；当前只启用 dry-run boundary |
| app-server dynamic tool calls | Hermes 应采用 allowlisted tool proxy / command wrapper，不把 secrets 给 subagents |
| review packet | task evidence / final review / dashboard links |

## 对 Hermes 单会话 60 次工具调用限制的解法

60 次工具调用上限不应靠“让一个会话硬撑”解决，而应把长任务拆成可恢复、可审计的 orchestration ticks：

1. 工具批处理：3 个以上机械工具调用改用 `execute_code` 聚合，循环、过滤、摘要在脚本内完成，减少外层 tool calls。
2. 状态外置：每轮把 task queue、evidence bundle、issue ledger、verification outputs 写入 Markdown/JSON artifact；会话压缩或中断后可继续。
3. 会话分片：把大 loop 分成 Plan tick / Execute tick / Verify tick / Certify tick，每个 tick 有明确输入输出，不依赖聊天上下文。
4. 子代理隔离：并行审查/代码探索用 `delegate_task` 或独立 Hermes/Claude/Codex 进程；父会话只收 summary + verifiable handle。
5. 后台与定时：长耗时 deterministic gates / multi-model certification 可用 background process 或 cron job，产出 artifact 后再由主会话读取。
6. 本地 orchestrator：`brain_task_orchestrator.py` 作为无 LLM 的 deterministic controller，负责 next/list/dashboard/selfcheck，避免把所有状态操作消耗在 LLM tool calls 上。
7. 失败恢复：工具上限触发时必须输出 handoff：已完成、未完成、证据路径、下一条命令；不得声称 full certification。

## 权限问题解法

权限问题不应通过 `--yolo` 或默认高信任解决，应采用分层权限模型：

| Tier | 能力 | 默认策略 |
|---|---|---|
| T0 read-only | read/search/status/diff/audit | 默认允许 |
| T1 derived write | dashboard、排序池、review artifact、临时证据 | scoped allowlist |
| T2 canonical task mutation | add/claim/release/done/retry task note | atomic write + lease + actor + proof log |
| T3 external side effect | PR、issue、message、deploy、push | dry-run first + explicit scope + verification |
| T4 destructive/secrets | delete、credential、prod data、unbounded shell | 默认拒绝，需人工明确授权 |

Symphony 文章中的 dynamic tool calls 对 Hermes 的启发是：把高权限动作放在宿主侧 allowlisted proxy，而不是把 token/secret/全权限 shell 交给 subagent。对于本地大脑，推荐实现为：

- subagent 只拿任务摘要和只读证据，不拿 secrets。
- 写操作通过 `brain_task_orchestrator.py` 的 typed command 完成，而不是任意 shell 改 vault。
- 外部系统 token 只在父 orchestrator/host tool 内部使用，返回最小必要结果。
- destructive action 必须先产出 dry-run plan，用户或上层 gate 批准后才执行。
- 所有 mutating tool 输出都写入 evidence/proof log，便于后续 audit。

## Multi-Model Fanout Result

State file: `/tmp/openai-symphony-article-hermes-review-state.json`

Fanout tick: `/Users/charles/.hermes/tick-20260507-175146/`

Four-model fanout completed for Claude Opus 4.7, gpt-5.5, DeepSeek v4 Pro, and MiMo v2.5 Pro. The merged result was `weak_consensus` because the full discussion/ratification step timed out before `discussion_result.json` was produced. Therefore this artifact is a multi-view advisory review, not a full certification artifact.

Consensus points across the four planners:

- The article is genuinely useful for task planning because it validates task/deliverable control planes over manual session micromanagement.
- Symphony should remain a reference pattern; `~/Documents/brain` Markdown should remain canonical.
- Tool-call budget should be solved through batching, durable artifacts, resumable ticks, subagents/background jobs/cron, and deterministic local controllers.
- Permission issues should be solved through host-side typed/dynamic tool proxies, scoped allowlists, dry-run-first external effects, and no secret exposure to subagents.

Advisory hardening ideas from gpt-5.5, explicitly outside the already completed scoped deliverable:

- First-class `blocked_by` / `blocks` / `ready_when` dependency frontmatter.
- Resumable tick checkpoint artifacts for long-running orchestrator loops.
- A formal permission policy proxy around high-impact commands.
- Review packet generation for completed tasks.

## Scope Status

本评审补充的是文章层面的设计确认与 Hermes 操作策略；它不改变已完成的 local-brain task orchestrator scope。当前 scoped control plane 仍是 completed，caveats: []。

## Evidence Boundary

Model agreement is provenance only; status promotion requires command/file/search proof recorded in this note or linked artifacts.

