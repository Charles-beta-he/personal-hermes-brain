# UVISA transaction timestamp localization pattern

Use this when a Lark UVISA task says wallet/assets/card transaction record times must use backend timestamps and display in the user's local timezone.

## Problem shape

Backend transaction APIs may return multiple time fields (`postedAt`, `occurredAt`, `createdAt`, `updatedAt`, `timestamp`, `eventTime`, `timeAt`, or legacy `date`). Frontend screens often render `tx.date` directly or slice/replace the raw string, which can silently preserve backend/UTC formatting instead of local time.

## Preferred implementation pattern

1. Add or extend a service-layer normalizer, not per-screen formatting patches.
2. Choose the timestamp source in this priority order:
   - `postedAt`
   - `occurredAt`
   - `createdAt`
   - `updatedAt`
   - `timestamp`
   - `eventTime`
   - `timeAt`
   - `date`
3. Accept ISO strings and numeric timestamps. For numeric timestamps, distinguish seconds vs milliseconds before constructing `Date`.
4. Convert the chosen timestamp through the project date utility that uses local JS `Date` getters (in `uvisa-app-2.0`, `formatDate(value, { time: true })`).
5. Preserve traceability fields (`postedAt`, `occurredAt`, `createdAt`, `updatedAt`, `timestamp`, ids/direction/currency) on the normalized transaction so UI/detail pages and debugging do not lose backend evidence.
6. Reuse the same normalizer for wallet transaction service, recent transactions, detail fetches, and card transaction service. Avoid divergent card/wallet time rules.
7. Keep backend enum compatibility in the same normalizer if needed (`CARD_SPEND`, `FX_*`, `TRANSFER_*` -> frontend `TxType`) so timestamp work does not break display routing.

## TDD guard pattern

Write RED tests before implementation:

- Service list endpoint prefers `postedAt` over raw display `date` and emits a local-time `date` string.
- Recent endpoint accepts numeric seconds timestamp and emits `occurredAt` + localized `date`.
- Detail endpoint accepts `createdAt` fallback and emits `occurredAt` + localized `date`.
- Card transaction service goes through the same normalizer and preserves `postedAt/occurredAt`.

Run at minimum:

```bash
pnpm exec vitest run src/services/__tests__/money-services.test.ts src/services/__tests__/card.service.test.ts --reporter=verbose
pnpm exec eslint src/services/transaction.service.ts src/services/card.service.ts src/types/index.ts src/services/__tests__/money-services.test.ts src/services/__tests__/card.service.test.ts
pnpm run build
```

Then run full `pnpm test` and classify existing baseline failures separately.

## Pitfalls from session evidence

- A green targeted Vitest run is not enough: `pnpm run build` can still fail on TypeScript strictness. In this case `card.service.ts` had `TS7006 Parameter 'item' implicitly has an 'any' type` after mapping API items. Fix typed map parameters before closeout.
- Do not claim Lark task completion until the task has commit/push/remote package check/TG notification if the user requested that closeout flow.
- Do not add per-screen `replace('T', ' ').slice(...)` patches; they preserve raw timezone assumptions and create inconsistent wallet/card behavior.
