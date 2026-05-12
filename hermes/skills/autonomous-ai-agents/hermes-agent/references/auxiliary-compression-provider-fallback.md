# Auxiliary compression provider fallback failures

Use when context compression prints errors like:

```text
Compression summary failed: Error code: 401 - {'status': 401, 'message': 'Your API key is invalid, blocked or out of funds. Please go visit the portal to sort that out: https://portal.nousresearch.com '}. Inserted a fallback context marker.
```

## Root-cause pattern

The failure can be a chain, not a single provider problem:

1. `context_compressor.py::_generate_summary()` calls `agent.auxiliary_client.call_llm(task="compression")`.
2. `auxiliary.compression.provider: auto` chooses the main model first, e.g. `openai-codex / gpt-5.5`.
3. Codex auxiliary compression may exceed its task timeout, e.g. `Codex auxiliary Responses stream exceeded 120.0s total timeout`.
4. Auto fallback then tries Nous, e.g. `falling back to nous (google/gemini-3-flash-preview)`.
5. If stored Nous OAuth/agent-key credentials are expired and runtime mint/refresh fails, Nous returns 401. Older fallback logic could stop here and surface the Nous 401 instead of continuing to later fallback providers.

## Safe diagnostic commands

Never print real secrets. Redact tokens/keys and only report provider, expiration, and base URL host.

```bash
# Show relevant config without secrets
python - <<'PY'
import yaml, json
from pathlib import Path
cfg=yaml.safe_load((Path.home()/'.hermes/config.yaml').read_text())
def red(o):
    if isinstance(o, dict):
        return {k: ('[REDACTED]' if any(s in k.lower() for s in ['key','token','secret','password']) else red(v)) for k,v in o.items()}
    if isinstance(o, list): return [red(x) for x in o]
    return o
for key in ['model','compression','auxiliary']:
    print(key, json.dumps(red(cfg.get(key)), ensure_ascii=False, indent=2)[:4000])
PY

# Inspect auth state and JWT/ISO expiry safely
python - <<'PY'
import json, base64, time
from pathlib import Path
p=Path.home()/'.hermes/auth.json'
data=json.loads(p.read_text())
print('active_provider', data.get('active_provider'))
for prov in ['nous','openai-codex','copilot']:
    print('\nPROVIDER', prov)
    obj=(data.get('providers') or {}).get(prov) or {}
    print(' provider_keys', sorted(obj.keys()))
    pool=(data.get('credential_pool') or {}).get(prov)
    creds = pool.get('credentials') or pool.get('entries') or [] if isinstance(pool, dict) else (pool if isinstance(pool, list) else [])
    print(' pool_entries', len(creds))
    for i,c in enumerate(creds[:3]):
        if not isinstance(c,dict): continue
        print('  entry',i,'keys', sorted(c.keys()), 'status', c.get('status') or c.get('state'), 'exhausted', c.get('exhausted'))
        for tk in ['access_token','agent_key','api_key']:
            v=c.get(tk)
            if isinstance(v,str) and v.count('.')>=2:
                try:
                    payload=v.split('.')[1]+'='*(-len(v.split('.')[1])%4)
                    claims=json.loads(base64.urlsafe_b64decode(payload))
                    exp=claims.get('exp')
                    if exp: print('   ',tk,'exp',exp, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(exp)), 'expired', time.time()>exp)
                except Exception: pass
            elif v:
                print('   ', tk, '[REDACTED]', 'len', len(str(v)))
PY
```

## Code fix pattern

For Hermes source fixes in `agent/auxiliary_client.py`:

- Treat expired stored Nous `agent_key` as unavailable when `resolve_nous_runtime_credentials(... force_mint=False)` cannot produce runtime credentials.
- If using credential pool entries, preserve `agent_key_expires_at` / `agent_key_expires_in` / `agent_key_obtained_at` / `expires_at` when converting a `PooledCredential` to a Nous provider dict.
- Fallback logic should not stop after the first fallback provider fails with a recoverable error. If Codex times out and Nous 401s, add Nous to a skip set and try the next provider in the chain.
- Classify fallback-provider auth errors (401), payment/credit errors, rate limits, and connection/timeouts as recoverable for chain continuation when the task provider is `auto`.

## Regression tests to add

In `tests/agent/test_auxiliary_client.py`:

- Test that `_try_nous()` returns `(None, None)` when stored Nous `agent_key_expires_at` is in the past and runtime refresh returns `None`; assert it does not build an OpenAI client.
- Test that `call_llm(task="compression")` continues the fallback chain after primary timeout followed by Nous 401, and passes `additional_skip={"nous"}` to the next fallback attempt.

## Verification

```bash
python3 -m py_compile agent/auxiliary_client.py tests/agent/test_auxiliary_client.py
python -m pytest tests/agent/test_auxiliary_client.py::TestAuxiliaryPoolAwareness tests/agent/test_auxiliary_client.py::TestCallLlmPaymentFallback tests/agent/test_auxiliary_client.py::TestTryPaymentFallback tests/agent/test_auxiliary_client.py::TestIsPaymentError tests/agent/test_auxiliary_client.py::TestIsRateLimitError -q -o 'addopts='
```

If `python3 -m pytest` says `No module named pytest`, use the repo venv `python` on PATH inside the Hermes repo (often `~/.hermes/hermes-agent/venv/bin/python`).

## Operational remediation

A code fix prevents stale Nous from poisoning fallback, but compression still needs at least one working auxiliary provider. If Codex still times out and no later fallback exists, either:

- Refresh Nous: `hermes login --provider nous` (or reset/re-auth via `hermes auth reset nous` then login), or
- Explicitly configure `auxiliary.compression.provider` and `.model` to a stable provider/model with valid credentials.
