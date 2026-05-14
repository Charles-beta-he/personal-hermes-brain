# Taskpool flow tolerance: Lark quarantine + historical proof debt

Use this reference when debugging Hermes/local-brain taskpool stalls where dispatchable tasks exist but no task reaches claimed/running/review.

Observed durable pattern:
- Taskpool may have a valid `next_task_id` and `dispatchable: true` while autorun still refuses to claim because `~/.hermes/state/auto_run_policy.json` is missing or too narrow.
- `brain_task_dispatch_tick.py` can be blocked by historical proof debt from already-`done` tasks: `proof_check` reports `done task missing evidence`, and `evidence_spine` escalates to ERROR even though active tasks are dispatchable.
- Lark-imported tasks can dominate active/review/done counts and obscure the local taskpool signal. When the user asks to remove Lark tasks temporarily, quarantine/move them with a manifest instead of deleting.

Safe workflow:
1. Snapshot current state with:
   - `python3 ~/.hermes/scripts/brain_task_dispatch_tick.py` or `taskpool_dynamic_runner.py`
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json`
   - dashboard `/Users/charles/Documents/brain/07-仪表盘/待完成任务运行态.md`
2. Identify Lark tasks by explicit markers in filename/frontmatter/body: `lark`, `lark-reopened`, `feishu`, `飞书`, `larksuite`, Lark URLs/IDs/source fields.
3. Quarantine, do not delete: move matching task markdown files under `tasks/_temporarily_removed_lark_tasks/<timestamp>/` and write `manifest.json` with from/to/status/title/reason/count.
4. Refresh dashboard and dispatch dry-run. Confirm `dispatchable: true` and inspect `next.id`.
5. If tick is blocked only by historical done-task proof debt, tolerate it in the tick layer while preserving visibility:
   - tolerate `proof_check` failures only when failures are limited to historical done-task proof debt such as `done task missing evidence:` or `autorun done task missing proof evidence:`;
   - tolerate `evidence_spine` only when its summary shows proof debt but `selfcheck == PASS` and `boundary_check == PASS`;
   - keep fail-closed for active-task proof errors, invalid proof hashes, selfcheck/boundary failures, unknown step errors, and any non-whitelisted failure.
6. Create or narrow `~/.hermes/state/auto_run_policy.json` only for the current selected task. Keep `close_mode: review_only`, constrained workspace roots, explicit `task_ids`, explicit lane, and safe command IDs such as `py_compile_taskpool`.
7. Trigger with `python3 ~/.hermes/scripts/brain_task_dispatch_tick.py --autorun-step`; then re-run dispatch dry-run and inspect the task/dashboard.

Pitfalls:
- Do not make historical proof debt disappear; record it as tolerated (`flow_tolerated_errors`) so governance debt stays visible.
- Do not use broad autorun policies. Missing policy is expected fail-closed behavior; the fix is a narrow policy, not disabling safety.
- Do not permanently delete Lark tasks unless explicitly asked; quarantine with manifest supports restoration.
