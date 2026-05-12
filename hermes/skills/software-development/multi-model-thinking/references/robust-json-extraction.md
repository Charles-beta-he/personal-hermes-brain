# Robust JSON Extraction from Model Outputs

## Problem

Different models output JSON in different formats:
- **Claude**: Clean JSON or `{"result": "..."}` wrapper
- **GPT-5.5**: May prepend text like `⚠️ Reached maximum iterations...\n{...}`
- **DeepSeek**: Clean JSON (when not truncated)
- **MiMo**: Wraps in ` ```json\n{...}\n``` ` markdown code blocks

A naive `json.loads(output)` fails for 2-3 of these.

## Universal Extractor

```python
def extract_json(s):
    """Extract JSON from any model output format."""
    s = (s or '').strip()
    if not s:
        raise ValueError('empty response')
    
    # Try 1: direct parse
    try:
        return json.loads(s)
    except Exception:
        pass
    
    # Try 2: ```json ... ``` code blocks
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', s, re.S)
    if m:
        return json.loads(m.group(1))
    
    # Try 3: find first { to last }
    a = s.find('{')
    b = s.rfind('}')
    if a >= 0 and b > a:
        return json.loads(s[a:b+1])
    
    raise ValueError(f'no json object in response ({len(s)} chars): {s[:200]}')
```

## Format Catalog

| Model | Typical format | Which try succeeds |
|-------|---------------|-------------------|
| Claude | `{"vote":"approve",...}` | Try 1 |
| Claude (via CLI) | `{"result":"{\"vote\":...}"}` | Try 1 (outer), then extract inner |
| GPT-5.5 | `⚠️ ...\n{"vote":"approve",...}\n` | Try 3 |
| DeepSeek | `{"vote":"approve",...}` | Try 1 |
| MiMo | ` ```json\n{"vote":"approve",...}\n``` ` | Try 2 |

## Pitfalls

- **MiMo empty response**: If MiMo returns empty (concurrency issue), `extract_json` raises `ValueError: empty response`. Fix: run MiMo sequentially. See `mimo-concurrency-pitfalls.md`.
- **DeepSeek truncation**: If `max_tokens` too low, JSON is cut mid-string. `extract_json` raises `JSONDecodeError`. Fix: increase `max_tokens>=2000`. See `deepseek-reasoning-budget.md`.
- **Nested JSON**: Claude CLI returns `{"result": "<inner JSON string>"}`. Need two-stage extraction:
  ```python
  outer = json.loads(raw)
  if isinstance(outer, dict) and isinstance(outer.get('result'), str):
      raw = outer['result']
  ```
- **GPT-5.5 max iterations prefix**: The `⚠️ Reached maximum iterations (1). Requesting summary...` prefix is always followed by the actual JSON. Try 3 handles this.
