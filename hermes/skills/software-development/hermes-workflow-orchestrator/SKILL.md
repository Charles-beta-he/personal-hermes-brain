---
name: hermes-workflow-orchestrator
description: Use when the task falls under Hermes Workflow Orchestrator.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - hermes
    - workflow
    - automation
    - orchestrator
    - pipeline
    related_skills:
    - arc-dispatch-executor
    - loop
    - multi-model-thinking
    - plan
    - requesting-code-review
    - research
    - router
---

# Hermes Workflow Orchestrator

## Recent operational references

- `references/taskpool-pre-ingest-multimodel-triage.md` — pre-ingest multimodel triage for external repo/article intake so tasks enter the pool with P1/P2/P3 already decided.

- `references/multimodel-certified-auto-close.md` — taskpool review→done automation pattern: missing certification triggers certification; PASS/LOOP_DONE proceeds to done; FAIL/inconclusive retries or blocks.
- `references/workflow-patterns.md`

- `references/taskpool-multimodel-auto-done.md` — fail-closed taskpool review→done automation: missing certification triggers multi-model certification; PASS+LOOP_DONE can done; FAIL/not_certified returns retry; advisory_passed is not done authority.
- `references/taskpool-review-closeout-evidence-shape.md` — repair pattern for review/blocked tasks whose multimodel frontmatter is already certified but `auto-close-review` still skips due to stale bare `multimodel_*:...` evidence entries; also documents the source-side fix to emit `command:`-prefixed evidence.

- `references/taskpool-event-hooks.md`
- `references/taskpool-event-hook-rc2-certification.md` — debug `task_added` event-hook `returncode 2` by parsing embedded dispatch JSON; avoid nested certification in hook auto-close. — Hermes/local-brain taskpool pattern: event hooks on add/ingest/transition with cron as fallback, non-recursive bounded dispatch tick, project-scoped autorun policy, and verification steps.
- `references/taskpool-flow-tolerance.md` — procedure for temporarily quarantining Lark taskpool items, tolerating historical done-task proof debt without weakening active gates, creating narrow autorun policies, and verifying dispatch/autorun flow.

## Overview

Hermes 强在纵深持久性（记得你、学习你、随时可达）；Claude Code 强在横向代码能力（LSP/AST 感知、harness 安全层、IDE 集成深度）。两者互补多于竞争。. In practice, load it when the task falls under Hermes Workflow Orchestrator. It defines the expected execution lane, scope boundaries, and verification shape for this class of work.
## When to Use

- 构建外部系统（Lark/Jira/Linear）→ Agent 执行 → 结果写回 的自动化 pipeline
- 需要跨会话记忆、定时执行、多平台通知的工作流
- 需要结合 Hermes 编排能力和 Claude Code 代码能力的场景
- Don't use for: requests that do not need the task falls under Hermes Workflow Orchestrator; choose a more specific child skill or a broader routing skill that actually matches the task.
## 核心架构

```
外部系统（Lark/Jira/GitHub）
    ↓
Collector（拉取任务 + 去重）
    ↓
Confirmer（廉价 LLM 过滤不可执行任务）
    ↓
Executor（hermes chat -q 执行，加载 skills）
    ↓
Validator（审查结果）
    ↓
Reporter（写回外部系统）
    ↓
Orchestrator（串联 + 错误隔离 + 通知）
```

## Hermes 能力集成

### 1. Memory — 跨会话记忆

```python
# 记住项目细节，减少重复上下文注入
memory(action="add", target="memory", content="项目使用 Vue 2 + Vuex + Element UI")
```

效果: executor 不用每次都读缓存，memory 直接注入。

### 2. Gateway — 多平台通知

```python
# 通过 hermes messaging 推送通知
subprocess.run(["hermes", "chat", "-q", "发送通知：任务完成", "--toolsets", "messaging"])
```

效果: Telegram/Discord/Slack 实时推送任务状态。

### 3. Cron — 定时执行

```python
# 注册定时任务
cronjob(action="create", name="workflow", schedule="*/30 * * * *", prompt="执行工作流")
```

效果: 全自动，无需人工干预。

### 4. Session 持久 — 上下文复用

```python
# 同项目复用 session，减少重复上下文
if existing_session:
    cmd = ["hermes", "--resume", session_id, "-q", prompt]
else:
    cmd = ["hermes", "chat", "-q", prompt]
```

