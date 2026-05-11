# UVISA large-amount typography Lark tasks

Use for UVISA frontend tasks where money text overflows mobile width (home total assets, wallet rows, account balance hero, card/wealth amount heroes).

Pattern:
1. Start with a RED component test using extreme but plausible amounts (13+ integer digits and 20+ total characters with decimals). Assert both the text content and the adaptive class/overflow guard.
2. Keep behavior additive: do not remove currencies, fields, routes, CTAs, or existing amount precision to make text fit.
3. Prefer deterministic typography tiers over CSS transform scaling for money text:
   - home total hero major amount: normal `text-44`, then `text-36`, `text-32`, `text-26` for very long totals;
   - account-detail balance hero may need a smaller 20+ character tier (`text-24` for the numeric amount, `text-20` for the symbol). In Lark `57da3f4f`, `text-26` looked plausible in component tests but clipped by ~2px in a real 375px Chromium render;
   - decimal/symbol shrink in parallel;
   - wallet row amount: cap available width (`max-w-[52%]` or equivalent), keep one line, shrink to `text-15`/`text-13`.
4. Add container guards on amount rows: `max-w-full min-w-0 overflow-hidden whitespace-nowrap`; add `shrink-0` to symbols/decimals where needed. Do not trust class assertions alone for fitting: measure `scrollWidth <= clientWidth` and document/page `scrollWidth <= viewport` in browser evidence.
5. Preserve previous Lark regression guards. Example: account detail balance must still avoid reintroducing a right-side currency-code suffix (`USD`) while showing CNH estimate normally.
6. Type-check tests: mock store fixtures must match current TS shape (for card limits use `{ atm, daily, monthly, single, spent: { daily, monthly } }`, not stale fields such as `atmDaily`).
7. Run gates in this order after implementation:
   - targeted Vitest for new/adjacent screen tests;
   - touched-file ESLint;
   - full `pnpm test -- --reporter=dot` when feasible;
   - `pnpm run build`;
   - `git diff --check`.
8. Browser evidence for layout-only money fitting can use Playwright route mocks plus authenticated local storage injection, but label it as layout/visual evidence rather than real-backend acceptance. Use mobile viewport 375x812, collect `scrollWidth`, rendered font size, text, and `bodyOverflowX`; save screenshots under `/tmp`.

Closeout reminder:
- Update `docs/UI_TEST_CASES.md` rows such as `HOME-01`, `HOME-02`, and `BND-VIS-02` from TODO/PARTIAL to PASS only after tests + browser layout evidence exist.
- For Lark closeout, still commit, push shared task-loop branch if remote monitor is required, check Railway frontend package/deploy, and send TG; tests/build alone are not full task completion.
