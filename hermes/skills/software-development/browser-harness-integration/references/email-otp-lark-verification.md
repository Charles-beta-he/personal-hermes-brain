# Email OTP via Desktop Lark/Feishu Verification

Use when a real deployed UI uses email OTP and the mailbox is only available in the user's desktop Lark/Feishu app.

## Proven sequence

1. Trigger OTP from the deployed UI/API only when ready to immediately read it; most codes are 5-minute TTL and may be one-time use.
2. Do not rely on deploy logs if the product path is email login. Prefer the real user mailbox path as acceptance evidence.
3. Bring Lark to foreground on macOS:
   ```bash
   osascript -e 'tell application "Lark" to activate'
   ```
4. If Lark is not showing Mail/邮箱, click the left-sidebar Mail item or use the visible screenshot coordinates. Then capture:
   ```bash
   screencapture -x /tmp/uvisa-lark-mail.png
   ```
5. Use vision/OCR on the screenshot to read the newest message titled like `UVisa verification code`. Always include timestamp in the readback.
6. If the visible code is rejected as `Wrong verification code`, do not assume login is broken. It may be a stale email/list view or a code already consumed by a prior API probe. Refresh/reopen Mail, wait a few seconds, and read the newest timestamp.
7. Verify through the real browser context. Redact tokens; report only token presence, user status/KYC, route, API status, console errors, and screenshots.

## Pitfalls

- OTP can be single-use: an API verification probe may consume it before the browser login attempt.
- Lark foreground does not guarantee Mail is selected; it may reopen a bot/chat such as 汇报.
- Mail list can lag. The latest visible code may be stale even after a new send-code request.
- Never persist concrete OTP codes, auth tokens, refresh tokens, or private mailbox screenshots in global memory or public docs. Put only durable mailbox workflow facts in the project Workpad if needed.
