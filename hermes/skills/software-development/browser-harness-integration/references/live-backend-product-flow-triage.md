# Live Backend Product-Flow Triage

Use this reference when validating a frontend against a real deployed/test backend and a PRD/user-flow ledger. The goal is to separate route reachability, UI rendering, backend data/config drift, and true business-flow closure.

## Workflow

1. Establish the live-stack baseline
   - Start the local frontend with its dev proxy pointed at the deployed/test backend.
   - Log in with the provided test account using the real OTP/MFA path.
   - Verify tokens/storage exist, but never copy tokens or OTP codes into durable docs.
   - Confirm the home/asset page renders from real backend data before testing deeper flows.

2. Walk PRD flows as evidence tiers
   - Route reachable + page renders = only PARTIAL.
   - Critical API returns expected shape/data = stronger PARTIAL.
   - Write action + status transition + balances/notifications/ledger consistency = PASS for money/card flows.
   - If no safe permission to perform a real write, explicitly mark "not executed" rather than implying PASS.

3. Instrument browser evidence
   - Capture visible page text, screenshots, console errors, and the last network calls.
   - Compare canonical vs legacy API paths from the frontend service layer and backend controllers.
   - Redact credentials, OTP, tokens, account-private secrets, and payment PINs from summaries.

4. Source-level attribution
   - For each abnormal UI state, locate the frontend service/store and backend controller/data source.
   - Classify ownership: frontend display/route issue, backend API contract issue, backend DB/config issue, missing test seed, or PRD/test-ledger stale ID.
   - Do not hide backend drift with a frontend/mock shim before recording the real backend evidence.

5. Status language
   - PASS: full PRD user outcome verified, including required backend state changes.
   - PARTIAL: route/API/page works but a required downstream event is unverified.
   - FAIL: live behavior contradicts PRD or required data/state is absent.
   - BLOCKED: cannot proceed safely or required seed/permission/tooling is unavailable.

## Common findings and how to classify them

- Public config endpoint returns bank names, suppliers, account numbers, channels, webhooks, or implementation details: backend DB/config P0. Fix the public config source and add contract tests; do not rely on frontend hiding.
- Frontend uses a legacy compatibility endpoint while the backend has a canonical endpoint: contract drift. Verify both endpoints live; inspect the compatibility controller for placeholder/fallback behavior.
- A card/account page displays an operable placeholder when the canonical list endpoint is empty: frontend/backend contract issue plus missing seed. Mark no-card/activation state explicitly; do not treat placeholder as a real card.
- PRD or tests use mock-era IDs that are absent from live `/products`, `/holdings`, or similar list endpoints: stale test ledger or missing deterministic seed. Update the ledger or seed fixed IDs.
- Device/security pages render plausible lists without real network calls: likely static/demo state. Mark reachable only, not verified.
- UI contains demo hints such as hardcoded PINs/passwords in a real-backend walkthrough: frontend product-copy/security issue.

## Evidence report checklist

- Environment: local frontend URL, backend target, account class/role/KYC if relevant (no secrets).
- Flow-by-flow verdicts with route, key API calls/statuses, and visible UI observations.
- Root-cause attribution with exact frontend and backend file paths where available.
- Explicit list of writes not performed for safety.
- Next actions split by P0/P1 and by frontend/backend/test-data ownership.
