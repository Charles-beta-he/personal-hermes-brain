---
name: arc-dispatch-executor
description: "arc-dispatch 任务执行规范 — Lark 任务自动执行的最佳实践。当 executor 派发前端开发任务时加载此 skill。"
license: MIT
tags: [arc-dispatch, automation, frontend, vue, react]
---

# arc-dispatch 任务执行规范

> 你是一个前端代码执行 agent，由 arc-dispatch 自动调度。严格按以下流程执行任务。

## When to Use

由 arc-dispatch executor 自动加载。不需手动触发。

## 执行流程

### Step 1: 理解任务

1. 阅读任务摘要、详情、评论区补充
2. 阅读 confirmer 计划（action/scope/risk/execution_hint）
3. 阅读项目上下文（scanner 缓存的目录结构 + 框架信息）
4. 如有 reference_path（如 android 参考），仅作行为参考，不修改

### Step 2: 定位修改范围

根据 confirmer 的 scope 字段定位目标文件：
- Vue 2 项目: `src/pages/`, `src/views/`, `src/components/`
- React 项目: `src/pages/`, `src/models/`
- 仅修改 scope 中指定的文件，不做范围外改动

### Step 3: 执行修改

1. 阅读目标文件，理解现有代码结构
2. 做最小改动实现需求
3. 遵循项目现有代码风格（缩进、命名、组件模式）
4. 不引入新依赖（除非任务明确要求）

### Step 4: 验证

执行以下验证，全部通过才算完成：

```bash
# 1. 语法检查
# Vue: 检查 template/script 是否有语法错误
# React: 检查 JSX/TSX 语法

# 2. 构建验证（必须）
npm run build   # 或 yarn build / pnpm build

# 3. 如果项目有测试
npm test        # 或 yarn test
```

**关键规则**: 构建失败 = 任务未完成。修复构建错误后重新验证。

### Step 5: 自审

检查 git diff，确认：
- [ ] 无硬编码密钥/密码/token
- [ ] 无 debug 代码（console.log, debugger）
- [ ] 修改范围不超过 confirmer scope
- [ ] 构建通过
- [ ] 遵循项目代码风格

### Step 6: 输出结果

在最后一行输出 JSON 格式的执行结果：

```json
{"verdict": "pass", "summary": "完成 xxx 修改，构建通过", "files_changed": ["src/pages/xxx.vue"]}
```

verdict 含义:
- `pass`: 任务完成，构建通过
- `warn`: 任务完成但有警告（如无法运行测试）
- `reject`: 无法完成（依赖缺失、需求不清等）

## 禁止行为

- ❌ 不修改 scope 之外的文件
- ❌ 不引入新依赖（除非任务明确要求）
- ❌ 不删除现有功能代码
- ❌ 不跳过构建验证
- ❌ 不提交代码（由 arc-dispatch 统一管理）

## Framework Quick Reference

### Vue 2 + Vant (uaec-h5)
- UI库: Vant 2.x
- 样式: scoped CSS / SCSS
- 状态: Vuex
- 路由: vue-router
- API: homeRanking (type: POPULAR_RANKING/GO_UP_RANKING/TO_FALL_RANKING/NEW_COIN_RANKING/VOL_RANKING)
- WebSocket: connect + subscribe/cancel 模式

### Vue 2 + Element UI (web-ui)
- UI库: Element UI
- 样式: scoped CSS
- 状态: Vuex
- 路由: vue-router

### React + Umi + DVA (partner-ui, excloud-ui)
- 框架: Umi 2 + DVA
- UI库: Ant Design
- 状态: DVA models (dispatch with namespace prefix)
- 路由: convention-based + config/router.config.js

### Android (uaec-android) - 仅参考
- 语言: Java/Kotlin
- 网络: OkHttp
- WebSocket: WsManager
- 布局: XML + RecyclerView
- 参考用途: API 调用参数、UI 结构、WebSocket 订阅模式

## Lark Integration Patterns

### Comment Link Extraction
When processing tasks, comments may contain:
- Figma design links (figma.com)
- Screenshot URLs (img.*, cdn.*, oss.*)
- API documentation links

Extract and analyze these links before execution. If Figma link is present, the task may need design mockup analysis.

### Token Auto-Refresh
Lark tokens expire. Use lark_auth module to auto-refresh:
```python
import lark_auth
token = lark_auth.get_token()  # Auto-refreshes if expired
```

## Design Analysis (for tasks with screenshots)

If task comments contain screenshot/design links:
1. Use `browser_vision` to analyze the screenshot
2. Extract: layout, colors, spacing, component types
3. Inject analysis into executor prompt as "设计稿分析"
4. Follow the design as reference, not exact pixel match

## Database Migration (for schema changes)

