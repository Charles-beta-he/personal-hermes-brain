---
name: hermes-pipeline
description: "Build automated task pipelines using hermes chat -q as execution engine. Compose hermes skills (confirmer, executor, validator) into multi-stage workflows with SQLite envelope bus, error isolation, and Lark/webhook integration."
license: MIT
tags: [pipeline, automation, hermes, orchestration, task-dispatch]
---

# Hermes Pipeline — Agent 执行引擎

> 用 hermes chat -q 构建自动化任务流水线，skills 作为 pipeline 组件。

## When to Use

- 构建无人值守任务调度系统（Lark/Jira/GitHub Issues → 自动执行 → 结果写回）
- 需要多阶段验证的自动化流程（确认 → 执行 → 审查 → 报告）
- 用 hermes skills 作为 pipeline 组件（如 requesting-code-review 做 validator）

## 核心模式：Envelope Bus + Hermes Executor

```
任务源 → collector → confirmer(hermes) → executor(hermes) → validator(hermes) → reporter
                        ↓                    ↓                    ↓
                    SKIPPED+通知          DONE+output         pass/warn/reject
```

### 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 执行引擎 | `hermes chat -q` | 完整 tool calling + skill 加载 + 多 provider |
| 确认模型 | hermes chat -q (Claude) | 准确性优先于成本 |
| 审查工具 | requesting-code-review skill | 复用已有 review pipeline |
| 状态存储 | SQLite envelope bus | 并发安全 + 查询能力 |
| 不可执行任务 | SKIPPED + 通知 | 非 FAILED，保留重试能力 |

## Implementation Pattern

### 1. Executor: hermes chat -q 替代直接 API 调用

```python
def execute_one(envelope):
    prompt = _build_prompt(envelope)
    cmd = [
        "hermes", "chat", "-q", prompt,
        "-s", "requesting-code-review",  # 加载 skill
        "--toolsets", "terminal,file",    # 只给需要的工具
    ]
    result = subprocess.run(cmd, cwd=project_path, timeout=600,
                            env={**os.environ, "HERMES_NO_BANNER": "1"})
    return result.stdout
```

### 2. Confirmer: 任务可行性分析

```python
def confirm(envelope):
    # hermes chat -q 做任务分析，输出 JSON
    raw = subprocess.run(["hermes", "chat", "-q", prompt, "--toolsets", "none"], ...)
    plan = extract_json(raw.stdout)
    
    if not plan["understood"]:
        # SKIPPED（非 FAILED）+ 发送通知
        db.update_status(eid, "SKIPPED")
        subprocess.run(["hermes", "chat", "-q", f"发送通知：{skip_reason}"], ...)
        return None
    return plan
```

### 3. Validator: 独立代码审查

```python
def validate(envelope):
    # 用 requesting-code-review skill 做 diff review
    verdict = subprocess.run([
        "hermes", "chat", "-q", review_prompt,
        "-s", "requesting-code-review",
    ], cwd=project_path, ...)
    
    if verdict == "reject":
        db.update_status(eid, "PENDING")  # 重置重试
```

### 4. Orchestrator: 错误隔离

```python
def run_full():
    for step in [collect, confirm, execute, validate, report]:
        try:
            step()
        except Exception as e:
            print(f"[{step.__name__} ERROR] {e}")
            # 不阻断后续步骤
```

## Environment Variables

```
ARC_HERMES_CMD=hermes                    # hermes 命令路径
ARC_EXECUTOR_SKILLS=requesting-code-review  # executor 加载的 skills
ARC_EXECUTOR_TOOLSETS=terminal,file      # executor 工具集
ARC_EXECUTOR_TIMEOUT=600                 # executor 超时
ARC_VALIDATOR_TIMEOUT=120                # validator 超时
ARC_CONFIRM_TIMEOUT=60                   # confirmer 超时
LARK_APP_ID=cli_xxx                      # Lark App ID (token 刷新)
LARK_APP_SECRET=xxx                      # Lark App Secret (token 刷新)
```

## Envelope Data Model

