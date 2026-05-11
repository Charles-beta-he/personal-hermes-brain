# Vite mock/real backend flow verification

Use this when a React/Vite financial app has both a local mock server and a real/staging backend, especially when UI test docs say demo fixtures should work but browser flows fail.

## Problem pattern

A Vite app can have three API routes that look similar but behave differently:

1. `src/lib/api.ts` uses `import.meta.env.VITE_API_BASE || '/api'`.
2. `vite.config.ts` proxies `'/api'` somewhere (local mock, staging, or production).
3. one-off code such as `navigator.sendBeacon('/api/analytics/vitals', ...)` hardcodes `/api` and ignores `VITE_API_BASE`.

If `vite.config.ts` points `/api` at a real backend while docs/test fixtures assume mock, demo OTP/PIN values like `123456` may fail even though the same flow passes with `VITE_API_BASE=http://localhost:3001/api`.

## Verification workflow

1. Read the project Workpad and `docs/UI_TEST_CASES.md` first. Treat documented demo credentials as scoped to the documented backend, not universal truth.
2. Inspect `vite.config.ts`, `src/lib/api.ts`, and analytics/vitals code for hardcoded `/api`.
3. Run two browser passes when behavior is ambiguous:
   - default dev path, e.g. `npm run dev` on `:5173`;
   - forced mock path, e.g. `VITE_API_BASE=http://localhost:3001/api npm run dev:client -- --port 5174` while mock server runs on `:3001`.
4. Capture requests, responses, console errors, page errors, screenshots, current URL, and key visible text at each step.
5. For auth/OTP endpoints, do not treat HTTP 200 as success. Inspect the body contract too:
   - mock often returns `{ success: true, data: ... }`;
   - real backends may return `{ code: 0, data: ... }` or failure bodies like `{ code: 20002, message: 'Wrong verification code' }` with HTTP 200.
6. Stop before irreversible profile/security mutation unless the user explicitly asked to complete it. For example, walking to a new-email verification screen is enough evidence for “login → email-code stage”; do not submit the final rebind code by default.
7. If browser flow passes but console/network is dirty, classify separately. A common culprit is `sendBeacon('/api/analytics/vitals')` ignoring `VITE_API_BASE`, producing 401s against the wrong proxy.
8. Deposit the result into `docs/UI_TEST_CASES.md` and the project Workpad Evidence Ledger. Mark split results honestly, e.g. `FAIL(default dev) / PASS(forced mock)`.

## Playwright script from /tmp with project dependencies

If writing a temporary `.mjs` script under `/tmp`, bare imports like `import { chromium } from '@playwright/test'` may fail because module resolution starts from `/tmp`. Use `createRequire` pinned to the project package:

```js
import { createRequire } from 'node:module';
const require = createRequire('/path/to/project/package.json');
const { chromium } = require('@playwright/test');
```

Parameterize output and base URL:

```js
const OUT = process.env.OUT_DIR || '/tmp/project-flow-evidence';
const baseURL = process.env.BASE_URL || 'http://localhost:5173';
```

## Reporting pattern

In the final report, separate:

- default current behavior;
- forced mock behavior;
- endpoint/body evidence;
- console/network cleanliness;
- UI/visual observations;
- documentation/config drift;
- next fix priority.

Do not claim “flow closed” if only the forced mock route passed and the default dev route still fails.