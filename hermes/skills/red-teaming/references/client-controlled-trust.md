# Client-controlled trusted-device red-team notes

Use this reference when auditing trusted-device, remembered-browser, MFA-step-up, or device/session persistence flows.

## Core finding pattern

A trusted-device flag is security-sensitive if it changes whether the user must pass an extra factor (PIN, OTP, MFA, payment password, recovery check). Any value that affects that decision must be server-derived for the current authentication event.

Client persistence such as `localStorage`, `sessionStorage`, IndexedDB, cookies without server signature, Zustand/persist snapshots, or UI caches may be used for display/UX continuity only. It must not be a fallback authority for skipping step-up.

## Red-team workflow

1. Trace the full login route after primary auth succeeds:
   - auth service response type
   - store normalization/consume-token path
   - route decision for step-up vs home
   - step-up verification endpoint
2. Identify the authority for trust:
   - PASS only if the route uses an explicit server response such as `currentDeviceTrusted === true` from the just-completed login.
   - FAIL CLOSED if the field is missing/null/false/contract drifted.
3. Attack local persistence before login:
   - pre-seed device id + trusted set
   - corrupt trusted JSON
   - replay another user's/local browser snapshot
   - simulate old backend response missing the server trust field
4. Check server trust mutation:
   - authenticated endpoint only
   - filters by current user id and active/non-revoked row
   - checks update count; zero rows should fail, not return success
   - revoke/logout-others clears trust
   - audit event written for trust/untrust/revoke
5. Check device binding strength:
   - User-Agent hash is only a weak identifier, not an authenticator.
   - Prefer server-issued opaque device secret/cookie, stored hashed server-side and tied to user + row + revoked + trusted state.

## Verdict rules

PASS:
- Step-up skip only happens on `serverTrusted === true` from the current login response.
- Missing server trust field, API failure, old backend, or malformed client cache all route to step-up.
- Client local trust can affect only device-list display or optimistic UI.

FAIL:
- Any local/client-controlled persisted value can skip step-up when the server field is absent, stale, or failed.
- PATCH trust failure still writes a local trusted flag that can affect next login routing.
- Backend returns success on non-owned/nonexistent/revoked device trust update without detecting zero-row updates.

## Required tests

- Local trusted cache pre-seeded + login response `currentDeviceTrusted=false` => route to step-up.
- Local trusted cache pre-seeded + login response omits trust field => route to step-up.
- PATCH trust failure => no persistent security-authoritative trust.
- Backend trust update for nonexistent/non-owned/revoked row => failure.
- Revoke/logout-others clears trusted state.