```sql
CREATE TABLE envelopes (
    id          TEXT PRIMARY KEY,
    type        TEXT CHECK(type IN ('TASK','PLAN','RESULT','VALIDATION')),
    status      TEXT CHECK(status IN ('PENDING','RUNNING','DONE','FAILED','SKIPPED')),
    project     TEXT,              -- executor cwd
    payload     TEXT,              -- JSON: task + 各步骤产出
    trace       TEXT,              -- JSON array: 每步事件
    error       TEXT,
    created_at  TEXT,
    updated_at  TEXT
);
```

payload 关键字段:
```
lark_task_guid    任务 ID
summary           任务标题
description       详情
comments          评论区补充（文档链接等）
project_id        路由结果
confirm_plan      confirmer 输出
executor_output   executor 输出
validation        validator 结果
```

## Status Flow

```
PENDING → confirmer → PENDING (confirmed)
                    → SKIPPED (understood=false, 发送通知)
PENDING → executor → RUNNING → DONE
                              → FAILED (timeout/error)
DONE → validator → DONE (pass/warn)
                 → PENDING (reject, 重试)
DONE → reporter → DONE (已上报标记)
```

## Lark Token Auto-Refresh

```python
def _get_token():
    # 读取 token
    if expired:
        subprocess.run([
            "npx", "@larksuiteoapi/lark-mcp", "login",
            "--app-id", os.environ.get("LARK_APP_ID"),
            "--app-secret", os.environ.get("LARK_APP_SECRET"),
        ])
        # 重新读取
    return token
```

## Advanced Patterns (from arc-dispatch production)

### Retry with Exponential Backoff

```python
def retry_with_backoff(max_attempts=3, base_delay=1.0, max_delay=30.0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        time.sleep(delay)
                    else:
                        raise
        return wrapper
    return decorator

@retry_with_backoff(max_attempts=3, base_delay=2.0)
def run_hermes():
    return subprocess.run(cmd, timeout=600)
```

### Validator Retry Counter (prevent infinite loops)

```python
def validate_and_handle(envelope, verdict):
    if verdict["verdict"] == "reject":
        retry_count = envelope["payload"].get("retry_count", 0)
        max_retries = 2

        if retry_count >= max_retries:
            db.update_status(eid, "FAILED", error=f"rejected after {max_retries} retries")
        else:
            new_payload = {**envelope["payload"], "retry_count": retry_count + 1}
            db.set_payload(eid, new_payload)
            db.update_status(eid, "PENDING")
```

### Confirm Skip Logic (don't re-analyze)

```python
def confirm_all():
    pending = db.list_pending(type="TASK")
    need_confirm = [e for e in pending if not e["payload"].get("confirm_plan")]
    already_confirmed = [e for e in pending if e["payload"].get("confirm_plan")]
    # Only analyze tasks without confirm_plan
    for env in need_confirm:
        confirm(env)
    return already_confirmed + newly_confirmed
```

### Shared Auth Module

Extract duplicate auth code (e.g., Lark token) into single module:

```python
# lark_auth.py — shared by collector and reporter
def get_token():
    token = read_from_store()
    if expired:
        refresh()
        token = read_from_store()
    return token

# collector.py / reporter.py
import lark_auth
def _get_token():
    return lark_auth.get_token()
```

### DB Query Helpers

```python
def list_by_status(status, type=None, limit=100):
    """List envelopes by status, optionally filtered by type."""
    ...

def count_by_status():
    """Count envelopes by status. Returns {status: count} dict."""
    ...
```

## Unit Testing Pattern

Test each module with temporary SQLite:

```python
import tempfile
from pathlib import Path

def test_db_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        db.DB_PATH = Path(tmpdir) / "test.db"
        env = db.create(type="TASK", project="/tmp/test", payload={})
        assert db.get(env["id"])["status"] == "PENDING"

def test_confirm_skip():
    with tempfile.TemporaryDirectory() as tmpdir:
        db.DB_PATH = Path(tmpdir) / "test.db"
        env = db.create(type="TASK", project="/tmp/test",
                        payload={"confirm_plan": {"action": "fix"}})
        confirmed, skipped = confirmer.confirm_all(dry_run=True)
        assert len(confirmed) == 1  # pre-confirmed task included
```