When adding new status values (e.g., SKIPPED) to existing SQLite:
```sql
CREATE TABLE envelopes_new (... new schema ...);
INSERT INTO envelopes_new SELECT * FROM envelopes;
DROP TABLE envelopes;
ALTER TABLE envelopes_new RENAME TO envelopes;
```

## Session Context

Executor reuses hermes session per project (via --resume). First task creates session, subsequent tasks resume it. Reduces redundant context injection.

## Self-Review Output

Executor must output JSON verdict on LAST line:
```json
{"verdict": "pass|warn|reject", "summary": "...", "files_changed": ["path/to/file"]}
```

This allows validator to parse verdict without separate LLM call.

## Optimization Trade-off Analysis (Plan B/C/D)

When evaluating pipeline optimizations, apply "拒绝丢失功能与精准度" principle:

| Plan | Change | Lose Functionality? | Lose Precision? | Safe? |
|------|--------|---------------------|-----------------|-------|
| A | Merge confirmer+executor | YES (lose early filtering) | NO | ❌ |
| B | Create skill for executor | NO (additive) | NO | ✅ |
| C | Executor self-review | NO (review still independent via skill) | NO | ✅ |
| D | Session persistence | NO (additive) | NO | ✅ |

**Rule**: Only execute plans that are pure additions (no removal of existing capability).

## Definition of Done

- [ ] **Outcome**: 任务功能实现，构建通过，无已知 bug
- [ ] **Endpoint semantics / same credential surface**: 对登录后设置的 PIN、支付密码、2FA、设备等安全类任务，必须追踪“设置 → 校验 → 修改”是否写读同一后端字段/服务。不要只按 UI 文案选择 endpoint；若用户文案叫“支付密码”但后端真实模型是 payment PIN，则 exchange/rebind/change 都必须保持同一 `/pin/*` surface。参考 `references/uvisa-payment-pin-surface.md`。
- [ ] **Token-issuing path parity**: 对 auth/session/device/PIN-skip 类任务，必须枚举所有前端可签发/消费 AuthToken 的路径（OTP `/auth/login`、legacy `/auth/verify`、password `/auth/login-with-password`、必要时 refresh），逐一确认后端路由存在且返回同一安全契约字段。不要因为主 OTP path PASS 就 closeout；例如 trusted-device persistence 需要 password-login path 同样返回 backend source-of-truth `currentDeviceTrusted`。参考 `references/uvisa-auth-token-issuing-paths.md`。
- [ ] **Auth failure rate-limit semantics**: 对登录/OTP/PIN/支付密码错误次数、锁定提示类任务，计数点必须跟具体失败原因一致，不要把 endpoint 调用次数当成错误次数。例如 password-login 锁定只应在后端确认 `PASSWORD_INVALID` 后触发 `login:password:email` rate-limit；成功登录、账号不存在、冻结等不应消耗“密码错误”次数。前端 `auth.loginPwd.rateLimited` 必须使用任务要求的锁定文案，不复用通用请求限流文案。参考 `references/uvisa-auth-rate-limit-semantics.md`。
- [ ] **Backend-aware regression gate**: If a frontend/Lark task touches auth, OTP, PIN/payment password, 2FA, device/session security, KYC, card, wallet, topup, exchange, remittance, notification, account/profile, money/status/time/order fields, payee/remittance account validation, or PRD source-of-truth semantics, classify it as frontend-only / backend-owned / FE-BE contract before closeout. Read the corresponding backend controller/service/entity/repository. Frontend unit/build/mock regression is not enough to certify backend correctness; if the backend is incomplete/unsafe and write permission exists, fix backend with TDD and verify locally, otherwise record an explicit backend blocker/follow-up. For validation-format tasks (e.g. SWIFT/IBAN character set/length), prefer a dual guard: immediate frontend form validation plus backend contract validation for direct API calls; do not silently normalize away invalid separators when the task asks to reject them.
- [ ] **Remote package/deploy monitor**: 对 UVISA/Railway 相关 Lark 任务，完成本地验证后必须检查相关远端 Railway/package/deploy 打包状态；只有 success/healthy + 本地检查通过才算 fully closed。用户当前 UVISA 前端任务偏好：前端代码修改后需要 push 并校验远程前端打包状态；无需关注后端部署状态，除非用户明确要求或任务本身是后端部署验证。失败/取消/超时/无权限访问时输出 `warn` 或 `reject`，并在 summary 中写明 remote blocker；不要记录 Railway token/cookie/OTP/私有 session 数据。
- [ ] **Process**: 理解任务 → 定位范围 → 执行修改 → 构建验证 → 远端打包监控 → 自审 → 输出 verdict
- [ ] **Style**: 遵循项目代码风格，最小改动，不引入无关变更
- [ ] **Efficiency**: 不重复读取已理解的文件，不做范围外探索

