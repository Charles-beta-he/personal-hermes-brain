# UVISA trusted-device security closeout pattern

Use this when a Lark/UVISA task touches device management, trusted-device state, login step-up, Payment PIN routing, or any client/server trust flag.

## Lesson captured

A task can pass local tests/build and still fail closeout if multi-model reviewers find that a client-controlled fallback participates in a security decision. For trusted devices, `localStorage` may support display/old-backend compatibility, but it must not be the source of truth for skipping a post-login Payment PIN or other step-up gate.

## Minimum safe pattern

1. Treat backend response from the just-finished login as the only value that can skip the step-up gate.
   - `currentDeviceTrusted === true` may skip.
   - Missing, null, false, network drift, or old backend response must fail closed and require PIN/step-up.
2. Keep display fallback separate from security routing.
   - `localStorage` trusted-device set may make an old Devices screen look stable.
   - It must not drive `VerifyCodeScreen -> /home` or equivalent authenticated-routing decisions.
   - Prefer two APIs/names: one display fallback, one server-authenticated login gate.
3. When a rolled-out backend explicitly returns `trusted:false`, do not OR it with stale local storage.
   - Only use local overlay when the backend field is absent because the API is old.
4. PATCH trust endpoints must not silently succeed on invalid rows.
   - Validate `trusted` is present.
   - Scope update by `user_id`, device row id, and `revoked = 0`.
   - Check affected row count; zero rows should return an error (`400/404/403` depending project convention), not `success:true`.
5. Revoke/delete/logout-others must clear trust on both sides.
   - Backend should `SET revoked = 1, trusted = 0`.
   - Frontend should clear local fallback for removed device ids and the current-browser display key when applicable.
6. Multi-model FAIL/AMEND blocks closeout even if deterministic tests are green.
   - Convert each concrete blocker into a regression test first.
   - Patch minimally, rerun targeted tests, full front-end test/build, backend target test/package, then rerun final review/certification.

## Suggested regression tests

Frontend:
- Local storage preloaded as trusted + login response `currentDeviceTrusted:false` => route must go to PIN/step-up, not home.
- Local storage preloaded as trusted + login response missing `currentDeviceTrusted` => fail closed to PIN/step-up.
- Backend device list returns explicit `trusted:false` while local storage says true => UI should show backend false.
- Backend device list omits `trusted` field while local storage says true => UI may use display fallback.
- Deleting one device and logout-others clear local trust fallback for removed rows.

Backend:
- `PATCH /api/me/devices/{id}/trust` succeeds for owned active rows.
- Missing/null `trusted` is rejected.
- Revoked, nonexistent, or other-user device rows do not return success.
- `GET /api/me/devices` only returns active rows and includes `trusted/current`.
- Login response returns `currentDeviceTrusted` for every token-issuing path.

## Closeout wording

Do not claim “trusted-device security” from a UA-only fingerprint or client local storage. Phrase it as: backend-persisted trust state with fail-closed login-step routing, with local fallback limited to old-backend/display compatibility. If UA-only fingerprint remains, list it as an accepted residual risk or future hardening item, not as a strong device-binding guarantee.
