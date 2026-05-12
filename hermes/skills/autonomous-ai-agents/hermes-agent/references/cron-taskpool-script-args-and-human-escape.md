# Cron task-pool script args + human_escape review pattern

Use when reviewing Hermes cron jobs that drive local task pools/envelope buses, especially when cron output says `Script not found: ... <script.py arg>` or a pipeline stays in `human_escape`/`escaped` state.

## Signals

- Cron job config has `script` values with spaces, e.g. `pipeline_tick.py tick`, `agent_team_controller.py cycle`, `envelope_executor.py run 1`.
- Cron output contains `Script not found: /.../.hermes/scripts/<script.py arg>` even though the base script exists.
- `last_status=ok` despite a `## Script Error` section in the cron output.
- Local task-pool code checks `human_escape` by counting all `FAILED`/`BLOCKED` rows, causing historical failures to permanently trip the breaker.

## Diagnosis steps (read-only reviewer mode)

1. Inspect the scheduler script runner, usually `cron/scheduler.py::_run_job_script()`:
   - Does it treat `script` as a path only?
   - Does it build `argv` with `[python, path]` or `[bash, path]`?
   - Does it use `shell=False` and path containment under `HERMES_HOME/scripts/`?
2. Inspect cron job storage, usually `~/.hermes/cron/jobs.json`, for `script` fields containing spaces.
3. Inspect recent cron outputs under `~/.hermes/cron/output/<job_id>/` for `Script not found: ... <args>`.
4. Inspect task-pool state, e.g. SQLite counts by status, and recent `FAILED`/`BLOCKED` rows.
5. Inspect `human_escape_check()` implementation:
   - If it counts all historical terminal rows, call out permanent熔断 risk.
   - Prefer `since_ack`/watermark semantics over mutating old task statuses.

## Safe architecture recommendation

- Split cron command shape into structured fields:
  - `script`: path relative to `~/.hermes/scripts/` only, no args.
  - `script_args`: list of strings passed as argv.
- Keep path validation only on `script`; never use shell parsing for execution.
- Reject or migrate legacy `script` strings containing whitespace. If compatibility is needed, use `shlex.split()` only to derive `[script, *args]`, still execute with `shell=False`, and emit a deprecation warning.
- Script failure should fail the cron job by default (`last_status=error`) instead of being hidden by an LLM response. Add an explicit opt-in such as `allow_script_failure=true` only for jobs that intentionally summarize failures.
- For `human_escape`, add an ack/watermark file or event table so only unacknowledged failures since the last human review count toward the breaker. Historical failures remain auditable and terminal; do not auto-mark them DONE.

## Validation checklist

- A job with `script="pipeline_tick.py", script_args=["tick"]` runs and its output reflects real script stdout.
- `script="pipeline_tick.py tick"` is rejected or migrated with a warning.
- `Script not found: ... <script.py arg>` disappears from new cron outputs.
- Absolute paths, `~`, traversal, symlink escapes, and shell metacharacter payloads are blocked.
- Nonzero script exit produces cron error status unless explicitly allowed.
- Historical acknowledged failures do not trip `human_escape`; new post-ack failures still do.
