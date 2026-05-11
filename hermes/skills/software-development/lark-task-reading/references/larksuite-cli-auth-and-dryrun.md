# larksuite/cli as auth + dry-run oracle for Lark Task reading

Session lesson from UVISA Lark task workflow audit (2026-05-10): when a Hermes-native Lark task reader fails with `NO_TOKEN`, do not conclude the reader logic is broken. First classify auth state vs collection logic.

## Observed signals

- Hermes-native reader failure before API call:
  - `RuntimeError: Lark token unavailable: NO_TOKEN`
  - `lark-mcp whoami` can report `No active login sessions found` and local token count 0.
- `larksuite/cli` in a Hermes context may refuse live use until it is explicitly bound:
  - `hermes context detected but lark-cli is not bound to it`
  - Its help says an AI agent must ask the user to confirm both intent and identity preset before `config bind`.
- A previous scoped snapshot can still prove reader logic worked when auth existed, but it is not a fresh live read.

## Recommended classification

1. `CURRENT_READY`: live token/bind exists and a fresh read succeeds.
2. `CURRENT_BLOCKED_NO_TOKEN`: reader cannot get a user token; report auth blocker.
3. `CLI_UNBOUND`: `lark-cli` refuses in Hermes context; ask user before binding.
4. `HERMES_APP_CREDENTIALS_MISSING`: `config bind --source hermes` was confirmed but fails because `~/.hermes/.env` lacks `FEISHU_APP_ID` / app secret; this is an app-credential setup blocker, not a task-reader bug.
5. `PREVIOUS_SNAPSHOT_AVAILABLE`: local snapshot exists and may be used for triage only, clearly labeled stale/non-live.

## Hermes bind / lark-mcp OAuth preflight pitfalls

Before running `lark-cli config bind --source hermes --identity user-default`, check whether Hermes actually has Feishu/Lark app credentials configured. A confirmed bind can still fail with:

```text
FEISHU_APP_ID not found in /Users/charles/.hermes/.env
hint: run 'hermes setup' to configure Feishu credentials
```

In that state:

- Do not keep retrying `auth login`; it will still report `hermes context detected but lark-cli is not bound to it`.
- Do not treat existing `lark-mcp` client metadata as proof of a live user token. Its storage may contain `clients.client_id_for_local_auth` and requested scopes while `tokens` / `localTokens` are empty.
- Report the blocker precisely: Hermes app credentials are missing or need a separate app initialization path.
- If attempting `lark-cli config init --new --force-init` from a non-interactive agent shell, run it as a managed background process and verify that it actually emits a browser URL. If it silently waits with no output, stop it and switch to an interactive/TTY-capable route or ask for the existing app credentials; do not leave orphaned CLI processes running.

For `lark-mcp login`, do a separate preflight because it reads different names than the Hermes bind path:

```bash
lark-mcp whoami
node - <<'NODE'
const root='/Users/charles/.nvm/versions/node/v24.14.0/lib/node_modules/@larksuiteoapi/lark-mcp';
const { authStore } = require(root + '/dist/auth/store.js');
authStore.initialize().then(() => {
  const d = authStore.storageDataCache || {};
  console.log(JSON.stringify({
    tokenKeys: Object.keys(d.tokens || {}),
    localTokenKeys: Object.keys(d.localTokens || {}),
    clientKeys: Object.keys(d.clients || {})
  }, null, 2));
  process.exit(0);
}).catch(e => { console.error(String(e)); process.exit(1); });
NODE
python3 - <<'PY'
import os
print({k: bool(os.environ.get(k)) for k in ['APP_ID','APP_SECRET','LARK_DOMAIN','LARK_USER_ACCESS_TOKEN','FEISHU_USER_ACCESS_TOKEN']})
PY
```

`lark-mcp login` requires app credentials as CLI args (`-a/--app-id`, `-s/--app-secret`) or environment variables `APP_ID` / `APP_SECRET` (per `dist/utils/constants.js`). It does **not** use `FEISHU_APP_ID` / `FEISHU_APP_SECRET` directly. If run without credentials it fails immediately with:

```text
Error: Missing App Credentials (appId and appSecret are required for login)
```

Do not infer readiness from `client_id_for_local_auth` alone. A store shape like `clients=[client_id_for_local_auth]` with `tokens=[]` and `localTokens=[]` is `CURRENT_BLOCKED_NO_TOKEN`, even if the client metadata contains requested scopes. If app credentials are not available, preserve any snapshot as `PREVIOUS_SNAPSHOT_AVAILABLE` only; do not claim a live task read.

## larksuite/cli value

Use official `@larksuite/cli` as an auth/dry-run/API-shape oracle and optional fallback, not as a blind replacement for a project-specific Hermes reader.

Useful commands after user confirms/binds:

```bash
# Inspect bind requirement; do not execute bind without user confirmation.
npx -y @larksuite/cli@latest config bind --help

# User-resource task reads require user identity.
npx -y @larksuite/cli@latest task +get-my-tasks --as user --complete=false --page-all --dry-run

# Official tasklist shape checks.
npx -y @larksuite/cli@latest task tasklists list --as user --dry-run --params '{"page_size":100}'
npx -y @larksuite/cli@latest task tasklists tasks --as user --dry-run --params '{"tasklist_guid":"<guid>","page_size":100}'

# Auth help for least-privilege login.
npx -y @larksuite/cli@latest auth login --help
```

Dry-run evidence seen in audit:

- `task +get-my-tasks --as user --complete=false --page-all --dry-run` plans `GET /open-apis/task/v2/tasks` with `type=my_tasks`, `completed=false`, `page_size=50`, `user_id_type=open_id`.
- `task tasklists list --as user --dry-run` plans `GET /open-apis/task/v2/tasklists`.
- `task tasklists tasks --as user --dry-run` plans `GET /open-apis/task/v2/tasklists/:guid/tasks`.

## Safe improved flow

1. Run an auth preflight before any task read. If token/bind is missing, emit a structured blocker instead of crashing mid-pipeline.
2. Keep the Hermes-native reader as primary when it has project-specific behavior such as hard scope filtering, comments/docs/image-key preservation, and payload normalization.
3. Use `larksuite/cli` dry-run to verify endpoint/parameter shape and to guide user-facing auth repair.
4. If using snapshots while auth is blocked, label them as stale evidence and never claim a fresh live read.
5. Preserve collection/reporter separation: dry-run and collection must not write Lark comments/status; reporter/closeout is a separate gate.

## User confirmation boundary

Because `lark-cli config bind --help` explicitly warns AI agents not to bind without confirmation, ask before running:

```bash
npx -y @larksuite/cli@latest config bind --source hermes --identity user-default
```

For assigned/personal tasks, `user-default` is required. `bot-only` is safer but cannot access personal resources such as “tasks assigned to me”.
