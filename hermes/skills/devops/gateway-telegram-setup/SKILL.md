---
name: gateway-telegram-setup
description: Debug and configure Hermes Gateway Telegram integration — config structure pitfalls, env var overrides, verbose verification, stale PID cleanup.
version: 1.0.0
author: Hermes Agent
metadata:
  hermes:
    tags: [gateway, telegram, debugging, config, messaging]
    related: [systematic-debugging, hermes-agent]
---

# Gateway Telegram Setup & Debugging

## When to Use
- Telegram bot not connecting after config changes
- Gateway shows "No messaging platforms enabled"
- Gateway starts but hangs with no output
- Migrating Telegram config between env vars and config.yaml
- `send_message` cannot send to bare `telegram` because no home channel is configured

## Critical Config Structure

**Gateway reads `platforms:` at the TOP LEVEL, NOT `gateway.platforms:`**

```yaml
# ✅ CORRECT — Gateway reads this
platforms:
  telegram:
    enabled: true
    token: '8685837705:AAGh...'

# ❌ WRONG — Gateway ignores this
gateway:
  platforms:
    telegram:
      enabled: true
      bot_token: 8685837705:...
```

Source: `gateway/config.py` line 539 reads `yaml_cfg.get("platforms")` — the top-level key.

**Key field mapping:**
- YAML key is `token`, NOT `bot_token`
- `PlatformConfig.from_dict()` reads `data.get("token")` at line 182

## Env Var Override (Recommended)

`gateway/config.py` `_apply_env_overrides()` (line 857-862) auto-enables Telegram from env:

```bash
# ~/.hermes/.env
TELEGRAM_BOT_TOKEN=8685837705:AAGh...
GATEWAY_ALLOW_ALL_USERS=true  # or TELEGRAM_ALLOWED_USERS=id1,id2
```

This is the simplest approach — no config.yaml changes needed for basic setup.

## Verification Steps

### 1. Test config loading directly
```bash
cd ~/.hermes/hermes-agent
python3 -c "
import os; from hermes_cli.env_loader import load_hermes_dotenv; load_hermes_dotenv()
from gateway.config import load_gateway_config
cfg = load_gateway_config()
for p, c in cfg.platforms.items():
    if c.enabled: print(f'{p.value}: enabled={c.enabled}, token_len={len(c.token) if c.token else 0}')
print('Connected:', cfg.get_connected_platforms())
"
```

### 2. Test bot token validity
```bash
TOKEN=$(grep "TELEGRAM_BOT_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2-)
curl -s "https://api.telegram.org/bot${TOKEN}/getMe" | python3 -m json.tool
```

### 3. Run gateway with verbose output
```bash
hermes gateway stop
hermes gateway run -vv 2>&1 | head -50
# Look for: "✓ telegram connected" and "Gateway running with 1 platform(s)"
```

**Why `-vv` is essential:** Default log level is WARNING. Connection success messages are INFO level and won't appear in `gateway.log` without verbose flag.

### 4. Verify polling is active
```bash
curl -s "https://api.telegram.org/bot${TOKEN}/getUpdates?limit=1" | \
  python3 -c "import sys,json; print(f'Pending: {len(json.load(sys.stdin).get(\"result\",[]))}')"
# 0 pending = gateway is consuming updates (good)
```

## Common Pitfalls

### Errno 24 / Too many open files in Telegram gateway
If Telegram replies with `Sorry, I encountered an error (OSError). [Errno 24] Too many open files: ~/.hermes/sessions/.sessions_*.tmp`, diagnose gateway FD exhaustion before blaming session storage:

```bash
launchctl limit maxfiles
PID=$(launchctl print gui/$(id -u)/ai.hermes.gateway 2>/dev/null | awk '/pid =/ {print $3; exit}')
lsof -p "$PID" -n -P 2>/dev/null | wc -l
python3 - <<'PY' "$PID"
import collections, re, subprocess, sys
out=subprocess.check_output(['lsof','-p',sys.argv[1],'-n','-P'], text=True, stderr=subprocess.DEVNULL)
fds=[]; by=collections.Counter()
for line in out.splitlines()[1:]:
    parts=line.split()
    if len(parts)>=5:
        m=re.match(r'^(\d+)', parts[3])
        if m: fds.append(int(m.group(1)))
        by[parts[4]] += 1
print('numeric_fd_count', len(set(fds)), 'max_fd', max(fds) if fds else None, 'by_type', dict(by.most_common(10)))
PY
```

