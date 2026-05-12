---
name: source-driven-development
description: Reverse-engineer understanding from existing code — read the source to derive the spec, rather than assuming from documentation. Essential for legacy projects and onboarding.
triggers:
  - "how does this work?"
  - "what does this do?"
  - "joining an existing project with no/few docs"
  - "before modifying legacy code"
  - "trace the logic"
  - "follow the call chain"
model: default (MiMo) for reading/tracing, strong for synthesizing findings
---

# source-driven-development

When docs are stale or nonexistent, the source IS the spec. Read, trace, map, then act.

## The Golden Rule
> The source code is the only artifact that cannot lie about what the system actually does. Docs, comments, and tribal knowledge can drift. The AST does not.

## Process

### Step 1: Find the Entry Point
- Web app: `index.ts` → router → first handler
- CLI: `main()` or `cli()` function
- API: `app.ts` → middleware chain → first route

### Step 2: Trace One Complete Flow
Pick the simplest real workflow. Follow every function call, every conditional branch, every side effect:

```
entry → authenticate() → validate() → process() → respond()
         ↓ checks       ↓ zod       ↓ business  ↓ format
         token          schema      logic       response
```

### Step 3: Map Dependencies
- What does this module import? → upstream
- What imports this module? → downstream (blast radius)
- What external services does it call? → side effects

### Step 4: Identify Patterns
- Error handling style (throw vs return vs Result type)
- State management (Redux, Zustand, context, prop drilling)
- Data flow (unidirectional? event-driven? polling?)

### Step 5: Document Findings
Write a "source-derived spec" — not what SHOULD happen, but what DOES happen:
```
MODULE: auth.service.ts
PURPOSE: JWT token validation + user lookup
ENTRY: validateToken(token: string) → User | null
FLOW: decode JWT → check expiry → query DB → cache result (TTL 5min)
EDGE CASES: expired token → null; DB down → throws; malformed → null
```

## Product-Semantic Contract Audits

When checking whether an implementation matches updated product docs, do not stop at "the UI can display it" or "the field is parseable." Trace the source of truth and compare semantic meaning:

1. Read the product/acceptance docs and extract the exact semantic claim (for example: "notification time reflects backend timestamp" vs "funds flow time is consistent across Home/Account/Tx/Notification").
2. Trace the API response field names and values back to persistence/schema and write paths.
3. Compare related downstream views that must be consistent (for example notification time vs transaction ledger `posted_at`, order `created_at`, webhook received time, or business `occurred_at`).
4. Classify results separately:
   - `display_compatible`: frontend can render the value safely.
   - `contract_compatible`: response fields match the documented API/FE priority contract.
   - `semantic_compatible`: the value represents the product meaning (business event time, settlement time, etc.).
5. Treat generic fields like `time` as suspicious until their source is traced. A parseable `time = notification.created_at` may satisfy display but still fail a product requirement that expects event/transaction time consistency.
6. If semantics are unclear, recommend explicit fields rather than overloading display fields: e.g. `createdAt` for notification creation, `occurredAt` for business event time, and domain identifiers (`type`, `journalId`, `transactionId`) for cross-page consistency.

### Auth / Device Trust / Security-State Audits

When reviewing trust state, remembered devices, login routing, 2FA/PIN gates, or "24h fund lock" semantics, treat them as security controls rather than UI preferences. Trace every auth path and identify what is a server source of truth versus a client cache:

1. Trace all token-issuing routes, not just the route touched in the diff (OTP login, password login, legacy aliases, refresh if it mutates claims/state). Each must return or derive the same security-state fields needed by the frontend.
2. Client storage (`localStorage`, cookies writable by JS, Zustand persistence, IndexedDB) may support optimistic UI or backward-compatible display, but must not be the deciding source for skipping PIN/2FA/fund-lock gates. If backend state is missing or unreachable, default to the safer untrusted/step-up path.
3. Server endpoints that elevate trust (`trusted=true`, device whitelisting, disabling MFA, changing contact details) require a fresh server-verified step-up or equivalent policy check; an already-issued login JWT alone is not enough if the login flow has not completed the step-up yet.
4. Device identity must be traced to the actual identifier used by both client and server. UA-only fingerprints are acceptable for rough display/new-device notifications but too weak for trust decisions; prefer a server-stored hash of a stable client device id plus UA or another explicit device credential.
5. Compare user-facing copy to actual side effects. Do not let text promise email, lock removal, revocation, or notification behavior unless the backend path implements that specific side effect.
6. Verdicts should separate: `complete` (all paths covered), `safe` (server authority and step-up hold), and `not_overbuilt` (no unnecessary WebAuthn/fraud-engine requirements when a PIN step-up or explicit device id closes the acceptance).

## When Source > Docs
- Docs haven't been updated in 6+ months
- Comments contradict behavior (trust the code)
- "This should..." vs "This actually..."
- Legacy code with no original author available

## Verification
- [ ] Entry point identified
- [ ] One complete flow traced end-to-end
- [ ] Dependencies mapped (upstream + downstream)
- [ ] Source-derived spec written for modified module
- [ ] Product claims are classified as display-compatible / contract-compatible / semantic-compatible when docs are involved
- [ ] No assumptions from docs unless verified in source
