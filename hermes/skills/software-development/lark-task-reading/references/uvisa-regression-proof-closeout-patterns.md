# UVISA regression-proof closeout patterns

Use when a stale Lark task appears to describe a bug that the current code already fixes, or where the safest change is to add regression evidence rather than alter product behavior.

## Pattern: existing implementation, missing proof

1. Inspect the exact screen/component first; do not assume the task is still broken from the stale snapshot.
2. If the current product code already satisfies the requirement, make the delivery explicit as **regression proof / ledger closeout**, not a product-code fix.
3. Add a focused test that exercises the user-visible behavior named in the task.
4. Update the project evidence ledger and `/tmp` evidence note to say “current implementation already had X; this slice adds proof/guard.”
5. In TG/reporting, avoid wording like “fixed product bug” unless code actually changed the behavior.

## TxDetailScreen / FlowNav example

For Lark-style tasks such as “法币兑换详情页左上角缺少返回按钮”:

- `TxDetailScreen` already uses `FlowNav` with no `hideBack`, so `FlowNav` renders a top-left back button with `aria-label={t('common.back')}`.
- A good closeout may be a regression test rendering an exchange transaction at `/tx/:id` and asserting `getByRole('button', { name: '返回' })`.
- `TxDetailScreen` calls `useCopy()`, which requires `ToastProvider`; wrap test renders with `<ToastProvider>` or the test will fail with `ToastProvider missing` before reaching the FlowNav assertion.
- Keep the test scoped: assert the back button plus a couple of detail-page anchors (title/type/account) so CTAs/tabs/routes are not accidentally removed.

## AccountDetailScreen balance-unit example

For “钱包账户金额右侧单位应去掉”:

- Remove only the right-side `wallet.ccy` span from the balance hero.
- Preserve the left currency symbol, formatted amount, title currency context, CNH estimate line, CTA buttons, transaction tabs, and route behavior.
- Regression test should assert the amount row contains e.g. `$12,345.67` but not `USD`, while the CNH estimate line still shows `CNH`.

## Reporting language

Use status labels precisely:

- `local_closed`: deterministic local tests/build/review/certification/commit/TG complete.
- `closed_with_remote_blocker`: local closeout complete but Railway/package/deploy monitor is failed, stopped, inaccessible, or unrelated backend unhealthy.
- `not_closed`: implementation evidence is incomplete, no commit, no certification when required, or no requested notification.