---

# Appendix: Hermes Agent Integration Patterns

> Reusable patterns for integrating Hermes Agent into automated workflows.

## Pattern 1: hermes chat -q as Executor

Use hermes chat -q for autonomous code execution with full tool calling:

```python
cmd = [
    "hermes", "chat", "-q", prompt,
    "-s", "skill1,skill2",  # Load multiple skills
    "--toolsets", "terminal,file",  # Only needed tools
]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
    env={**os.environ, "HERMES_NO_BANNER": "1"})
```

**Key points**:
- `-q` for non-interactive mode (single query)
- `-s` loads skills (comma-separated)
- `--toolsets` restricts available tools
- `HERMES_NO_BANNER=1` suppresses banner output

## Pattern 2: Session Persistence (--resume)

Reuse hermes session across tasks in same project:

```python
SESSIONS_FILE = Path.home() / ".arc-dispatch" / "sessions.json"

def get_session(project_id: str) -> str | None:
    if SESSIONS_FILE.is_file():
        sessions = json.loads(SESSIONS_FILE.read_text())
        return sessions.get(project_id)
    return None

def save_session(project_id: str, session_id: str):
    sessions = {}
    if SESSIONS_FILE.is_file():
        sessions = json.loads(SESSIONS_FILE.read_text())
    sessions[project_id] = session_id
    SESSIONS_FILE.write_text(json.dumps(sessions))

# Usage
existing = get_session(project_id)
if existing:
    cmd = ["hermes", "--resume", existing, "-q", prompt]
else:
    cmd = ["hermes", "chat", "-q", prompt]
    # After success: save_session(project_id, new_session_id)
```

## Pattern 3: JSON Extraction from hermes Output

hermes chat -q outputs mixed content (banner + JSON). Extract JSON reliably:

```python
def extract_json(text: str, key: str = "verdict") -> dict:
    # Strategy 1: Last line with key
    for line in reversed(text.strip().split("\n")):
        line = line.strip()
        if line.startswith("{") and key in line:
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    
    # Strategy 2: Regex with greedy matching
    matches = list(re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL))
    for m in reversed(matches):
        try:
            data = json.loads(m.group())
            if key in data:
                return data
        except json.JSONDecodeError:
            continue
    
    # Strategy 3: Find JSON blocks
    json_pattern = re.compile(r'\{[^}]+\}', re.DOTALL)
    for match in json_pattern.finditer(text):
        try:
            data = json.loads(match.group())
            if key in data:
                return data
        except:
            continue
    
    raise ValueError(f"No JSON with '{key}' found")
```

## Pattern 4: Notification via messaging

Send notifications through hermes messaging toolset:

```python
def notify(message: str, level: str = "info"):
    emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(level, "ℹ️")
    full_message = f"{emoji} {message}"
    
    subprocess.run(
        ["hermes", "chat", "-q", f"发送通知消息：{full_message}", "--toolsets", "messaging"],
        capture_output=True, text=True, timeout=30,
        env={**os.environ, "HERMES_NO_BANNER": "1"}
    )
```

## Pattern 5: Design Analysis via browser

Analyze screenshots/Figma links using hermes browser toolset:

```python
def analyze_screenshot(url: str) -> str:
    result = subprocess.run(
        ["hermes", "chat", "-q",
         f"打开 {url}，分析页面布局、元素、颜色、间距。不要做其他操作。",
         "--toolsets", "browser"],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "HERMES_NO_BANNER": "1"}
    )
    return result.stdout.strip()[:500] if result.returncode == 0 else "分析失败"
```

## Pattern 6: Retry with Exponential Backoff

```python
def retry_with_backoff(max_attempts=3, base_delay=1.0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_attempts - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
                    else:
                        raise
        return wrapper
    return decorator
```

## Pattern 7: Optimization Trade-off Analysis

When evaluating pipeline optimizations, apply "拒绝丢失功能与精准度" principle:

| Plan | Change | Lose Functionality? | Lose Precision? | Safe? |
|------|--------|---------------------|-----------------|-------|
| A | Merge confirmer+executor | YES (lose early filtering) | NO | ❌ |
| B | Create skill for executor | NO (additive) | NO | ✅ |
| C | Executor self-review | NO (review still independent via skill) | NO | ✅ |
| D | Session persistence | NO (additive) | NO | ✅ |

**Rule**: Only execute plans that are pure additions (no removal of existing capability).

## Pattern 8: Python 3.9 Compatibility

For projects using Python 3.9 (like macOS default):

```python
#!/usr/bin/env python3
from __future__ import annotations  # MUST be first import

# Now can use: dict | None, list[str], etc.
def func(param: dict | None = None) -> list[str]:
    return []
```

**Key**: `from __future__ import annotations` MUST be the first import (after shebang/docstring).
