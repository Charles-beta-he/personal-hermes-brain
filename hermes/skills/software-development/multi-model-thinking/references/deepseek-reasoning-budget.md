# DeepSeek Reasoning Token Budget Pitfall

## Problem

DeepSeek V4 Pro uses a "thinking" mode that generates `reasoning_content` tokens. These tokens **consume the same `max_tokens` budget** as the actual content output. A ratification prompt that should produce ~200 tokens of JSON can be truncated because DeepSeek spends 2000+ tokens reasoning first.

Symptom: `finish_reason: length` with content truncated mid-JSON (e.g., `{"vote":"approve","best_within_constraints":true,"unresolved_sever` — cut off at 66 chars).

## Budget Breakdown

From a real test:
- `max_tokens: 500` (set in request)
- `reasoning_tokens: 2142` (in completion_tokens_details)
- `content_tokens: 66` (actual output, truncated)
- `finish_reason: length`

The reasoning tokens ate 2142 of the 500-token budget → content got only 66 chars before cutoff.

## Solution

**Set `max_tokens>=2000` for DeepSeek ratification requests.**

```python
# CORRECT
body = json.dumps({
    'model': 'deepseek-v4-pro',
    'messages': [{'role': 'user', 'content': PROMPT}],
    'temperature': 0,
    'max_tokens': 2000,  # Must accommodate reasoning + content
}).encode()

# WRONG — reasoning will consume most of the budget
'max_tokens': 500  # Too low for DeepSeek
```

## Other Models (for comparison)

| Model | max_tokens needed | Reason |
|-------|------------------|--------|
| DeepSeek V4 Pro | 2000+ | reasoning_content consumes budget |
| GPT-5.5 | 500 | no hidden reasoning tokens |
| Claude Opus 4.7 | 500 | no hidden reasoning tokens |
| MiMo v2.5 Pro | 500 | reasoning_content present but small |

## Detection

Symptom: DeepSeek returns truncated JSON with `finish_reason: length`. The content is a valid JSON prefix that fails to parse.

Check: `data['choices'][0]['finish_reason'] == 'length'` → increase max_tokens.

## Verified

2026-05-10, ratification loop. DeepSeek at max_tokens=500 consistently truncated. At max_tokens=2000, works reliably.
