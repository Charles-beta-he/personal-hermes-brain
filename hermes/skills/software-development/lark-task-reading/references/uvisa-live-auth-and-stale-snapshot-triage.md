# UVISA Lark live auth + stale snapshot triage

Use this when continuing a UVISA Lark task loop after a context/tool-budget interruption and the Hermes-native reader cannot obtain a fresh user token.

## Observed failure pattern

Fresh live read command:

```bash
python3 ~/.hermes/scripts/lark_task_reader.py --scope-mode only --summary
```

Failure:

```text
RuntimeError: Lark token unavailable: NO_TOKEN
```

Classification:

- `CURRENT_BLOCKED_NO_TOKEN`: no live user token is available.
- `HERMES_APP_CREDENTIALS_MISSING`: `~/.hermes/.env` lacks `FEISHU_APP_ID` / `FEISHU_APP_SECRET` and `LARK_APP_ID` / `LARK_APP_SECRET`, so `lark-mcp login` cannot start a valid OAuth flow.
- Existing `lark-mcp` auth-store client metadata such as `client_id_for_local_auth` does **not** prove a usable session; verify `tokens` and `localTokens` are non-empty.

## Safe probes

Check credential presence without printing secret values:

```bash
python3 - <<'PY'
from pathlib import Path
import re
p = Path.home()/'.hermes/.env'
text = p.read_text(errors='ignore') if p.exists() else ''
for k in ['FEISHU_APP_ID','FEISHU_APP_SECRET','LARK_APP_ID','LARK_APP_SECRET']:
    m = re.search(rf'^{k}=(.*)$', text, re.M)
    print(k, bool(m and m.group(1).strip()), len(m.group(1).strip()) if m else 0)
PY
```

Inspect `lark-mcp` token store without leaking token values. Force process exit; otherwise the Node/keytar path can leave handles open and the shell may time out after printing useful output.

```bash
node - <<'NODE'
const { authStore } = require('/Users/charles/.nvm/versions/node/v24.14.0/lib/node_modules/@larksuiteoapi/lark-mcp/dist/auth/store.js');
authStore.initialize().then(() => {
  const d = authStore.storageDataCache || {};
  console.log(JSON.stringify({
    keys: Object.keys(d),
    tokenKeys: Object.keys(d.tokens || {}),
    localTokenKeys: Object.keys(d.localTokens || {}),
    clientKeys: Object.keys(d.clients || {})
  }, null, 2));
  process.exit(0);
}).catch(e => { console.error(String(e)); process.exit(1); });
NODE
```

## Stale snapshot triage

If live read is blocked, search for previous snapshots and validate JSON before using them:

```bash
python3 - <<'PY'
from pathlib import Path
import json
candidates = [
    Path('/tmp/uvisa-lark-tasks-authorized-user.json'),
    Path.home()/'.hermes/tmp/uvisa_lark_tasks_only_20260510_001254.json',
]
for p in candidates:
    print('\n==', p, 'exists=', p.exists())
    if not p.exists():
        continue
    try:
        data = json.loads(p.read_text())
    except Exception as exc:
        print('INVALID_JSON', type(exc).__name__, exc)
        continue
    print('count', len(data) if isinstance(data, list) else type(data))
    for i, t in enumerate((data if isinstance(data, list) else [])[:10], 1):
        print(i, (t.get('lark_task_guid') or t.get('guid') or '')[:12], t.get('summary') or t.get('issue_title') or t.get('title'))
PY
```

Rules:

- Treat invalid/empty JSON snapshot files as unusable even if their filenames look promising.
- Label all snapshot-derived task lists as `stale/non-live`; never claim a fresh Lark read from them.
- Prefer quick stale-task regression-proof closeout for low-risk i18n/UI tasks when live auth is blocked, but mark the live-read blocker in the evidence note/TG.
- Do not retry the identical `lark_task_reader.py --scope-mode only --summary` command after `NO_TOKEN`; change strategy to auth preflight or stale-snapshot triage.
