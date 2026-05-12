# UVISA auth/security tasks: token-issuing path parity

Session learning from Lark trusted-device persistence (95b2a5d5): a security task can look complete on the primary OTP login path while another token-issuing path remains missing or stale.

## Rule
For any Lark task that affects auth, trusted devices, PIN-skip gates, session/SSO, password login, or post-login routing, enumerate every frontend path that can create an authenticated session, then verify the backend route for each path returns the same security contract.

Typical UVISA token-issuing paths to check:
- `POST /api/auth/login` (OTP login)
- deprecated alias `POST /api/auth/verify`
- `POST /api/auth/login-with-password` if frontend exposes password login
- refresh/token rotation paths if session validity or SSO is in scope

## Trusted-device contract example
When implementing trusted-device persistence, it is not enough that OTP login returns `currentDeviceTrusted`. If the frontend also calls `/auth/login-with-password` and then uses the same route gate (`isCurrentBrowserTrusted()`), the backend password-login endpoint must exist and return `currentDeviceTrusted` from backend source-of-truth. Otherwise the task remains partially closed or blocked.

## Closeout checklist
1. Search frontend for all calls that consume `AuthToken` / `consumeAuthToken` / post-login navigation gates.
2. Search backend controllers for matching routes.
3. Confirm each token-issuing backend route returns the same fields required by the frontend security decision.
4. Prefer fail-closed behavior for missing backend fields, but do not treat fail-closed as feature completion when the task requires persistence or skip behavior.
5. Add targeted tests for each token-issuing route touched by the security contract.
