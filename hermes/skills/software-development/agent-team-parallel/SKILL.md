---
name: agent-team-parallel
description: "Agent Team 并行任务执行 — orchestrator pattern with parallel dispatch, envelope bus state, proof-gated merge, human escape, kill switch. 触发词: agent team, parallel dispatch, 并行任务, fan-out, agent team controller, worktree"
version: 1.0.0
license: MIT
tags: [parallel, multi-agent, orchestration, envelope-bus, proof-gated, worktree]
---

# Agent Team Parallel — 并行任务执行控制器

> 用 brain_task_orchestrator + envelope_bus + delegate_task 实现并行任务执行，proof-gated merge，N=1→N=2→N=3 渐进扩展。

## When to Use

- 多个独立 boundary 的任务可并行执行
- 需要 crash-safe 状态管理 (SQLite envelope bus)
- 需要 proof artifact 做 review gate
- 需要 human escape 机制防止失控
- 用户要求同时修改多个不冲突的模块/文件
- 希望在子任务失败时不影响主工作区

## Architecture

```
brain_task_orchestrator (source-of-truth)
  ↓ parallel-dispatch-dry-run --max-agents N
agent_team_controller.py
  ↓ claim → create envelope → delegate_task
  ↓ worker produces PROOF_JSON
  ↓ controller collects proof → review → done
envelope_bus.py (SQLite state)
  ↓ PENDING → RUNNING → DONE/FAILED/SKIPPED/BLOCKED
pipeline_tick.py (cron trigger)
  ↓ sync brain tasks → check timeouts → check escape
```

## Numeric Guardrails (4-Model Certified 2026-05-10)

| Parameter | Value | Purpose |
|-----------|-------|---------|
| appetite_timeout | 30min default | Shape Up time budget |
| max_retry | 3 | After 3 failures: escalate + block |
| human_escape | 2 block OR 3 crash | Auto-pause + notify |
| max_runtime | 3600s/task | Single task max |
| lease_ttl | 900s | Worker claim validity |
| heartbeat_interval | 120s | Worker heartbeat |
| state_source | SQLite envelope bus | Single source of truth |

## Key Safety Rules

1. **Worker CANNOT mark DONE** — only controller can transition to review→done
2. **Proof artifact required** — worker must output `PROOF_JSON: {...}` as last line
3. **Kill switch** — `AGENT_TEAM_DISABLED=1` or `state/agent_team_disabled` file
4. **Human escape** — 2 consecutive blocks or 3 crashes → auto-pause pipeline
5. **Boundary isolation** — different `parallel_boundary` values can run in parallel
6. **Lease TTL** — claims expire, stale claims get reclaimed

## Implementation Scripts

All at `~/.hermes/scripts/`:

| Script | Purpose | Cron |
|--------|---------|------|
| `agent_team_controller.py` | Parallel dispatch controller | every 1h |
| `envelope_bus.py` | SQLite state management | - |
| `pipeline_tick.py` | Pipeline automation tick | every 1h |
| `kanban_bridge.py` | Brain→Kanban one-way sync | every 2h |

## Worker Context Template

Controller builds context for each delegate_task child:

```
TASK: {title}
ID: {task_id}
PRIORITY: {priority}
PROJECT: {project}
BOUNDARY: {parallel_boundary}

RULES:
1. You CANNOT mark this task done. Only the controller can.
2. You must produce a PROOF artifact when complete.
3. Stay within your boundary.
4. If blocked, output BLOCKED: <reason>
5. If you need human input, output BLOCKED: HUMAN_INPUT_NEEDED: <question>

PROOF FORMAT (output as last line):
PROOF_JSON: {{"status":"done|blocked","summary":"<=200 chars","files_changed":[],"tests_passed":0,"proof_sha":"sha256_of_output"}}
```

## Scaling Strategy

```
Phase 1: N=1 — single worker, prove lifecycle
Phase 2: N=2 — two workers with different boundaries
Phase 3: N=3 — full parallel with boundary conflict detection
```

Scaling criteria:
- N=1 stable for 3 days → try N=2
- N=2 stable for 3 days → try N=3
- Any human escape trigger → drop back to N=1

## Git Worktree Isolation

For code-changing tasks, create isolated worktrees:

```bash
git worktree add /tmp/wt-{task-name} {base-branch}
cd /tmp/wt-{task-name}
# ... do work ...
git add . && git commit -m "..."
# Back in main repo:
cd {main-repo}
git merge /tmp/wt-{task-name} --no-edit
git worktree remove /tmp/wt-{task-name}
```

## Integration with brain_task_orchestrator

```bash
python3 brain_task_orchestrator.py parallel-dispatch-dry-run --max-agents 3 --json
python3 brain_task_orchestrator.py claim TASK_ID --actor agent-team-controller --ttl-minutes 60 --json
python3 brain_task_orchestrator.py boundary-check --json
python3 brain_task_orchestrator.py release TASK_ID --json
```

## Integration with envelope_bus

```python
from envelope_bus import create, get, update_status, append_trace, stats
eid = create(type='TASK', title='...', project='...', appetite_seconds=1800)
update_status(eid, 'RUNNING')
append_trace(eid, {'event': 'worker_started'})
update_status(eid, 'DONE', proof_sha='sha256...')
stats()  # → {total, by_status, timeouts, human_escape_triggered}
```

## Pitfalls

- **auto-claim-and-handoff needs allowlist** — Use `claim` command directly instead (supports `--force`).
- **brain_task_orchestrator list uses `rows` not `tasks`** — `list --json` returns `{"rows":[...]}`.
- **hermes kanban create ID parsing** — output is `Created t_xxxx (ready, assignee=xxx)`. Use `re.search(r'Created\s+(t_[a-f0-9]+)', output)`, NOT `output.split()[-1]`.
- **Cron job model fix** — `hermes cron edit` doesn't support `--model`. Use `cronjob(action='update', ...)` tool. The `last_error` field still shows old errors; fix takes effect on next run.
- **MiMo concurrent empty response** — Must run sequentially: Claude+GPT+DeepSeek concurrent, then MiMo alone.
- **DeepSeek reasoning budget** — reasoning_content shares max_tokens with content. Need max_tokens>=2000 for ratification prompts.
- **Parallel boundary conflicts** — tasks with same `parallel_boundary` cannot run in parallel. Use `boundary-check` to identify conflict groups.
- **Proof artifacts directory** — must create `state/proof_artifacts/` before workers can save proofs.
- **Release requires --force if claimed by controller** — `release TASK_ID` refuses if claimed by non-hermes actor.
- **delegate_task concurrency limit** — default 3 concurrent children; excess queues.
- **Sub-agents have no user interaction** — cannot use clarify inside delegate_task.
- **Worker 不得执行 Markdown task body，不得 mark done** — controller 负责 isolated workdir、diff/boundary review、proof 校验、merge。
- **活跃任务阻断真实并行** — claimed/running/review 的 claim-bound task 存在时，默认 fail-closed。
- **多模型 fanout ≠ real execution permit** — planner quorum 只是 advisory，不能升级为执行许可。
- **Two tasks modifying same file → merge conflict** — use boundary-check to prevent.
- **Each worktree needs its own branch** — `git worktree add` requires a branch argument.
- **Clean up worktrees after DONE/FAILED** — disk space leak.