Minimum test coverage: db CRUD, router matching, confirm skip, retry counter.

## Plan B/C/D Optimization Pattern

Three optimizations that reduce LLM calls and improve quality:

### Plan B: Skill Encapsulation

Create domain-specific skill for executor:

```markdown
# ~/.hermes/skills/software-development/my-executor/SKILL.md
## Steps: understand → locate → modify → verify → self-review → output verdict
## Definition of Done
```

Executor loads skill dynamically:
```python
skills = skill_map.get_skills_for_project(project_id)
cmd = [hermes, "chat", "-q", prompt, "-s", skills]
```

### Plan C: Self-Review in Executor (saves 1 LLM call/task)

Executor includes self-review and outputs JSON verdict:

```python
prompt = """
...task instructions...
## Self-review
1. Check git diff for security issues
2. Verify build passes
3. Output JSON verdict on LAST line:
   {"verdict": "pass|warn|reject", "summary": "...", "files_changed": [...]}
"""
```

Validator parses output instead of separate LLM call:
```python
verdict = _parse_verdict(executor_output)  # No hermes call needed
```

### Plan D: Session Persistence (reduce context re-injection)

Reuse hermes session across tasks in same project:

```python
SESSIONS_FILE = ~/.arc-dispatch/sessions.json  # {project_id: session_id}

existing_session = _get_session(project_id)
if existing_session:
    cmd = [hermes, "--resume", existing_session, "-q", prompt, ...]
else:
    cmd = [hermes, "chat", "-q", prompt, ...]
    # Save session ID after success
    _set_session(project_id, new_session_id)
```

## Hermes Feature Integration

### Memory — Cross-session project knowledge

```python
memory(action="add", target="memory", content="project uses Vue 2 + Vuex...")
```

Injected every turn. Executor doesn't re-read context.

### Gateway Notifications — Real-time updates

```python
notify.notify_task_completed(summary, project_id, files_changed)
notify.notify_task_failed(summary, project_id, error)
notify.notify_round_summary(db.count_by_status())
```

### Cron — Fully unattended

```bash
hermes cron create "*/30 * * * *" --name "pipeline" --prompt "run pipeline"
```

### Session Search — Reuse historical solutions

```python
similar = session_search.search_similar_tasks(f"{project_id} {task_summary}")
if similar:
    parts.append(f"## Historical Reference\n{similar[0]['content'][:300]}")
```

### Skill Map — Dynamic skill loading per project

```python
PROJECT_SKILLS = {
    "web_ui": "vue2-element-skill",
    "uaec_h5": "vue2-vant-skill",
    "partner_ui": "react-umi-skill",
}
skills = skill_map.get_skills_for_project(project_id)
```

### Delegate — Parallel execution

```python
delegate_task(tasks=[
    {goal: "execute web-ui task", context: "..."},
    {goal: "execute uaec-h5 task", context: "..."}
])
```

## Hybrid Execution Mode

Step-by-step with P10 audit between steps:

```
Step 1: Collect → report → user confirms
Step 2: Confirm → report → user confirms
Step 3: Execute --limit 1 → report → user confirms
Step 4: Validate → report → user confirms
Step 5: Report → done
```

Or fully automated via cron.

## Full Auto-Trigger Chain (4-Model Certified 2026-05-11)

```
orchestrator.list (brain_task_orchestrator.py)
    ↓ cron: pipeline-tick-hourly
pipeline_tick.py (create PENDING envelopes from dispatchable tasks)
    ↓ cron: envelope-executor-cycle (every 30m)
envelope_executor.py (PENDING → claim → delegate to worker → DONE/BLOCKED/RETRY)
    ↓ cron: brain-kanban-bridge-sync (every 2h)
kanban_bridge.py (one-way mirror to Kanban for observability)
    ↓ cron: v-state-hourly
v_state.py (V(x) health score, alert if < 0.7)
```

