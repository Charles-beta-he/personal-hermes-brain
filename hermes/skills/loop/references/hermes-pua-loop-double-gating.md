# Hermes PUA-Loop Double-Gating Pattern

> Captured from 2026-05-12 session where I incorrectly stated "PUA-loop自动执行路径被明确禁用".
> User corrected: "什么地方明确禁用了 PUA-loop 自动执行路径？需要解禁"
> After investigation: it's NOT disabled, it's multi-layer double-gated.

## The Misdiagnosis Trap

Wrong conclusion: "PUA-loop is disabled"
Correct reality: PUA-loop has 4 independent gate layers, each must pass

The `SKIP: autorun_multimodel_disabled` return from dispatch tick is BY DESIGN, not a disable switch.

## The 4 Gate Layers

### Gate 1: dispatch tick double-gate (brain_task_dispatch_tick.py)
- Requires: `--multimodel-step` CLI flag AND `HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1`
- Missing flag → SKIP (not error)
- Missing env var → SKIP (not error)
- Both present → runs multimodel-intervention-step

### Gate 2: orchestrator allowlist (brain_task_orchestrator.py)
- File: `~/.hermes/state/multimodel_intervention_allowlist.json`
- If file exists and task doesn't match → blocked
- If file empty/missing → all tasks pass

### Gate 3: auto-run allowlist
- File: `~/.hermes/state/auto_run_allowlist.json`
- Controls which projects can auto-run at all
- Missing project → auto-claim FAIL_CLOSED

### Gate 4: autonomy write guard
- File: `~/.hermes/config/autonomy-write-allowlist.json`
- Must contain `["taskpool", "kanban-worker"]`
- Missing → auto-claim FAIL_CLOSED

## How to Diagnose "Is It Working?"

```bash
# Check all 4 gates at once:
env | grep HERMES_LOCAL_BRAIN_AUTORUN
cat ~/.hermes/state/auto_run_allowlist.json
cat ~/.hermes/state/multimodel_intervention_allowlist.json
cat ~/.hermes/config/autonomy-write-allowlist.json

# Check dynamic step logs:
tail -5 ~/.hermes/logs/multimodel_intervention_dynamic_step.jsonl

# Check worker logs:
tail -5 ~/.hermes/logs/multimodel_intervention_dynamic_worker.log
```

## Session-Level Authorization Override

When user explicitly says "继续/推进/loop/pua-loop 落地" in current session:
- Advisory auto-push: ALLOWED
- Certification execution: ALLOWED
- Closeout auto-pass: CONDITIONAL (gate PASS only)
- Done write: CONDITIONAL (gate PASS + evidence bound)

This is NOT disabling gates. It's authorizing iteration progress while gates control completion.

## Key Code Locations

| Gate | File | Key line/area |
|------|------|---------------|
| Double-gate | brain_task_dispatch_tick.py | `if args.multimodel_step and os.environ.get(...) == "1"` |
| SKIP reason | brain_task_dispatch_tick.py | `"reason": "autorun_multimodel_disabled"` |
| Allowlist | brain_task_orchestrator.py | `MULTIMODEL_ALLOWLIST = AUTORUN_STATE_DIR / "multimodel_intervention_allowlist.json"` |
| Env flag | brain_task_orchestrator.py | `MULTIMODEL_AUTORUN_ENV_FLAG = "HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL"` |
| Write guard | brain_task_orchestrator.py | `AUTONOMY_WRITE_ALLOWLIST = ... / "autonomy-write-allowlist.json"` |
