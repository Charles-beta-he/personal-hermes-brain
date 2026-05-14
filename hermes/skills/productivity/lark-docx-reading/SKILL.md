---
name: lark-docx-reading
description: Use when reading Lark/Larksuite/Feishu Docx product documents for project analysis. Covers OpenAPI bot attempts, browser-login fallback via Chrome copy, redacted evidence artifacts, and multi-model certification.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - lark
    - feishu
    - docx
    - product-doc
    - evidence
    - browser-fallback
    related_skills:
    - multi-model-thinking
    - hermes-agent
---

# Lark Docx Reading

## Overview

Use this skill to read Lark/Larksuite Docx documents when a project PRD or product spec is stored in Lark. Prefer official OpenAPI when the bot has permission; fall back to the user's already logged-in browser when OpenAPI returns permission errors.

Never print or persist app secrets, tenant tokens, cookies, auth headers, localStorage, or document-private credentials. Evidence files must be redacted before summary or multi-model review.

## When to Use

- User gives a Lark/Larksuite/Feishu `docx/...` URL and asks to read/analyze it.
- User has a Lark bot app id/secret and wants Hermes to read project docs.
- Browser is already logged into Lark and OpenAPI cannot access the doc.
- Need evidence-first multi-model certification that the document was actually read.

Do not use this for `.docx` Office files already downloaded locally; use `ocr-and-documents` / `python-docx` for those.

## Workflow

### 1. Discover access paths

1. Try available Hermes toolsets first if present: `feishu_doc`, `feishu_drive`.
2. Try OpenAPI with a temporary environment, not hardcoded secrets:
   - `LARK_APP_ID`
   - `LARK_APP_SECRET`
3. If OpenAPI returns `403` / `1770032 forBidden`, interpret as: bot token likely works but the app/bot lacks document permission, document authorization, or required scopes.
4. Check browser state:
   - `browser_navigate(url)` may show login if the tool browser has no session.
   - On macOS, inspect Chrome tabs with AppleScript.

### 2. OpenAPI script

A reusable script lives in two places:

- Active user-level helper: `~/.hermes/scripts/lark_docx_reader.py`
- Packaged skill copy: `scripts/lark_docx_reader.py`

Use the user-level helper in normal Hermes sessions; use the packaged copy if the global helper is missing or the skill is being ported to another environment.

Usage:

```bash
LARK_APP_ID="..." LARK_APP_SECRET="..." \
python3 ~/.hermes/scripts/lark_docx_reader.py \
  'https://.../docx/<token>' \
  --out /tmp/lark-doc-evidence.json
```

Security rules:

- Pass secrets only via environment variables.
- Do not commit generated `/tmp/*evidence.json`.
- Do not echo secrets in final responses.
- Redact common token/password/secret fields in extracted text.

### 3. Browser-login fallback on macOS Chrome

If the user's Chrome is already logged in and displays the doc, but AppleScript JavaScript execution is disabled, use copy fallback:

```bash
osascript <<'OSA'
tell application "Google Chrome"
  activate
  repeat with wi from 1 to count of windows
    set w to window wi
    repeat with ti from 1 to count of tabs of w
      set t to tab ti of w
      if (URL of t contains "<doc-token-or-host>") then
        set active tab index of w to ti
        set index of w to 1
        exit repeat
      end if
    end repeat
  end repeat
end tell
delay 0.8
tell application "System Events"
  keystroke "a" using command down
  delay 0.5
  keystroke "c" using command down
  delay 1.2
end tell
OSA
pbpaste > /tmp/lark-doc-clipboard.txt
```

Then generate evidence:

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib, json, re
p = Path('/tmp/lark-doc-clipboard.txt')
text = p.read_text(encoding='utf-8')
for pat in [
    re.compile(r'(?i)(api[_-]?key|token|secret|password|passwd|pwd|authorization|bearer)\\s*[:：=]\\s*([^\\s,;，；]+)'),
    re.compile(r'(?i)(access[_-]?token|refresh[_-]?token)\\s*[:：=]\\s*([^\\s,;，；]+)'),
]:
    text = pat.sub(lambda m: f'{m.group(1)}=[REDACTED]', text)
