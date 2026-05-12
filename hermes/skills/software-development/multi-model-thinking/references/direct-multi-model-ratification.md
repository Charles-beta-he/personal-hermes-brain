# Direct Multi-Model Ratification Loop

Use when you need multi-model consensus WITHOUT consult_models.py — direct API/CLI calls to each model, with iterative amend loops.

## Provider Quirks (Hard-Won)

| Provider | Quirk | Fix |
|----------|-------|-----|
| DeepSeek V4 Pro | Reasoning tokens consume max_tokens budget. With max_tokens=500, content gets truncated mid-JSON after ~70 chars. | Set max_tokens>=2000 for DeepSeek. |
| MiMo (Xiaomi) | Returns empty string when called concurrently with other providers. Works fine individually. | Run MiMo **sequentially** AFTER concurrent batch. |
| MiMo (Xiaomi) | Wraps JSON output in ```` ```json ... ``` ```` blocks even when prompt says "raw JSON only". | Use `extract_json()` with regex fallback for code blocks. |
| Claude (Anthropic) | `--max-turns 1` with long prompts sometimes triggers `error_max_turns` response. | Use `--max-turns 1` (not 0) and keep prompt under 3000 chars. |
| GPT-5.5 (OpenAI Codex) | Prefixes output with `⚠️ Reached maximum iterations (1). Requesting summary...` | `extract_json()` with `{` find/`}` rfind handles this. |

## The 3+1 Pattern

```
Phase 1: Claude + GPT + DeepSeek concurrent (ThreadPoolExecutor, max_workers=3)
Phase 2: MiMo sequential (with 3 retries, 3s backoff)
```

**Why not all 4 concurrent:** MiMo consistently returns empty responses when competing for resources with the other 3. Tested across 10+ rounds — 0% success concurrent, 100% success sequential.

## JSON Extraction (Critical)

```python
def extract_json(s):
    s = (s or '').strip()
    if not s: raise ValueError('empty response')
    try: return json.loads(s)
    except: pass
    # Handle ```json code blocks (MiMo)
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', s, re.S)
    if m: return json.loads(m.group(1))
    # Handle prefix text (GPT warning)
    a = s.find('{'); b = s.rfind('}')
    if a >= 0 and b > a: return json.loads(s[a:b+1])
    raise ValueError(f'no json object ({len(s)} chars): {s[:200]}')
```

## Ratification Schema

Each model outputs:
```json
{
  "vote": "approve|amend|reject",
  "best_within_constraints": true|false,
  "unresolved_severity_ge_3_blockers": [],
  "reasoning": "<=500 chars citing claim/evidence ids"
}
```

For multi-direction analysis, nest per direction:
```json
{
  "direction_1": {"vote": "...", "best_within_constraints": true, ...},
  "direction_2": {"vote": "...", ...},
  "overall": {"vote": "approve|amend|reject", "reasoning": "..."}
}
```

## Certification Levels

| Level | Condition | Label |
|-------|-----------|-------|
| Full | 4/4 approve | `certified_four_model` |
| Scoped | 3/4 approve, 0 reject | `certified_scoped_three_model_with_X_caveat` |
| Not certified | <3 approve or any reject | `not_certified` |

## Amend Loop

When models return `amend`:
1. Extract specific requirements from reasoning (e.g., "add numeric guardrails")
2. Update the proposal with those specifics
3. Re-run ratification for the amended version
4. If still amend after 2 rounds, accept the model's suggestions and implement

## Evidence Requirements

Models are more likely to approve when evidence includes:
- Concrete file paths (not just descriptions)
- Selfcheck PASS/FAIL output
- Stats (task counts, error counts)
- Timestamps showing recency

GPT is particularly strict — it will vote `false` on "verified" if it suspects claims aren't backed by tool output.

## Template: Ratification Script Skeleton

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_ratification(claims, decision, directions=None):
    prompt = build_prompt(claims, decision, directions)
    
    # Phase 1: concurrent
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = {
            ex.submit(call_claude, prompt): 'claude',
            ex.submit(call_gpt, prompt): 'gpt',
            ex.submit(call_deepseek, prompt): 'deepseek',
        }
        for fut in as_completed(futs):
            model = futs[fut]
            try:
                parsed = extract_json(fut.result())
                votes.append({'model': model, 'ok': True, 'parsed': parsed})
            except Exception as e:
                votes.append({'model': model, 'ok': False, 'error': str(e)})
    
    # Phase 2: MiMo sequential
    try:
        parsed = extract_json(call_mimo(prompt))
        votes.append({'model': 'mimo', 'ok': True, 'parsed': parsed})
    except Exception as e:
        votes.append({'model': 'mimo', 'ok': False, 'error': str(e)})
    
    return summarize(votes)
```