效果: 同项目任务共享上下文，不用每次都注入项目信息。

### 5. Session Search — 历史复用

```python
# 搜索历史对话复用方案
subprocess.run(["hermes", "chat", "-q", "搜索类似任务", "--toolsets", "session_search"])
```

效果: 相似任务直接复用历史方案。

### 6. Skills — 领域知识注入

```python
# 按任务类型加载不同 skill
skills = get_skills_for_project(project_id)  # "arc-dispatch-executor,requesting-code-review"
cmd = ["hermes", "chat", "-q", prompt, "-s", skills]
```

效果: 每个任务注入最精准的领域知识。

### 7. Delegate — 并行执行

```python
# 并行执行多条任务
delegate_task(tasks=[
    {"goal": "执行任务A", "context": "..."},
    {"goal": "执行任务B", "context": "..."}
])
```

效果: 多条任务同时执行。

## Hermes + Claude Code 互补

| 维度 | Hermes | Claude Code |
|------|--------|-------------|
| 记忆 | Memory（跨会话） | 无（每次新会话） |
| 可达 | Gateway（多平台） | CLI only |
| 调度 | Cron（定时） | 需外部触发 |
| 代码 | 基本改文件 | LSP/AST 深度感知 |
| 安全 | toolsets 控制 | sandbox 隔离 |
| 执行 | hermes chat -q | claude --print |

**最佳实践**: Hermes 做编排层（调度/记忆/通知），Claude Code 做执行层（改代码/跑测试）。

```python
# Hermes 编排 + Claude Code 执行
executor = {
    "engine": "hermes",  # 编排层
    "executor": "claude",  # 执行层（通过 skill 委派）
    "skills": ["arc-dispatch-executor"],  # 领域知识
}
```

## 关键模式

### Confirmer 模式

用廉价 LLM（如 qwen3-8b）过滤不可执行任务，避免浪费昂贵 LLM 额度。

```python
# 确认可行性（廉价）
plan = call_cheap_llm(task_summary, project_context)
if not plan["understood"]:
    mark_skipped(task)
    notify_user(task, plan["skip_reason"])
    continue

# 执行（昂贵）
result = call_expensive_llm(task, plan)
```

### 自审模式

Executor 执行完后自审，减少单独的 validator LLM 调用。

```python
# executor prompt 增加自审指令
prompt = """
...执行任务...
完成后自审：
- 无硬编码密钥
- 构建通过
- 修改范围正确
输出 JSON verdict: {"verdict": "pass|warn|reject", "summary": "..."}
"""

# validator 只解析 JSON，不再调 LLM
verdict = parse_json_verdict(executor_output)
```

### 重试模式

指数退避重试，防止网络抖动导致任务失败。

```python
@retry_with_backoff(max_attempts=3, base_delay=2.0)
def execute():
    return subprocess.run(cmd, timeout=600)
```

### 错误隔离

每个 envelope 独立处理，单个失败不影响其他任务。

```python
for env in pending:
    try:
        process(env)
    except Exception as e:
        log_error(env, e)
        continue  # 不阻断其他任务
```

## Implementation Steps

1. **Collector**: 拉取外部系统任务 + 去重（SQL O(1)）
2. **Router**: 关键词路由到目标项目
3. **Confirmer**: 廉价 LLM 分析可行性
4. **Executor**: hermes chat -q 执行 + session 持久 + 自审
5. **Validator**: 解析 executor 输出的 JSON verdict
6. **Reporter**: 写回外部系统
7. **Orchestrator**: 串联 + 错误隔离 + 通知 + cron

## Local Brain Task Pool Progress Check

When the user asks to "检查任务池进度" / "check task pool progress", treat the local-brain Markdown task orchestrator as the canonical source unless they explicitly mention an external system like Lark/arc-dispatch.

Run these read-only checks before summarizing:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py list --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py next --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py list --include-done --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
```

Also check the no-agent safe tick cron when available:

```python
cronjob(action="list")  # look for local-brain-task-dispatch-safe-tick
```

Report in Telegram-friendly bullets, not tables: active counts, pending/claimed/running/retry/blocked/expired, stale/expired leases, proof-check failures/warnings, next dispatchable task, claim command, and safe-tick last/next run status. Do **not** claim or execute a task when the user only asks for progress.

When the user explicitly asks to **recover/restore** task-pool dispatch after a stale claim or reconcile gate, use the write path and verify it, rather than only reporting the dry-run blocker:

```bash
# Release expired claimed/running/review leases, then promote due retry tasks if next/dispatch still reports reconcile_required.
python3 ~/.hermes/scripts/brain_task_orchestrator.py reconcile --write --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py reconcile --promote-due-retry --write --json

