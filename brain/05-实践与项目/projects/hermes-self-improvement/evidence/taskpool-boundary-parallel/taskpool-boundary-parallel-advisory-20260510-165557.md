---
type: evidence_report
project: hermes-self-improvement
topic: local-brain-taskpool-boundary-parallel-agents
created: 2026-05-10T16:55:57.891384
status: advisory_not_certified
---

# Taskpool boundary + multi-agent parallel advisory

## User question

多模型思考，任务池是否可以增加任务边界，补充多agent并行处理。

## Evidence sources

- consult_models state: `/tmp/taskpool-boundary-parallel-mm-state.json`
- consult_models merged plan: `/Users/charles/.hermes/tick-20260510-084401/merged_plan.json`
- merged plan state_hash: `944b756f11c9b1078a7e64d2241f074c6ca2655967d0e0b0669c035ec5bc9b89`
- source script: `/Users/charles/.hermes/scripts/brain_task_orchestrator.py`
- current checks: `brain_task_orchestrator.py list --json`, `dispatch-dry-run --json`, `selfcheck --json`

## Certification status

Not full T3 certification. The consult run produced planner fan-out/merged plan only:

- tick: `/Users/charles/.hermes/tick-20260510-084401`
- models attempted: gpt-5.5, claude-opus-4-7, mimo-v2.5-pro
- successful useful planners: gpt-5.5, claude-opus-4-7
- MiMo adapter failed (`Param Incorrect`, xiaomi model unsupported in that route)
- no `discussion_result.json`
- merged consensus verdict: `weak_consensus`
- evidence bundle truth status: `grounded`, evidence coverage `1.0`

Therefore this is truth-grounded advisory, not certified autonomous-execution approval.

## Current factual baseline

- Task notes are canonical Markdown; dashboards are derived.
- Existing lifecycle: proposed / pending / claimed / running / retry / review / blocked / done / archived / expired.
- Claim-bound statuses: claimed / running / review.
- review/done transitions require structured evidence; autorun done requires proof hash.
- Lanes exist: work / advisory / evolution, sorted so work is ahead of evolution.
- Current preferred frontmatter has no first-class task boundary fields like `allowed_globs`, `forbidden_globs`, `loc_budget`, `conflict_group`, `parallel_group`, `workspace_isolation`, `merge_gate`.
- Current autorun is bounded claim-and-handoff, not direct Markdown execution.
- Current active pool includes work and evolution tasks; next dispatchable item is a P0 uvisa work blocker, so self-evolution must not starve work.

## Decision

Can add task boundaries and multi-agent parallel processing, but only in phases:

1. Schema + validation first.
2. Parallel dry-run planning second.
3. Parallel claim/handoff third.
4. Isolated worktree execution fourth.
5. Merge queue + proof-gated review/done last.

Do not jump directly to automatic multi-agent write execution.

## Recommended v1 fields

Use flat/dotted fields first because current parser is yamlish and does not fully support nested YAML objects:

- `task_boundary.allowed_globs`
- `task_boundary.forbidden_globs`
- `task_boundary.loc_budget`
- `conflict_group`
- `parallel_group`
- `workspace_isolation`: `none | readonly | copy | worktree`
- `merge_gate`: `manual | diff-boundary | tests | build-and-tests`

Legacy tasks without boundary remain valid for single-task serial dispatch. Any write-capable parallel dispatch must fail closed if boundary is absent or invalid.

## P0 implementation slice

- Extend frontmatter render/preferred fields with task boundary fields.
- Add boundary normalize/validate helpers.
- Add `boundary-check --json`.
- Add `parallel-dispatch-dry-run --max-agents N --json` that only emits a plan, does not claim, does not execute, does not create worktrees.
- Add selfcheck coverage for boundary parser/validator and parallel eligibility.
- Preserve P0/P1 work priority over evolution.

## P1 implementation slice

- Add `parallel-claim-and-handoff --max-agents N --json`, default dry-run.
- `--write` claims a non-conflicting batch atomically/fail-closed.
- Generate per-task handoff artifacts.
- Optional `--prepare-worktrees` creates isolated git worktrees only when base repo is clean or explicitly allowed.
- Add `boundary-diff-check TASK_ID --workspace PATH --json`.

## P2 implementation slice

- Add bounded external runner `brain_task_parallel_runner.py` consuming handoff JSON.
- Workers run only in isolated worktrees, with timeout/tool budget/log artifact.
- Workers cannot mark done; they can only produce commit/diff/evidence and move to review with structured evidence.
- Add merge queue commands: `merge-queue-dry-run`, `merge-queue-apply`.
- Coordinator serially merges, reruns required tests/build/proof, then transitions review -> done.

## Safety invariants

- Markdown body is data, never executable script.
- No direct tick -> done.
- No write-capable parallelism without worktree or equivalent isolation.
- Same conflict_group cannot be in the same parallel write batch.
- Same workspace defaults to same conflict_group unless explicit non-overlapping globs + worktree isolation.
- forbidden_globs dominate allowed_globs.
- changed files must be proven inside allowed_globs and outside forbidden_globs.
- loc_budget must be checked against diff.
- P0/P1 work lane cannot be starved by evolution lane.
- Secrets/OTP/cookies/tokens must never enter task notes, logs, evidence, docs, or memory.

## Validation commands

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json
python3 ~/.hermes/scripts/test_brain_task_orchestrator.py
python3 ~/.hermes/scripts/brain_task_orchestrator.py boundary-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py parallel-dispatch-dry-run --max-agents 2 --json
```