Path('/tmp/lark-doc-redacted.txt').write_text(text, encoding='utf-8')
Path('/tmp/lark-doc-evidence.json').write_text(json.dumps({
    'chars': len(text),
    'lines': len(text.splitlines()),
    'sha256': hashlib.sha256(text.encode()).hexdigest(),
    'preview': text[:3000],
}, ensure_ascii=False, indent=2), encoding='utf-8')
PY
```

### 4. Screenshot / vision fallback for higher fidelity

Use screenshot sweep when copied text contains placeholders such as `暂时无法在Lark文档外展示此内容`, when visual tables/images matter, or when a model needs visual proof that the browser-rendered doc was browsed end-to-end.

Recommended macOS Chrome evidence recipe:

1. Locate the real Chrome tab with AppleScript title/URL inventory.
2. Capture the Chrome PRD window only, not the full desktop, using the CGWindow id when possible.
3. Start from the top, then scroll/page down through the document.
4. Save a manifest with screenshot path, sha256, and method.
5. Run `vision_analyze` on representative screenshots: beginning, mid modules, late appendix/end. For long PRDs, sample at least one screenshot per major chapter range.

Session-proven artifact pattern:

- `/tmp/<project>-lark-window-screenshot-proof/manifest.json`
- `/tmp/<project>-lark-window-screenshot-proof/shot-000.png` ...

Important: full-screen screenshots can accidentally capture terminals, mail, or secrets. Prefer window-only screenshots via Quartz/CGWindow and redact/delete any accidental sensitive capture before using it as evidence.

### 5. Lark permission remediation playbook

When OpenAPI returns `403` / `1770032 forbidden`, tell the user/app admin exactly what is missing instead of saying only “no permission”. For Docx block reading, Lark docs list permissions in the console as Chinese permission names:

- Minimum read scope: `查看新版文档` (view/read new Docx documents).
- Broader edit scope if historical revisions or writes are needed: `创建及编辑新版文档`.
- Optional field permission only if user identity fields are needed: `获取用户 user ID`.

Also check document-level access:

- The app/bot or the acting user token must have access to the target document.
- For tenant access token reads, app scopes alone may still fail if the app/bot is not allowed to read that document/space.
- For user access token reads, the user behind the token must have normal document read permission.

If the Lark developer console is already open and the user explicitly authorizes GUI operation, you may operate the console to request/add these permissions. Safety rules: do not reveal or copy app secrets; stop before irreversible publish/tenant-wide install/approval prompts unless the user already authorized that exact action.

### 6. Prefer user identity OAuth when the user can view the doc

If the user can open/read the target Lark document in their browser but the bot/app gets `403` / `1770032`, do **not** keep broadening tenant/app access by default. Switch the primary plan to OAuth user identity:

1. In Lark Developer Console, add an OAuth redirect URL that exactly matches the local callback, e.g. `http://localhost:8765/callback`.
2. Request **user** scopes via Permission Management. For Docx reading, user scope is commonly `docx:document` (console may label it `查看新版文档` / new Docx access). Add `offline_access` only if refresh tokens are needed.
3. Start the local callback catcher before opening the authorize URL:
   ```bash
   rm -f /tmp/lark-oauth-callback.json
   python3 ~/.hermes/skills/productivity/lark-docx-reading/scripts/lark_oauth_callback_server.py
   ```
   If port `8765` is busy, an old callback server is probably still running; identify/stop it before retrying.
4. Build an authorization URL:
   - Base: `https://accounts.larksuite.com/open-apis/authen/v1/authorize`
   - Required query: `client_id`, `redirect_uri`, `scope`, `state`
5. The user authorizes; local callback receives `code` in `/tmp/lark-oauth-callback.json`. Treat this file as sensitive and never paste the code into chat/final output.
6. Exchange code through `POST https://open.larksuite.com/open-apis/authen/v2/oauth/token` with `grant_type=authorization_code`.
7. Call Docx APIs with `Authorization: Bearer <user_access_token>`.

Important error routing:

- `20029` during OAuth authorize means redirect URL is not registered/does not exactly match. Fix Security Settings → Redirect URL first.
- `20027` during OAuth authorize means the app has not opened the requested scopes **or** the new scopes are only `待发布`. Fix Permission Management scopes, then publish/approve if Lark requires it.
- Lark can show `待发布｜可调试` after applying scopes; OAuth can still return `20027` until a new app version is released/approved. Do not claim user-token OpenAPI read is complete at this stage.
- Version publication/tenant install/admin approval can be irreversible or tenant-wide. Stop and ask before clicking those, even if the user allows console operation.

The active helper `~/.hermes/scripts/lark_docx_reader.py` should support `--auth user`, `LARK_USER_ACCESS_TOKEN`, OAuth code exchange, and `--make-auth-url`. If the packaged skill script is stale, update it from the active helper or record the delta in `references/lark-user-oauth-docx.md`.

### 7. Evidence checklist

A successful read should produce:

- Source URL and document token.
- Extraction method (`openapi_docx`, `chrome_rendered_copy_fallback`, or `chrome_window_screenshot_sweep`).
- Character count and line count when text extraction succeeds.
- SHA-256 of redacted text and/or screenshot manifest.
- Title if available.
- First 20-80 preview lines.
- Section/module headings.
- Vision-confirmed representative screenshots for hidden/visual content.
- Known limitations, e.g. Lark placeholders like `暂时无法在Lark文档外展示此内容`.
- Permission errors from failed access paths without exposing secrets.

### 7.1 Product-document deposition checklist

When the Lark Docx is a PRD/product requirements document, reading it is not enough. Deposit the product semantics into the project evidence system so later implementation loops do not only test page mechanics.

