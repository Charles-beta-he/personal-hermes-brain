# Lark task closeout notes: auth support CTA session

This reference captures reusable details from a UVISA Lark task closeout where the product defect was already fixed in production code and the remaining work was evidence, regression coverage, commit, and notification.

## Pattern: implementation already present

When code evidence shows the defect path is already implemented, do not churn production code just to make a diff. Instead:

1. Cite exact code evidence for the existing behavior.
2. Add the missing regression test that would have caught the original defect.
3. Add the minimum ledger/docs row for traceability.
4. Run targeted browser tests for the regression across configured desktop/mobile projects.
5. Run build and `git diff --check`.
6. If a full suite is known red, record exact failure counts and tie them to pre-existing documented drift; do not hide the failure.
7. Commit the scoped regression/docs diff and notify through the requested channel.

## Railway CLI monitor

If Railway CLI is authenticated and linked, prefer it over browser screenshots:

```bash
railway status
railway service status --all --json
railway deployment list --service <service> --limit 3 --json
```

Use `service status` for the closeout health gate. Record only service name, deploymentId, status, and stopped flag.

## Telegram notification fallback

If `send_message(target="telegram")` fails with no home channel, retry with the known direct target form such as `telegram:he cheng` before declaring notification blocked.

## Background process cleanup fallback

If the process tool cannot kill a background dev server because local runtime deps such as `psutil` are missing, terminate by PGID and verify ports are closed:

```bash
pgid=$(ps -o pgid= -p "$PID" | tr -d ' ')
[ -n "$pgid" ] && kill -TERM -$pgid 2>/dev/null || true
python3 - <<'PY'
import socket, time
for _ in range(10):
    open_ports=[]
    for host in ('127.0.0.1','::1'):
        for port in (5173,3001):
            family=socket.AF_INET6 if host=='::1' else socket.AF_INET
            s=socket.socket(family); s.settimeout(0.2)
            try:
                s.connect((host, port)); open_ports.append(f'{host}:{port}')
            except Exception:
                pass
            finally:
                s.close()
    if not open_ports:
        print('ports closed')
        break
    time.sleep(0.5)
else:
    print('still open:', ','.join(open_ports))
PY
```
