---
name: react-architecture-migration
description: "Migrate React app from hardcoded mock data to production architecture: API client → Services → Zustand stores → Mock server. Includes i18n, dark mode, PWA, error tracking, analytics, and TypeScript build error triage. Trigger: '填充架构', '架构迁移', 'mock to api', 'production-ready', '项目优化', 'loop 填充', 'tsc errors', 'build errors', 'TypeScript errors'."
---

# React Architecture Migration — Mock Data → Production

> Complete migration workflow for React+TypeScript apps from hardcoded mock data to production architecture with services, stores, mock server, i18n, dark mode, PWA, and monitoring.

## When to Use

- React app has hardcoded mock data in `data/mock.ts` or inline in screens
- Need to build API/service/store layer from scratch
- Need i18n, dark mode, PWA, error tracking, analytics
- User wants "loop until 99% complete"
- Need to build a mock server from existing service files (Expo or Vite)
- User says "mock server", "模拟服务器", "本地API", "loop until flow closed", "页面流程闭环"
- User asks to browser-test login/auth/security flows where mock demo credentials may differ from real/staging backend behavior
- **Prototype sync**: User points to a prototype directory and says "sync", "copy missing pages", "补充缺少页面", "同步后填充"
- **Unified deployment**: User wants to deploy mock server + dist as one process, "打包部署", "serve.js", "docker部署"

## Architecture Pattern

```
src/
├── lib/
│   ├── api.ts           # Axios client + auth interceptor + 401 redirect
│   ├── haptics.ts       # navigator.vibrate patterns
│   ├── sentry.ts        # Sentry init + captureError + setUser
│   ├── vitals.ts        # Core Web Vitals (LCP/FID/CLS/FCP/TTFB)
│   └── analytics.ts     # Event tracking (batched, sendBeacon)
├── services/            # One per domain, all use shared api client
│   ├── auth.service.ts  # sendCode, verify, setupPin, getProfile, logout
│   ├── wallet.service.ts # getWallets, getTotal, getFxRates
│   ├── transaction.service.ts # list, get, getRecent
│   ├── card.service.ts  # getInfo, getCvv, freeze, topup, withdraw
│   ├── wealth.service.ts # getProducts, getHoldings, purchase, redeem
│   ├── exchange.service.ts # getQuote, execute, getHistory
│   ├── remit.service.ts # getPayees, addPayee, preview, execute, timeline
│   ├── payout.service.ts # payoutUsdt, payoutCny, getNetworks
│   ├── topup.service.ts # getSwiftDetails, submitSwift, getUsdtAddress
│   ├── notification.service.ts # list, markRead, markAllRead
│   └── index.ts
├── stores/              # Zustand with loading/error states
│   ├── auth.store.ts
│   ├── wallet.store.ts
│   ├── transaction.store.ts
│   ├── card.store.ts
│   ├── wealth.store.ts
│   ├── notification.store.ts
│   ├── theme.store.ts   # localStorage + data-theme + system detection
│   └── index.ts
├── hooks/
│   ├── useAppBootstrap.ts # Global data init (call in App.tsx ShellLayout)
│   ├── useSwipeBack.ts  # Edge swipe gesture → navigate(-1)
│   └── index.ts
├── i18n/
│   ├── index.ts         # i18next + LanguageDetector + ReactI18next
│   ├── zh.json          # Chinese translations
│   └── en.json          # English translations
├── components/
│   ├── ErrorBoundary.tsx # Class component, retry + go home
│   ├── ScreenSkeleton.tsx # Suspense fallback for lazy routes
│   ├── RouteTransition.tsx # Page transition (forward/back detection)
│   └── ui/
│       ├── SkeletonScreen.tsx # HomeSkeleton, TxListSkeleton, CardSkeleton
│       └── PullToRefresh.tsx  # Touch-based pull-to-refresh wrapper
└── screens/             # All lazy-loaded via React.lazy()

mock-server/
├── server.js            # Express, all endpoints, in-memory mutable state
├── data/mock.js         # Centralized mock data
└── package.json
```

## Project Workpad Preflight (Long-running Frontend Loops)

Before starting a long-running React/frontend closure loop, especially when the user says “继续下一步”, “loop”, “pua-loop”, “A+”, or when a project-specific Workpad exists:

1. Load/read the project Workpad from `~/Documents/brain/05-实践与项目/projects/<project>/Workpad - <project>.md` if present.
2. Treat Workpad North Star, Red Lines, Anchors, Skill Route, Business Flow Matrix, and Acceptance Matrix as the active project contract.
3. If the Workpad references a comparison/prototype anchor, verify the anchor path exists before claiming parity. If the expected reference path is missing but a candidate exists elsewhere, record it as unresolved/provisional and ask or explicitly flag before parity-diff work.
4. Do not write project-specific transient state to global memory; update the Workpad/Evidence Ledger instead.
5. After each loop, deposit evidence into `docs/UI_TEST_CASES.md`, ADRs when needed, and the Workpad Evidence Ledger.

## Execution Sequence (Loop with P10 Self-Check Each Round)

### Round 1: Foundation
1. `npm i zustand axios`
2. Create `src/lib/api.ts` — Axios with auth interceptor
3. Create all `src/services/*.service.ts` — one per domain
4. Create all `src/stores/*.store.ts` — Zustand stores with loading/error
5. Create `mock-server/` — Express with all endpoints
6. Update `vite.config.ts` — API proxy to mock server
7. `node node_modules/typescript/bin/tsc --noEmit` verify

### Round 2: Screen Migration
1. Remove `import { ... } from '../data/mock'` from all screens
2. Add store/service imports
3. Replace hardcoded constants with store hooks
4. Use `useEffect` for data fetching
5. `tsc --noEmit` verify

### Round 3: Multi-Model Review (SMALL SCOPE)
Delegate 3 parallel subagents — **5-8 files each max**:
- Agent 1: API/Service layer review
- Agent 2: Screen layer review (sample screens)
- Agent 3: Security/Performance review
Fix all CRITICAL/HIGH issues found.

### Round 4: Dark Mode + Skeleton + Error Boundary
1. `src/stores/theme.store.ts` — persist to localStorage, set data-theme
2. Add `dark:` Tailwind variants to ALL components
3. Create `SkeletonScreen.tsx` with page-specific patterns
4. Create `ErrorBoundary.tsx` — 3 level (app/screen/component)
5. Wire into `App.tsx` — lazy + Suspense + ErrorBoundary

### Round 5: i18n + PWA + Monitoring
1. `npm i react-i18next i18next i18next-browser-languagedetector`
2. Create `src/i18n/` with zh/en JSON
3. Migrate screens to `useTranslation()` — use batch script (see below)
4. `npm i -D vite-plugin-pwa` + configure
5. `npm i @sentry/react web-vitals`
6. Create `sentry.ts`, `vitals.ts`, `analytics.ts`

### Round 6: Testing + Final Audit
1. `npm i -D vitest @testing-library/react @testing-library/jest-dom jsdom`
2. Create test files for stores and utilities
3. Programmatic completeness audit

### i18n Overflow Audit (After Migration)

