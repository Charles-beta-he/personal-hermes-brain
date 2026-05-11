# MiMo Concurrency Pitfall

## Problem

MiMo (Xiaomi mimo-v2.5-pro) returns **empty responses** when called concurrently with other models via `ThreadPoolExecutor`. The same MiMo endpoint works fine when called individually.

Root cause: likely rate limiting or connection pool contention on the MiMo API side.

## Solution

**Always run MiMo sequentially AFTER the concurrent trio (Claude + GPT + DeepSeek).**

```python
# CORRECT: Phase 1 concurrent, Phase 2 MiMo sequential
with ThreadPoolExecutor(max_workers=3) as ex:
    futs = {ex.submit(fn): m for m, fn in [
        ('claude-opus-4-7', call_claude),
        ('gpt-5.5', call_gpt),
        ('deepseek-v4-pro', call_deepseek),
    ]}
    # collect results...

# Phase 2: MiMo alone
result = call_mimo()  # Works reliably when sequential
```

```python
# WRONG: all 4 concurrent
with ThreadPoolExecutor(max_workers=4) as ex:  # MiMo will return empty
```

## Retry Pattern for MiMo

```python
def call_mimo():
    for attempt in range(3):
        try:
            content = make_request()
            if content and content.strip():
                return content
            time.sleep(3 * (attempt + 1))  # empty response, retry
        except HTTPError as e:
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
    raise RuntimeError('MiMo returned empty after 3 retries')
```

## Detection

Symptom: `extract_json` raises `ValueError: empty response` for MiMo only, while other models succeed. The `error` field in the vote shows `"empty response"`.

## Verified

2026-05-10, multiple ratification rounds. MiMo concurrent = empty, MiMo sequential = works every time.
