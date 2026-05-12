# UVISA secure receiving-info closeout pattern

Use this reference for UVISA Lark tasks about top-up receiving information leaking plaintext bank/provider payloads, especially SWIFT/CNH or domestic CNY transfer screens.

## Product/security interpretation

For wording like “接口调用后显示明文，未加密，并且显示一大堆银行信息；这里只显示电汇收款信息，并且是加密的”: treat the frontend closeout as a fail-closed rendering contract, not proof of cryptographic backend encryption.

Minimum frontend contract:

1. Render only fixed allowlisted customer-facing rows for the selected rail. Never map arbitrary backend payload keys into UI.
2. Source receiving info from the safe platform config contract (`/platform-config/topup`) rather than legacy detail endpoints like `/topup/swift/details` that can expose raw bank payloads.
3. Require an explicit backend visibility marker such as `publicVisible === true` before showing any receiving values.
4. Validate every displayed field, not only account number.
5. If any required displayed field is missing or unsafe, fallback the entire receiving-info section to advisor/customer-service guidance; do not mix partially safe and unsafe backend values.
6. Copy buttons must copy the same safe display values only; never copy hidden raw payload values.

## Field-level guardrails

Account numbers:
- Must contain `*` or `•`.
- Visible digit count must be <= 4.
- Reject split/contiguous digit bypasses such as `****-1234-5678` or runs of 5+ digits.

SWIFT/BIC:
- Normalize/validate as BIC shape: `^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$`.
- Reject spaces, punctuation, URLs, JSON, and internal/provider words.

Other displayed receiving fields (`bankName`, `beneficiary`, `bankAddress`, hints/reference prefixes):
- Reject empty/non-string/object/array values.
- Reject JSON-like payloads, URLs, emails, HTML/script-like strings, and excessive length.
- Reject internal/provider/channel words: `provider`, `channel`, `callback`, `webhook`, `activationCode`, `payload`, `rawBank`, `settlement`, `intermediary`, `apiKey`, `secret`, `token`, `privateKey`, `vendor`, `vendorId`, `supplier`, plus known leaked vendor/bank/channel names from evidence.
- Treat account-like markers as unsafe outside the account field too: `account`, `acct`, `IBAN`, `routing`, `sortCode`, `sort code`, and punctuation variants such as `sort-code` / `sort/code` after compact normalization.
- Count all visible Unicode decimal digits after NFKC normalization, not only JavaScript ASCII `\d`; reject split-digit payloads such as `12-34-56`, `1234 5678`, fullwidth digits, and Arabic/Persian digit variants.

Reference / user UID:
- Do not show a synthetic or unsafe reference when the receiving config itself is unsafe. Fallback to advisor guidance together with the rest of the receiving-info fields.
- Use a reference-specific sanitizer for authenticated user IDs. Normal UIDs can legitimately contain 6+ digits (for example `UA123456`); do not reuse bank-address/account sanitizers for submit gating or the CTA may incorrectly send valid users to customer service.

- Do not show a synthetic or unsafe reference when the receiving config itself is unsafe. Fallback to advisor guidance together with the rest of the receiving-info fields.
- Use a separate reference/user-UID sanitizer instead of reusing the bank-field sanitizer. Numeric UIDs can legitimately contain 6+ digits, so the non-account digit-count rejection would create a false fallback. The reference sanitizer should still reject empty/overlong strings, JSON/URL/payload-like values, and dangerous internal/provider terms.

## Regression tests to add

For helper-level tests:
- `publicVisible` missing/false => all receiving values fallback.
- `publicVisible=true` but account is unmasked or exposes too many digits => unusable.
- `publicVisible=true` but any displayed SWIFT field contains provider/callback/URL/JSON/raw payload => unusable.
- Vendor/supplier metadata (`vendor`, `vendorId`, `supplier`) in any displayed receiving field => unusable.
- Unicode digit bypasses are blocked: fullwidth split digits (`１２-３４-５６`), Arabic/Persian digit groups, and masked account values with more than four non-ASCII visible digits.
- Normal numeric user references remain usable when receiving config is safe (for example `UA123456` allows submit and renders as reference), but unsafe reference text still blocks submit.
- Extra backend keys such as `rawBankPayload`, `intermediaryBank`, `providerPayload`, `callbackUrl`, or `activationCode` never appear in built fields.
- Valid masked fixture uses a real BIC-shaped value such as `EXAMPLXX`, not an invalid placeholder like `EXAMPLEXXX`.

- Safe receiving config can still display a normal numeric user UID/reference; this proves the reference sanitizer is separate from the stricter bank-field sanitizer.
- Valid masked fixture uses a real BIC-shaped value such as `EXAMPLXX`, not an invalid placeholder like `EXAMPLEXXX`.

For component/browser checks:
- Page requests `/api/platform-config/topup` and does not call `/api/topup/swift/details`.
- DOM text does not contain known raw leak strings or dangerous backend keys.
- Unsafe/empty config shows advisor/customer-service state.

## Closeout sequence reminder

After frontend changes for UVISA Lark tasks:
1. Run targeted tests for touched screens/services.
2. Run touched-file ESLint, full unit test, `git diff --check`, and `pnpm run build`.
3. Commit scoped frontend files.
4. Push the shared task-loop branch and monitor the remote frontend package/build status only, unless the user explicitly asks for backend deployment monitoring.
5. Send TG notification for the task id with summary, commit hash, local verification, and remote frontend build status.

If browser auth/OTP/session blocks UI verification after deterministic gates pass, record that gate explicitly and prioritize commit/TG handoff instead of burning the final tool budget on exploratory clicks.

## Backend masking pattern

When the frontend already uses the sanitized public endpoint (`/platform-config/topup`), but authenticated endpoints (`/topup/swift/details`, `/topup/cny/banks`) also return raw data, add defense-in-depth masking to the authenticated endpoints too.

Implementation:
1. Add `maskReceivingFields(Map<String, Object> raw)` to the **Controller** class (not the Service class).
2. Apply it in the endpoint methods: `return ApiResponse.ok(maskReceivingFields(topupService.getRawDetails()))`.
3. Keep the raw Service methods unchanged — they're used internally by transaction processing (e.g., `createSwiftTopup` needs the real account number).

**PITFALL: Java class scope in multi-class files.** In UVISA backend, `TopupController` and `TopupService` are separate Java classes in the same `.java` file. A `private static` method in `TopupService` is NOT accessible from `TopupController`. If you add masking helpers to the Service, the Controller can't call them. Always put API-response masking in the Controller class.

`maskAccountNumber` implementation: keep last 4 visible digits, replace rest with `*`. Pass through already-masked values (containing `*` or `•`).
