# UVISA exchange quote countdown closeout pattern

Use for Lark tasks about exchange quote validity, countdown linkage, quote expiry, or avoiding re-quote after PIN/2FA.

## Evidence learned

- Frontend `ExchangeScreen` may display a fake/static quote countdown (for example hardcoded `15 refreshAfter`) while computing `out` from wallet-store FX rates.
- `ExchangeConfirmScreen` may independently hardcode another countdown (for example `12 refreshAfter`) and pass only `from/to/amount/out` to `/exchange/finish`.
- `ExchangeFinishScreen` calling `exchangeService.execute({ from, to, amount, pin })` without `quoteId` causes `exchange.service.execute()` to call `getQuote()` after PIN/2FA. That breaks the business invariant that the confirmed quote is the same backend quote the user saw before verification.
- Backend `/api/exchange/quote` already returns `quoteId` and `expiresAt`; backend `/api/exchange/confirm` validates `quoteId`, `used`, and expiry. Prefer frontend linkage over backend changes when this contract exists.
- Multi-model/reviewer blockers on this task class often show up after the first targeted tests pass: expiry can happen during PIN/2FA, malformed finish URLs can omit `quoteId`, and `exchange.service.execute()` fallback can silently re-quote unless the finish screen rejects missing quoteId before calling it.

## Preferred implementation shape

1. RED tests first under `src/screens/exchange/__tests__/`:
   - Input amount + select receive currency calls `exchangeService.getQuote(from,to,amount)`.
   - Input page displays quote `converted/rate` and countdown derived from backend `expiresAt`.
   - Clicking next passes `{ from, to, amount, out, quoteId, expiresAt, rate }` to confirm route state.
   - Confirm page displays the same countdown from the same `expiresAt`.
   - Confirming routes to `/pay/verify/pin?next=.../exchange/finish?...quoteId=...&expiresAt=...`.
   - Expired quote disables next/confirm and shows a refresh/expired prompt rather than sending stale quote through PIN.
   - `ExchangeFinishScreen` rejects missing `quoteId` or expired `expiresAt` before calling `exchangeService.execute`; this guards direct/stale `/exchange/finish` URLs and quote expiry during PIN/2FA.
   - `ExchangeFinishScreen` success path calls `exchangeService.execute` with the same `quoteId` and does not call `getQuote` after PIN.
2. GREEN implementation:
   - `ExchangeScreen`: fetch quote when `from/to/amount` is valid; use `quote.rate`, `quote.converted`, `quote.expiresAt`; calculate remaining seconds with an interval or timer from `Date.now()`; expire slightly early with a shared safety buffer (5s was used in UVISA).
   - Avoid React 19 `react-hooks/set-state-in-effect` failures: do not synchronously reset quote/loading/error state inside an effect just to represent derived invalid/loading state. Prefer a `quoteRequestKey` and derive `quote`, `quoteError`, and `quoteLoading` from keyed state; effects should subscribe/fetch and set state from async callbacks/timers.
   - `ExchangeConfirmScreen`: require `quoteId` + `expiresAt` in state; reuse the same countdown; block confirmation when expired.
   - `ExchangeFinishScreen`: read `quoteId` and `expiresAt` from URL; reject missing/expired quote before execute; call `exchangeService.execute({ from, to, amount, quoteId, pin })`; do not re-quote after PIN on this path.
   - `exchange.service`: preserve/normalize backend `quoteId`, `rate`, `amountIn/amount`, `amountOut/converted`, and `expiresAt`. If a legacy fallback quote remains in `execute`, ensure the UI finish path never reaches it after PIN.
3. i18n keys usually needed:
   - `exchange.expiredRefresh`
   - `exchange.refreshQuote`
   - optionally `exchange.quoteLoading` / `exchange.quoteFailed`.
4. Ledger updates:
   - `docs/UI_TEST_CASES.md`: EX-01/EX-02.
   - `docs/PRODUCT_USER_LOGIC_TEST_CASES.md`: PUL-FLOW-06 / PUL-MONEY-06.
   - Workpad closeout row with evidence path.

## Testing pitfalls

- `screen.getByRole('button', { name: '选择收款币种' })` can match both the receive-currency card button and the bottom CTA. Scope the query to the receive card/dialog or use `getAllByRole(...)[0]` only if the DOM ordering is stable enough for this project.
- Currency picker rows like `/USD/` can match USD/USDT/USDC. Select the exact label inside the dialog, then click `label.closest('button')` rather than using a broad accessible-name regex.
- `BottomSheet` portals may need `document.body.innerHTML = '<div id="phone-portal"></div>'` in test setup.
- Fake timers must set the system time before rendering; use backend `expiresAt` near the fake system time so countdown assertions are deterministic.
- With fake timers and async quote fetching, prefer a small `act(async () => Promise.resolve()...)` flush or `waitFor` before advancing timers. Advancing timers outside `act` creates noisy React warnings.
- If `findByText` / `waitFor` times out under fake timers, stop retrying the same command: flush promises explicitly or temporarily switch the assertion to synchronous after the async quote promise settles.
- `FlowNav` title and CTA can both render the same text (`确认兑换`); use `getAllByText` or role-specific selectors.
- Test wallet `fxRates` use `timestamp`, not `fetchedAt`; otherwise `pnpm exec tsc -b --pretty false` fails even if Vitest passes.
- For `ExchangeFinishScreen`, wrap the test in `ToastProvider`, clear `sessionStorage`, and include routes for `/exchange` and `/order/:id`; `useFinishOnce` adds a `txKey` redirect before invoking the finish action.

## Verification commands

```bash
pnpm exec vitest run src/screens/exchange/__tests__/ExchangeQuoteCountdown.test.tsx src/services/__tests__/money-services.test.ts --reporter=verbose
pnpm exec eslint src/screens/exchange/ExchangeScreen.tsx src/screens/exchange/ExchangeConfirmScreen.tsx src/screens/payment/PaymentFinishScreens.tsx src/services/exchange.service.ts src/screens/exchange/__tests__/ExchangeQuoteCountdown.test.tsx
pnpm exec tsc -b --pretty false
git diff --check
pnpm run build
```

If full `pnpm test` still fails on unrelated baseline tests, record the exact touched-scope pass and baseline failure counts without claiming full green.

## Closeout guard

Do not spend the final tool/context budget on optional extra reviewer loops once deterministic blockers are known. After an AMEND reviewer result, convert each blocker to a regression test, fix it, rerun targeted tests + eslint + tsc/build, then commit/TG before exploring the next task. If max tool iterations interrupt before the final rerun/commit/TG, report the task as `not_closed` and list unfinished gates explicitly.
