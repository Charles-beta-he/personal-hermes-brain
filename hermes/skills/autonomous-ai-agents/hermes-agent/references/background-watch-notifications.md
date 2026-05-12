# Background watch notifications: stale/orphan event repair pattern

Use this when Hermes emits a notification such as:

```text
[IMPORTANT: Background process proc_xxx matched watch pattern Local:]
```

but `process(action='poll', session_id='proc_xxx')` returns `not_found`, the expected port is closed, or OS process checks show no live process.

## Symptom

A queued `watch_match` event is delivered after the underlying process has exited, been killed, been pruned from the registry, or after gateway/session lifecycle drift. The notification should be treated as a past observation, not proof of current readiness.

## Immediate operational verification

Before acting on a background readiness notification:

1. Poll the process session:
   - `process(action='poll', session_id='proc_xxx')`
2. If it is a server readiness signal, check the actual endpoint/port:
   - `curl -fsS http://127.0.0.1:<port>/health` or equivalent
   - `lsof -nP -iTCP:<port> -sTCP:LISTEN`
3. Check OS processes when relevant:
   - `ps -ef | grep -E '<command|server|vite|node>' | grep -v grep`

If `poll=not_found` and the port/process is absent, mark the notification as stale and do not continue as if the server is ready.

## Root cause class

`verifier_gap / async lifecycle gap`:

- `tools/process_registry.py` scans process output and queues `watch_match` events in `completion_queue`.
- CLI/gateway drain that queue later and may convert the event into a synthetic `[IMPORTANT]` turn.
- A process can exit or disappear between event production and drain.
- If the event lacks `emitted_at`, `event_seq`, and liveness snapshot, the consumer cannot reliably classify freshness.

## Source-code repair pattern

Prefer a shared helper in `tools/process_registry.py` so CLI and gateway stay consistent.

### 1. Add event metadata at production

When constructing `watch_match` events, add:

- `emitted_at`: wall clock for logs/UX
- `emitted_at_monotonic`: monotonic timestamp for TTL checks
- `event_seq`: registry/session sequence for idempotency
- `pid_snapshot`
- `exited_at_emit`
- `exit_code_at_emit`
- `output_len_at_emit`

Do not add full unbounded output; keep existing truncation/sanitization behavior.

### 2. Add a stale classifier

Implement a helper similar to:

```python
def classify_watch_event(evt, now_monotonic=None) -> dict:
    return {"action": "deliver" | "downgrade" | "drop", "reason": str, "age_seconds": float}
```

Suggested rules:

- Missing `session_id` => `drop`
- Duplicate `(session_id, event_seq)` => `drop`
- Session exists and is still running => `deliver`
- Session missing and age > `WATCH_MATCH_STALE_TTL_SECONDS` => `drop`
- Session exited and age <= `WATCH_MATCH_EXIT_GRACE_SECONDS` => `downgrade` to non-action info
- Session exited and old => `drop`
- Legacy event with no timestamp => compatibility path: deliver or downgrade at most once, with debug log

Suggested defaults:

```text
WATCH_MATCH_STALE_TTL_SECONDS = 30 or 60
WATCH_MATCH_EXIT_GRACE_SECONDS = 10
```

### 3. Gate both CLI and gateway drains

CLI locations to inspect:

- `cli.py` idle drain around `completion_queue.get_nowait()`
- `cli.py` after-agent drain around `completion_queue.get_nowait()`

Gateway location to inspect:

- `gateway/run.py` watch queue drain before `_inject_watch_notification(...)`

Fresh events should still render as `[IMPORTANT]`. Stale events should either be dropped or rendered as non-action `[INFO]`; gateway stale events should usually be log-only to avoid triggering noisy synthetic turns.

### 4. Improve poll/log UX with tombstones

Keep a bounded recent tombstone map for finished/pruned sessions. When `poll(session_id)` cannot find a session but the tombstone exists, return structured context:

```json
{
  "status": "not_found",
  "session_id": "proc_xxx",
  "stale_or_pruned": true,
  "reason": "process exited and was pruned from registry",
  "exit_code": 0,
  "finished_at": "...",
  "hint": "Delayed watch notifications for this process should be treated as stale."
}
```

This preserves backward compatibility (`status=not_found`) while making the tool result actionable.

## Regression tests to add

Target areas:

- `tests/tools/test_notify_on_complete.py` or a dedicated `tests/tools/test_watch_notifications.py`
- `tests/gateway/test_background_process_notifications.py`
- CLI notification formatter/drain tests if present

Cases:

1. Fresh `watch_match` for a running long-lived process delivers exactly once.
2. Missing-session old `watch_match` is dropped or downgraded and does not become `[IMPORTANT]`.
3. Exited-session old `watch_match` is dropped.
4. Exited-session very fresh `watch_match` is downgraded, not treated as readiness.
5. Duplicate `event_seq` is ignored.
6. Existing `notify_on_complete` / `is_completion_consumed` behavior is unchanged.
7. Gateway stale `watch_match` does not call synthetic agent injection.
8. `poll()` for a recent tombstone returns `stale_or_pruned` explanation.

## Verification commands

Use the repo's Python, not bare `python` on macOS where it may be missing:

```bash
PY=.venv/bin/python; [ -x "$PY" ] || PY=venv/bin/python; [ -x "$PY" ] || PY=python3
"$PY" -m pytest tests/tools/test_notify_on_complete.py tests/gateway/test_background_process_notifications.py -q -o 'addopts='
"$PY" -m pytest tests/tools/test_process_registry.py -q -o 'addopts='
"$PY" -m pytest tests/hermes_cli -q -o 'addopts='
"$PY" -m pytest tests/gateway -q -o 'addopts='
```

## Pitfalls

- Do not disable `watch_patterns` wholesale; fresh one-shot server readiness notifications are useful.
- Do not let stale gateway watch events trigger new agent turns by default.
- Do not rely on model agreement alone; verify by poll + port/process checks.
- Do not use bare `python` on macOS; prefer venv Python or `python3`.
- If editing a vendor/upstream-tracking Hermes checkout, account for `hermes update` overwriting local patches; prefer upstreamable small patches or post-update healing.