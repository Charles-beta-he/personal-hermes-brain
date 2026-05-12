# Operational Pitfalls for multimodel-intervention-step

## Shell=True for && chains

`build_state_command` and `run_discussion_command` contain shell `&&` chains (e.g., `mkdir -p /path && python3 consult_models.py state ...`). Using `shlex.split()` + `subprocess.run(args)` fails because `&&` is treated as a literal argument, not shell chaining. Use `subprocess.run(cmd, shell=True, ...)` instead.

## state_path stale directory cleanup

If a previous run crashed or was interrupted, `state_path` (e.g., `~/.hermes/state/taskpool-multimodel/<task-id>-state.json`) may exist as a **directory** instead of a file (created by `mkdir -p` misinterpreting the path). `consult_models.py state --out <dir>` then fails with `IsADirectoryError: [Errno 21] Is a directory`. Before running build_state, check and clean:

```python
if state_path:
    sp = Path(os.path.expanduser(state_path))
    if sp.exists() and sp.is_dir():
        import shutil
        shutil.rmtree(sp, ignore_errors=True)
```

## Discussion timeout: 1200s for 4 models

`consult_models.py run --discussion --tier T3 --quorum 4` calls 4 models sequentially. With round-trip latency + JSON parsing + retry, 600s is insufficient (3/4 models may complete before timeout). Use `timeout=1200` (20 minutes) for the subprocess call. For T1/T2 with fewer models, 600s is usually enough.

## Multimodel allowlist

`multimodel_intervention_allowlist.json` in `AUTORUN_STATE_DIR` (default `~/.hermes/state/`). Same format as `auto_run_allowlist.json`: list of strings (task_id, project, "project:xxx", "task:xxx", title) or dicts ({task_id, project, title}). File doesn't exist = all tasks eligible (no filtering). File exists + empty = no tasks eligible (fail-closed).

## Cron job setup

```bash
hermes cron create --name multimodel-intervention-step \
  --schedule "every 360m" \
  --prompt "Run multimodel-intervention-step --json. Report convergence stats."
```

The cron job runs `multimodel-intervention-step` which is gated by `HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1`. Set this env var in the cron prompt or in the environment.

## Tick integration with SKIP status

When integrating `multimodel-intervention-step` into `brain_task_dispatch_tick.py`, the error-checking loop must allow `SKIP` status (returned when env var is not set). Without this, the tick reports the step as ERROR even though it's intentionally inactive:

```python
allowed_statuses = {"OK", "PASS", "SKIP"}  # SKIP for multimodel_step when env var not set
for key in [..., "multimodel_step", ...]:
    item = event.get(key, {})
    if item and item.get("status") not in allowed_statuses:
        errors.append(...)
```