After i18n migration, run 3 parallel subagents (5-8 files each):
- Agent 1: Screen audit — check fixed-width containers, missing truncation, flex without min-w-0
- Agent 2: Length audit — compare zh vs en string lengths, flag >4x ratios
- Agent 3: CSS audit — check Tailwind for missing truncate, overflow-hidden on grids

Critical overflow patterns:
- 4-column action grids (grid-cols-4): add `truncate` + `overflow-hidden` to labels
- Tab bars: "Quantitative" (12 chars) crowds narrow cells — add `max-w` or `truncate`
- Section titles: "Cross-border Remittance (SWIFT / E-wallet / Crypto)" = 51 chars
- Always add `min-w-0 truncate` to flex children containing text
- Currency names: use bilingual `{ zh, en }` pattern or i18n keys

### Programmatic i18n Fix (When Subagent Times Out)

When subagent times out on i18n text replacement, use `execute_code`:

```python
import os, re
for root, dirs, files in os.walk('src/screens'):
    for f in files:
        if not f.endswith('.tsx'): continue
        fp = os.path.join(root, f)
        content = open(fp).read()
        if 'useTranslation' in content: continue
        # Add import + hook call programmatically
        lines = content.split('\n')
        last_import = max(i for i, l in enumerate(lines) if l.startswith('import '))
        lines.insert(last_import + 1, 'import { useTranslation } from "react-i18next";')
        content = '\n'.join(lines)
        match = re.search(r'(export default function \w+\([^)]*\)\s*\{)', content)
        if match:
            content = content[:match.end()] + '\n  const { t } = useTranslation();' + content[match.end():]
        open(fp, 'w').write(content)
```

Then do common string replacement in a second pass, and add new i18n keys to zh.json/en.json.

### i18n Batch Migration (When Subagents Timeout)

**Subagents timeout on 55-file migrations.** Use `execute_code`:

```python
import os, re
base = "/path/to/src/screens"
for root, dirs, files in os.walk(base):
    for f in files:
        if not f.endswith('.tsx'): continue
        fp = os.path.join(root, f)
        content = open(fp).read()
        if 'useTranslation' in content: continue
        lines = content.split('\n')
        last_import = max(i for i, l in enumerate(lines) if l.startswith('import '))
        lines.insert(last_import + 1, 'import { useTranslation } from "react-i18next";')
        content = '\n'.join(lines)
        match = re.search(r'(export default function \w+\([^)]*\)\s*\{)', content)
        if match:
            content = content[:match.end()] + '\n  const { t } = useTranslation();' + content[match.end():]
        open(fp, 'w').write(content)
```

Then do text replacement for common Chinese strings in a second pass.

## "未动" Audit Pattern

Use `execute_code` to programmatically find gaps:

```python
app = open("src/App.tsx").read()
for c in ["ErrorBoundary", "Suspense", "useAppBootstrap", "AnalyticsTracker"]:
    print(f"  {'✓' if c in app else '✗'} {c}")

for root, dirs, files in os.walk("src/screens"):
    for f in files:
        if not f.endswith('.tsx'): continue
        c = open(os.path.join(root, f)).read()
        # Count: stores, services, i18n, loading, dark: adoption
```

## Vite Mock vs Real Backend Flow Verification

When browser-verifying auth/security flows in Vite apps, apply `references/vite-mock-real-backend-flow-verification.md`: inspect `vite.config.ts` and `VITE_API_BASE`, run both default dev and forced-mock routes when docs/demo fixtures disagree with behavior, inspect response bodies rather than HTTP status alone, capture screenshots/network/console evidence, and record split results such as `FAIL(default dev) / PASS(forced mock)` instead of flattening them into one verdict.

## Playwright E2E Testing for Financial Apps

After all architecture is in place, add E2E tests for flow closure:

```bash
npm install -D @playwright/test
npx playwright install chromium
```

### Key Test Patterns

```typescript
// tests/flow-closure.spec.ts
// Test PIN error recovery
test('wrong PIN → error → clear → retry → success', async ({ page }) => {
  await page.goto('/card/topup/pin?amt=100');
  // Enter wrong PIN via numbered buttons
  for (const d of '111111') {
    await page.click(`button:has-text("${d}")`);
  }
  await expect(page.locator('.text-danger')).toBeVisible();
  await page.waitForTimeout(500); // wait for auto-clear
  // Enter correct PIN
  for (const d of '888888') {
    await page.click(`button:has-text("${d}")`);
  }
  await page.waitForTimeout(2000);
  expect(page.url()).toContain('/order/');
});

// Test state leak on navigation
test('navigate away during flow does not crash', async ({ page }) => {
  await page.goto('/exchange');
  await page.fill('input', '5000');
  await page.goto('/home');
  // No JS errors
});

// Test double-submit protection
test('double-click does not duplicate transaction', async ({ page }) => {
  // ... verify debounce works
});
```

### Playwright Config
```typescript
// playwright.config.ts
export default defineConfig({
  use: { baseURL: 'http://localhost:5173' },
  webServer: {
    command: 'npm run mock',
    url: 'http://localhost:3001/api/wallets',
    reuseExistingServer: true,
  },
});
```

### Flow Closure Test Matrix
```
Flow         Steps                                    Verify
PIN verify   enter wrong → error → clear → retry     State resets, can retry
Exchange     select → amount → confirm → execute      Navigates to /order/
Remit        payee → amount → preview → PIN → SMS     Timeline loads
Card freeze  confirm → processing → frozen → unfreeze Status toggles
Wealth       browse → select → buy → confirm          Holding created
```

## Expo / React Native Mock Server Setup (Non-Vite)

When the project uses **Expo** (metro bundler) instead of Vite, the proxy and mock server setup differs:

### Step 1: Extract All API Endpoints from Service Files

Use `execute_code` to scan all service files for API patterns:

```python
import re
from pathlib import Path

api_calls = []
services_dir = Path('/path/to/project/services')
for file_path in services_dir.glob('*'):
    if file_path.suffix not in ['.ts', '.js']:
        continue
    content = file_path.read_text(encoding='utf-8')
    patterns = [
        (r'get\(`\$\{BASE_URL\}([^`]+)`', 'GET'),
        (r'post\(`\$\{BASE_URL\}([^`]+)`', 'POST'),
        (r'put\(`\$\{BASE_URL\}([^`]+)`', 'PUT'),
        (r'del\(`\$\{BASE_URL\}([^`]+)`', 'DELETE'),
    ]
    for pattern, method in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            api_calls.append({
                'file': file_path.name,
                'method': method,
                'path': f'/api{match}',
            })
```

This finds all endpoints including parameterized ones like `/api/ucard/${id}/details`.

### Step 2: Identify Response Format

Read the axios interceptor or service error handling to determine the response contract:
- Expo projects often use `{ code: 0, data: {...} }` for success
- Some use `{ success: true, data: {...} }` 
- Token failure is typically `code === -4` (redirect to login)
- Account disabled is `code === -6`

### Step 3: Mock Server (Node.js built-in http module)

**Do NOT install Express** — npm peer dep conflicts are common in Expo projects. Use Node.js built-in `http` module:

```javascript
// scripts/mock-server.js
const http = require('http');
const url = require('url');

const PORT = 9999;

// Route handlers grouped by domain
const routes = {
  // Auth — return success directly (API key related)
  'POST /api/auth/login': () => ({ code: 0, data: { token: 'mock_token_abc123', user: { id: '1', email: 'test@test.com', name: 'Test User' } } }),
  'POST /api/auth/register': () => ({ code: 0, data: { message: '注册成功' } }),
  'POST /api/auth/send-code': () => ({ code: 0, data: { message: '验证码已发送' } }),
  // ... all 174 endpoints
};

const server = http.createServer((req, res) => {
  const parsed = url.parse(req.url, true);
  const key = `${req.method} ${parsed.pathname}`;
  const handler = routes[key] || routes[`GET ${parsed.pathname}`];
  
  if (handler) {
    const body = [];
    req.on('data', chunk => body.push(chunk));
    req.on('end', () => {
      const data = handler(parsed.query, body.length ? JSON.parse(Buffer.concat(body).toString()) : {});
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(data));
    });
  } else {
    // Fallback: return generic success for unmatched routes
    console.log(`⚠️  Unmatched: ${key}`);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ code: 0, data: {} }));
  }
});

