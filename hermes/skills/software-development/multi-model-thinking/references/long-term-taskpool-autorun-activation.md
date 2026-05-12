# Long-term local-brain taskpool autorun activation

Use when the user asks to “启动长期自运行架构”, “长期自运行”, or similar.

## Activation pattern

1. Verify prerequisites before enabling anything:
   - `brain_task_orchestrator.py selfcheck --json`
   - `proof-check --json`
   - `boundary-check --json`
   - `evidence-spine --json` must report `gate_status=PASS`
   - `autonomy-readiness --json` must report no architecture blockers
   - `cron-health-quarantine.py` bad_count=0 and `cron-missed-run-guard.py` missed_count=0
   - gateway running and cron status says jobs will fire
2. Ensure fail-closed allowlists exist:
   - `~/.hermes/state/auto_run_allowlist.json`
   - `~/.hermes/state/multimodel_intervention_allowlist.json`
   - `~/.hermes/config/autonomy-write-allowlist.json` includes `taskpool` and `kanban-worker`
3. Prefer no-argument cron wrapper scripts. Hermes cron `script` fields do not reliably carry argv or source interactive shell rc files. For multimodel autorun, create a wrapper that sets `HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1` and invokes:
   `brain_task_orchestrator.py multimodel-intervention-parallel-step --max-workers 3 --json`
4. Add/verify two heartbeat layers:
   - safe summary tick: `brain_task_dispatch_summary_tick.py` with no mutation
   - bounded autorun summary tick: `brain_task_dispatch_autorun_summary_tick.py`, which sets `HERMES_LOCAL_BRAIN_AUTORUN=1` and calls `brain_task_dispatch_tick.py --summary --autorun-step`
5. Trigger representative jobs once with `hermes cron run <id>`, then wait and re-read `~/.hermes/cron/jobs.json` or `hermes cron list`. `cron run` only schedules immediate execution; it is not proof until `last_run_at` and `last_status` change.
6. Re-run readiness with env enabled:
   `HERMES_LOCAL_BRAIN_AUTORUN=1 HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1 python3 ~/.hermes/scripts/brain_task_orchestrator.py autonomy-readiness --json`
   Target: `full_runtime_activation_ready=true`.

## Important safety interpretation

- `auto_run_policy.json` missing with autorun heartbeat returning `policy_missing` is a safe fail-closed result, not an activation failure. It proves the bridge is live but will not claim/execute without an explicit static-command policy.
- The long-running architecture is considered started when guardian, auto-completer, multimodel intervention, evidence heartbeat, proof gates, and cron health are all active and observable. Do not weaken proof/done gates to force visible activity.
- Do not execute Markdown task bodies. Bounded autorun may only use static command IDs from `brain_task_autorun_step.py` and stops at `review`, never `done`.
- Keep `deliver=local` for CLI/background status jobs unless a real origin delivery target is bound. `deliver=origin` can produce `no delivery target resolved` even when the job itself succeeded.
- Treat `~/.hermes/cron/jobs.json` as scheduler runtime state: editing via cron tools is real activation, but do not include large last_run_at/completed churn in scoped code commits unless the task is explicitly to version cron state.

## Closeout evidence to report

- job ids, schedule, next_run_at, last_status for guardian, safe heartbeat, autorun heartbeat, auto-completer, multimodel intervention, pipeline tick, envelope executor, and agent-team cycle
- latest cron output files under `~/.hermes/cron/output/<job_id>/...md`
- `cron-health-quarantine.py` and `cron-missed-run-guard.py` results
- readiness summary: `unattended_runtime_enabled`, `multimodel_runtime_enabled`, `full_runtime_activation_ready`, blockers
- local commit hash for wrapper/script changes; explicitly state no push

## Rollback / pause

- Kill switch env: `export HERMES_LOCAL_BRAIN_AUTORUN_KILL=1`
- Kill switch file: `~/.hermes/state/auto_run.kill`
- Pause jobs: `hermes cron pause <job_id>` for auto-completer, multimodel intervention, autorun heartbeat, guardian
- Remove only the added heartbeat if needed: `hermes cron remove <autorun-heartbeat-job-id>`
- Revert wrapper code with a local `git revert <commit>` when wrappers were committed.
