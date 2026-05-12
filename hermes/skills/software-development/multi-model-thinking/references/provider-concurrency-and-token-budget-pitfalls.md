# Provider Concurrency and Token Budget Pitfalls

Session: 2026-05-10 Kanban Watch multi-model ratification (4/4 certified)
Symptom: parallel 4-model ratification failed repeatedly; sequential + adjusted budgets succeeded.

## MiMo Concurrent Empty Response

**Symptom:** When all 4 models are called via `ThreadPoolExecutor(max_workers=4)`, MiMo v2.5 Pro returns empty `content` string with `finish_reason: stop`. The API returns HTTP 200, no error — just zero-length content.

**Root cause:** MiMo's API has a concurrency/rate-limit behavior where simultaneous requests from the same API key can produce silently empty completions. Not a token limit, not a prompt issue — it's a provider-side concurrency artifact.

**Fix:** Run MiMo **sequentially after** the other 3 models finish concurrently:

```python
# Phase 1: concurrent Claude + GPT + DeepSeek
with ThreadPoolExecutor(max_workers=3) as ex:
    futs = {ex.submit(fn): model for model, fn in [
        ('claude-opus-4-7', call_claude),
        ('gpt-5.5', call_gpt),
        ('deepseek-v4-pro', call_deepseek),
    ]}
    for fut in as_completed(futs):
        # collect results

# Phase 2: MiMo sequential
raw = call_mimo()  # no retry needed when sequential
```

**Retry logic is insufficient:** Even with 3 retries + exponential backoff (2s, 4s, 6s), MiMo continued returning empty content when called concurrently. Only sequential execution resolved it.

**Detection:** `extract_json(s)` raises `ValueError('empty response')` when `s.strip()` is empty. Log `finish_reason` and content length for diagnosis.

## DeepSeek Reasoning Token Budget

**Symptom:** DeepSeek V4 Pro returns `finish_reason: length` with only ~66 chars of `content` but 2000+ chars of `reasoning_content`. The `max_tokens` budget is shared between reasoning tokens and content tokens.

**Root cause:** DeepSeek's chain-of-thought reasoning consumes from the same `max_tokens` budget as the final output. A `max_tokens=500` setting allows ~400 tokens of reasoning + ~100 tokens of content, which truncates JSON mid-string.

**Fix:** Set `max_tokens=2000` for DeepSeek in ratification prompts:

```python
# Wrong: max_tokens=500 → reasoning consumes budget, content truncated
body = json.dumps({'model': 'deepseek-v4-pro', 'messages': [...], 'max_tokens': 500})

# Right: max_tokens=2000 → reasoning + content both fit
body = json.dumps({'model': 'deepseek-v4-pro', 'messages': [...], 'max_tokens': 2000})
```

**Detection:** Check `finish_reason == 'length'` in the response. Parse error `Unterminated string starting at: line 1 column N` on DeepSeek output is a strong signal of token budget truncation.

**Cost impact:** DeepSeek is cheap; the 4x token increase is negligible (~$0.002 per ratification).

## MiMo ```json Code Block Wrapping

**Symptom:** MiMo wraps JSON output in markdown code blocks even when the prompt says "Return ONLY compact JSON":

```
```json
{"vote":"approve",...}
```
```

**Fix:** `extract_json()` must handle code blocks:

```python
def extract_json(s):
    s = (s or '').strip()
    if not s:
        raise ValueError('empty response')
    try:
        return json.loads(s)
    except Exception:
        pass
    # Handle ```json ... ``` blocks
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', s, re.S)
    if m:
        return json.loads(m.group(1))
    # Fallback: find first { to last }
    a = s.find('{')
    b = s.rfind('}')
    if a >= 0 and b > a:
        return json.loads(s[a:b+1])
    raise ValueError(f'no json object in response ({len(s)} chars)')
```

## Recommended 4-Model Ratification Pattern

```python
# Step 1: Build prompt with grounded claims/evidence + decision
PROMPT = f"""You are an independent ratifier in a multi-model decision loop. Return ONLY compact JSON.
Question: {QUESTION}
Grounded claims/evidence: {json.dumps(CLAIMS, ensure_ascii=False)}
Proposed decision: {json.dumps(DECISION, ensure_ascii=False)}
Required JSON schema: {{"vote":"approve|amend|reject","best_within_constraints":true|false,"unresolved_severity_ge_3_blockers":[],"reasoning":"<=500 chars"}}
"""

# Step 2: Concurrent trio (Claude + GPT + DeepSeek)
# DeepSeek needs max_tokens=2000 due to reasoning budget
with ThreadPoolExecutor(max_workers=3) as ex:
    ...

# Step 3: MiMo sequential
raw = call_mimo()

# Step 4: Validate 4/4 approval
all_approved = all(v['parsed']['vote'] == 'approve' for v in votes)
```

## Per-Provider Budget Summary

| Provider   | max_tokens | Concurrency | Notes                          |
|------------|-----------|-------------|--------------------------------|
| Claude     | 500       | Safe        | No reasoning token overhead    |
| GPT-5.5    | 500       | Safe        | May prefix with warnings       |
| DeepSeek   | 2000      | Safe        | Reasoning consumes budget      |
| MiMo       | 500       | SEQUENTIAL  | Empty response if concurrent   |

## Verified: Multi-Direction Ratification (2026-05-10)

Ran 3-direction ratification (Agent Team + Kanban Watch + Missions Task Pool) with 4 models. Confirmed:
- Claude + GPT + DeepSeek concurrent: all 3 returned valid JSON
- MiMo sequential: returned valid JSON (3/3 attempts)
- DeepSeek max_tokens=2000: `finish_reason=stop`, full JSON content (~300 chars)
- DeepSeek max_tokens=500: `finish_reason=length`, truncated at ~66 chars (confirms budget issue)

Amend loop: Claude/GPT voted amend on Direction 3 (missing numeric guardrails). After adding specific values (appetite=30min, max_retry=3, human_escape=2block/3crash, max_runtime=3600s, lease=900s, heartbeat=120s), all 4 voted approve on re-ratification.

Final confirmation: 4/4 models confirmed consolidated 3-direction result = FINAL_CERTIFIED.
