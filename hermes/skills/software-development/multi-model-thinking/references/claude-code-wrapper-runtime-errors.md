# Claude Code wrapper runtime errors in `consult_models.py`

Use this when Hermes multi-model fanout/discussion reports a Claude parsing failure, blank `adapter claude-code failed:` message, or `failed_closed` discussion artifact while Claude Code CLI is invoked with `--output-format json`.

## Root cause pattern

Claude Code JSON mode returns an **outer CLI wrapper**, not just model-authored JSON:

```json
{
  "type": "result",
  "is_error": false,
  "api_error_status": null,
  "result": "{\"ok\":true}"
}
```

Runtime/provider failures can still return `returncode == 0` with the failure encoded in stdout:

```json
{
  "type": "result",
  "is_error": true,
  "api_error_status": 403,
  "result": "Credit balance is too low"
}
```

Do not classify that as a model JSON parse failure. It is a provider/runtime failure. The same applies when `is_error` is false/missing but `api_error_status` is non-zero.

## Diagnostic checklist

1. Inspect the latest tick artifacts before rerunning:
   - `~/.hermes/tick-*/plans/claude*.json`
   - `~/.hermes/tick-*/discussion/round_*/model_response_claude*.json`
   - `~/.hermes/tick-*/discussion/round_*/parse_status_claude*.json`
2. Distinguish phases:
   - Planner phase: low-confidence shadow plan, blank `adapter claude-code failed:` or `output parse/invoke failed`.
   - Discussion phase: `failed_closed` or `runtime_error` with wrapper snippets in raw/diagnosis.
3. Verify the CLI path independently with a minimal wrapper probe:

```bash
printf 'Reply with exactly {"ok":true}\n' \
  | claude -p --model claude-opus-4-7 --max-turns 1 --output-format json \
  > /tmp/claude_probe_stdout.json 2> /tmp/claude_probe_stderr.txt
python - <<'PY'
import json, pathlib
obj=json.loads(pathlib.Path('/tmp/claude_probe_stdout.json').read_text())
print({k: obj.get(k) for k in ['type','is_error','api_error_status']})
print(str(obj.get('result',''))[:120])
PY
```

4. Sanitize every stdout/stderr excerpt before storing or reporting; stdout wrappers can contain provider messages and occasionally credential-shaped text.

## Fix pattern

- Centralize wrapper decoding in one helper (for example `_decode_claude_code_output`).
- Treat a dict as a Claude wrapper if it has `result`, `is_error`, `api_error_status`, `error`, `subtype`, or `type in {"result", "error"}`.
- Coerce `is_error` carefully: `bool("false") == True`, so normalize strings explicitly.
- Runtime error condition:
  - `is_error is true`, or
  - `api_error_status not in (None, 0, "0", "")`, or
  - wrapper type/subtype indicates error/failure.
- For successful wrappers, pass only inner `result` to planner/discussion JSON parsing.
- For error wrappers, raise a typed runtime exception (for example `ModelRuntimeError`) with redacted detail and status.
- Do not let `extract_plan_json` slice `{...}` out of error text; reject error wrappers before fallback JSON boundary extraction.
- In discussion loops, do not retry runtime/auth/quota failures with a stricter JSON prompt. Mark the model `runtime_error`/fail-closed and preserve the raw wrapper excerpt.
- In planner loops, record quota success only after wrapper decode + `extract_plan_json` + normalization succeed; otherwise you double-count success then failure.
- Preserve the original `_truncate_text` helper if it is used elsewhere; introduce a separate runtime-error redaction/truncation helper instead of redefining it.

## Regression tests to add

- Success wrapper unwraps to inner JSON for planner and discussion.
- `returncode == 0` + `is_error=true` raises/returns runtime failure, not parse failure.
- `api_error_status=403` is runtime failure even when `is_error` is false.
- `is_error="false"` does not become true by Python truthiness.
- Error wrapper containing JSON-looking text is not parsed as a valid plan.
- Runtime errors in discussion are not retried with strict JSON prompt.
- Truncation/redaction helper changes do not override the module-wide `_truncate_text` behavior.

## Known-good verification from the session

- `python3 -m py_compile ~/.hermes/scripts/consult_models.py ~/.hermes/scripts/test_consult_models_integration.py`
- Targeted wrapper tests: `8 passed`
- Full integration suite for `test_consult_models_integration.py`: `100 passed, 13 subtests passed`
- Real Claude CLI minimal probe returned `type=result`, `is_error=False`, `api_error_status=None`, `result={"ok":true}`.
