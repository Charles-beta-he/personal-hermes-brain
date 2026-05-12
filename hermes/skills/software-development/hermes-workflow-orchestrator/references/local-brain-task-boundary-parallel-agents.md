# Local Brain Task Boundaries + Parallel Agents

Use this when enhancing the local-brain Markdown task pool with task-boundary metadata or multi-agent parallel execution.

## Status model

This pattern is an autonomy/write-surface upgrade. Treat multi-model or subagent review as advisory unless a `discussion_result.json` ratification artifact exists and passes the usual gates. A planner fan-out/merged plan without discussion is useful, but not certification for write-capable autonomy.

## Core decision

Task boundaries and multi-agent parallelism are desirable, but must land in phases:

1. Boundary schema + deterministic validation.
2. Read-only `parallel-dispatch-dry-run` planning.
3. `parallel-claim-and-handoff` that claims/leases and emits bounded handoffs, but still does not execute task bodies.
4. Worktree-isolated worker execution.
5. Serial merge queue + proof-gated `review -> done` closure.

Never jump directly from a Markdown task note to automatic multi-agent write execution.

## Boundary v1 fields

Prefer flat/dotted fields first because `brain_task_orchestrator.py` currently uses a simple yamlish parser, not a full nested YAML parser:

- `task_boundary.allowed_globs`
- `task_boundary.forbidden_globs`
- `task_boundary.loc_budget`
- `conflict_group`
- `parallel_group`
- `workspace_isolation`: `none | readonly | copy | worktree`
- `merge_gate`: `manual | diff-boundary | tests | build-and-tests`

Legacy serial tasks with no boundary should remain compatible. Any write-capable parallel dispatch without valid boundary metadata must fail closed.

## Safety invariants

- Markdown body is data, not script.
- No cron tick, safe tick, or worker may directly mark a task `done`.
- Same `conflict_group` cannot be in the same parallel write batch.
- Same workspace defaults to mutual exclusion unless explicit non-overlapping globs plus `workspace_isolation=worktree`.
- `forbidden_globs` dominate `allowed_globs`.
- Changed files must be proven inside `allowed_globs` and outside `forbidden_globs` before merge/done.
- `loc_budget` must be checked against the diff.
- P0/P1 `work/product delivery` tasks must not be starved by `evolution/self-improvement` tasks.
- Secrets/OTP/cookies/tokens never enter task notes, logs, evidence, docs, or memory.

## P0 slice: schema + read-only planning

Add:

- Preferred frontmatter fields for the boundary metadata.
- Boundary normalize/validate helpers.
- `boundary-check --json`.
- `parallel-dispatch-dry-run --max-agents N --json` that only emits a plan; no claim, no execution, no worktree creation.
- Selfcheck/test coverage for invalid boundary, conflict groups, forbidden globs, loc budget, and parallel eligibility.

Validation:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json
python3 ~/.hermes/scripts/test_brain_task_orchestrator.py
python3 ~/.hermes/scripts/brain_task_orchestrator.py boundary-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py parallel-dispatch-dry-run --max-agents 2 --json
```

## P1 slice: claim/handoff, still no direct execution

Add:

- `parallel-claim-and-handoff --max-agents N --json`, default dry-run.
- `--write` claims a non-conflicting batch atomically/fail-closed.
- Per-task handoff artifacts with task path, isolated workspace path, allowed/forbidden globs, loc budget, merge gate, and forbidden operations.
- Optional `--prepare-worktrees`, only when the base repo is clean or explicitly allowed.
- `boundary-diff-check TASK_ID --workspace PATH --json`.

If any claim in a batch fails, prefer fail-closed rollback/release over partial claim.

## P2 slice: bounded runner + merge queue

Add an external runner rather than stuffing all execution into the orchestrator:

- `brain_task_parallel_runner.py` consumes handoff artifacts.
- Each worker runs in an isolated worktree with timeout/tool budget/log artifact.
- Workers can produce commit/diff/evidence and move to `review`, but cannot mark `done`.
- Merge queue commands (`merge-queue-dry-run`, `merge-queue-apply`) serialize merges.
- Coordinator reruns boundary diff checks plus project tests/build/proof before `review -> done`.

## Pitfalls

- Do not use nested `task_boundary:` YAML before replacing the parser; the current parser treats simple lists and flat keys more predictably.
- Do not enable parallel execution while stale `running`/claim leases exist; reconcile or explicitly review them first.
- Do not let self-evolution tasks preempt a P0/P1 work blocker just because they are parallelizable.
- Do not treat planner weak consensus as autonomous-execution certification.
