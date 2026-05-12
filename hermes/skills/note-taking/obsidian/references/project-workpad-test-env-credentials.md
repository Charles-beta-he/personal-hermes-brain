# Project Workpad: test environments, test accounts, and OTP debug channels

Use this reference when a user asks to add QA/test-environment facts into a project image, Workpad, or local-brain project note.

## Scope rule

- Store these facts in the project Workpad/local project note, not global memory.
- Do not copy test credentials or OTP workflows into public README, PR descriptions, issues, or broad cross-project playbooks unless explicitly sanitized.
- If the user later says the account is not disposable/test-only, remove it from the Workpad and advise rotating credentials.

## What to store

Good Workpad fields:

- Environment name and URL.
- Test account identity fields needed for repeatable QA, e.g. phone/UID/KYC level.
- Stable test PIN/password only if explicitly provided for a disposable test account.
- Source and date, e.g. “user-provided for test environment”.
- Verification rule: must be validated by browser/Playwright before claiming PASS.
- Evidence-deposition rule: login/console/network/storage proof belongs in evidence ledger/UI test ledger.

## OTP/SMS debug-channel pattern

For environments where verification codes are surfaced through backend logs instead of real SMS:

- Store the method, not the one-time code value.
- Example method: Railway console → project → `uvisa-backend` service → `Deploy Logs`.
- Useful log filters/keywords: `OTP-CODE`, `SMS-DEV`, `purpose=LOGIN`, target phone suffix, `OtpService`, `LogSmsSender`, `ttlSeconds=300`, “5 分钟内有效”.
- Use only the latest log entry matching the current login request and target account.
- One-time OTP values must not be persisted in Workpad, screenshots committed to repo, public docs, PRs/issues, or global memory.

## Timing pitfall

There can be a delay between clicking/sending the verification code in the frontend and the backend log line appearing.

Workflow:

1. Send code once from the frontend.
2. Do not immediately mark failure if the log is absent.
3. Wait briefly, refresh the Deploy Logs, or apply keyword filters.
4. Read the latest matching `LOGIN` OTP.
5. If expired or if multiple requests were sent, resend and re-read the latest matching log.
6. Record the fact that login was completed with log-derived OTP, but redact the OTP itself.

## Suggested Workpad wording

```md
### Verification Code Retrieval / 当前临时验证码来源

- 当前测试环境短信验证码暂时不以真实短信为准，而是在浏览器已打开的 backend 服务日志中读取。
- 操作入口：<console> → <backend service> → Deploy Logs。
- 识别方式：搜索/过滤 `OTP-CODE`、`SMS-DEV`、`purpose=LOGIN`、目标手机号后四位。
- 使用规则：发送验证码后，后端日志出现 OTP 可能有一段时间间隔；不要立刻判定失败，应等待/刷新/过滤后读取最新匹配的 `LOGIN` 验证码。
- 安全规则：只记录读取方法，不保存任何一次性验证码值。
```

## Verification after editing

- Search the Workpad for the new environment/log-source terms.
- Run any project/local-brain self-check script if available.
- Confirm application repo status if only the brain/Workpad should change.
