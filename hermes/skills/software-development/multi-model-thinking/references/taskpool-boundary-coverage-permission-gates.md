# Taskpool boundary coverage + permission gate review

Use this when the user asks whether the local-brain/taskpool architecture covers all boundaries, whether Lark/work tasks differ from self-evolution tasks in ways that can block progress, or whether task completion authority is classified correctly (especially `--yolo`).

## Read-only evidence suite

Collect current state before answering or mutating anything:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py list --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py boundary-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py parallel-dispatch-dry-run --max-agents 3 --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py permission-audit --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py autonomy-readiness --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-dry-run --json
python3 ~/.hermes/scripts/task_pool_guardian.py run --json
python3 ~/.hermes/scripts/cron-health-quarantine.py
python3 ~/.hermes/scripts/cron-missed-run-guard.py --json
```

Package claim-linked evidence if asking models to certify architecture coverage. Claims should distinguish: deterministic gates, work-lane preemption, `--yolo` semantics, completion lifecycle/proof gating, observability/guardian health, and remaining non-coverage such as cron degradation/defaulted fields/high multimodel backlog.

## Interpretation rules

- `selfcheck=PASS`, `proof-check=PASS`, `boundary-check=PASS`, and Guardian `HEALTHY` prove the core safety skeleton, not all-boundary coverage.
- `parallel-dispatch-dry-run` proving a selected `work` task while `evolution` tasks are skipped with `lane_preempted_by_work` is the key evidence that Lark/work is not starved by self-evolution.
- `permission-audit=PASS` can coexist with a governance gap: tasks may be using lane defaults rather than explicit frontmatter. Treat `missing_fields` as a real boundary-risk inventory, not as a failure only if validation fails.
- `multimodel_pass_rate` low and `trigger_rate` high indicates self-evolution ratification throughput can block evolution closeout. It does not necessarily block current Lark/work if work-lane preemption and the selected work task do not require multimodel intervention.
- `cron-health-quarantine bad_count>0` with Guardian healthy means degraded automation reliability, not global taskpool failure. It still blocks a claim of “all boundaries covered.”
- `autonomy-readiness PASS` with activation blockers like `autorun_env_disabled` / `multimodel_autorun_env_disabled` is a safe fail-closed posture, not full runtime activation.

## Permission / completion semantics

Canonical authority order:

```text
read < dry-run < dispatch-hint < claim-and-handoff < budget-handoff < autonomous-execution < yolo-execution
```

`--yolo` maps to `yolo-execution` and is the highest execution approval tier. However, it must never mean “may mark the task done.” Completion remains lifecycle/proof gated:

- transition to `review` / `done` requires structured evidence;
- `done` should enter from `review` unless force-audited manual closure is explicitly used;
- autorun-originated `done` requires `proof:sha256:...` from the append-only proof chain;
- `yolo-execution` attempting direct `done` should fail closed (`yolo-execution cannot complete task; requires_lifecycle_gate review_to_done`).

Lane defaults:

- work/Lark: `required_authority=autonomous-execution`, `max_authority=yolo-execution`, `completion_gate=project-evidence-review-done`.
- self-evolution: `required_authority=budget-handoff`, `max_authority=autonomous-execution`, `completion_gate=ratification-or-selfcheck-review-done`.
- advisory: `required_authority=dispatch-hint`, `max_authority=budget-handoff`, `completion_gate=advisory-evidence-review-done`.

If `permission-audit` reports many missing fields (e.g. every task missing `required_authority`, `max_authority`, `write_surfaces`, `completion_gate`), do not say permission classification is absent. Say: taxonomy and runtime defaults exist, but task-level explicit governance is incomplete; the next hardening slice is `permission-migrate --dry-run` then scoped `permission-migrate --apply` if safe.

## Multi-model certification posture

For a boundary-coverage question, 4-model participation is not enough. If T3 returns all planners but `discussion_result.status=not_certified`, `approval_count=0/4`, agreement below 0.85, or unresolved severity>=3 issues, report `partial/conditional coverage`.

Common `not_certified` blockers for taskpool boundary coverage:

- defaulted permission fields need explicit backfill or stricter verifier;
- completion gates are declared but not lane-specifically enforced beyond generic evidence/review/proof gates;
- cron degradation has not been classified or repaired;
- multimodel backlog needs throttle/lane-aware drain;
- merged plan has concrete patch proposals but `patches=[]` / no implementation order.

If the outer `consult_models.py run` times out after fan-out/consensus, inspect the latest tick. When `plans/*.json` and `merged_plan.json` exist but `discussion_result.json` is missing, run:

```bash
python3 ~/.hermes/scripts/consult_models.py resume-discussion ~/.hermes/tick-YYYYMMDD-HHMMSS --max-rounds 2 --timeout 300
```

Then inspect `final/certification_manifest.json`; treat it as conservative. A grounded truth bundle with 1.0 evidence coverage can still be `not_certified` if ratification votes are `amend` and severity>=3 issues remain.

## Recommended answer shape

1. State the certification/support level first. For “all-boundary coverage” use `core safety covered; all-boundary certification not achieved` or `certified` only if manifest permits. For “do all tasks support the new taskpool,” distinguish `runtime-compatible`, `explicit-metadata-migrated`, and `multi-model-certified`.
2. List evidence counts: active/pending/claimed/stale, selfcheck/proof/boundary/permission/guardian, work-preemption, multimodel convergence, cron degradation.
3. Separate covered boundaries from remaining boundary risks.
4. Explain Lark/work vs self-evolution differences: work delivery uses project evidence and can use `--yolo` execution approval; evolution closeout is ratification/selfcheck gated and can be blocked by multimodel backlog.
5. Clarify `--yolo`: highest execution authority, not done authority.
6. Give the minimal hardening order: explicit permission frontmatter migration, lane-specific completion-gate verifier, cron degradation repair/classification, multimodel backlog throttle, fresh T3 rerun.

### Runtime support vs explicit migration vs certification

When every canonical task passes `lifecycle/selfcheck/proof-check/boundary-check/permission-audit`, answer that the taskpool runtime supports the tasks. Do not imply all task notes are fully migrated if `permission-audit.missing_fields` is non-empty: lane defaults may derive `required_authority`, `max_authority`, `write_surfaces`, and `completion_gate` at runtime while Markdown frontmatter still lacks explicit fields. Also do not imply all tasks are multi-model certified: `multimodel_passed` / `pass_rate` is a separate convergence metric. A precise closeout statement should be:

- “All tasks are runtime-compatible with the new taskpool” if invalid_count/failures are zero.
- “Not all tasks are explicit-migrated” if missing permission/frontmatter fields remain.
- “Not all tasks are multi-model passed” unless convergence shows every required task has current target-bound T3 certification.