server.listen(PORT, () => console.log(`Mock server on http://localhost:${PORT}`));
```

### Step 4: Configure metro.config.js Proxy

Expo uses `metro.config.js` with `http-proxy-middleware`. Change the proxy target to local mock server:

```javascript
// In metro.config.js, find the proxy configuration
// Change url[index] to point to mock server
const url = [
    'http://localhost:9999',  // ← Mock server (was remote API)
    'https://realtest.hmalls.cn:9998/ucard',
    'https://app.denatrust.com',
];
const index = 0;  // ← Changed from 2 to 0

// The proxy uses enhanceMiddleware pattern:
apiProxy = createProxyMiddleware({
    target: url[index],
    changeOrigin: true,
    secure: false,
    pathRewrite: { '^/api': '/api' },
});
```

**Key difference from Vite**: Expo uses `defaultConfig.server.enhanceMiddleware` to intercept requests, not `server.proxy` in vite.config.ts.

### Step 5: Run Both Servers

```bash
# Terminal 1: Mock server
node scripts/mock-server.js

# Terminal 2: Expo dev server
EXPO_NO_TELEMETRY=1 expo start --web
```

### Pitfalls for Expo Mock Server

1. **npm install fails in Expo projects**: Use Node.js built-in `http` module, not Express. Expo's dependency tree has strict peer dep constraints.

2. **metro.config.js proxy structure**: The proxy is NOT in `server.proxy` like Vite. It's in `defaultConfig.server.enhanceMiddleware` which wraps the middleware function.

3. **FormData handling**: Expo's axios interceptor sends `multipart/form-data` with FormData. Mock server must handle multipart parsing or accept any Content-Type.

4. **BASE_URL is conditional**: `process.env.NODE_ENV === 'development' ? '/api' : 'https://app.denatrust.com/api'`. Mock server only works in dev mode because that's when requests go through `/api` proxy. **FIX for production builds**: Change to `Platform.OS === 'web' ? '/api' : (process.env.NODE_ENV === 'development' ? ... : ...)`. This makes web always use relative paths (works with both proxy in dev and same-origin in prod). Native keeps full URLs. Without this fix, production builds will call the remote API instead of the local mock server.

5. **Path parameters**: Endpoints like `/api/ucard/${id}/details` need regex matching in mock server, not exact string match. Use a route matcher that handles `:id` patterns.

6. **Token in headers**: The app sends `Authorization` header with stored token. Mock server should accept any token value — don't validate.

7. **Fallback handler is critical**: Unmatched routes should return `{ code: 0, data: {} }` not 404. This prevents the app from crashing on endpoints you haven't mocked yet. Log unmatched routes to build the complete list iteratively.

8. **Loop until flow closed**: Run the app, navigate every screen, watch mock server logs for unmatched routes → add handlers → repeat until zero unmatched.

## Mock Data Format Discovery (Critical Pattern)

When building a mock server, the #1 failure mode is **wrong data format**. Frontend hooks/components destructure response data in specific ways that are NOT obvious from the service layer. You must read the hooks and page components to discover the exact expected shape.

### Discovery Method

1. **Read the hook** (e.g., `useBalances.ts`, `useUCard.ts`) — find `formatData()` or `map()` calls
2. **Read the page component** — find destructuring patterns like `({trade}) =>` or `res.list.map()`
3. **Check field names** — `item.coin_name` not `item.currency`, `product.ID` not `product.id`
4. **Check types** — `.toFixed()` and `reduce((sum, x) => sum + x, 0)` require numbers, not strings

### Common Format Mismatches (Expo/React Native)

| Endpoint | WRONG (naive mock) | RIGHT (frontend expects) |
|----------|-------------------|--------------------------|
| wallet/balances | `{fiat:[{currency:'USD'}], crypto:[...]}` | `{list:[{coin_name:'USD', balance:'5000.00'}]}` |
| wallet/sec-balances | `[{symbol:'USDT', balance:'1500'}]` | `{list:[{coin_name:'USDT', balance:1500}]}` — balance MUST be number |
| wallet/fiat/fee | `{deposit_fee_rate:'0.01'}` | `{fb:{recharge_fee:0.01,...}, sec:{network_fee:0.0005,...}}` |
| ucard/trades | `{list:[{id:'t1', type:'payment', amount:-50}]}` | `{list:[{trade:{ID:'t1', action:'payment', status:'success', amount:-50, mask_id:'****1111'}}]}` |
| investment/products | `{list:[{id:'prod001', apy:'8.5%'}]}` | `{list:[{ID:'prod001', expected_return:'8.5', min_amount:100}]}` |
| investment/holdings | `{list:[{id:'hold001', amount:'5000'}]}` | `[{holding:{ID:'hold001', product_id:'prod001', amount:5000}}]` |
| investment/today-earnings | `{today_earnings:'12.50'}` | `{earnings:[{amount:12.50, product_name:'Fund'}]}` |
| investment/holding/:id/chart | `{chart:[{date:'...', value:5000}]}` | `[{date:'...', value:5000}]` — array directly, not wrapped |
| wallet/sec-balances (type) | `{list:[{coin_name:'USDT', balance:'1500.00'}]}` | `{list:[{coin_name:'USDT', balance:1500}]}` — string balance causes `toFixed is not a function` in `reduce((sum, x) => sum + x, 0)` |
| investment/today-earnings (type) | `{earnings:[{amount:12.50}], total_earnings:'425.00'}` | `total_earnings` MUST be number — `convert(amount)` calls `.toFixed(2)` on it |

### `.toFixed()` Type Chain Rule

Any value that flows through `CurrencyContext.tsx` → `convertAmount(amount, ...)` → `amount.toFixed(2)` MUST be a number at every point in the chain. One string breaks the entire page. This affects:
- `portfolioData.totalAssets`, `totalReturn`, `todayReturn`
- `walletBalances[].balance`, `cryptoBalances[].balance`
- `holdings[].amount`, `holdings[].earnings`
- `total_earnings`, `total_amount` from API responses

**Detection**: If a page crashes with `toFixed is not a function`, trace the value back through hooks/stores to the API response. The root cause is always a string where a number is expected.

### Unified Production Server (serve.js)

After building `dist/`, create a single Node.js server that handles both mock API and static files. Two variants:

**ESM variant (recommended for Vite projects)**:
```javascript
// serve.js — ESM, conditional mock loading
import express from 'express';
import cors from 'cors';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.PORT || 3000;
const ENABLE_MOCK = process.env.MOCK !== 'false';

