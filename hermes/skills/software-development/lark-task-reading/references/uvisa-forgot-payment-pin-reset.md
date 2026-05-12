# UVISA forgot payment PIN / payment password reset closeout

Use this when a UVISA Lark task touches “忘记支付密码”, “支付密码重置”, or frontend calls around `/api/auth/pin/forgot/*`.

## Classification

Treat this as FE-BE contract/security work, not a frontend-only copy task:

- Frontend may call methods named `sendForgotPaymentPwdCode` / `resetPaymentPwd`, but the backend source of truth is the payment PIN service and `/api/auth/pin/*` surface.
- The flow is logged-in account security recovery: derive the target account from `CurrentUser.requireUserId()`. Do not accept email/phone from the client for OTP target selection.
- If exact backend routes are missing, implement them in the existing legacy PIN controller area where `/api/auth/pin/setup|verify|change` live, not in an unrelated auth controller.

## Backend implementation pattern

Expected endpoints:

- `POST /api/auth/pin/forgot/send-code`
  - require current authenticated user
  - load `User` by current JWT subject
  - require bound email; fail fast with a clear BAD_REQUEST message if absent
  - normalize bound email by trim + lowercase before OTP issue/verify
  - issue email OTP with a stable purpose such as `pin-reset`
  - return only safe metadata: `success`, masked `email`, `channel: "EMAIL"`, `expiresInSec`

- `POST /api/auth/pin/forgot/reset`
  - validate `newPin` and `confirmPin` are both exactly 6 chars and equal before consuming OTP
  - require current authenticated user
  - load bound email from the user record
  - verify OTP against that bound email and `pin-reset` purpose
  - call `PaymentPinService.setPin(userId, newPin)`
  - audit the sensitive reset action, but never include full email/phone or the PIN

Audit payloads are often manually serialized strings in this backend. Escape JSON string values or use an existing JSON utility; do not concatenate raw header/email values into JSON.

## Test pattern

Add a focused controller/unit test before implementation:

- authenticated `JwtAuthenticationToken` needs an authority such as `ROLE_USER`; a bare `new JwtAuthenticationToken(jwt)` may fail `auth.isAuthenticated()` checks in `CurrentUser.requireUserId()`.
- send-code test should prove bound-email lookup, masked response, `EMAIL` channel, expiry seconds, and `otpService.issueEmail("pin-reset", normalizedEmail, clientIp)`.
- reset test should prove OTP verification, `PaymentPinService.setPin`, and sanitized audit payload.
- mismatch test should prove `newPin != confirmPin` rejects before user lookup / OTP consumption / PIN mutation.
- no-bound-email test should prove OTP is not issued.

Useful backend gate:

```bash
JAVA_HOME=$(/usr/libexec/java_home -v 21 2>/dev/null || echo /opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home) \
  mvn -pl api/api-public -am -Dtest=LegacyApiControllerPaymentPinForgotTest -Dsurefire.failIfNoSpecifiedTests=false test

JAVA_HOME=$(/usr/libexec/java_home -v 21 2>/dev/null || echo /opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home) \
  mvn -pl api/api-public -am test
```

Use Java 21 for this backend; newer Java/Lombok combinations may fail elsewhere.

## Frontend contract check

Frontend success type should match the backend response shape:

- send-code success: `{ success: true, email, channel: 'EMAIL', expiresInSec }`
- reset success: `{ success: true }`

For the screen UX, while the initial send-code request is pending, show a neutral sending state such as `auth.sendingCode`, not `auth.sendCodeFailed`. Only show failure copy after the request fails.

Typical frontend gates:

```bash
pnpm vitest run src/screens/me/__tests__/ForgotPaymentPwdScreen.test.tsx src/screens/me/security/__tests__/ChangePhoneScreen.test.tsx
pnpm test
pnpm build
```

## Closeout priority

Do not spend the final tool-call budget starting a long multi-model discussion before commit/push/remote/TG gates. For this class of security task, multi-model review is useful, but deterministic gates plus sanitized diffs must be preserved first. If a discussion runner is started, record its state path and poll it only if enough budget remains to finish closeout.
