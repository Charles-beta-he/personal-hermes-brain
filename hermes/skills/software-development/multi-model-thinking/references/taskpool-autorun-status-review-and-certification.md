# Taskpool autorun status review + certification pattern

Use this when asked to check local-brain taskpool progress and analyze how it can run autonomously for a long time.

## Read-only status suite first

Before proposing changes or enabling autorun, collect deterministic status evidence:

```bash
python3 ~/.hermes/scripts/taskpool_watch_report.py --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py list --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py parallel-dispatch-dry-run --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-dry-run --json
python3 ~/.hermes/scripts/task_pool_guardian.py run --json
python3 ~/.hermes/scripts/v_state.py --json
python3 ~/.hermes/scripts/cron-missed-run-guard.py --json
python3 ~/.hermes/scripts/cron-health-quarantine.py
```

Also inspect relevant cron jobs via Hermes cron list/tool output: `local-brain-taskpool-auto-completer`, `multimodel-intervention-step`, `task-pool-guardian-10m`, `pipeline-tick-hourly`, `agent-team-cycle-hourly`, `envelope-executor-cycle`.

## Status interpretation

- `selfcheck=PASS`, `proof-check=PASS`, `guardian V≈healthy`, `stale_claim=0`, `timeouts=0` means the base state machine is healthy.
- `autorun_enabled=false` is not a bug by itself; it is a fail-closed safety posture.
- `multimodel trigger_rate high` with `pass_rate=0.0` means the ratification loop triggers but has not produced passable claim/evidence artifacts. Do not fix this by blindly lowering thresholds.
- `local-brain-taskpool-auto-completer last_status=error` may still have completed a bounded task slice. Read the session/error body before classifying it as no progress.
- A baseline build blocker outside the scoped task should be recorded as `review_with_baseline_blocker` / `ok_with_task_blocker`, not as an unstructured cron failure that stops future ticks.
- `parallel-dispatch-dry-run` is the clearest proof that work lane preempts evolution: work tasks should be selected and evolution tasks skipped with `lane_preempted_by_work` while work is available.

## Evidence packaging for T3 certification

Do not call `consult_models.py state --file /tmp/status.json` and assume the truth gate can link the file to claims. That commonly yields:

- `truth_status=unsupported`
- `evidence_coverage=0.0`
- `unsupported_high_severity_claim_ids=[C-001,...]`
- final `not_certified` even though all four models participated

Instead, build claim-linked evidence. Preferred options:

1. Use `consult_models.py state` with explicit `--claim` values plus `--evidence-json` entries whose `supports` arrays reference the exact claim IDs (`C-001`, not aliases like `C1`).
2. If the CLI cannot express the needed evidence shape safely, manually write a known-good `schema: multi_model_state_v1` JSON with `claims[]`, `evidence[]`, `supports[]`, `context`, and `acceptance_criteria`, validate with `python3 -m json.tool`, then run `consult_models.py run`.
3. Treat an unlinked run as useful advisory provenance only. Never call it full certification.

## Evidence-spine implementation pattern

If the local taskpool already has or needs a durable read-only status endpoint, prefer one consolidated command over stitching many ad-hoc JSON files in prose:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py evidence-spine --json
```

Recommended schema shape:

- `schema`: `local_brain_taskpool_evidence_spine_v1`
- `status`: overall read-only collection status (`OK` / degraded)
- `gate_status`: aggregate deterministic gate status (`PASS` / `FAIL`)
- `summary`: compact counts and convergence metrics
- `safety`: autorun flags, kill switch, allowlists, work-lane preemption, safe-for-next-tick flags
- `evidence[]`: stable IDs future ratification can cite:
  - `E-TP-COUNTS`: active/pending/claimed/review/stale/dispatchable/by_lane/by_status
  - `E-TP-GATES`: `proof-check` + `selfcheck`
  - `E-TP-DISPATCH`: boundary check + `parallel-dispatch-dry-run`
  - `E-TP-AUTORUN`: autorun env flags, multimodel autorun flag, kill switch, allowlist paths
  - `E-TP-AUTO-COMPLETER`: auto-completer cron state and semantic classification
  - `E-TP-MULTIMODEL`: convergence stats, pass/trigger rates, ratification failure taxonomy
  - `E-TP-CRON`: key cron jobs and next/last run status

When wiring dispatch ticks, inject a compact `evidence_spine` heartbeat into the tick summary (`status`, `gate_status`, `summary`, `safety`) so later sessions can inspect one artifact before rerunning expensive probes.

For `build_multimodel_intervention_plan()`, generate `consult_models.py state` with explicit claims and `--evidence-json` supports. A useful baseline mapping is:

- `C-001` task decomposition / accuracy <- `E-TASK-CANONICAL`
- `C-002` ratification gate / one-shot landing <- `E-RATIFICATION-GATE`
- `C-003` lane/project preservation / long-term goal <- `E-WORK-LANE-PREEMPTION`

This prevents `evidence_coverage=0.0` caused by raw status files that contain evidence but do not link it to the exact claim IDs.

## Multi-model failure taxonomy for taskpool readiness

Expose the reason `pass_rate=0.0` instead of only reporting the aggregate number. Recommended taxonomy keys:

- `no_claims`
- `unsupported_claims`
- `evidence_missing`
- `vote_reject`
- `agreement_low`
- `provider_parse_error`
- `quota_unobservable`
- `criteria_missing`
- `final_design_missing`
- `model_vote_missing`

Use the taxonomy to choose the next fix: evidence/linkage problems require claim/evidence repair; vote/agreement/design problems require issue-ledger resolution; provider/parse/quota problems require adapter or budget handling. Do not lower the ratification threshold to make the metric look better.

## Long-running autonomous architecture answer shape

When summarizing how to make the taskpool self-run long term, separate the architecture into layers:

1. Scheduler: chooses bounded next work; never marks done.
2. Guardian: fixes stale leases/timeouts and reports V-state; never certifies task completion alone.
3. Worker: executes scoped task with TTL/workspace boundary/budget.
4. Proof gate: controls `review -> done` using deterministic artifacts and residual blockers.
5. Multi-model ratifier: verifies claim/evidence bundles; agreement alone is not evidence.
6. Reporter/dashboard: emits concise watch reports and alerts.

Default upgrade order:

1. Add/read a machine-verifiable taskpool evidence-spine status export with stable evidence IDs.
2. Harden auto-completer error semantics: bounded task blocker vs cron/system error.
3. Add multi-model failure taxonomy (`no_claims`, `unsupported_claims`, `evidence_missing`, `vote_reject`, `agreement_low`, `provider_parse_error`, `quota_unobservable`).
4. Keep autorun disabled until allowlist, leases, kill-switch, budget, proof-gated done, and work-lane preemption all pass.
5. Resolve parallel boundary conflicts before increasing worker count.

## Pitfalls

- Full four-model participation is not full certification if the ratification artifact says `not_certified` or truth coverage is 0.
- Do not enable `HERMES_LOCAL_BRAIN_AUTORUN` just because guardian is healthy. Healthy monitoring is necessary but not sufficient for write-capable autonomy.
- Do not let evolution tasks starve work/product-delivery tasks; verify this with `parallel-dispatch-dry-run`, not prose.
- Do not treat a cron `RuntimeError` summary as the root cause until you read the bounded task evidence and baseline blocker details.