app.use(cors());
app.use(express.json());

if (ENABLE_MOCK) {
  const { WALLETS, ... } = await import('./mock-server/data/mock.js');
  // ... mount all API routes
  console.log('[mock] API routes mounted at /api');
}

// Static files with caching
app.use(express.static(join(__dirname, 'dist'), {
  maxAge: '1y', immutable: true, index: false,
  setHeaders(res, path) {
    if (path.endsWith('.html')) res.setHeader('Cache-Control', 'no-cache');
  },
}));

// SPA fallback (MUST be last)
app.get('*', (_req, res) => {
  res.sendFile(join(__dirname, 'dist', 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`🌐 http://localhost:${PORT}`);
});
```

Key: HTML gets `no-cache`, JS/CSS get `1y immutable`. SPA fallback catches all non-API, non-static routes.

**CJS variant (for Expo/legacy projects)**:
```javascript
const http = require('http');
const fs = require('fs');
const path = require('path');
// ... see Unified Production Server Pattern above
```

### Docker Deployment

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY mock-server/package*.json ./mock-server/
RUN cd mock-server && npm ci --production
COPY serve.js ./
COPY mock-server/data ./mock-server/data
COPY dist ./dist
EXPOSE 3000
ENV NODE_ENV=production
CMD ["node", "serve.js"]
```

Add `.dockerignore`:
```
node_modules
src
mock-server/node_modules
*.md
.git
```

### Pitfalls for Unified Server
- **express not in root node_modules**: If express is only in `mock-server/node_modules`, either `npm i express cors` at root or symlink: `ln -sf mock-server/node_modules/express node_modules/express`
- **ESM imports**: Use `await import()` for conditional mock loading, not `require()`. ESM `await` at top level works in `.js` files with `"type": "module"` in package.json
- **SPA fallback must be LAST**: After `express.static()` and all API routes, `app.get('*', ...)` catches everything else
- **vite build without tsc**: When `tsc -b` fails on pre-existing errors, run `node node_modules/vite/bin/vite.js build` directly to skip type checking

### Key differences from dev mock server

- **Balance fields used in `.toFixed()` or `reduce((sum, x) => sum + x)`**: MUST be `number`, not `string`
- **ID fields used in routing (`product.ID`)**: MUST be uppercase `ID`, not `id`
- **Nested destructuring (`{trade: {...}}`, `{holding: {...}}`)**: MUST have the nesting wrapper
- **Array vs object**: Some endpoints return bare arrays `[{...}]`, others wrap in `{list: [...]}`
- **`.toFixed(2)` propagation**: If a value flows into `convert(amount, ...)` which calls `amount.toFixed(2)`, the value MUST be number at every point in the chain — including `total_earnings`, `total_amount`, `earnings[].amount`. One string in the chain breaks the entire page.
- **`reduce((sum, x) => sum + x, 0)` with strings**: If any `x` is a string like `"1500.00"`, the reduce produces string concatenation `"01500.002.5"` instead of `1502.5`. All values feeding into numeric reduce MUST be numbers.

### Parallel Subagent Strategy for 100+ Endpoints

When the project has 100+ API endpoints, use 3 parallel subagents to generate handlers by domain:
- Agent 1: Auth + User + KYC (40-50 endpoints)
- Agent 2: Wallet + UCard (60-70 endpoints)
- Agent 3: Investment + Notifications + Chat + Misc (40-50 endpoints)

Each agent writes to `/tmp/mock-{domain}.js`, the main server imports all three.

### Full Endpoint Self-Check (After Build)

After the mock server is built, run a programmatic self-test of ALL endpoints:

```python
import subprocess, json

BASE = "http://localhost:9969"

def test_get(path):
    try:
        result = subprocess.run(["curl", "-s", f"{BASE}{path}"],
            capture_output=True, text=True, timeout=5)
        data = json.loads(result.stdout)
        return data.get("code") == 0 and data.get("data") is not None
    except: return False

def test_post(path, data=None):
    try:
        cmd = ["curl", "-s", "-X", "POST", f"{BASE}{path}",
               "-H", "Content-Type: application/json",
               "-d", json.dumps(data or {})]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        data = json.loads(result.stdout)
        return data.get("code") == 0 and data.get("data") is not None
    except: return False

# Group endpoints by domain, test each group
categories = {
    "AUTH": [("POST", "/api/auth/login", {"account":"test","password":"123"}), ...],
    "WALLET": [("GET", "/api/wallet/balances", None), ...],
    # ... all domains
}
for cat, endpoints in categories.items():
    passed = sum(1 for m, p, d in endpoints if (test_get if m=="GET" else test_post)(p, d))
    print(f"{'✅' if passed == len(endpoints) else '❌'} {cat} {passed}/{len(endpoints)}")
```

This catches missing handlers, wrong response shapes, and runtime errors in mock data before the browser test phase.

### Iterative Fix Loop

When the task is **syncing missing pages from a prototype/reference project** (not building service layers from scratch), use this focused workflow instead of the full migration:

### Trigger Conditions
- User points to a prototype directory (e.g. `uvisa-app-2.0`) and says "sync", "copy missing pages", "补充缺少页面"
- Two React projects need page-level reconciliation

### Quick Steps
1. **File diff**: `diff <(find proto/src/screens -name "*.tsx" | sed 's|.*/src/screens/||' | sort) <(find curr/src/screens ...)` — identify missing screens
2. **Copy + adapt**: Copy missing files, fix TS errors (type narrowing, unused params, import paths)
3. **Register routes**: Add lazy imports + `<Route>` entries in App.tsx following current patterns (lazy for default exports, direct import for named exports)
4. **Fix navigation links** (most commonly missed!): Diff `nav()` targets between prototype and current screens. Existing screens that should link to new pages often still point to old/wrong paths.
5. **Verify**: File diff = 0, route diff = 0, all nav targets have routes, all imports resolve, 0 new TS errors, tests pass

### Common Navigation Gaps
- SecurityCenterScreen: all sub-links point to `/me/security` (self) instead of `/me/security/phone`, `/email`, etc.
- HomeScreen "更多": points to `/remit` instead of `/more`
- PayeeListScreen "新建": points to `/remit` instead of `/remit/payees/new`
- PayoutHubScreen: USDT/USDC both point to `/payout/usdt` instead of `/payout/crypto/USDT` and `/payout/crypto/USDC`

### Pitfalls
- **Named vs default exports**: `lazy()` only works with default exports. Named exports (e.g. `PaymentVerifyScreens` exporting multiple components) need direct `import { X } from "..."`
- **i18n key gaps**: Prototype uses hardcoded strings, current uses `t("key")`. Either add keys to zh.json/en.json or use literals.
- **Missing data files**: Always trace imports from new screens — they may need `payeeStore.ts`, `securityStore.ts`, etc. that don't exist yet.
- **Pre-existing errors masking new issues**: Filter build output to only show errors from new files.
- **`tsc -b` fails on pre-existing errors**: When `npm run build` is `tsc -b && vite build` and tsc fails, run `node node_modules/vite/bin/vite.js build` directly to skip type checking. The build will still catch runtime import errors.
- **vite preview does NOT proxy**: `vite preview` uses the `preview` config section, not `server.proxy`. In Vite 5+, the proxy works in preview mode too, but verify with `curl http://localhost:4173/api/wallets`. If it returns HTML (index.html) instead of JSON, the proxy isn't working — use the dev server instead or configure `preview.proxy` separately.

### Multi-Dimensional Verification (10-Dimension Cross-Check)

When the sync is complete, run these additional cross-checks beyond file/route diff:

1. **File-level diff**: `diff <(find proto/src -name "*.tsx" -o -name "*.ts" | sed 's|proto/src/||' | sort) <(find curr/src ...)` — identify ALL missing files (screens + components + data + lib)
2. **Route-level diff**: Extract all `path=` from both App.tsx, sort, diff — should be identical (or curr has MORE)
3. **Navigation target coverage (dynamic)**: `grep -roh 'nav(\`/[^\`]*\`' src/screens/ | sed 's/nav(\`//;s/\`$//' | sort -u` — extract template-string nav targets
4. **Navigation target coverage (static)**: `grep -roh 'nav("/[^"]*"' src/screens/ | sort -u` — extract string nav targets
5. **Link to= static paths**: `grep -roh 'to="/[^"]*"' src/screens/ | sort -u` — compare `<Link>` targets
6. **Type export parity**: `diff <(grep "export" proto/src/types/index.ts | sort) <(grep "export" curr/src/types/index.ts | sort)` — ensures no type was lost
7. **Data file parity**: `diff <(ls proto/src/data/) <(ls curr/src/data/)` — ensures all data modules copied
8. **Component import resolution**: For every new file, resolve all relative imports and verify the target exists. Use a Python script to walk imports and check file existence.
9. **Missing nav targets**: Compare prototype nav targets against current routes — any nav target without a route = broken navigation
10. **Architecture diff**: Check if prototype uses different flows (e.g. centralized `/pay/verify/pin` vs per-screen PIN screens) — document the difference, don't force one pattern

- **Reference anchor unresolved during parity work**: If a Workpad or user request says “align with reference uvisa-app/prototype”, first verify the reference path exists and enumerate routes/screens. Do not claim parity against a missing path. If another candidate path exists (for example under Downloads), mark it provisional until the user confirms it.

## TypeScript Build Error Triage

When `tsc -b` fails with many errors during migration, don't fix file-by-file. Categorize first:

### Category: Missing Test Framework Types (TS2593)
`Cannot find name 'beforeEach'/'describe'/'vi'` → Add `"vitest/globals"` to `tsconfig.app.json` types array.

### Category: Plugin API Drift (TS2561/TS2322)
- `vite-plugin-compression2` v2: `algorithm` → `algorithms` (array: `['brotliCompress']`)
- Vitest `test` config: `import { defineConfig } from 'vitest/config'` (not from `'vite'`)

### Category: Variable Shadowing → "Not Callable"
When `t('...')` errors as "Type 'Number' has no call signatures":
- `const t = setTimeout(...)` shadows `useTranslation()`'s `t` → rename timer
- `.map((t) => { t('...') })` shadows translation `t` → rename param to `tx`

### Category: Implicit `any` in Zustand Selectors (TS7006)
`useXxxStore((s) => s.field)` where `s` is `any`:
1. Export state interfaces: `export interface WalletState { ... }`
2. Import types: `import type { WalletState } from '../stores/wallet.store'`
3. Annotate: `useWalletStore((s: WalletState) => s.wallets)`

Same for `.filter((t) => ...)` and `.map((tx, i) => ...)` callbacks — add explicit parameter types.

### Category: Zustand v5 Persist Changes
- `onFinishHydration` removed → use `onRehydrateStorage` in persist config instead
- `transactions: []` inferred as `never[]` → `[] as Transaction[]`
- `useXxxStore.getState()` circular ref → use `(set, get)` store creator param, call `get()`

### Category: Test Mock Type Mismatches
Use `as any` for test mock data objects. Tests verify behavior, not type correctness.
For `ApiResult<T>` mocks missing `data` field: `mockResolvedValue({ success: false } as any)`.

### Verification
After each fix batch:
```bash
npx tsc -b 2>&1 | grep -c 'error TS'             # count remaining
npx tsc -b 2>&1 | grep '^src/' | grep -v '__tests__' | grep -v 'src/test/'  # source only
```

## Pitfalls

1. **#1 FAILURE: Subagent timeout on large scopes**: MiMo model subagents silently return empty response when reading 10+ large files. Diagnostic: "Model returned empty after tool calls". FIX: limit each subagent to 5-8 files. For mass changes (55-screen i18n migration), use `execute_code` with programmatic file manipulation instead of delegating to subagents.

2. **Tool name mismatch**: Skills reference `read_multiple_files` but actual tool is `mcp_filesystem_read_multiple_files`. FIX: use `read_file`/`terminal` in subagent prompts.

3. **i18n subagent timeout**: 55-screen i18n migration via subagent always times out. FIX: use `execute_code` programmatic approach — add import + useTranslation to all files in one script, then do text replacement in a second pass.

4. **npm cache permissions (macOS)**: `npm install --cache /tmp/npm-cache` workaround.

5. **vite-plugin-pwa peer deps**: May need `--legacy-peer-deps` for vite 8.

6. **tsc path (macOS)**: `node node_modules/typescript/bin/tsc --noEmit` (not `npx tsc`).

7. **Mock data separation**: Keep UI config (colors, labels) inline. Only move business data to mock server.

8. **Dark mode without UI changes**: Add `dark:` to existing className strings. Don't change JSX structure.

9. **Screen count reality check**: ~23/55 screens are static/input-only (auth, settings, PIN entry). They don't need stores, loading states, or PullToRefresh. The "58% store adoption" for data-fetching screens is actually 100%.

10. **i18n text overflow**: Chinese → English text expands 2-5x. CRITICAL areas:
    - 4-column action grids (ActionBtn, CardAction): add `truncate` + `overflow-hidden`
    - Tab bars: English labels like "Quantitative" (12 chars) crowd narrow cells
    - Section titles: "Cross-border Remittance (SWIFT / E-wallet / Crypto)" = 51 chars
    - Always add `min-w-0 truncate` to flex children that contain text
    - Use `flex-wrap` on product card metadata rows

11. **web-vitals API change**: `onFID` removed in v5, use `onINP` instead.

12. **Hardcoded version strings**: Use `src/lib/version.ts` with `APP_VERSION` constant, reference in MeScreen + AboutScreen.

13. **PWA icons**: Must be real PNG files (not SVG). Generate with Pillow or download from Figma.

14. **Mock server not in build**: `npm run build` only bundles frontend. Mock server deploys separately (Railway/Render/VPS).

15. **Mock server API path mismatch**: Frontend services may call different paths than mock server endpoints. Always run the path alignment check (Round 9.5) before declaring "done".

16. **browser_console for flow verification**: Can test all API endpoints directly in the browser without Playwright. Faster than E2E tests for verifying endpoint existence and error handling.

17. **vite-plugin-pwa registerType 'prompt'**: Must NOT have `skipWaiting: true` or `clientsClaim: true` in workbox config. The 'prompt' mode handles SKIP_WAITING via the useServiceWorkerUpdate hook.

18. **PWA icons must be real PNG**: Generate with Pillow (`from PIL import Image`) if design tools unavailable. SVG icons don't work for PWA manifest.

### Dark Mode CSS Variable Pattern (Critical Fix)

When dark mode renders as "all black" or nav bar is invisible, the root cause is usually hardcoded rgba/hex colors without dark variants. The fix pattern:

```css
/* BEFORE — hardcoded, no dark variant */
.glass {
  background: rgba(255,255,255,0.72);
  border: 0.5px solid rgba(255,255,255,0.7);
}
.hairline { box-shadow: inset 0 -0.5px 0 #F0F2F5; }

/* AFTER — CSS variables with dark variants in :root and [data-theme="dark"] */
:root, [data-theme="light"] {
  --glass-bg: rgba(255,255,255,0.72);
  --glass-border: rgba(255,255,255,0.7);
  --border: #F0F2F5;
  --surface: #FFFFFF;
}
[data-theme="dark"] {
  --glass-bg: rgba(30,33,40,0.82);
  --glass-border: rgba(255,255,255,0.06);
  --border: #2A2D35;
  --surface: #1B1E25;
}
.glass {
  background: var(--glass-bg);
  border: 0.5px solid var(--glass-border);
}
.hairline { box-shadow: inset 0 -0.5px 0 var(--border); }
```

**Bulk screen dark mode fix** (when 50+ screens have `bg-white` without `dark:`):
```python
# execute_code batch fix
content = content.replace(
    'bg-white shadow-card',
    'bg-white dark:bg-surface-elevated dark:shadow-none shadow-card'
)
content = content.replace('text-ink-900', 'text-ink-900 dark:text-ink-50')
content = content.replace('text-ink-500', 'text-ink-500 dark:text-ink-400')
content = content.replace('bg-ink-50', 'bg-ink-50 dark:bg-ink-800/50')
```

### Build Size Optimization

Target: <250KB gzipped JS+CSS. Add compression and chunk splitting:

```typescript
// vite.config.ts
import viteCompression from 'vite-plugin-compression2';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({ registerType: 'prompt', /* ... */ }),
    viteCompression({ algorithm: 'gzip' }),
    viteCompression({ algorithm: 'brotliCompress' }),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'i18n-vendor': ['i18next', 'react-i18next', 'i18next-browser-languagedetector'],
          'vendor': ['zustand', 'axios'],
        },
      },
    },
  },
});
```

Verify: `for f in dist/assets/*.js dist/assets/*.css; do gzip -c "$f" | wc -c; done | awk '{s+=$1} END {print s/1024 " KB gzipped"}'`

### i18n Key Alignment Check

After migration, verify zh/en keys match:

```python
def flatten_dict(d, prefix=''):
    items = []
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict): items.extend(flatten_dict(v, key))
        else: items.append(key)
    return items

zh_keys = flatten_dict(json.load(open('src/i18n/zh.json')))
en_keys = flatten_dict(json.load(open('src/i18n/en.json')))
missing_en = set(zh_keys) - set(en_keys)
missing_zh = set(en_keys) - set(zh_keys)
print(f"zh: {len(zh_keys)}, en: {len(en_keys)}, missing_en: {missing_en}, missing_zh: {missing_zh}")
```

### Test Writing Patterns for Stores/Services

```typescript
// Store test — mock the API service
vi.mock('../../services/auth.service', () => ({
  authService: {
    sendCode: vi.fn().mockResolvedValue({ success: true }),
    verifyCode: vi.fn().mockResolvedValue({ token: 'test', user: mockUser }),
  },
}));

// Service test — mock the api client
vi.mock('../../lib/api', () => ({
  api: { get: vi.fn().mockResolvedValue({ data: { success: true, data: [...] } }),
         post: vi.fn().mockResolvedValue({ data: { success: true } }) },
}));

// Hook test — renderHook + act
const { result } = renderHook(() => useOnlineStatus());
act(() => { window.dispatchEvent(new Event('offline')); });
expect(result.current).toBe(false);
```

### P10 Self-Check Checklist (Each Round)

```python
# Run after each round
checks = {
    'TypeScript': os.system('tsc --noEmit') == 0,
    'Tests': os.system('npx vitest run --reporter=json') == 0,
    'i18n aligned': len(zh_keys) == len(en_keys),
    'dark mode screens': dark_screen_count / total_screens >= 0.95,
    'dark mode components': dark_comp_count / total_components >= 0.80,
    'build gzip < 250KB': gzip_size < 256000,
}
for name, ok in checks.items():
    print(f"  {'✓' if ok else '✗'} {name}")
```

## Round 7: Security Hardening (CRITICAL for financial apps)

### Route Guards
```
src/components/ProtectedRoute.tsx:
- Checks useAuthStore((s) => s.isAuthenticated)
- Redirects to /login via <Navigate> if not authenticated
- In App.tsx: wrap all non-auth routes in ProtectedLayout (Outlet pattern)
```

### PIN Attempt Limiting
```
src/lib/pinGuard.ts:
- trackAttempt(key): { blocked, remaining, lockoutUntil }
- Max 5 attempts per 10-min rolling window, 5-min lockout
- Stored in sessionStorage (resets on tab close)
- usePinGuard(key) hook for React components
```

### Session Timeout
```
src/hooks/useSessionTimeout.ts:
- Tracks lastActivity, resets on click/keydown/touchstart/mousemove
- Checks every 60s: idle > 15 min → authStore.logout() + redirect
- visibilitychange: tab hidden > 30 min → logout on return
- Call useSessionTimeout() in App.tsx ShellLayout
```

### Token Refresh with Request Queuing
```
In src/lib/api.ts response interceptor:
- On 401: try POST /auth/refresh with stored refresh_token
- Queue concurrent 401s in failedQueue
- If refresh succeeds: replay all queued requests
- If refresh fails: clear tokens, redirect to /login
- Add refreshToken() to auth.service.ts
```

### Replace Hardcoded PINs
```
src/lib/pinVerify.ts:
- verifyPin(pin) → calls POST /auth/pin/verify if API available
- Falls back to VITE_DEMO_PIN env var (default "888888")
- All 5 PIN screens use this + pinGuard instead of const CORRECT = "888888"
```

### Shared Validators
```
src/lib/validators.ts:
- isWeakPin(pin): checks 18 common PINs + all-same-digit
- isValidAmount(val, min, max, decimals): range + precision check
- isValidEthAddress(addr): 0x + 40 hex chars
```

### i18n Security Fix
```
In src/i18n/index.ts: change escapeValue: false → true
(Financial apps MUST escape HTML in translations)
```

## Round 8: Architecture Protection

### Zustand Middleware (all 7 stores)
```typescript
import { create } from 'zustand';
import { persist, devtools, createJSONStorage } from 'zustand/middleware';

export const useStore = create<State>()(
  devtools(
    persist(
      (set, get) => ({ /* state & actions */ }),
      {
        name: 'store-name',
        storage: createJSONStorage(() => sessionStorage),
        partialize: (state) => ({ /* critical fields only */ }),
      }
    ),
    { name: 'StoreName' }
  )
);
```

### Request Cancellation
```
src/lib/useApiEffect.ts:
- useApiEffect(url, deps, onData) — auto-cancels on unmount
- useCancelScope() — low-level AbortController wrapper
```

### Financial CTA Debounce
```
src/hooks/useDebounceAction.ts:
- Wraps callback to ignore rapid repeated calls within delay ms
- Use on all financial operation buttons (1000ms default)
```

### Offline Detection
```
src/hooks/useOnlineStatus.ts: navigator.onLine + events
src/components/OfflineBanner.tsx: sticky yellow warning bar
Wire <OfflineBanner /> in App.tsx ShellLayout
```

### Feature Flags
```
src/lib/featureFlags.ts:
- Static config with isEnabled(flag) + useFeature(flag) hook
- Can be swapped for remote config later
```

### Retry Logic
```
src/lib/retry.ts:
- withRetry<T>(fn, maxRetries=3, delay=1000) with exponential backoff
```

### Transaction Export
```
src/lib/exportUtils.ts:
- exportToCsv(transactions, filename) using Blob + URL.createObjectURL
- BOM prefix for Excel CJK compatibility
```

## Round 9: PWA Update Notification

### Problem
With `registerType: 'autoUpdate'`, users don't see updates because SW silently caches old assets.

### Solution: `registerType: 'prompt'` with Forced Countdown
```
vite.config.ts:
  VitePWA({ registerType: 'prompt', ... })
  → SW installs but waits for user confirmation before activating

src/hooks/useServiceWorkerUpdate.ts:
  → Detects 'updatefound' event on SW registration
  → When new SW state === 'installed' && controller exists → isUpdateAvailable = true
  → Modes: 'prompt' (user clicks) or 'forced' (30s countdown then auto-update)
  → updateApp() sends { type: 'SKIP_WAITING' } to waiting SW
  → 'controllerchange' event fires → page.reload()
  → checkForUpdate() for manual version check (wire to MeScreen version card)

src/components/UpdateBanner.tsx:
  → Shows sticky banner: "发现新版本  28s  [立即更新]"
  → In 'forced' mode: countdown timer, auto-updates when 0
  → In 'prompt' mode: user clicks to update
  → Calls updateApp() on click or countdown expiry
  → Dark: mode support
```

### Manual Version Check (MeScreen Integration)
Wire `checkForUpdate()` from useServiceWorkerUpdate to MeScreen version card:
```tsx
const { checkForUpdate, updateStatus } = useServiceWorkerUpdate();
// onClick={checkForUpdate} on version card button
// updateStatus: 'idle' | 'checking' | 'available' | 'up-to-date'
// Show spinner when checking, green check when up-to-date
```

### Update Flow
```
SW registers → checks every 60 min + on mount
New version found → installs in background
isUpdateAvailable = true → banner shows with countdown
User clicks OR countdown hits 0 → SKIP_WAITING → new SW activates → page reloads
Fresh assets from new cache
```

### Dynamic Version Display
Create `src/lib/version.ts`:
```typescript
export const APP_VERSION = '1.0.0';
export const BUILD_NUMBER = '24042701';
export const FULL_VERSION = `v${APP_VERSION} (build ${BUILD_NUMBER})`;
```
Reference in MeScreen and AboutScreen instead of hardcoded 'v1.0.0'.

## Round 9.5: Mock Server API Path Alignment (CRITICAL)

After all services are created, verify frontend paths match mock server endpoints:

```bash
# Check POST endpoints match
for svc in src/services/*.service.ts; do
  paths=$(grep -o "'/[^']*'" $svc | tr -d "'" | sort -u)
  for p in $paths; do
    status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:3001/api$p" -H "Content-Type: application/json" -d '{}' 2>/dev/null)
    if [ "$status" = "404" ] || [ "$status" = "000" ]; then
      echo "❌ $svc → $p (HTTP $status)"
    fi
  done
done
```

Common mismatches (service → mock server):
- `exchange/execute` vs `exchange/confirm` — service uses execute, tests may use confirm
- `remit/preview` vs `remit/quote` — service uses preview, tests may use quote
- `auth/pin/setup` vs `auth/verify-pin` — service uses pin/setup
- `wealth/holdings/:id/redeem` vs `wealth/redeem` — service uses nested path

Fix: Add missing endpoint aliases to mock server (not change services).

### Browser-Based Flow Verification

Use `browser_console` to test all API endpoints directly in the running app:

```javascript
// Run in browser_console to verify all flows
async function fullAcceptanceTest() {
  const tests = [
    {name: 'Login', url: '/api/auth/verify', method: 'POST', body: {phone: '13856785678', code: '123456'}},
    {name: 'Wallets', url: '/api/wallets', method: 'GET'},
    {name: 'Exchange Quote', url: '/api/exchange/quote', method: 'POST', body: {from: 'USD', to: 'CNH', amount: 100}},
    {name: 'Exchange Confirm', url: '/api/exchange/confirm', method: 'POST', body: {from: 'USD', to: 'CNH', fromAmount: 100, toAmount: 720, rate: 7.2}},
    // ... all 17+ POST endpoints + 18 GET endpoints
    {name: 'Wrong PIN', url: '/api/auth/verify-pin', method: 'POST', body: {pin: '000000'}, expectFail: true},
  ];
  // Each test: fetch → check success field → log ✅ or ❌
}
```

This catches path mismatches, missing endpoints, and error handling gaps before they reach production.

## Round 10: Multi-Model Gap Analysis (Final)

After all rounds, run 3 parallel subagents (5-8 files each):
- Agent 1: Auth & Security audit (token, session, PIN, validation)
- Agent 2: Business Logic audit (exchange countdown, payout wiring, export, limits)
- Agent 3: Architecture Protection audit (persist, cancel, retry, feature flags)

16. **browser_console for flow verification**: Can test all API endpoints directly in the browser without Playwright. Faster than E2E tests for verifying endpoint existence and error handling.

17. **vite-plugin-pwa registerType 'prompt'**: Must NOT have `skipWaiting: true` or `clientsClaim: true` in workbox config. The 'prompt' mode handles SKIP_WAITING via the useServiceWorkerUpdate hook.

18. **PWA icons must be real PNG**: Generate with Pillow (`from PIL import Image`) if design tools unavailable. SVG icons don't work for PWA manifest.

19. **Mock server not in build**: `npm run build` only bundles frontend. Mock server deploys separately (Railway/Render/VPS). **EXCEPTION**: You can create a unified `serve.js` that serves both `dist/` static files AND mock API in one Node.js process (see Unified Production Server pattern below).

20. **Mock server API path mismatch**: Frontend services may call different paths than mock server endpoints. Always run the path alignment check (Round 9.5) before declaring "done".

21. **PWA Update Banner i18n keys**: Add `update.available` and `update.button` to zh.json/en.json. Use nested key structure (i18next supports it alongside flat keys).

22. **BottomSheet portal after PhoneCanvas removal**: When converting from PhoneCanvas prototype to real H5, BottomSheet portals into `#phone-portal` which no longer exists. Change to `document.body` with `fixed` positioning.

23. **Build gzip verification**: `du -sh dist/` shows uncompressed size. Always verify gzipped: `for f in dist/assets/*.js dist/assets/*.css; do gzip -c "$f" | wc -c; done | awk '{s+=$1} END {print s/1024 " KB"}'`

24. **web-vitals API change**: `onFID` removed in v5, use `onINP` instead.

## Round 11: H5 Conversion (Prototype → Production)

When the app uses PhoneCanvas for prototype display, convert to real H5:

1. Remove `<PhoneCanvas>` wrapper from App.tsx — render ShellLayout directly
2. Delete PhoneCanvas.tsx file
3. Replace fake StatusBar (9:41 + signal icons) with safe-area spacer:
   ```tsx
   export default function StatusBar() {
     return <div className="w-full shrink-0" style={{ height: 'env(safe-area-inset-top, 0px)' }} />;
   }
   ```
4. Fix BottomSheet: change portal target from `#phone-portal` to `document.body`, use `fixed` instead of `absolute`
5. Update index.html viewport: remove `maximum-scale=1.0, user-scalable=no`
6. Verify with tsc --noEmit

## BottomSheet Portal Fix (H5 Conversion)

When removing PhoneCanvas, BottomSheet portals into `#phone-portal` which no longer exists:

```typescript
// BEFORE (PhoneCanvas mode)
const host = document.getElementById("phone-portal");
// Uses absolute positioning relative to phone canvas

// AFTER (H5 mode)
// Portal into document.body with fixed positioning
return createPortal(
  <div className="fixed inset-0 z-[1000] ...">...</div>,
  document.body,
);
```

Key changes: `absolute` → `fixed`, `#phone-portal` → `document.body`, add `aria-modal` + `role="dialog"`.

## PIN Error Recovery Pattern

When PIN verification fails, the error state and input must be cleared in separate steps:

```typescript
// WRONG — race condition, both cleared simultaneously
setTimeout(() => { setPin(""); setError(null); }, 480);

// CORRECT — clear pin first, then error, with verifying guard
const [verifying, setVerifying] = useState(false);

useEffect(() => {
  if (pin.length !== 6 || error || verifying) return;
  setVerifying(true);
  verifyPin(pin).then((ok) => {
    setVerifying(false);
    if (ok) { /* success */ }
    else {
      // Track failure, show error
      setError({ key: Date.now(), msg: errorMsg });
      // Separate clearing: pin first, then error
      setTimeout(() => { setPin(""); }, 300);
      setTimeout(() => { setError(null); }, 480);
    }
  });
}, [pin, error, verifying]);
```

The `verifying` guard prevents double-triggering while async verification is in progress.

## Completion Checklist

- [ ] Infrastructure: 23/23 (api, stores×7, services×10, theme, error boundary, skeleton, route transition, pull-to-refresh, haptics, sentry, vitals, analytics, i18n, PWA, vitest, mock server, validators, pinGuard, pinVerify, exportUtils, featureFlags, retry)
- [ ] Code splitting: 55/55 lazy imports in App.tsx
- [ ] ErrorBoundary + Suspense wrapping all routes
- [ ] ProtectedRoute guarding all non-auth routes
- [ ] useSessionTimeout in App.tsx ShellLayout
- [ ] i18n: 55/55 screens use useTranslation, escapeValue: true
- [ ] Dark mode: 15+ components with dark: variants + theme store
- [ ] Loading states on data-fetching screens
- [ ] PullToRefresh on data screens
- [ ] Zustand persist + devtools on all 7 stores
- [ ] Token refresh with request queuing in api.ts
- [ ] PIN guard (5 attempts/10min) on all PIN screens
- [ ] No hardcoded PINs (use pinVerify.ts)
- [ ] Exchange real countdown timer (not hardcoded string)
- [ ] Payout screens call payoutService (not sessionStore)
- [ ] Transaction CSV export
- [ ] Debounce on financial CTAs
- [ ] OfflineBanner + useOnlineStatus
- [ ] Feature flags system
- [ ] Retry logic (exponential backoff)
- [ ] PWA update notification (registerType: 'prompt' + UpdateBanner with countdown)
- [ ] Manual version check wired to MeScreen
- [ ] Dynamic version display (src/lib/version.ts)
- [ ] Tests: vitest + Playwright E2E
- [ ] TypeScript: 0 errors
- [ ] Mock server: all endpoints matching services

## Programmatic Completeness Audit

After all rounds, run this to verify:

```python
import os, json

# 1. Infrastructure files
infra = ['api.ts', 'sentry.ts', 'vitals.ts', 'analytics.ts', 'haptics.ts',
         'validators.ts', 'pinGuard.ts', 'pinVerify.ts', 'exportUtils.ts',
         'featureFlags.ts', 'retry.ts', 'version.ts']
for f in infra:
    exists = os.path.exists(f'src/lib/{f}')
    print(f"  {'✓' if exists else '✗'} {f}")

# 2. Store middleware
for f in os.listdir('src/stores'):
    if f.endswith('.store.ts'):
        content = open(f'src/stores/{f}').read()
        has_persist = 'persist' in content
        has_devtools = 'devtools' in content
        print(f"  {f}: persist={has_persist} devtools={has_devtools}")

# 3. Screen adoption
for root, dirs, files in os.walk('src/screens'):
    for f in files:
        if not f.endswith('.tsx'): continue
        c = open(os.path.join(root, f)).read()
        has_i18n = 'useTranslation' in c
        # Check for remaining Chinese (acceptable: brand/bank/language names)
        import re
        chinese = re.findall(r'[\u4e00-\u9fff]+', c)
        # ... categorize and report
```

## Deployment

### Build
```bash
npm run build          # → dist/ (944KB, 71 JS chunks + PWA files)
npm run preview        # → localhost:4173 preview
```

### Deploy Frontend
```bash
# Cloudflare Pages
wrangler pages deploy dist --project-name uvisa-app

# Vercel
vercel --prod

# Netlify
netlify deploy --prod --dir=dist
```

### Deploy Mock Server (separate)
```bash
# On VPS
scp -r mock-server/ user@server:/opt/uvisa-mock/
ssh user@server "cd /opt/uvisa-mock && npm install --production && pm2 start server.js"

# Or Railway
cd mock-server && railway up
```

### Environment Variables
```bash
# .env.production
VITE_API_BASE=https://mock.uvisa.app/api  # → real API later
VITE_SENTRY_DSN=https://xxx@sentry.io/123
VITE_DEMO_PIN=                            # empty in prod
VITE_DEMO_SMS_CODE=                       # empty in prod
```

### CI/CD (GitHub Actions)
```yaml
on: push to main
steps: npm ci → npm test → npm run build → deploy to CDN
```

- `p10` — CTO strategic review
- `p10-architecture-self-check` — Architecture health check
- `loop` — PUA loop iteration
- `subagent-driven-development` — Parallel task execution
- `save-workflow-as-skill` — Save after completion