Supporting crons:
- `agent-team-cycle-hourly` — dynamic N controller (claims tasks, conflict group scheduling)
- `orchestrator-selfcheck-6h` — brain_task_orchestrator.py selfcheck
- `memory-selfcheck-6h` — agent_memory_architecture_selfcheck.py

## V(x) State Function

System health score `V(x) = Σ wᵢ·fᵢ(xᵢ) ∈ [0,1]`. See `references/v-state-function.md`.

## Dynamic N + Task Classifier

Adaptive parallelism: `N = min(ceil(dispatchable/7), conflict_groups, 3)` with smoothing. See `references/dynamic-n-and-classifier.md`.

## Task Continuation (Budget Exhaustion Resume)

When worker hits "Iteration budget reached (60/60)", checkpoint progress and resume with injected context. Max 3 continuations. See `references/task-continuation-pattern.md`.

## Envelope Executor (The Missing Link)

Pipeline_tick creates PENDING envelopes but doesn't execute them. The executor consumes them. See `references/envelope-executor-missing-link.md`.

## Numeric Guardrails (4-Model Certified)

When using hermes-pipeline for autonomous/long-running execution, enforce these numeric bounds:

| Parameter | Default | Configurable | Purpose |
|-----------|---------|-------------|---------|
| appetite_timeout | 30min | 15/60/120min per task type | Shape Up time budget per task |
| max_retry | 3 | - | After 3 failures: escalate + block |
| human_escape | 2 block OR 3 crash | - | Auto-pause pipeline + notify user |
| max_runtime | 3600s/task | - | Single task max execution time |
| lease_ttl | 900s | - | Worker claim validity |
| heartbeat_interval | 120s | - | Worker heartbeat frequency |
| state_source | SQLite envelope bus | - | Single source of truth, cron triggers tick only |
| OKR↔proof | sha256 artifact | - | Each KR must link to envelope DONE proof |

These guardrails were 4-model certified (Claude + GPT-5.5 + DeepSeek + MiMo) on 2026-05-10. See `references/numeric-guardrails.md` in the multi-model-thinking skill for the full ratification artifact path.

## Self-Optimizing Verification Loop

When `verify_with_models` rejects a task, the system enters a self-improving loop:

1. `save_rejection()` — record rejection history
2. `analyze_rejection()` — detect patterns (missing_build/test/screenshot/evidence)
3. `generate_enhanced_criteria()` — expand acceptance 4→8 criteria
4. `update_project_profile()` — auto-learn rules into project profile
5. Retry with enhanced criteria (max 3 attempts)

Safety: no scope expansion, intent preservation, 3 failures → human escalation.

Full implementation: see multi-model-thinking skill `references/self-optimizing-verification-loop.md`.

## Capability Routing

Route tasks to appropriate models by type:

```python
needs_code = any(kw in title.lower() for kw in ['修复', 'fix', '实现', '代码', 'uvisa'])
model = 'gpt-5.5' if needs_code else 'mimo-v2.5-pro'
provider = 'openai-codex' if needs_code else 'xiaomi'
max_turns = 30 if needs_code else 15
timeout = 600 if needs_code else 300
```

## Pitfalls

