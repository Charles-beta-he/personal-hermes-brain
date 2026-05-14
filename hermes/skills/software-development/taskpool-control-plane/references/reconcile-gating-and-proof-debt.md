# Reconcile gating and proof-debt triage

Use this when dispatch tick shows no active task even though pending tasks exist.

Key lessons from the session:
- Separate historical governance debt from current safety gates.
- Historical done-task proof/evidence debt can be downgraded to warning telemetry when it only reflects old structured-evidence gaps, including `done task missing evidence:` and historical `unstructured evidence in ...` multimodel markers.
- Keep fail-closed behavior for current safety gates such as write-surface allowlist, reconcile-required canonical-note fixes, permission gates, and similar live mutation guards.
- `brain_task_dispatch_tick.py --summary --autorun-step --no-state` is the fastest runtime probe for: tick status, next task id, autorun eligibility, claimed/advanced state, and whether proof/evidence issues are fatal or only WARN.
- If `next`/`eligibility-check` report `reconcile_required`, inspect reconcile actions instead of assuming all actions are blocking.
- Treat `auto_subtask_progress_synced` as non-blocking when `ready=false` and `missing_children=[]`; this is parent progress telemetry for open child tasks, not a canonical-note repair that should stop child dispatch.
- Check `next --json` and `next --no-reconcile --json` together. If `--no-reconcile` selects a task but plain `next` returns `null`, the reconcile gate is over-blocking.
- Validate allowlist at the correct surface identity. Current taskpool autorun writes on surface `taskpool`, so tests and local fixtures must allowlist `taskpool`, not stale identities like `kanban-worker`.

Suggested verification sequence:
1. `python3 ~/.hermes/scripts/brain_task_dispatch_tick.py --summary --autorun-step --no-state`
2. `python3 ~/.hermes/scripts/brain_task_orchestrator.py next --json`
3. `python3 ~/.hermes/scripts/brain_task_orchestrator.py next --no-reconcile --json`
4. `python3 ~/.hermes/scripts/brain_task_orchestrator.py eligibility-check --json`
5. `python3 ~/.hermes/scripts/brain_task_orchestrator.py reconcile --json`

Patch targets proven useful:
- Runtime first: `~/.hermes/scripts/brain_task_dispatch_tick.py`, `~/.hermes/scripts/brain_task_orchestrator.py`
- Then sync back to repo copies and add regression coverage.
