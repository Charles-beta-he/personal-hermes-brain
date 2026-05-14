# Taskpool runtime debugging notes

Use when diagnosing why the Hermes/Lark-derived task pool has no `running` tasks, why tasks are marked `blocked`, or what multimodel statuses such as `advisory_passed` mean.

## Quick probe sequence

1. Inspect the generated runtime dashboard:
   - `/Users/charles/Documents/brain/07-仪表盘/待完成任务运行态.md`
   - Check `Counts`, `Sorted Active Task Pool`, and any multimodel round-state section.
2. Run the taskpool dynamic runner and dispatch tick as JSON, then inspect nested statuses rather than only the top-level exit code:
   - `python3 /Users/charles/.hermes/scripts/taskpool_dynamic_runner.py`
   - `/Applications/Xcode.app/Contents/Developer/usr/bin/python3 /Users/charles/.hermes/scripts/brain_task_dispatch_tick.py`
3. If there are no `claimed`/`running` tasks but `dispatchable: true`, probe autorun directly:
   - `python3 /Users/charles/.hermes/scripts/brain_task_autorun_step.py --json`
   - A result like `eligible: true`, `claimed: false`, `reasons: ["policy_missing"]`, `safety: "fail-closed; policy required before claim"` means the pool found work but will not claim it until `/Users/charles/.hermes/state/auto_run_policy.json` exists.
4. If the dispatch tick returns `ERROR`, expand the failing gates:
   - `proof_check: ERROR` / `evidence_spine: ERROR` commonly means proof/evidence invariants failed.
   - Run `/Applications/Xcode.app/Contents/Developer/usr/bin/python3 /Users/charles/.hermes/scripts/brain_task_orchestrator.py proof-check --json` to list missing proof/evidence failures.
5. For blocked tasks, compare the derived dashboard with the task note frontmatter and body under `/Users/charles/Documents/brain/05-实践与项目/tasks`.
   - The dashboard may classify a row as blocked because the body/history contains `Blocked`, even when current frontmatter is still `status: pending`.
   - Extract `blocked_reason`, `Blockers / Confusions`, and recent body lines containing `Blocked`, `阻塞`, `评论区`, `原型`, `待 PM`, `requires`, or backend/contract hints.

## Interpreting common statuses

- `running: 0` with `dispatchable: true`: not an empty pool; usually fail-closed autorun or proof gates are preventing claim/advance.
- `policy_missing`: autorun policy file is absent, so the system refuses to claim tasks even if one is eligible.
- `proof_check: FAIL`: done/review tasks may be missing structured evidence or Final Handoff proof; fix evidence rather than forcing scheduler state.
- `advisory_passed`: multimodel advisory-only round passed (`PASS_ADVISORY_ONLY`) but has no certification authority. It must not close a task, set final ratification, or be treated as equivalent to `passed`.
- `passed`: true multimodel certification (`PASS` + `LOOP_DONE`) and can be used as a stronger closure signal.

## Reporting format

When answering the user, separate:

1. observed pool counts (`pending`, `claimed`, `running`, `review`, `blocked`, etc.);
2. scheduler/autorun reason for no running work;
3. proof/evidence gate failures;
4. blocked task categories and representative examples;
5. precise explanation of `advisory_passed` vs `passed`.

Avoid saying simply “no tasks are running because there are no tasks” unless the counts prove the pool is empty.