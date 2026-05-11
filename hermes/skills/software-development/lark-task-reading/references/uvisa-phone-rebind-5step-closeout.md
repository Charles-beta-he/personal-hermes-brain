# UVISA phone rebind 5-step closeout pattern

Use when a Lark task mentions 手机号换绑, MY-06/MY-06B, or a 5-step phone rebind prototype.

## Expected frontend flow

The PRD/prototype flow is not the older "verify old phone" path. Treat it as:

1. Confirm current bound phone.
2. Dual verification 1/2: payment PIN.
3. Dual verification 2/2: default email verification code, with a switch to SMS verification.
4. Enter new phone.
5. Verify new-phone SMS code.

Key distinction: the second factor confirms the current account identity and defaults to email. Do not model it as `verifyOldPhone()` unless the current task evidence explicitly overrides the prototype.

## Implementation notes

- Keep the existing change-phone route and protection-after-success behavior.
- Use existing contact masking helpers (`maskPhone`, `maskEmail`) instead of inline masking.
- Request second-factor code when entering the second-factor stage and again on resend.
- Switching factor should clear the current code and request the new method's code.
- Verification should call the generic 2FA method (`verifyTwoFactorCode(method, code, purpose)` or equivalent) for the second factor, then continue to new-phone input. For phone rebind, pass a purpose such as `phone-rebind` so the backend can mark the account-identity step-up separately from login 2FA.
- New-phone verification remains the dedicated new-phone SMS verification path.
- Do not claim that the new-phone SMS was sent unless the frontend actually called a request-new-phone-code endpoint before showing the verify-new step. Add resend coverage for the same endpoint.
- Translate service error/i18n keys before displaying them. A raw key such as `auth.sendCodeFailed` in the UI is a product bug, not acceptable evidence.

## Backend/API contract notes

Phone rebind is a frontend + backend security flow, not just a screen copy task. Before closeout, inspect the real backend contract and prove these semantics are true or patch the backend with TDD:

- Payment PIN verification and current-account second factor must create short-lived step-up state (for example Redis keys keyed by user id and purpose).
- The final new-phone verification endpoint must require both step-up states before mutating the phone. A direct API call to `/me/phone/verify-new` or legacy `/auth/phone/verify-new` must fail without the prior PIN + account-factor gates.
- The 2FA request/verify endpoints may originally only support TOTP/backup or login-style OTP. If the UI uses email/SMS account verification, backend support must be added deliberately and purpose-scoped; do not assume UI method names map to backend behavior.
- Add or keep a dedicated request-new-phone-code endpoint so step 5 sends an OTP to the new phone, not the old phone/current account.
- For legacy compatibility, patch both canonical `/api/me/...` and legacy `/api/auth/...` surfaces when the app still uses both.


## Regression test shape

Add a component-level test that proves:

- Intro screen shows current bound phone and 5-step/flow copy.
- After payment PIN success, the UI reaches "双重验证 · 2/2".
- Default second factor requests email and shows email-code copy.
- The SMS switch requests SMS and changes the copy/button label.
- Entering the new-phone step calls the request-new-phone-code endpoint before the UI says the code was sent.
- The final verification submits the new-phone code through the dedicated new-phone verification endpoint.
- `verifyOldPhone()` is not called in the default prototype flow.

Add backend tests for the security invariant when backend code is touched:

- final phone mutation is rejected without payment-PIN step-up;
- final phone mutation is rejected without current-account 2FA step-up;
- final phone mutation succeeds only after both gates and consumes/clears the step-up state;
- legacy and canonical endpoints share the same guard behavior if both exist.

## Closeout pitfalls from session

- A new test file under `__tests__/` can remain untracked; `git diff --stat` will not include it unless staged. Before review/commit, stage the intended files and export `git diff --cached > /tmp/uvisa-task-<id>-staged.diff`.
- Backend test placement matters in the UVISA multi-module Maven repo. If `app/uvisa-app` has unrelated compile blockers, do not put an api-public service test under `app/uvisa-app/src/test`; place it under `api/api-public/src/test/java/...` with the package matching the touched service, or document the module-level blocker explicitly. Keep `JAVA_HOME` on openjdk@21 for Maven verification.
- If app-level tests fail because of an unrelated existing compile error, preserve the exact failing symbol/file as a blocker and still run the narrower touched module compile/test lane when possible. Do not let an unrelated app module failure erase the evidence from `api-public` compile or frontend tests.
- If a reviewer finds a security/product blocker after an earlier multi-model state or discussion has run, that artifact is stale for the final diff. Fix with RED tests, rerun deterministic gates, and build a fresh claim/evidence state before claiming certification.
- If browser verification is interrupted after seeding auth state, final handoff must say the UI gate is unfinished and include the preview process/session id so the next run can either continue the walkthrough or clean it up.
- For ad-hoc Playwright browser proof in this Vite app, run scripts from inside the frontend repo and import `chromium` from `@playwright/test`, not `playwright`; otherwise Node may fail with `ERR_MODULE_NOT_FOUND` even though `@playwright/test` is in devDependencies. Keep the temporary script under an ignored/local path and delete it before status/commit.
- When the page has both status text and a field label containing the same phrase (for example `邮箱验证码已发送至...` and exact label `邮箱验证码`), use exact locators such as `getByText('邮箱验证码', { exact: true })` to avoid Playwright strict-mode violations.
- A route-mocked browser walkthrough may produce 404 console noise from unrelated app bootstrap calls (`/wallets`, `/notifications`, etc.). Do not fail the phone-rebind proof on those if the task-specific required call sequence passes and no pageerror appears; separately record the noise as route-mock scope, not product failure.
- The UI proof should assert the full API sequence, not just visible screens: `pin/verify` with `purpose=phone-rebind`, account 2FA request/verify with the same purpose, `me/phone/request-new-code` before `me/phone/verify-new`, and no `phone/verify-old` in the default prototype flow.
- TypeScript test fixtures must match `User` exactly (`realName`, `vipLevel`, `joinedAt`, `advisor`, `idNo`), and mocked `verifyOldPhone` / `verifyNewPhone` should satisfy `ApiResult` by including `data`.
- When building `consult_models.py` state for an already-staged implementation closeout, make the intent explicit: the candidate solution is the staged frontend/backend diff, and the expected model action is closeout ratification (`no_action_certification_of_staged_implementation`), not a request to invent new patches. If the state is phrased as generic `implementation_required`, the discussion can get stuck in a false `noop-vs-implementation` metadata loop even when all claims are truth-grounded (`evidence_coverage=1.0`) and no code blocker exists. In that case, do not burn the closeout window on repeated discussion resumes: preserve the tick as `truth_grounded_but_not_fully_ratified`, rebuild the state with explicit staged-candidate intent if budget allows, otherwise prioritize deterministic commit/push/remote/TG with an honest ratification caveat.
