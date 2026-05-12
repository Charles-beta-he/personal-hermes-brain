# UVISA CNY top-up pending transaction visibility closeout pattern

Use this when a UVISA Lark task says a CNY/domestic-bank top-up order should appear in Home recent transactions and Me -> Transaction Records after the user creates the order and returns from the progress/pending page.

## Product semantics

- Treat `submitCny` success as **order-created / pending**, not as credited funds.
- Do not update wallet balance or total assets until the status endpoint / backend ledger says credited/completed.
- The frontend may insert a session-local pending row only after the backend create call returns a real `txId`/order id.
- Backend `/transactions/recent`, `/transactions`, or transaction detail remains authoritative. Same id from backend must replace the optimistic row.
- If backend refresh does not yet include the order, keep the session-local pending row visible; never upgrade it to completed without backend evidence.

## Implementation pattern

1. Add a store-level upsert/reconcile API rather than scattering array mutation in screens:
   - `upsertLocal(tx)` for real-submit optimistic pending rows.
   - `refreshOne(id)` to fetch backend detail and replace local row by id.
   - `fetchRecent`/`fetchList` should merge by transaction id and preserve unmatched optimistic pending rows instead of blind replacement.
   - Do not persist `optimistic` rows across reload/session restore.
2. In the submit screen (`CnyBankScreen` pattern):
   - call `submitCny({ amount, ccy: 'CNY' })`.
   - if `success && data.txId`, upsert a `transfer-in`, `CNY`, positive amount, `pending`, `optimistic: true` transaction.
   - if failure or missing tx id, insert nothing.
3. In the progress screen (`CnyProgressScreen` pattern):
   - before every return-home exit (`check later`, `go home`, and visible back), run `fetchRecent(10)` and `refreshOne(orderId)` best-effort, then navigate.
   - on credited stage, refresh wallets and transactions.
4. In display components:
   - map `pending` like `processing` (spinner/blue/处理中), not like `failed`.
   - update both Home recent row and TxDetail status mapping.

## Regression tests to add

- Store:
  - optimistic pending row is kept when recent refresh omits it.
  - backend same-id row replaces optimistic row without duplicate.
  - `refreshOne(id)` replaces optimistic with authoritative backend status.
  - optimistic rows are excluded from persisted state.
- Submit screen:
  - successful submit with tx id inserts pending CNY transfer-in row.
  - failed submit or missing tx id inserts no transaction.
- Progress screen:
  - `check later` / `go home` call `fetchRecent(10)` + `refreshOne(orderId)` before navigation.
  - credited callback refreshes both wallets and transactions.
- Home / Tx:
  - pending CNY top-up appears in Home recent and `/tx`.
  - pending displays as processing/处理中, not failed.

## Testing pitfalls observed

- If merge logic sorts by `createdAt`/`date`, existing tests that expected mock insertion order will fail. Update assertions to expect chronological order or be order-insensitive.
- `toMatchObject({ optimistic: undefined })` fails when the property is absent. Use `expect(row).not.toHaveProperty('optimistic')` after backend reconciliation.
- Home may contain multiple `入金` labels (quick action and recent row). Avoid `getByText('入金')` as a unique selector; use `getAllByText`, row-scoped queries, amount/status assertions, or add a stable test id if justified.
- If `fetchRecent` preserves optimistic pending rows, old tests that expected exact `transactions === mockTransactions` may need to sort/compare by ids rather than deep-equal the original array.
- Do not use one merge helper for all transaction-store paths without proving its retention semantics. A `mergeTransactions()` helper that only preserves existing `optimistic` rows is appropriate for backend list/recent reconciliation, but it is dangerous for `upsertLocal()` and `refreshOne()`: it can drop unrelated already-loaded authoritative rows from Home/Tx state. Use a separate all-row id upsert helper for local insertion/detail refresh, and add regression tests proving existing normal rows survive both paths.
- Guard backend create response status before inserting a local pending row. `success && txId` is not enough if the create payload can carry `FAILED`, `REJECTED`, `EXPIRED`, or another terminal status. Terminal create responses must not masquerade as normal pending rows.
- Filtered list refreshes must apply the requested `ccy`/`type` filters to preserved optimistic rows; otherwise a CNY pending row can leak into unrelated USD/exchange pages and corrupt totals.
- Optimistic transfer-in detail data must map `payerAccount`/account fields to the masked receiving account number, not the bank branch, because `TxDetailScreen` labels that field as `topup.accountNumber`.

## Closeout gates

After fixing this class of task:

1. Run targeted Vitest for store + topup + Home + Tx list/detail tests.
2. Run full unit tests and `pnpm build` before claiming done; if reviewer-driven RED tests are added late, rerun both targeted and full gates because totals change.
3. Write a concise evidence note with task id, changed files, verification outputs, and explicit residual risk that refresh persistence depends on backend transaction endpoints returning the order after reload.
4. Before staging/commit, run a stale-count scan across repo ledgers and the `/tmp` evidence note for old totals such as `25/25`, `28/28`, `524 passed`, or `527 passed`. Late AMEND fixes often leave stale proof text even when code is correct.
5. Stage the intended task files only, run `git diff --cached --check`, save `git diff --cached > /tmp/uvisa-lark-<id>-staged.diff`, and run final independent review on that staged diff. If any reviewer returns AMEND after the last code/test change, fix it and rerun review; do not cite a pre-fix APPROVE.
6. Commit scoped files, push the shared UVISA Lark loop branch, monitor the remote frontend build only, and send TG notification before moving to the next Lark task.
