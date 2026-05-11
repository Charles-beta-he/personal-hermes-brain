# UVISA first-login PIN setup confirmation attempt guard

Session lesson from UVISA Lark task `fc9888e4`: first-login payment PIN setup has two distinct failure surfaces:

1. **Set-stage weak PIN** — e.g. sequential/repeated digits. This is a validation error for the newly chosen PIN and should not consume the confirmation mismatch attempt budget.
2. **Confirm-stage mismatch** — the second entry does not match the first PIN. This is the task's "连续输入错误支付密码" surface and must have a finite attempt budget/lockout.

## Source-derived root cause pattern

`src/screens/auth/PinSetupScreen.tsx` can look complete because it already shows `auth.pinMismatch`, clears `confirm`, and shakes the PIN block. That is not enough for the Lark acceptance criterion. If confirm mismatch only does:

```ts
setConfirm("");
setError({ key: Date.now(), code: "mismatch" });
```

then users can retry forever.

The repo already has the reusable guard in `src/lib/pinGuard.ts`:

- `trackAttempt(key)`
- `getGuardState(key)`
- `resetAttempts(key)`
- behavior: 5 attempts, 10-minute rolling window, 5-minute lockout

Other payment-PIN surfaces use it with `payment-pin`. For first-login setup confirmation, prefer a separate key such as `payment-pin-setup` so setup confirmation failures do not pollute the normal payment verification budget.

## TDD recipe

Add a focused component test before changing production code, e.g.

```bash
pnpm vitest run src/screens/auth/__tests__/PinSetupScreen.test.tsx
```

Test shape:

1. Render `/pin-setup` with `useAuthStore` authenticated and `user.hasPaymentPin=false`.
2. Enter a non-weak first PIN, e.g. `135790`.
3. Re-enter a mismatched PIN, e.g. `246801`, four times.
4. Assert remaining-attempt text after each mismatch:
   - `两次密码不一致，还可尝试 4 次`
   - ... down to `1 次`
5. Fifth mismatch asserts lockout text:
   - `连续错误次数过多，请 5 分钟后再试`
6. After transient error clears, another mismatch still asserts lockout text.

Expected RED before the fix: the screen still shows the old generic `两次密码不一致，请重新输入`, proving the task defect is reproduced.

## Implementation checklist

- Import `trackAttempt`, `getGuardState`, and `resetAttempts` from `../../lib/pinGuard`.
- Keep weak-PIN validation separate from confirm-mismatch tracking.
- On confirm mismatch:
  1. call `getGuardState("payment-pin-setup")` first;
  2. if blocked, clear confirm and show a lockout message with remaining minutes;
  3. otherwise call `trackAttempt("payment-pin-setup")`;
  4. show either attempts-left or lockout message.
- On successful `setupPin`, call `resetAttempts("payment-pin-setup")` before navigating home.
- Add i18n keys to both `zh.json` and `en.json` rather than hardcoding strings.

Suggested keys:

```json
"auth.pinSetupAttemptsLeft": "两次密码不一致，还可尝试 {{remaining}} 次",
"auth.pinSetupLockedOut": "连续错误次数过多，请 {{minutes}} 分钟后再试"
```

English equivalents can mirror the existing security lockout wording.

## Closeout gates

After GREEN:

```bash
pnpm vitest run src/screens/auth/__tests__/PinSetupScreen.test.tsx
pnpm vitest run src/lib/__tests__/pinGuard.test.ts src/stores/__tests__/auth.store.test.ts src/screens/auth/__tests__/PinSetupScreen.test.tsx
pnpm test
pnpm build
git diff --check
```

Then write the evidence note, make a scoped commit, push/monitor the shared UVISA Lark task-loop branch when remote closeout is required, and send the TG notification. Do not claim the Lark task is complete from RED/GREEN alone.
