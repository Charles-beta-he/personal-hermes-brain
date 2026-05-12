# U-VISA Lark Docx Reading Session — 2026-05-09

## Source

- URL: `https://uaecprod.sg.larksuite.com/docx/GaGLdayTSosobYx6kWylgS7PgMg`
- Title: `U-VISA2.0 C 端产品需求文档（PRD v1.0）`

## Access Outcomes

1. `feishu_doc` / `feishu_drive` toolsets were not callable in the active Hermes tool namespace.
2. OpenAPI helper acquired token but Docx read returned `403 / 1770032 forbidden`.
3. Logged-in Chrome rendered-copy fallback succeeded: 27069 chars, 967 lines, 11 modules, 13 flows.
4. Window-only screenshot sweep added higher-fidelity visual proof: 129 screenshots, 110 unique hashes.

## Screenshot Sweep Lessons

- Full-screen screenshots can accidentally capture terminal panes and unrelated tabs; prefer Chrome window-only captures using CGWindow id.
- AppleScript JavaScript execution may be disabled in Chrome; do not depend on `execute javascript`.
- Keyboard PageDown can be slow in Lark; Quartz scroll-wheel events cover long documents faster.
- Use `vision_analyze` on representative screenshots: beginning, product decisions, design rules, business modules, late appendix/end.
- Current U-VISA visual samples confirmed sections 1, 4, 5, 6, and late Appendix D (`D.6 状态词`, `D.7 翻译原则`).

## Permission Remediation

For `403 / 1770032 forbidden`, ask the user/admin for:

- `查看新版文档` — minimum read permission for Docx block/content reads.
- `创建及编辑新版文档` — only if editing or historical revision read is required.
- `获取用户 user ID` — optional sensitive field permission only if user IDs are needed.
- Document-level read access for the app/bot or the user token.

If the Lark developer console is open and the user explicitly authorizes GUI operation, the agent may request/apply these permissions. Stop before irreversible publish/install/approval prompts unless explicitly authorized.

## Evidence Artifacts

- `/tmp/uvisa-lark-product-doc-redacted.txt`
- `/tmp/uvisa-lark-product-doc-evidence.json`
- `/tmp/uvisa-lark-product-doc-summary.md`
- `/tmp/uvisa-lark-window-screenshot-proof/manifest.json`
- `/tmp/uvisa-lark-window-screenshot-proof/summary.json`
- `/Users/charles/.hermes/tick-20260509-040423`

## Certification

T2 multi-model discussion certified 4/4 approve, truth grounded 5/5, unresolved severity>=3 = 0.

## Product Portrait / Test-Ledger Deposition Lessons

After the PRD read, the project Workpad was updated with the Lark PRD anchor, Railway user test environment, test account scope rules, and the temporary OTP retrieval workflow. The OTP workflow matters for future real-backend browser tests: current verification codes are read from the browser-open Railway `uvisa-backend` service Deploy Logs, log emission can lag after clicking “send code,” and one-time code values must not be persisted.

The project initially had `docs/UI_TEST_CASES.md` focused on page function, UI interaction, visual quality, and boundary cases. The PRD required a separate product/user-logic layer. The session added `docs/PRODUCT_USER_LOGIC_TEST_CASES.md` and linked it from `docs/UI_TEST_CASES.md` section 0.3.

Reusable pattern for PRD reads:

- Do not stop at summarizing the product document.
- Add a PRD-derived product logic ledger when existing tests are page-oriented.
- Keep page-function PASS distinct from product-logic PASS.
- For financial/mobile products, product logic cases should cover user eligibility, account-opening channel, KYC ownership, T2/2FA, protection windows, device trust, funds/state closure, card lifecycle, network limits, and backend-capability transparency.
- Update the project Workpad Evidence Ledger and Next Loop Queue so future loops derive backlog from both UI cases and product logic cases.
