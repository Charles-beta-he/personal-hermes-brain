# Local-brain taskpool permission taxonomy

Use this when checking or repairing local-brain taskpool progress, especially when the user asks whether Lark/product tasks differ from Hermes self-evolution tasks, or asks what authority is required to complete taskpool work.

## Core invariant

`--yolo` / `yolo-execution` is the highest execution-approval tier, but it is not a lifecycle completion proof.

- It may bypass command approval prompts.
- It must not bypass task lifecycle gates.
- It must not directly mark taskpool items `done` without proof/evidence/review gates.

Short form: `--yolo != done proof`.

## Recommended authority tiers

| Tier | Meaning | Can complete task? |
|---|---|---|
| `dispatch-hint` | read/control-plane hinting only | no |
| `claim-and-handoff` | claim or hand off taskpool item | no |
| `budget-handoff` | dispatch with quota/diversity/router readiness | no |
| `autonomous-execution` | execute bounded work with explicit enablement | no, unless lifecycle gate is separately satisfied |
| `yolo-execution` | highest command approval bypass | no, unless lifecycle gate is separately satisfied |

Completion is a lifecycle transition, not just an execution permission.

## Lane distinction: Lark/product vs self-evolution

When comparing Lark/product tasks with Hermes self-evolution tasks, classify the difference explicitly instead of treating all taskpool work as one queue:

- Lark/product tasks usually have external acceptance criteria, PRD/business semantics, user-facing regressions, and project red lines. They may require product docs, backend/frontend contract inspection, browser evidence, and deploy/package status.
- Self-evolution tasks usually have control-plane invariants, script/test/selfcheck/proof-chain gates, multi-model certification, and rollback/safety concerns.
- Both lanes can use `--yolo` for execution approval, but neither lane can use it as proof of task completion.
- Work-lane priority can preempt evolution-lane tasks; report this as scheduling semantics, not as a stuck state, unless claims are stale or gates fail.

## Completion gate checklist

Before marking a task done or claiming it is complete, verify:

1. Owner/claim/lease state is valid and not stale.
2. Required write surfaces are recognized; unknown allowlisted surfaces fail closed.
3. Evidence/proof hash exists when autorun or lifecycle policy requires it.
4. Boundary/selfcheck/proof/evidence-spine gates pass.
5. If multi-model certification is required, current-code certification exists; old ticks are provenance only after amendments.
6. `yolo-execution` is treated as approval bypass only; done/review transitions still require lifecycle proof.

## Permission field migration workflow

When a status check shows `permission-audit=PASS` but many `missing_fields` because historical Markdown tasks rely on lane defaults, do not call that a hard failure. If the user asks to "补齐" / make all tasks explicitly support the new taskpool contract, run the migration with proof:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py permission-migrate --dry-run --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py permission-migrate --apply --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py permission-audit --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py lifecycle --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py boundary-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py list --json
```

Expected successful result:
- `permission-audit.status=PASS`
- `missing_fields=[]` / missing field count is 0
- lifecycle `invalid_count=0`
- active list rows have no missing `required_authority`, `max_authority`, `permission_tier`, `write_surfaces`, `completion_gate`, or `lane_semantics`
- derived views refresh in the apply result (`dashboard`, `sorted_pool`, `control_center`)

After Markdown mutations in the local brain, refresh retrieval surfaces. `brainctl.py` takes `--json` before the subcommand, not after it:

```bash
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json search 'permission migrate taskpool yolo completion_gate'
```

If `/Users/charles/Documents/brain` is not a git repo, do not invent a local commit requirement. Treat the generated evidence artifacts plus `brainctl sync/reindex` as the closeout evidence. If it is a git repo in a future environment, make a scoped commit of only the task note/dashboard changes.

## Reporting pattern

When asked to inspect taskpool progress, report separately:

- queue counts and claimed/pending/running/review/blocked/stale state;
- next dispatch candidate and lane preemption reason;
- gate health (`selfcheck`, `proof-check`, boundary/evidence readiness);
- permission taxonomy status, including whether `yolo_done_bypass_possible=false`;
- whether missing permission fields are hard failures or migratable defaults.

## “Do all tasks support the new taskpool?” distinction

Do not collapse this question into a single yes/no. Split the answer into three independent levels:

1. Runtime/lifecycle compatibility: `lifecycle`, `selfcheck`, `proof-check`, `boundary-check`, and `permission-audit` PASS with `invalid_count=0` means existing canonical tasks can be parsed and governed by the new taskpool state machine.
2. Explicit frontmatter migration: `permission-audit` may PASS while reporting `missing_fields`; this means lane defaults are filling `required_authority`, `max_authority`, `write_surfaces`, and `completion_gate`. Report this as “runtime-compatible but not fully explicit-migrated,” not as unsupported.
3. Multi-model closeout certification: `multimodel-intervention-dry-run` convergence is separate. A task can support the new taskpool and still not have T3/4-model certification. Report `multimodel_passed`, `multimodel_triggered`, `pass_rate`, and pending IDs separately.

Useful summary query after collecting the read-only suite: count active tasks, active missing-field tasks, missing entries by field/lane, boundary warning count, and multimodel convergence. If active rows already expose derived `required_authority`, `max_authority`, `write_surfaces`, and `completion_gate`, say runtime defaults are working; recommend `permission-migrate --dry-run` then scoped apply only when the user asks to harden explicit metadata.
