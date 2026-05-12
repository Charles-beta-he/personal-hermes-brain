# UVISA auth rate-limit semantics

Session learning from Lark task `b8920d15` (password-login lockout copy).

## Rule

For password-login lockout tasks, do not treat every `/auth/login-with-password` request as a wrong-password attempt. The lockout counter must increment only after the backend has identified a real password mismatch (`PASSWORD_INVALID`).

## Correct backend shape

In `api/api-public/src/main/java/com/uvisa/api/pub/auth/AuthService.java`:

1. Normalize email and find the user.
2. Reject frozen / missing user as their own auth failures.
3. Call `loginPasswordService.verify(userId, password)`.
4. Catch `BizException` only when `ex.error() == ErrorCode.PASSWORD_INVALID`.
5. In that catch block call:

```java
rateLimit.hit("login:password:email", email, 5, Duration.ofMinutes(30),
        "密码错误次数过多，账户已锁定 30 分钟");
```

6. Re-throw the original password-invalid exception unless `rateLimit.hit(...)` throws its explicit lockout message.
7. Successful password login must not consume the wrong-password limit.

## Frontend copy rule

The password-login UI maps `RATE_LIMITED` / code `10006` to `auth.loginPwd.rateLimited`. For this task class, set Chinese copy exactly to:

`密码错误次数过多，账户已锁定 30 分钟`

Do not reuse generic request-throttle copy (`请求次数过多，请稍后再试`) for password-mismatch lockout.

### Consumer-scope guard

Before changing any shared i18n key or error-mapping key, grep all consumers and classify whether each consumer has the same semantics. In `b8920d15`, `auth.loginPwd.rateLimited` looked password-specific but was also used by `ForgotLoginPwdScreen` for forgot-password OTP/reset throttling. The correct fix was to:

1. keep password-login lockout on `auth.loginPwd.rateLimited` with the exact 30-minute lock copy;
2. remap forgot-login-password `10006` to generic `auth.requestTooFrequent`;
3. add a regression assertion for the adjacent flow so future copy-only fixes do not leak wrong-password lock language into OTP/reset throttling.

Use this pattern for any auth copy task: changing the visible copy is not enough; prove that adjacent auth flows sharing the key still receive the correct domain-specific or generic message.

## Tests to add

Backend targeted unit tests:

- successful password login does not call the wrong-password rate-limit hit;
- wrong password calls `rateLimit.hit("login:password:email", ..., 5, PT30M, exact lockout copy)`;
- when `rateLimit.hit` throws `BizException(ErrorCode.RATE_LIMITED, exact copy)`, the exact copy is propagated and no token/device success side effects happen.

Frontend targeted tests:

- assert `zh['auth.loginPwd.rateLimited'] === '密码错误次数过多，账户已锁定 30 分钟'`;
- assert English copy distinguishes wrong-password lockout from generic throttling;
- assert adjacent forgot-login-password `RATE_LIMITED`/`10006` still maps to `auth.requestTooFrequent`, not `auth.loginPwd.rateLimited`.

## Pitfall

Putting `rateLimit.hit(...)` at the top of `loginWithPassword` creates false lockouts from valid successful logins, missing-user probes, or non-password failures. For financial/security UX tasks, count the specific failure being reported, not the endpoint call.