Strong signal: launchd soft maxfiles is 256 and gateway numeric FDs are ~250, often with many CLOSED IPv4 sockets to the local proxy. Short-term: `hermes gateway start`/restart after cleaning stale pid/lock if needed. Persistent local fix in this setup: launchd generated plist includes `SoftResourceLimits NumberOfFiles=4096` and `HardResourceLimits NumberOfFiles=8192`; `~/.hermes/scripts/post-update-check.py --fix` has `launchd_gateway_nofile_limit` to reapply after updates.

Governance pattern: raising `nofile` is only mitigation. For recurring Errno 24, install/verify an observe-only FD watchdog under `~/.hermes/scripts/` and run it as `no_agent` cron. The watchdog should emit strict JSON, keep bounded FD history, capture lsof snapshots only on warning/critical, surface cron `Errno 24` collateral damage, and explicitly avoid auto-restart/auto-kill. Add a post-update check that py-compiles the watchdog and verifies `auto_restart=false` / `auto_kill=false`. In this user's setup, `~/.hermes/scripts/gateway_fd_watchdog.py` plus cron `gateway-fd-watchdog` is the established pattern.

Deep-dive root-cause workflow: see `references/fd-exhaustion-deep-dive.md` for the evidence commands, likely source-code contributors (Telegram PTB pool budget, auxiliary async client stale-loop cleanup, `/model` client replacement, gateway AIAgent cache), and TDD regression tests. Do not stop at launchd `nofile`; prove FD slope and fix lifecycle contributors.

### Stale PID/Lock files
After crashes, `gateway.pid` and `gateway.lock` may contain dead PIDs:
```bash
rm -f ~/.hermes/gateway.pid ~/.hermes/gateway.lock
hermes gateway restart
```

### launchd log truncation
launchd stdout/stderr go to `gateway.log` / `gateway.error.log` but at WARNING level only. The gateway banner ("Hermes Gateway Starting...") prints to stdout, but connection details need INFO level.

### macOS lsof shows system processes
`lsof -p <PID>` on macOS may show unrelated system processes. Use `ps -p <PID>` to verify process state instead.

### ohmo gateway conflict
Check for competing gateway processes: `ps aux | grep "gateway run" | grep -v grep`

### No home channel for Telegram sends
If `send_message` with bare `target="telegram"` fails with `No home channel set for telegram`, list targets and send to the explicit chat instead of assuming config is broken:

```text
send_message(action="list")
send_message(action="send", target="telegram:<chat name>", message="...")
```

In this user's setup, the DM target has been observed as `telegram:he cheng`. Use a bare platform only after `TELEGRAM_HOME_CHANNEL` is configured. The durable config equivalent is:

```bash
hermes config set TELEGRAM_HOME_CHANNEL <channel_id>
```

## Allowlist Configuration

Without allowlist, all users are denied:
```bash
# In ~/.hermes/.env
GATEWAY_ALLOW_ALL_USERS=true          # Open access (dev only)
TELEGRAM_ALLOWED_USERS=123456,789012  # Specific user IDs
```

Gateway checks: `TELEGRAM_ALLOWED_USERS`, `GATEWAY_ALLOW_ALL_USERS`, `TELEGRAM_ALLOW_ALL_USERS`

## Restart Flow
```bash
# Clean restart
launchctl stop ai.hermes.gateway
rm -f ~/.hermes/gateway.pid ~/.hermes/gateway.lock
launchctl start ai.hermes.gateway

# Or use hermes command
hermes gateway restart
```

## Bot Commands Registered
Gateway auto-registers slash commands from skills. Telegram limits 100 visible commands; overflow uses /commands for full list.
