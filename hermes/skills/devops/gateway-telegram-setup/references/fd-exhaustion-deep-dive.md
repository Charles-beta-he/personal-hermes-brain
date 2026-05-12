# Gateway / Telegram FD exhaustion deep-dive

Use when Telegram reports `OSError: [Errno 24] Too many open files`, especially for paths under `~/.hermes/sessions/.sessions_*.tmp`.

## Symptom interpretation

`Too many open files` on a session temp file is usually a process-wide gateway FD exhaustion symptom, not a corrupt sessions store. Corroborating collateral failures often include:

- `cron/jobs.json` read failures
- `.channel_directory_*.tmp` write failures
- shell hook failures opening `/dev/null`
- LLM API calls failing with `[Errno 24] Too many open files`
- session_search/sqlite/kanban failures in the same timestamp window

## Evidence collection commands

```bash
LABEL=ai.hermes.gateway
UID_NUM=$(id -u)
PID=$(launchctl print "gui/$UID_NUM/$LABEL" 2>/dev/null | awk '/pid =/ {print $3; exit}')
echo "pid=${PID:-none}"
ps -o pid,ppid,stat,etime,command -p "$PID"
launchctl print "gui/$UID_NUM/$LABEL" | sed -n '/resource limits = {/,/}/p'
launchctl limit maxfiles

/usr/bin/python3 - "$PID" <<'PY'
import collections, re, subprocess, sys
pid=sys.argv[1]
out=subprocess.check_output(['lsof','-nP','-p',pid], text=True, stderr=subprocess.DEVNULL)
lines=out.splitlines()
fds=[]; by=collections.Counter(); states=collections.Counter(); proxy=[]
for line in lines[1:]:
    parts=line.split(None,8)
    if len(parts)>=5:
        m=re.match(r'^(\d+)', parts[3])
        if m: fds.append(int(m.group(1)))
        by[parts[4]]+=1
    if 'TCP' in line or 'UDP' in line:
        sm=re.search(r'\(([^()]*)\)\s*$', line)
        if sm: states[sm.group(1)]+=1
    if '127.0.0.1:1082' in line: proxy.append(line)
print('numeric_fd_count',len(set(fds)),'max_fd',max(fds) if fds else None)
print('by_type', dict(by.most_common(10)))
print('states', dict(states))
print('proxy_1082', len(proxy))
for x in proxy[:20]: print('proxy', x)
PY

grep -n "Too many open files\|Errno 24" ~/.hermes/logs/gateway.error.log | tail -40
```

Avoid assigning shell variable `UID` in bash; it is readonly on macOS bash. Use `UID_NUM`.

## High-probability source-code contributors

1. Telegram PTB `HTTPXRequest` pool budget
   - `gateway/platforms/telegram.py` builds two separate pools: `request` and `get_updates_request`.
   - A default pool size of 512 means `512 × 2` potential connections before other gateway FD users.
   - If `TELEGRAM_PROXY`/environment proxy points to `127.0.0.1:1082`, many sockets may show as local proxy `CLOSED`/`ESTABLISHED` entries.
   - Prefer a default around 16-32 and keep `HERMES_TELEGRAM_HTTP_POOL_SIZE` override.

2. Auxiliary async client stale-loop cleanup
   - `agent/auxiliary_client.py` process-global `_client_cache` stores async clients bound to event loops.
   - Cleanup that only sets `httpx._state = CLOSED` can suppress finalizer errors while leaving sockets until process exit.
   - Robust cleanup should force-close underlying httpcore sockets for stale-loop async clients, then mark the client closed.

3. `AIAgent.switch_model()` client replacement
   - When `/model` creates a new primary client, save the old `self.client` / `_anthropic_client` before replacement and explicitly close them after the new client is installed.
   - Otherwise old httpx pools can be stranded in long-lived gateway sessions.

4. Gateway AIAgent cache pressure
   - `_AGENT_CACHE_MAX_SIZE=128` and long idle TTL can be legal but high FD budget for a gateway that holds LLM clients.
   - Consider FD-aware cache caps or env overrides if FD slope remains high after fixing Telegram/auxiliary clients.

## TDD regression tests to add

- Telegram HTTP defaults: assert two distinct `HTTPXRequest` objects and default `connection_pool_size == 32` (or chosen bounded default), env override still works, proxy path passes proxy to both.
- Auxiliary async cleanup: fake `client._client._transport._pool._connections[*]._network_stream._sock`, call `_force_close_async_httpx`, assert `shutdown()` and `close()` were called.
- Model switch cleanup: construct an `AIAgent` with fake old client, monkeypatch `_create_openai_client` to return new client, call `switch_model()`, assert old client was closed and new client was not.

## Runtime fix sequence

1. Confirm current FD pressure and launchd per-service nofile.
2. Write RED tests for each suspected lifecycle bug.
3. Implement the smallest code fixes.
4. Run targeted tests first, then relevant test files.
5. Restart gateway so code changes load.
6. Re-sample FD counts and proxy socket states over at least 5 intervals.
7. Commit locally only after tests + runtime sample pass.

Concrete closeout pattern that worked in May 2026:

```bash
cd ~/.hermes/hermes-agent
./venv/bin/python -m pytest \
  tests/gateway/test_telegram_conflict.py::test_connect_uses_fd_safe_telegram_http_pool_defaults \
  tests/agent/test_crossloop_client_cache.py::test_force_close_async_httpx_closes_underlying_pool_sockets \
  tests/run_agent/test_openai_client_lifecycle.py::test_switch_model_closes_replaced_shared_openai_client -q
./venv/bin/python -m pytest \
  tests/gateway/test_telegram_conflict.py \
  tests/agent/test_crossloop_client_cache.py \
  tests/run_agent/test_openai_client_lifecycle.py -q
hermes gateway restart
# Then sample launchd limits + FD counts; expect service soft/hard nofile 4096/8192
# and numeric_fd_count far below the soft limit (for example ~30-40 after restart).
python3 ~/.hermes/scripts/post-update-check.py
```

Patch details to preserve if reapplying after upstream update:
- `gateway/platforms/telegram.py`: bound the default `HERMES_TELEGRAM_HTTP_POOL_SIZE` to 32, while still allowing env override, and assert both `builder.request(...)` and `builder.get_updates_request(...)` receive distinct bounded `HTTPXRequest` objects.
- `agent/auxiliary_client.py`: `_force_close_async_httpx()` should walk `httpcore` pool private attrs (`_connections` / `_pool`, `_network_stream` / `_stream`) and call `socket.shutdown(SHUT_RDWR)` + `socket.close()` before marking the inner httpx client `ClientState.CLOSED`.
- `run_agent.py`: `AIAgent.switch_model()` should capture the old shared OpenAI-compatible client before replacing it and call `_close_openai_client(old_client, reason="switch_model_replace", shared=True)` after the new client is installed when the object differs.

Certification caveat:
- A `consult_models.py --discussion` run can be truth-grounded and 3-model approved but still return `not_certified` if the MiMo/Xiaomi discussion adapter fails with `400 Not supported model xiaomi` or another provider runtime error. Report this as `evidence-grounded + deterministic tests passed + degraded multi-model advisory`, not as full four-model certification.
- For final operational closure, prefer an observe-only FD slope check over auto-restart claims: one clean post-restart FD snapshot proves immediate mitigation, while a 1h/24h bounded trend proves absence of slow leakage.

## Watchdog stance

For this user's setup, watchdog should be observe-only by default: emit bounded JSON and alerts, capture lsof snapshots only on warning/critical, and avoid auto-kill/auto-restart until ratification and deterministic gates explicitly approve it.
