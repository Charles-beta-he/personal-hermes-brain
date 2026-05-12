# Auth / Payment-PIN Security Gate Patterns

Use this reference when verifying mobile/H5 auth, OTP, PIN setup, payment-password, card PIN, or account-recovery flows.

## Why this exists

A flow can pass page-level UI checks while its state machine is wrong. In one uvisa-style case, OTP verification always navigated to `/pin-setup`; logout -> relogin forced existing users through first-login PIN setup again. If the backend also allows direct PIN setup/reset, SMS/OTP becomes a single-factor path to overwrite the payment PIN.

## Required browser/Playwright cases

For login / first-login PIN setup:
1. Existing user with payment PIN: `/login -> /verify` must land on `/home`, not `/pin-setup`.
2. Logout then relogin as same existing user: must still land on `/home`.
3. First-login user explicitly flagged by backend (`needsPinSetup=true` or `hasPaymentPin=false`): must land on `/pin-setup`.
4. First-login user cannot deep-link around PIN setup: after login, `/home` and other protected pages redirect back to `/pin-setup` until setup succeeds.
5. Unauthenticated deep-link to `/pin-setup` redirects to `/login`; PIN setup must not be a public route.
6. After successful setup, local/auth profile state updates `hasPaymentPin=true` so the user can enter the app.

For payment/card PIN reset:
1. Any reset/change surface must verify the current payment PIN first (`/auth/payment-password/verify` or equivalent).
2. The first sensitive request must be the verification call, not direct `/card/pin-reset` or direct `setPin`.
3. Client-side guards (`sessionStorage`, pinGuard, disabled buttons) are UX only. Record a backend follow-up if the server endpoint still accepts direct reset without old PIN/MFA/action token.

For account recovery/rebind:
1. Phone/email rebind must start with payment-password/PIN verification before old-channel or new-channel OTP verification.
2. Do not treat OTP delivered to the channel being changed as a sufficient first factor; that is circular.

## Backend contract checks

Look for these response fields in login/profile responses:
- `needsPinSetup` — true only for accounts that must set a PIN now.
- `user.hasPaymentPin` or equivalent — true when payment PIN is already configured.

If the real backend omits these fields, the frontend may need a temporary conservative fallback for existing users, but the backend follow-up should request an explicit contract. For view-only backend repos, write a root-level frontend documentation record with evidence instead of editing backend code.

## Evidence to record

- Exact Playwright command and pass/fail count.
- Relevant route transitions and final URLs.
- Network request order for sensitive flows.
- Backend file/line evidence when a server endpoint directly calls `setPin` without verifying old PIN.
- Docs/workpad ledger updates; never persist OTP values or real credentials outside the project-scoped private workpad.