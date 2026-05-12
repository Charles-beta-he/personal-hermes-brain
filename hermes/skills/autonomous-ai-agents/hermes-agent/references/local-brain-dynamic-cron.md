# Local-brain dynamic cron and timeout blast-radius control

Use this when Hermes cron jobs around a local brain/task pool start failing with `Request timed out`, long multi-model runs, or cron-agent wrappers that block waiting for LLM work.

## Evidence-first diagnosis

Before changing jobs, gather structured evidence:

```bash
hermes cron list
python3 - <<'PY'
from pathlib import Path
import json, re
H=Path.home()/'.hermes'
jobs=json.loads((H/'cron/jobs.json').read_text())
if isinstance(jobs, dict): jobs=jobs.get('jobs', [])
for j in jobs:
    if str(j.get('last_status')).lower() in {'error','failed'}:
        print(json.dumps({k:j.get(k) for k in ['id','job_id','name','script','model','provider','last_status','last_error','last_run_at','next_run_at']}, ensure_ascii=False))
PY
grep -E "Request timed out|Not supported model|can't open file|subprocess_timeout" ~/.hermes/logs/errors.log | tail -50
```

Classify failures separately:

- `provider_model_mismatch`: provider/model pin is rejected (for example xiaomi + unsupported model id). Do not retry the same pin forever.
- `llm_or_job_timeout`: cron prompt or script waits on model/multi-model work too long.
- `wrapper_path_or_args`: cron script value/wrapper points at a missing file or encodes args incorrectly.
- `observability_noise`: hooks/loggers missing but not affecting task state.

If dispatch/taskpool summary tails are still `OK` and `next_task_id` advances, do not assume canonical taskpool data corruption.

## Remediation pattern

Prefer deterministic `no_agent` cron scripts and event-gated runners:

1. Make the cron entry short-running and deterministic (`no_agent: true` when possible).
2. Compute a taskpool signature from the canonical summary: next task, dispatchability, error count, reconcile count, multimodel task/queue count.
3. If the signature is unchanged and no error/advance happened, exit silently.
4. If an expensive multi-model step is required, start a detached worker and return immediately.
5. Use pid locks + cooldown + process-group timeout to prevent duplicate/orphan workers.
6. Preserve certification ratchets: the detached worker may run T3/quorum4/discussion, but the scheduler tick must not downgrade the gate to avoid timeouts.
7. Log compact JSONL state for auditability.

## Minimal contract checks

A dynamic taskpool runner should contain:

- `--summary`, `--autorun-step`, and `--no-state` when calling the dispatch tick.
- A deterministic `signature(summary)` and `changed` gate.
- `start_new_session=True`, `os.killpg`, and a structured `subprocess_timeout` record.
- A short timeout for probing the multi-model worker starter (for example 60s), not for running the full discussion.

A detached multi-model starter should contain:

- `--worker` mode launched with `subprocess.Popen(..., start_new_session=True)`.
- `worker.pid`/alive check so cron does not spawn duplicates.
- signature + cooldown suppression such as `suppressed_no_change_cooldown`.
- explicit `HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1` only inside the worker environment.
- the original `multimodel-intervention-parallel-step` / T3 discussion path intact.

## Provider/model mismatch handling

For recurring script-summary jobs that fail only because a model/provider pin is rejected:

- Prefer converting the job to no-agent deterministic reporting when the script output is already machine-readable.
- Otherwise repin via Hermes' provider registry/model picker rather than hardcoding a guessed provider/model.
- Do not conflate provider pin failures with local-brain taskpool corruption.

## Verification

Run the runner directly before editing cron:

```bash
python3 ~/.hermes/scripts/taskpool_dynamic_runner.py
python3 ~/.hermes/scripts/multimodel_intervention_dynamic_step.py --json
python3 ~/.hermes/scripts/multimodel_keypoint_coverage_ratchet.py --skip-taskpool
```

After editing cron, trigger the job and re-check:

```bash
hermes cron run <job-id>
hermes cron list
```

For evidence-first/multi-model reviews, require a new discussion result after code or cron changes. Old certification ticks are only provenance after amendments.