- **hermes chat -q 比直接 API 调用慢** — 但获得完整 tool calling + skill 加载
- **Programmatic JSON 需要 quiet mode** — confirmer/validator 解析 JSON 时使用 `-Q`/`HERMES_NO_BANNER=1` 抑制 banner；不要使用未知 CLI 参数（例如旧版 `--toolsets none` 会输出 warning 并污染 JSON）。仍需用 robust extractor 从 mixed stdout 中取 JSON。
- **只保存真实 Hermes session id** — `--resume` 必须使用 Hermes 真实 session id；禁止按时间戳伪造 `arc-{project}-{ts}`。首轮用稳定 `--source` tag，之后从 stdout/stderr 或 `hermes sessions list --source <tag>` 提取真实 id，提取失败就不 resume。
- **Backpressure 要贯穿所有阶段** — pipeline 的 `--limit` 不应只限制 execute；confirm/execute/full 都要支持同一 limit，且 limit 只裁剪"需要新处理"的任务，不隐藏 already-confirmed/validated 的既有状态。
- **状态必须反映最终验证结果** — executor 可先临时写 DONE 以保存 output，但 build failure、auto-fix failure、browser harness critical issues 必须最终覆盖为 FAILED；避免通知失败/验证失败后留下假 DONE。
- **为边界状态写回归测试** — 覆盖 build result 缺少 `error` 但有 `output`、browser harness critical→FAILED、mixed Hermes JSON、真实 session id 提取、confirm limit 等容易在无人值守 loop 中变成 silent failure 的路径。
- **Git hygiene: pycache 可能已被跟踪** — 添加 `.gitignore` 不会停止跟踪已入库 `__pycache__/*.pyc`；用 `git ls-files '*__pycache__*' '*.pyc'` 检查，必要时 `git rm --cached` 或删除并 commit 清理，验证前后都看 `git status --short`。
- **SKIPPED vs FAILED** — 不可执行任务用 SKIPPED，保留重试能力，通过通知让用户知晓
- **错误隔离** — 每个步骤独立 try-catch，单个 envelope 失败不阻断其他
- **Python 3.9 兼容** — 加 `from __future__ import annotations`，用 `Optional[dict]` 或 `dict | None`（需 future annotations）
- **Comments API 404** — Lark 评论 API 可能需要额外权限，降级处理返回空列表
- **token 过期** — 自动刷新需要 LARK_APP_ID/LARK_APP_SECRET 环境变量
- **无限重试** — validator reject 必须加 retry_count + max_retries 限制
- **confirm 重复分析** — 过滤已有 confirm_plan 的任务，只分析新任务
- **共享代码** — 认证等重复逻辑提取到共享模块，不要 copy-paste
- **Claim-delegate 死锁** — controller 如果只 claim 不 delegate，任务会永远卡在 claimed 状态。正确做法是 claim 后立即 delegate（在同一 cycle 内），或者让 envelope_executor 消费 PENDING envelopes。executor 用 `hermes chat -q` 跑 worker 时如果太重（max_turns=60, 600s timeout），会超时导致 envelope 卡在 RUNNING。轻量化 worker: max_turns=15, MiMo 模型, 300s timeout。详见 multi-model-thinking skill 的 `references/task-flow-deadlock-detection-and-fix.md`。
- **brain_task_orchestrator list 输出用 `rows` 不是 `tasks`** — `list --json` 返回 `{"rows":[...]}` 不是 `{"tasks":[...]}`，读取时用 `data.get('rows', [])`。
- **hermes cron edit 不支持 --model** — 改 cron job 的 model/provider 用 `cronjob(action='update')` 工具，不是 `hermes cron edit`。修改后 last_error 仍是历史记录，下次运行才生效。
- **hermes kanban create 输出格式** — `Created t_xxxx (ready, assignee=xxx)`，提取 ID 用 `re.search(r'Created\s+(t_[a-f0-9]+)', output)`。
- **envelope bus + pipeline tick 详见** `references/envelope-bus-implementation.md`。
- **brain_task_orchestrator 集成模式详见** `references/brain-task-orchestrator-integration.md`。
- **envelope_executor 是 PENDING envelope 的消费者** — pipeline_tick 创建 envelope，executor 消费它们。详见 `references/envelope-executor-missing-link.md`。
- **Never run long pipeline scripts synchronously** — scripts that delegate to `hermes chat -q` (envelope_executor, brain_task_orchestrator) can take 600s+ per envelope. The agent terminal times out at 60-300s. Always use `background=True, notify_on_complete=True` and poll for completion.
- **完整自动触发链路** — orchestrator→pipeline_tick→envelope_executor→kanban_bridge，通过 cron 连接。pipeline-tick-hourly 创建，envelope-executor-cycle(30m) 消费，brain-kanban-bridge-sync(2h) 镜像，v-state-hourly 监控健康度。
