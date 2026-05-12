# UVISA Lark single-session auth tasks

Use for UVISA Lark tasks like `未做单点登陆` / `同账户不同设备登陆未顶掉帐号` where the expected behavior is: a new user login invalidates older sessions on other devices.

## Diagnosis pattern

1. Do not solve this only in the frontend. If the old device still has a valid backend access/refresh token, frontend-only logout calls from the new device cannot reliably kick the old device.
2. Check frontend first for existing 401 handling:
   - `src/lib/api.ts` request interceptor sends `auth_token`.
   - response interceptor should handle 401 by attempting `/auth/refresh`; if refresh fails it removes `auth_token`/`refresh_token`, dispatches `uvisa:auth-expired`, and redirects to `/login`.
   - If this exists, the frontend likely already supports being kicked once the backend rejects old tokens.
3. Check backend token model:
   - `AuthService.loginWithOtp` / `loginWithEmailOtp` issuing `tokens.issueForUser(userId)` without revoking or superseding previous tokens means old devices remain valid.
   - `JwtTokenService` with only `auth:refresh:{jti}` and `auth:bl:{accessJti}` cannot invalidate unknown old access tokens immediately unless there is a per-user session generation/epoch check.
   - `DeviceFingerprintService.revokeAllExcept(...)` updating `identity_user_device.revoked` is not enough unless token validation checks it; device list revoke is not token revoke.

## Preferred fix shape

Implement single active USER session at the token layer, not as a UI workaround.
The approach below is Redis Active-Session (recommended over DB session_version column — no migration, atomic SET, same security).

1. Add constants to `JwtTokenService`:
   ```java
   private static final Duration SESSION_TTL = Duration.ofDays(7); // matches REFRESH_TTL
   private static final String CLAIM_SID = "sid";
   private static String sessionKey(String userId) { return "auth:session:" + userId; }
   ```
2. In `issue(UUID subjectId, String type)` during login:
   - generate `String sessionId = UUID.randomUUID().toString()`;
   - store `redis.opsForValue().set(sessionKey(subjectId.toString()), sessionId, SESSION_TTL)` — this atomically replaces any old session;
   - add `.claim(CLAIM_SID, sessionId)` to BOTH access and refresh token JWT claims.
3. In `rotate(String refreshToken)`:
   - after extracting `subjectId` from the stored refresh value, read the `sid` claim from the old refresh JWT;
   - check `redis.opsForValue().get(sessionKey(subjectId.toString()))` — if activeSid exists and doesn't match the token's sid, return `Optional.empty()` (session superseded);
   - the new `issue()` call will create a fresh session entry (same sid since it's the same user logging in again is fine — the SET replaces).
4. Add `isSessionValid(String userId, String sessionId)` method:
   - return true if sessionId is null (legacy tokens without sid claim);
   - return true if no active session in Redis (fail-open on Redis down — defense-in-depth, not primary auth);
   - return `activeSid.equals(sessionId)`.
5. Add `clearSession(String userId)` method: `redis.delete(sessionKey(userId))`.
6. In `JwtBlacklistAuthConverter.convert(Jwt jwt)`:
   - after blacklist check and use==access check, add:
   ```java
   String userId = jwt.getSubject();
   String sid = jwt.getClaimAsString("sid");
   if (!tokens.isSessionValid(userId, sid)) {
       throw new BizException(ErrorCode.UNAUTHORIZED, "已在其他设备登录，如非本人操作请注意账户安全");
   }
   ```
   - **PITFALL**: `BizException` only has 2-arg constructor `(ErrorCode, String displayMessage)`. Do NOT use 3-arg `(ErrorCode, String code, String message)` — it doesn't exist and won't compile.
7. In `AuthService.logout()`:
   - after `tokens.revoke(...)`, add `if (userId != null) tokens.clearSession(userId.toString())`.
8. Keep ADMIN behavior unchanged unless the task explicitly asks for admin single-session.

## TDD checklist

Create a focused backend test before implementation, for example:

`api/api-public/src/test/java/com/uvisa/api/pub/security/JwtTokenServiceSingleSessionTest.java`

Cover at minimum:

- First `issueForUser(userId)` access token validates before a second login.
- Second `issueForUser(userId)` makes first access token fail converter validation.
- First refresh token cannot rotate after the second login.
- Second/current refresh token can rotate.
- Refresh rotation preserves the current session id and does not invalidate itself unexpectedly.
- Admin tokens are not invalidated by USER session replacement unless explicitly in scope.

## Dirty backend repo pitfall

UVISA backend often has existing WIP files from other tasks. Before editing, record `git status --short` and keep this task scoped to auth/session files only. Do not `git add .`. If unrelated dirty files exist, commit only exact paths touched for the single-session fix.

## Frontend SSO toast

When backend rejects a stale session, the frontend needs to show a specific message (not generic "登录已过期"):

1. In `api.ts` 401 handler, after refresh fails, detect SSO kick from the error message:
   ```typescript
   const msg = err.response?.data?.message ?? '';
   const isSsoKick = msg.includes('其他设备') || msg.includes('SESSION_EXPIRED');
   window.dispatchEvent(new CustomEvent('uvisa:auth-expired', { detail: { ssoKick: isSsoKick, message: msg } }));
   ```
2. In `App.tsx`, the `uvisa:auth-expired` handler checks `detail.ssoKick` and shows a toast:
   ```typescript
   const handler = (e: Event) => {
     const detail = (e as CustomEvent).detail;
     if (detail?.ssoKick) {
       toast(detail.message || '已在其他设备登录', 'error');
     }
     nav("/login", { replace: true });
   };
   ```
   The project uses a custom `useToast` hook from `components/ui/Toast.tsx`, NOT react-hot-toast.

## Scope limitation: masking vs encryption

This reference covers session invalidation only. For receiving-info data masking (account numbers, bank details), see `references/uvisa-secure-receiving-info-closeout.md`. The TopupController masking pitfall (masking methods must be in the Controller class, not the Service class, when the two are separate Java classes in the same file) is a general Java scoping issue, not SSO-specific.

## Closeout notes

- This is a backend-auth state-machine task, so remote monitoring should target Railway service `uvisa-backend`, not just the frontend service.
- In the TG closeout, explicitly state that frontend already logs out on backend 401/refresh failure, and the task fix is backend invalidation of stale access/refresh tokens.
- If full backend suite has known ArchUnit/M1 failures, do not claim full green; report targeted test + module/package result and list known unrelated failures.
