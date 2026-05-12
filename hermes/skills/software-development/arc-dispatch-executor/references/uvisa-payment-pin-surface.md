# UVISA payment PIN / payment-password surface pitfall

Use this when a Lark task mentions 支付密码/PIN, 未设置支付密码, exchange pay gate, rebind security gate, or repeated PIN setup after login.

## Lesson
Do not map endpoints from UI wording alone. In UVISA 2.0 the user-facing copy may say “支付密码”, but the 6-digit fund credential set during login is the backend payment PIN.

For one credential, verify the full lifecycle uses one storage/service surface:

- setup: `/auth/pin/setup`
- verify: `/auth/pin/verify`
- change: `/auth/pin/change`

If verify/change goes to `/auth/payment-password/*` or `/me/payment-password/*`, the frontend can write/read a different hash and cause production symptoms like:

- exchange `/pay/verify/pin` returns backend code `20021` / message `未设置支付密码`
- user set PIN during login but subsequent sensitive flow treats it as unset
- changing “payment password” updates an unrelated payment-password hash rather than the login setup PIN

## Regression pattern
Add both service and browser-level guards:

1. Service unit tests:
   - `verifyPaymentPassword('888888')` calls `/auth/pin/verify` with `{ pin }`
   - change payment PIN calls `/auth/pin/change` with `{ oldPin, newPin }`
   - assert not called with `/auth/payment-password/*` or `/me/payment-password/*`

2. Playwright request recorder:
   - record `/auth/pin/verify` as the expected first sensitive auth call
   - record `/auth/pin/change` for change flow
   - record legacy `/auth|/me/payment-password/verify|change` as forbidden
   - cover exchange gate (`/pay/verify/pin`) and payment PIN change (`/me/payment-pwd`)

3. Login routing tests:
   - existing user with `hasPaymentPin` true, or missing backend flag normalized to true, lands on `/home`
   - explicit `hasPaymentPin === false` / `needsPinSetup` lands on `/pin-setup`

## Closeout evidence
For Lark closeout, include:

- root cause: split credential surfaces
- changed files and endpoint mapping
- targeted service test result
- Playwright gate result
- full `pnpm test` and `pnpm run build`
- remote frontend package/deploy monitor result if closing the task

Never include real bearer tokens, OTPs, cookies, or Railway session secrets in docs or notifications.
