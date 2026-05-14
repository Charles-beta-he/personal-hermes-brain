When taskpool appears to have "no tasks in progress", diagnose in this order:

1. Verify active pool instead of assuming emptiness.
   - Run `python3 /Users/charles/Code/personal-hermes-brain/hermes/scripts/brain_task_orchestrator.py list`
   - Run `python3 /Users/charles/Code/personal-hermes-brain/hermes/scripts/brain_task_orchestrator.py dashboard`
   - Count `pending`, `blocked`, `claimed`, and `running` separately. A pool can have active tasks with `running: 0`.

2. Check whether dispatch is failing rather than idle.
   - Inspect `~/.hermes/logs/taskpool_dynamic_runner.jsonl`
   - Key signals: `dispatchable: true`, `next_task_id` present, but `status: ERROR`, `error_count > 0`, `autorun.requested: true`, `autorun.present: false`.
   - This means the system found work but failed to advance it.

3. Reproduce the control-plane tick directly.
   - Run `/Users/charles/.hermes/hermes-agent/venv/bin/python /Users/charles/.hermes/scripts/brain_task_dispatch_tick.py --summary --autorun-step --no-state`
   - Exit code `2` means the tick completed in non-OK state. Read the JSON body, not just the shell code.

4. Check proof/evidence gates when tick is ERROR.
   - Inspect `evidence_spine.status` and `summary.proof_check` from the tick output.
   - If `proof_check = FAIL`, run `python3 /Users/charles/Code/personal-hermes-brain/hermes/scripts/brain_task_orchestrator.py proof-check`
   - A common blocker is `done task missing evidence`, which can make `evidence_spine.status = ERROR` and keep autorun from advancing tasks.

5. Verify eligibility before concluding the pool is stuck.
   - Run `python3 /Users/charles/Code/personal-hermes-brain/hermes/scripts/brain_task_orchestrator.py eligibility-check`
   - If `eligible: True`, there is runnable work even if nothing is currently `running`.

6. Manually test the autorun handoff path.
   - Run `python3 /Users/charles/Code/personal-hermes-brain/hermes/scripts/brain_task_orchestrator.py autorun-runner`
   - If this returns `claimed: True` / `handoff_created`, re-check the task file; `claimed` is sufficient evidence that progress resumed even if dashboard still shows `running: 0`.

7. Treat boundary warnings as secondary unless they are the only failing signal.
   - Example: `parallel_boundary_conflict` warnings can coexist with the real blocker being proof/evidence failure.

Observed durable pattern:
- "No in-progress tasks" often really means "active tasks are stuck in pending/blocked because dispatch tick is failing governance gates" rather than an empty taskpool or disabled autorun.
