# Lark MCP user-auth recovery without leaking secrets

Use this when a live Lark Task read fails with `NO_TOKEN`, `lark-mcp whoami` reports no active session, or `lark-mcp login` fails with `Missing App Credentials`.

## Procedure

1. Classify the failure before retrying:
   - `NO_TOKEN` from the Hermes task reader means live user auth is absent/expired; it does not prove the reader is broken.
   - `lark-mcp login` requires app credentials via CLI flags or its expected env names. A configured local auth client alone is not a user token.
   - Existing JSON task snapshots are stale triage only until a fresh reader run succeeds.

2. **Domain selection (critical pitfall):**
   - `lark-mcp login` defaults to `https://open.feishu.cn` (China Feishu). International Lark apps on `larksuite.com` will get **error 20029** ("重定向 URL 有误") if you omit `--domain`.
   - **Always pass `--domain https://open.larksuite.com`** for international Lark tenants. The API base in `lark_task_reader.py` is `https://open.larksuite.com/open-apis`, confirming the tenant is international.
   - The developer console URL also uses the domain: `https://open.larksuite.com/app/{appId}/safe` (not feishu.cn).

3. **Redirect URI registration (error 20029):**
   - Before `lark-mcp login`, verify the redirect URI `http://localhost:{port}/callback` is registered in the app's security settings at the developer console.
   - If error 20029 appears, the user must add the redirect URI manually in the developer console (requires their Lark account login). Navigate to `https://open.larksuite.com/app/{appId}/safe` → 安全设置 → 重定向 URL → add `http://localhost:{port}/callback`.
   - The controlled browser (browserbase) and the user's Chrome do NOT share sessions. If the developer console requires login, ask the user to operate their own Chrome or provide credentials for the controlled browser.

4. Locate credential *sources* safely, but do not print values:
   - Search known Hermes config/session locations for key names only.
   - If extracting values into a helper process, keep them in process memory/env and redact stdout/stderr.
   - Never save app secrets, user tokens, OAuth codes, cookies, OTPs, or connection strings into memory, skills, repo docs, commits, or user-facing summaries.
   - To extract stored credentials from authStore: run a Node script that reads `authStore.storageDataCache.clients[client_id_for_local_auth]`. Field names vary by lark-mcp version: check both `appId`/`appSecret` and `client_id`/`client_secret`. The `tokens` dict may be empty after a failed login wipes it, but `clients` persists.

5. Start login with supplied app credentials and required Task scopes:
   - First prefer the single-flight guard instead of raw background `lark-mcp login`: `python3 ~/.hermes/scripts/lark_oauth_guard.py --json --cleanup-stale`. It checks for an existing valid token, uses a lock to avoid spawning duplicate login flows, cleans stale `localhost:3010` listeners only when requested, opens the auth URL once, redacts token keys/secrets from JSON output, and prevents duplicate Hermes watch-pattern notifications / `EADDRINUSE` loops. For status-only checks, use `--no-open` to avoid triggering a new browser flow. See `references/lark-oauth-single-flight-guard.md` for the guard design, expiry semantics, regression tests, and certification sequence.
   - Use a temporary helper script under `/tmp` with restrictive permissions only if the guard is unavailable or needs debugging.
   - Prefer a durable app credential source when available. Treat `authStore.storageDataCache.clients[client_id_for_local_auth]` as a candidate only after validating that its values are not placeholders. If both `client_id` and `client_secret` literally equal `client_id_for_local_auth`, that entry is local MCP metadata, not a real Lark app credential pair; use the real app id/secret source instead.
   - Do not rely only on expired `tokens[*].extra.appId/appSecret`, because a failed/expired login probe can leave `tokens` and `localTokens` empty while `clients` still exists.
   - Pass app id/secret to `lark-mcp login` without echoing the command line in final evidence.
   - Include the task/user scopes required by the reader, for example user id + task read/tasklist read scopes. Use the exact granted scope strings already present in the client/session when possible; avoid inventing near-miss scope names.
   - **Always pass `--domain https://open.larksuite.com`** for international tenants.
   - Start the login as a background process only when you can immediately open/click the authorization page before the CLI timeout. A 60-second timeout can fail and clear stale token entries, so do not launch it and then spend the window on unrelated work.
   - Prefer a PTY when capturing `lark-mcp login` output from Hermes tools. Some runs do not flush the authorization URL reliably through plain pipes, while `pty=true` exposes the `Authorization URL:` line promptly enough to open it.
   - Before retrying, clear stale listeners on the fixed callback port: `lsof -nP -iTCP:3010 -sTCP:LISTEN` and kill only the leftover `lark-mcp login`/helper process. `EADDRINUSE ::1:3010` is usually a prior login attempt still listening, not a credential problem.
   - **Timing flow**: lark-mcp login starts a local HTTP server on `localhost:{port}`. The authorize URL is `http://localhost:{port}/authorize?...` (with PKCE code_challenge). Navigate to this URL immediately; it redirects to the Lark OAuth page. The server handles PKCE internally — you do NOT need to reconstruct the code_challenge. Wait for the server to be ready (curl localhost:{port}/ returns 404, not connection refused), then navigate.
   - Watch for an authorization URL or browser popup.

6. If a browser authorization page appears, operate it directly:
   - Inspect the page.
   - Click authorize/allow/continue.
   - Return to the terminal and verify that the login finished.

7. Verify with token-store state and the actual reader, not just process exit or `whoami`:
   - Exit code `0` from `lark-mcp login` without a success line and with `authStore.storageDataCache.tokens` still empty is not proof of authorization; it can mean the browser flow ended/canceled without storing a token.
   - When probing auth-store from Node, call `process.exit(0)` after printing non-secret counts, otherwise keytar/file watcher handles can keep the process alive until the shell timeout.
   - `lark-mcp whoami` is useful but may print or fail in ways unrelated to the Hermes reader.
   - The success criterion for a Lark-task loop is a fresh `lark_task_reader.py --scope-mode only --summary` or equivalent live API call.
   - Save live output to a timestamped `/tmp` JSON path and include task count/source timestamp in evidence.

8. Clean up temporary helpers:
   - Remove or chmod-restrict helper scripts after use if they embedded secret access logic.
   - Do not commit `/tmp` helpers or downloaded auth artifacts.

## Evidence wording

Good:
- “Live reader succeeded; saved 24 tasks to `/tmp/...json`; credentials were redacted.”
- “Auth blocked: `NO_TOKEN`; stale snapshot exists but was not treated as live.”

Bad:
- Pasting app ids/secrets/tokens.
- Saying “Lark tasks read” from a stale snapshot.
- Saying “authorized” from `lark-mcp` client metadata when no user token exists.
