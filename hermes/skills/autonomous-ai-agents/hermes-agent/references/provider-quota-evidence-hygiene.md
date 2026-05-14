# Provider quota evidence hygiene

Use this when changing Hermes provider/model quota tracking, token-usage logs, model routing evidence, or local-brain tasks that persist provider usage snapshots.

## Why it matters

Quota and usage telemetry is evidence for routing and budget decisions, but provider response headers and caller metadata can contain secrets or prompt/completion text. Treat quota state/logs as clean-room operational evidence: enough numeric facts to drive decisions, no credentials and no user/model content.

## Implementation pattern

1. Sanitize before every persistence boundary, not only at display time:
   - in-memory state snapshots returned to callers
   - JSON state files
   - JSONL append logs
   - any taskpool evidence object that embeds usage/quota data
2. Redact credential-shaped keys and values recursively:
   - `Authorization`, `api_key`, `access_token`, `refresh_token`, `id_token`, `auth_token`, `session_token`
   - `secret`, `password`, `passwd`, `cookie`
   - Bearer tokens, `sk-*`, `xox*`, and similar long credential-like strings
3. Preserve only safe usage facts:
   - token counts: `input_tokens`, `output_tokens`, `prompt_tokens`, `completion_tokens`, cache token counts, `total_tokens`
   - operational numbers: `remaining_tokens`, `cost_usd`, `latency_ms`, reset timestamps/epoch values
   - provider/model identifiers if they are not credentials
4. Drop prompt/completion text and arbitrary non-numeric usage fields before writing state or logs. Do not rely on later readers to ignore them.
5. Keep quota semantics intact: safe fields such as `remaining_tokens` must not be over-redacted, and low-confidence/no-quota headers must not overwrite a higher-confidence exact snapshot.

## Test pattern

Add a regression test that calls the public recording API with a deliberately toxic payload containing:

- authorization headers and bearer tokens
- common credential key names
- prompt/completion text in usage-like objects
- safe numeric usage fields

Then assert all persistence surfaces are clean:

- returned snapshot/state
- saved state file
- appended JSONL log

Also assert the safe numeric fields remain present so the sanitizer does not destroy routing utility.

## Verification commands

For user-local Hermes scripts, prefer direct script tests plus compile and broader Hermes self-test when available:

```bash
python3 ~/.hermes/scripts/test_model_quota.py
python3 -m py_compile ~/.hermes/scripts/model_quota.py ~/.hermes/scripts/test_model_quota.py
python3 ~/.hermes/scripts/self-test.py
```

If the change is part of a taskpool closeout, run proof/selfcheck/dashboard gates after the code tests and record the sanitized evidence path in the task note.

## Pitfalls

- Do not persist first and redact during reporting; logs and state files are already durable evidence.
- Do not blanket-redact every field containing `token`; `remaining_tokens`, `input_tokens`, and `output_tokens` are the useful quota signal.
- Do not store prompt/completion samples to make debugging easier; use claim-linked numeric evidence instead.
- Do not mark a task done from sanitizer tests alone if the task metadata requires taskpool proof, dashboard refresh, or multi-model target-binding checks.