- Add or update the project Workpad/project portrait with the PRD anchor, extraction evidence, and current known limitations.
- If the project already has page/UI functional cases, add a separate PRD-derived product/user-logic test ledger instead of mixing all cases into UI smoke tests.
- Explicitly distinguish page-function PASS from product-logic PASS: buttons/screens working does not prove user eligibility, funds closure, risk controls, state lifecycle, notifications, or backend-transparency rules.
- Extract cross-page PRD constraints such as account-opening eligibility, KYC ownership, 2FA/T2 rules, protection periods, device trust, funds rollback, card lifecycle, network/chain limits, and “backend capability invisible to user” requirements.
- Link the product-logic ledger from the existing UI test document, and update the Workpad Evidence Ledger/Next Loop Queue so future loops derive P0/P1/P2 from both page cases and product logic cases.
- Keep real test credentials, one-time OTP values, payment PINs, and sensitive log screenshots out of repo docs, global memory, final responses, commits, PRs, and public issue text. If the user provides disposable test credentials, store non-secret identifiers (for example test URL, UID, KYC tier, masked phone) only in the local project Workpad with scope rules; store PIN/OTP/token values only in the project-scoped private credential area if one exists, otherwise ask before persisting them.

### 8. Multi-model certification

Build a state JSON with claims like:

- `C-001`: document content was extracted from the target Lark URL.
- `C-002`: OpenAPI bot path was attempted and failed with permission error, so fallback was used.
- `C-003`: evidence artifacts are redacted and include counts/hash/preview/headings.
- `C-004`: extracted doc summary matches PRD structure and known modules.

Run:

```bash
python3 ~/.hermes/scripts/consult_models.py run /tmp/<state>.json --tier T2 --quorum 4 --timeout 180 --keep
python3 ~/.hermes/scripts/consult_models.py resume-discussion /Users/charles/.hermes/tick-... --max-rounds 2 --timeout 120
```

Certify only if:

- quorum is met;
- truth status is grounded;
- discussion is certified or all models approve;
- unresolved severity >= 3 count is zero;
- the tick/artifacts clearly refer to the target Lark doc and not another project.

## Common Pitfalls

1. Browser tool session is not the user's Chrome session. `browser_navigate` can show Lark login even when the user's local Chrome is logged in.
2. Chrome AppleScript `execute javascript` is often disabled. Use `cmd+a/cmd+c` copy fallback instead.
3. OpenAPI tenant token success does not mean document permission. Docx meta/read can still return `403` / `1770032`.
4. If the human user can read the doc but tenant/app identity cannot, prefer user OAuth (`user_access_token`) over repeatedly broadening bot/app document access. The acting user token inherits the user's normal doc access and still needs app-declared scopes.
5. Lark OAuth errors route to different fixes: `20029` = redirect URL mismatch; `20027` = requested scopes not opened in app permission management or not yet published. Do not confuse either with document-level denial.
6. Lark permission batch import may distinguish `tenant` vs `user` scopes. For a user-identity read, import `docx:document` under `user`; do not unnecessarily add tenant scopes.
7. Lark may mark newly added scopes as `待发布｜可调试`; OAuth can still fail with `20027` until version release/approval completes. Stop before publish/approval unless explicitly authorized.
8. A localhost callback server may already hold port `8765`; if starting `lark_oauth_callback_server.py` fails with `Address already in use`, stop the old server or reuse it instead of starting duplicates.
9. Some Lark blocks render as `暂时无法在Lark文档外展示此内容` when copied/exported. Preserve this as a limitation, do not hallucinate hidden content.
10. Do not save Lark app secrets, OAuth codes, access tokens, refresh tokens, cookies, or authorization headers to memory, skills, Workpad, or final responses.
11. If copy/export hides content, use a window-only screenshot sweep + `vision_analyze` samples before declaring full coverage.
12. For OpenAPI `1770032`, request `查看新版文档` first, then document-level app/user access; do not ask for broad edit scopes unless needed.

## Session-Proven Support Files

- `scripts/lark_docx_reader.py` — reusable OpenAPI reader/token parser used for Lark Docx documents; copy or compare it against `~/.hermes/scripts/lark_docx_reader.py` if the global helper is missing.
- `scripts/lark_oauth_callback_server.py` — minimal localhost callback catcher for user-identity OAuth; writes `/tmp/lark-oauth-callback.json` and must be treated as sensitive because it can contain a one-time code.
- `references/uvisa-lark-docx-reading-2026-05-09.md` — condensed session notes from the U-VISA2.0 PRD read: access-path outcomes, error codes, fallback recipe, certification result, and limitations.
- `references/lark-user-oauth-docx.md` — user-identity OAuth route for Docx reading: redirect URL setup, `20029`/`20027` remediation, user-vs-tenant scopes, and safe stopping points.

## Verification Checklist

- [ ] At least one access path succeeded, or failure reason is explicit.
- [ ] Evidence file exists and has non-trivial line/char count.
- [ ] Redaction was applied.
- [ ] Summary includes title, scope, modules, flows, constraints.
- [ ] Multi-model certification passes before claiming the skill is fully validated.
- [ ] Any reusable script is referenced and executable.
