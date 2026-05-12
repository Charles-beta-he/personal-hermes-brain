---
name: red-teaming
description: "Red Teaming workflow skill. See references/ for detailed guides."
license: MIT
---

# Red Teaming

> Red Teaming 相关的工作流 Skill

## 输入

- 用户请求的具体参数

## 输出

- 执行结果或生成的文件

## 约束

- 遵循项目规范
- 在 context budget 内完成

## 检查点

- [ ] 输入参数完整
- [ ] 输出符合预期

## Security step-up / trusted-device audit pattern

When auditing trusted-device, remembered-browser, MFA/PIN step-up, or device/session persistence flows:

1. Trace the complete route from primary auth success → token/store normalization → route decision → step-up verification endpoint.
2. Classify every trust input by authority: server response for the current login, backend persisted device row, client cache, UI overlay, optimistic state.
3. Treat client-controlled persistence (`localStorage`, `sessionStorage`, IndexedDB, unsigned cookies, Zustand snapshots) as display-only. It must never be the fallback authority for skipping PIN/OTP/MFA/payment-password step-up.
4. Require fail-closed behavior: if the server trust field is missing, false, malformed, stale, or the trust PATCH failed, route to step-up.
5. On the backend, verify trust mutation filters by user + active/non-revoked device, checks zero-row update count, clears trust on revoke/logout-others, and writes an audit event.
6. Call out weak device binding separately: User-Agent hashes are identifiers, not authenticators; prefer server-issued opaque device secrets hashed server-side.

Reference: `references/client-controlled-trust.md` contains a focused checklist and verdict rules for client-controlled trusted-device bypass reviews.

## 关联 Skill

- `pua`: 核心行为基线


## 约束

- 遵循项目规范
- 在 context budget 内完成