# Recovery is not complete until these are healthy:
python3 ~/.hermes/scripts/brain_task_orchestrator.py next --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py lifecycle --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write --json
```

Pitfall: `next --json` internally dry-runs due retry promotion with `promote_due_retry=True`, but plain `reconcile --write` does **not** promote retry tasks unless `--promote-due-retry` is passed. If `reconcile --write` reports `action_count=0` while `next` still says `retry_due_promoted`, rerun `reconcile --promote-due-retry --write --json`.

## Local Brain Project Profile Gate

When local-brain/taskpool work can dispatch across multiple projects, every worker-start path must inject a project profile before execution and fail closed when neither the project-specific profile nor `~/.hermes/project-profiles/hermes.json` fallback exists. Use `multi-model-thinking` reference `references/project-profile-injection-pattern.md` for the implementation pattern: row status fields, dispatch/lifecycle/selfcheck gates, TDD fixtures, and autorun/parallel handoff prompt injection.

## Local Brain Autorun / Execution Bridge

When the user asks whether the local-brain task pool lacks automatic dispatch/execution, or asks to implement autonomous task-pool execution, use `references/local-brain-autorun-bridge.md`.

Key rule: safe dispatch and execution are separate. Do **not** convert the no-agent safe tick into a default executor. The safe pattern is a default-off, allowlist-driven `auto-claim-and-handoff` bridge that claims one eligible task and writes a bounded handoff/proof head; an external bounded runner may execute, and completion must still pass proof-gated `review -> done`. Never execute Markdown task bodies or mark `done` directly from a tick.

### When the user says "全盘推进" / "push the whole pool forward"

Treat this as a bounded advancement request, not permission to force-close the queue.

1. Read current health first:
   ```bash
   python3 ~/.hermes/scripts/brain_task_orchestrator.py list --include-done --json
   python3 ~/.hermes/scripts/brain_task_orchestrator.py next --json
   python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json
   python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
   ```
2. Attempt the normal bounded automation path:
   ```bash
   python3 ~/.hermes/scripts/brain_task_orchestrator.py autorun-runner --actor hermes --ttl-minutes 60 --json
   python3 ~/.hermes/scripts/brain_task_orchestrator.py auto-claim-and-handoff --actor hermes --ttl-minutes 60 --json
   python3 ~/.hermes/scripts/multimodel_intervention_dynamic_step.py --json
   ```
3. If both runner and handoff return `eligible=false` with reason `autorun_disabled`, do **not** stop at reporting. Manually advance one smallest verifiable slice on the highest-value dispatchable task: `claim` it, reconcile/read the task note, perform one bounded audit or evidence-writing step, write proof back to the note, then `release` it to the appropriate non-terminal state.
4. Re-measure immediately after the manual slice using `list --include-done --json`, `next --json`, and `selfcheck --json`. Report the delta, not just the latest snapshot: blocked count movement, done count movement, active count movement, and what specifically advanced.

Key interpretation rules during this pass:
- `PASS_ADVISORY_ONLY` is progress but **not** closeout authority; advisory-completed tasks still need a real execution/evidence pass.
- `economy_gate.action=pause` with messages like `task has 10 failed T3 rounds (max=5)` is a fail-closed pause, not a dead worker. Report it as a targeted evidence/human-review gate.
- If active dispatchable work remains while blocked count falls or done count rises, conclude the pool is advancing even if autorun is disabled.
- If a task shows current multimodel state `certified / PASS / LOOP_DONE` but `auto-close-review` or review closeout still skips, inspect the `evidence:` list for stale bare `multimodel_*:...` entries. Normalize/remove them before retrying closeout, and if the orchestrator is the writer, patch it to emit `command:`-prefixed evidence at source to prevent repeated poisoning.

When adding a local-brain task from an external idea artifact such as an image/social-post screenshot, treat it as task creation plus evidence deposition, not as implementation closeout. The task note should include source artifact path, analysis/tick artifacts, certification status, P0/P1/P2 plan, and explicit caveats if multi-model discussion is `not_certified`. If the artifact is a local app-cache image (for example a Lark `sdk_storage/.../resources/images/*.jpg` path), first copy it into a canonical vault evidence folder such as `~/Documents/brain/05-实践与项目/projects/<project>/evidence/screenshots/`, write a sidecar JSON with original path, copied path, sha256, byte size, and observed issue, then reference the canonical copy in the task frontmatter `evidence:` list and body. Enrich the generated task note with screenshot-derived problem statement, verification questions, execution notes, and acceptance criteria; do not leave the auto-generated skeleton as the only context for an executor. After creating or patching the task, regenerate derived dashboards and run `dashboard --write`, `proof-check`, `selfcheck`, `dispatch-dry-run`, `taskpool_watch_report.py`, `brainctl sync`, and `brainctl reindex` to verify the taskpool remains healthy. If `brainctl search` returns no hits for the new task, do not treat that as creation failure; verify via `brain_task_orchestrator.py list --json` and direct `read_file` on the task note, because FTS can lag or over-constrain mixed Chinese/English terms.

### Work delivery vs self-evolution routing

When補入任务池 or scheduling autorun, explicitly classify the task as one of:
- `work/product delivery`: user/project/Lark/PRD/customer-facing delivery, blocker repair, closeout follow-up.
- `evolution/self-improvement`: Hermes skills, router, cron, eval, governance, framework analysis.
- `advisory/research`: evidence-gathering or analysis that may later spawn implementation work.

For `work/product delivery`, set project/workspace/concepts so it cannot be mistaken for Hermes evolution (for example `concepts: work-task,uvisa,lark,backend,product-closeout`), prefer P0/P1 when it is a returned blocker, and ensure the next dispatchable task reflects that priority. Do not let open-ended self-evolution tasks starve P0/P1 work. After adding the note, run:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json
python3 ~/.hermes/scripts/taskpool_watch_report.py
python3 ~/.hermes/scripts/brainctl.py --json sync && python3 ~/.hermes/scripts/brainctl.py --json reindex
```

Report the next executor cron (`local-brain-taskpool-auto-completer`) and occasional report cron times. If a work task is now first in `dispatch-dry-run`, say so explicitly.

## Local Brain Idle Runner / Risk Router

When adding or reviewing local-brain idle/autorun/background runner logic, use `references/local-brain-idle-runner-risk-router.md`. Key rule: idle detection is a read-only control-plane classifier, not an executor. It must fail closed on claim-bound lifecycle states (`claimed`, `running`, `review`) and on partial lease metadata (`claimed_by`, `claim_expires_at`, `run_id`), merging from frontmatter if the list-row API omits a field.

## Local Brain Task Boundaries / Parallel Agents

When the user asks whether the task pool can add task boundaries, scoped execution, or multi-agent parallel processing, use `references/local-brain-task-boundary-parallel-agents.md`. Key rule: land schema and deterministic validators first, then read-only parallel dry-run, then claim/handoff, and only later worktree-isolated execution plus serial merge queue. Legacy serial tasks remain compatible, but write-capable parallel dispatch must fail closed without valid boundary metadata. Markdown task bodies remain data, never scripts; workers cannot directly mark `done`; P0/P1 work tasks must not be starved by evolution/self-improvement tasks.

## PA Evolution Report Cron Pattern

When a scheduled job asks to run the personal-assistant self-evolution trigger and daily report:

1. Run both scripts:
   ```bash
   python3 ~/.hermes/scripts/pa-evolution-trigger.py
   python3 ~/.hermes/scripts/pa-daily-report.py
   ```
2. Read the newest `~/.hermes/notes/reports/pa-daily-*.md`.
3. Extract: date/time, today's sessions, `V_PA`, `V̇_PA`, learned task patterns, and PA level.
4. Check degradation: `V̇_PA < -0.05` is the significant regression threshold. If below threshold, inspect `~/.hermes/notes/engineering-cybernetics/pa-health-history.jsonl` and `health-history.jsonl` for root cause; otherwise record that no degradation alert fired.
5. If `skill_solidify` fires, verify the underlying `task_type` before creating a skill:
   - Read `~/.hermes/notes/user-routine-patterns.json`.
   - Inspect recent records in `~/.hermes/notes/engineering-cybernetics/health-history.jsonl`.
   - Count recent `task_type` values.
   - Only create/update a skill if the repeated task type represents a real reusable workflow.
6. Respect cron delivery gating. If the prompt says to suppress routine/no-news output and the run has no trigger actions, no degradation (`V̇_PA >= -0.05`), no verified `skill_solidify`, and metrics are flat/routine (for example `V̇_PA = +0.0000`), final response should be exactly `[SILENT]`. Do **not** send a normal summary merely because the scripts ran successfully or because a daily report file was generated; routine success is still silence. Produce a normal report only when there is an alert, a non-routine metric change, a verified skill opportunity, or an execution failure.
7. Distinguish **current-run triggers** from **historical trigger logs**:
   - Read `~/.hermes/notes/engineering-cybernetics/pa-trigger-log.jsonl` only as context.
   - If the current trigger run reports no `skill_solidify`, do not revive an old `skill_solidify` entry as if it fired today.
   - Historical entries are useful for background assessment (for example, deciding whether a repeated `unknown` task type is worth fixing at the classification layer), but they do not by themselves justify breaking `[SILENT]`.

Useful diagnostic snippet:

```bash
python3 - <<'PY'
import json, datetime
from pathlib import Path
from collections import Counter
health = Path.home()/'.hermes/notes/engineering-cybernetics/health-history.jsonl'
cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
records=[]
for line in health.read_text().splitlines():
    if not line.strip():
        continue
    rec=json.loads(line)
    ts=datetime.datetime.fromisoformat(rec['timestamp'])
    if ts > cutoff:
        records.append(rec)
print('recent_health_records', len(records))
print('task_type_counts', dict(Counter(r.get('task_type','unknown') for r in records)))
for r in records:
    if r.get('task_type','unknown') == 'unknown':
        print('-', r['timestamp'], 'keys=', ','.join(r.keys()), 'V=', r.get('V'), 'V_dot=', r.get('V_dot'))
PY
```

## Common Pitfalls

- Omitting `capability_delta`, `anti_drift_check`, or `acceptance_evidence` when adding an `evolution` task.
- Treating `task_added` event-hook `returncode=2` as task creation failure before checking `created` and `derived_refresh`.
- Forgetting to verify queue placement in `list --json` or `任务池-排序.md` after batch additions.


- **Synchronous delegation blocks cron**: An orchestrator that calls `hermes chat -q` (or any long-running worker) inside its main loop will hang and never complete within cron timeouts. The `agent_team_controller.py cycle` hit this repeatedly — it claims tasks, creates envelopes, then synchronously delegates workers with 300-600s timeouts per task, causing cron to time out while PENDING envelopes accumulate. **Fix**: split into a fast claim/enqueue phase (returns in <5s) and a separate background execute phase. The claim phase should only create envelopes and write them to a queue; a separate process or background thread dequeues and delegates. See `references/agent-team-controller-timeout-pattern.md`.
- **Token 过期**: 外部系统 token 需要自动刷新机制
- **Token 过期**: 外部系统 token 需要自动刷新机制
- **JSON 解析**: LLM 输出可能包含额外内容，需要 robust 的 JSON 提取（从最后一行开始找）
- **无限重试**: validator reject 需要计数器限制最大重试次数
- **Schema 迁移**: SQLite 新增字段需要重建表（ALTER TABLE 不支持 CHECK 约束修改）
- **Session 复用**: hermes --resume 需要正确的 session_id 管理
- **SKIPPED vs FAILED**: 不可执行任务用 SKIPPED（可通知），执行失败用 FAILED
1. Skipping prerequisite checks and assuming the environment already matches the workflow.
2. Applying the workflow mechanically without confirming that the request still matches this skill's trigger class.
3. Reporting success before reading back the actual outputs, files, or external side-effects.
## Definition of Done

- [ ] **Outcome**: 完整 pipeline 可运行，任务从采集到写回全流程打通
- [ ] **Process**: Collector→Router→Confirmer→Executor→Validator→Reporter 各模块独立可测
- [ ] **Style**: 错误隔离、重试机制、通知机制、状态追踪完整
- [ ] **Efficiency**: Session 复用减少上下文注入、自审减少 LLM 调用、SQL 去重 O(1)

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] The Definition of Done items above were explicitly checked, not assumed.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

