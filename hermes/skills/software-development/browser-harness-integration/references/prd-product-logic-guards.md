# PRD-derived product logic guards

Use this when a frontend project has a PRD/business-logic ledger separate from UI/page-function tests (for example `docs/PRODUCT_USER_LOGIC_TEST_CASES.md`). Page-render PASS is not enough for product semantics such as registration boundaries, KYC ownership, allowed rails/networks, T2 verification, card lifecycle limits, or product scope.

## Pattern

1. Load the project Workpad and PRD-derived ledger before writing assertions.
2. Keep secrets out of repo docs/tests: real test accounts, OTP retrieval methods, and payment PINs belong only in project-scoped private notes/Workpad if explicitly provided.
3. Ask multi-model review for priority only when semantics/risk are non-trivial; use its output to choose P0/P1 guards, not as proof.
4. Add deterministic Playwright guards that assert business invariants directly:
   - Negative routes/CTAs are absent or redirect safely (e.g. no C-side signup/open-account flow).
   - Read-only compliance data has no editable controls and shows the correct correction path (advisor/support).
   - Money-moving rails expose only allowed choices (e.g. EVM networks only; TRC20/Solana absent) and reject invalid destination formats before submit.
   - T2 flows prove pagination/order: payment PIN step first, second-factor code step second; no single-PIN completion for outflows.
   - Version/scope limits remain visible as empty states, not hidden purchase paths (e.g. single physical card, stable-only wealth products).
5. Run both desktop and mobile Playwright projects when available; a mobile-only pass is useful but not final if the config includes desktop.
6. Update all evidence ledgers after the run:
   - PRD/product logic ledger: status per constraint + command + result + follow-up gaps.
   - UI ledger: short pointer that product-logic evidence exists elsewhere.
   - Workpad: private evidence row, preserving any real-env credential rules only in the Workpad.
7. Only then run full test/build and commit.

## Pitfalls

- Do not mark a whole constraint PASS if only one surface was tested. Use PARTIAL when one asset/route is covered but sibling surfaces remain (e.g. USDT payout EVM-only tested, but USDT topup or USDC payout still pending).
- Do not encode real OTP values or live payment PINs in committed tests or docs. Use mock/demo credentials already documented for the in-repo mock environment, or private Workpad-only real-env credentials.
- If a route renders a newer implementation than the file initially inspected, trust browser evidence and inspect the actual routed component before retrying selectors.
- When Playwright fails due to selectors, read the error-context page snapshot and adjust selectors to user-visible roles/text rather than repeating the same command.
