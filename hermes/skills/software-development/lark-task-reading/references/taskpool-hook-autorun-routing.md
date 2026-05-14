# Taskpool hook/autorun routing diagnosis

Use this when a local-brain task is `dispatchable: true` but the user expects hook-driven step-by-step execution and it is not moving.

## Expected pipeline

`local-brain-taskpool-auto-completer` cron job → `taskpool_dynamic_runner.py` → `brain_task_dispatch_tick.py --summary --autorun-step --no-state` → `dispatch-dry-run` → `eligibility-check` → `auto_run_policy` validation → claim → bounded command → proof/handoff → review/done gate.

## Fast checks

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py eligibility-check --task '<task-id>' --json
python3 ~/.hermes/scripts/brain_task_dispatch_tick.py --summary --autorun-step --no-state --print-always
python3 - <<'PY'
from pathlib import Path
for p in ['~/.hermes/state/auto_run_allowlist.json','~/.hermes/state/auto_run_policy.json']:
    path = Path(p).expanduser()
    print('\n---', path, path.exists())
    if path.exists(): print(path.read_text()[:4000])
PY
```

## Common fail-closed reasons

- `allowlist_miss`: the task project is not present in `~/.hermes/state/auto_run_allowlist.json` (usually as `project:<project-slug>`).
- `policy_task_miss`: `~/.hermes/state/auto_run_policy.json` still points at an old task id.
- `policy_missing`: policy file absent; autorun refuses to claim.
- Historical proof debt can make evidence-spine warn/fail; distinguish this from current active-task failures. If dispatch tick has the historical-proof-debt tolerance, it should record `flow_tolerated_errors` rather than blocking autorun.

## User expectation

For 贺程, do not stop at “task is pending/dispatchable”. If the task should flow automatically, actively inspect cron timing, allowlist, policy, eligibility, and tick output. If safe, update the narrow policy/allowlist and trigger one bounded tick to verify claim/proof/handoff/review progression.

## Safe narrow policy pattern

Keep policy task-specific and review-only unless explicitly asked otherwise:

```json
{
  "profiles": {
    "default": {
      "task_ids": ["<current-next-task-id>"],
      "lanes": ["evolution"],
      "command_ids": ["py_compile_taskpool"],
      "close_mode": "review_only",
      "workspace": "/Users/charles/.hermes",
      "workspace_roots": ["/Users/charles/.hermes"],
      "max_seconds": 300
    }
  }
}
```

After triggering, verify:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py list --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json
```
