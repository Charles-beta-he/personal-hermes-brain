# 4-Model Verification Execution Patterns

Proven execution patterns for running Claude + GPT + DeepSeek + MiMo ratification.

## Execution Order

```
Phase 1: Concurrent — GPT + DeepSeek (2 parallel)
Phase 2: Sequential — Claude alone
Phase 3: Sequential — MiMo alone (after all others complete)
```

**Why this order:**
- MiMo returns empty responses when called concurrently with other models. MUST be sequential.
- Claude `-p` mode sometimes hits `error_max_turns` on complex prompts. Running alone reduces contention.
- GPT + DeepSeek are reliable in concurrent mode.

## Model-Specific Quirks

### DeepSeek
- `reasoning_content` tokens consume `max_tokens` budget
- For ratification prompts: use `max_tokens>=2000` (not 500)
- With 500, reasoning eats budget → content truncated mid-JSON → parse error
- API: `https://api.deepseek.com/chat/completions`, model=`deepseek-v4-pro`

### MiMo (Xiaomi)
- Returns empty content in concurrent calls — always run sequentially
- May wrap JSON in ```json code blocks
- API: `https://token-plan-cn.xiaomimimo.com/v1/chat/completions`, model=`mimo-v2.5-pro`
- Retry 3 times with exponential backoff for empty responses

### Claude (`-p` mode)
- Returns wrapper JSON: `{"type":"result","result":"..."}` — extract inner result
- May hit `error_max_turns` even with `--max-turns 1` on complex prompts
- Shorten prompt or accept failure gracefully

### GPT-5.5 (via hermes chat -q)
- Can prepend "⚠️ Reached maximum iterations..." before JSON
- Robust extractor handles this (scans for `{...}` anywhere in output)
- Use `--provider openai-codex --quiet --ignore-rules`

## JSON Extraction

All models may wrap JSON in ```json code blocks. Universal extractor:

```python
def extract_json(s):
    s = (s or '').strip()
    if not s: raise ValueError('empty')
    try: return json.loads(s)
    except: pass
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', s, re.S)
    if m: return json.loads(m.group(1))
    a, b = s.find('{'), s.rfind('}')
    if a >= 0 and b > a: return json.loads(s[a:b+1])
    raise ValueError(f'no json object ({len(s)} chars)')
```

## Certification Levels

| Level | Meaning |
|-------|---------|
| `certified_four_model` | All 4 approve, 0 reject |
| `certified_three_model` | 3 approve, 0 reject (1 infra failure) |
| `certified_scoped` | 2+ approve, 0 reject (document which failed) |
| `not_certified` | <2 approve OR any reject |

Document infra failures vs model dissent separately. Infra failures don't block scoped certification.

## Pitfalls

- **Never run MiMo concurrently** — guaranteed empty response
- **Never use DeepSeek max_tokens=500** — reasoning truncates content
- **Never skip Claude wrapper extraction** — raw output is not the model's response
- **Cron jobs using MiMo may show historical errors** — `last_error` persists from before fix, next run clears it
