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
- A deterministic `signature(summary)` and `changed` gate. Include `auto_close_review.closed_count` and `auto_close_review.error_count` in the signature so proof-gated review closeouts are visible even when `next_task_id` is unchanged.
- Full `stdout`/`stderr` retained for internal JSON parsing; only log/report fields may be truncated to `stdout_tail` / `stderr_tail`. Never parse a tail slice.
- Explicit fail-closed parse handling: non-empty successful stdout that cannot be parsed is `*_parse_failed` / exit non-zero, not `no_intervention_needed` or null summary fields.
- `start_new_session=True`, `os.killpg`, and a structured `subprocess_timeout` record.
- A short timeout for probing the multi-model worker starter (for example 60s), not for running the full discussion.
- `auto_close_review` should be part of the emitted event/state, not only the raw tick tail, so cron/no-agent summaries can distinguish `closed`, `skipped`, and `error` closeout outcomes.

## Proof-gated review -> done closeout

When automating local-brain task closeout, do not mark `review` tasks `done` just because a runner or multi-model round finished. Add an explicit closer command (for example `brain_task_orchestrator.py auto-close-review --json`) and invoke it after the bounded `--autorun-step` runner:

1. Select only tasks currently in `review`.
2. Build base evidence only from task frontmatter evidence plus a certified local multi-model artifact when `task_multimodel_passed(task)` is true.
3. Probe the normal lane-specific `lifecycle_gate(task, "done", ...)` with base evidence first. If it fails, record a `skip`; do not mint an autorun proof hash and do not force the transition.
4. Only after the base evidence passes, append an autorun proof-chain event and add `proof:sha256:<hash>` as audit evidence.
5. Re-run the same `lifecycle_gate` with final evidence and then call the normal lifecycle transition path. This keeps autorun proof from becoming a fake completion proof.
6. For certified multi-model rounds, land the artifact explicitly as `artifact:ratification multimodel certified <discussion_result.json>` so future audits can see why a review task was closable.
7. Emit `closed`, `skipped`, `errors`, counts, and a safety string in the summary. Skips caused by invalid evidence shape or unknown completion gates are desired fail-closed behavior, not scheduler failures.

A detached multi-model starter should contain:

- `--worker` mode launched with `subprocess.Popen(..., start_new_session=True)`.
- `worker.pid`/alive check so cron does not spawn duplicates.
- signature + cooldown suppression such as `suppressed_no_change_cooldown`.
- explicit `HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1` only inside the worker environment.
- the original `multimodel-intervention-parallel-step` / T3 discussion path intact.
- worker logs should include a compact `worker_summary` parsed from the full stdout before any stdout tail compaction. Keeping only `stdout_tail` is fine for log size, but future audits must not need to parse a tail slice as JSON.

## Provider/model mismatch handling

For recurring script-summary jobs that fail only because a model/provider pin is rejected:

- Prefer converting the job to no-agent deterministic reporting when the script output is already machine-readable.
- Otherwise repin via Hermes' provider registry/model picker rather than hardcoding a guessed provider/model.
- Do not conflate provider pin failures with local-brain taskpool corruption.

## No-agent wrapper convention for recurring audits

When a cron job is mostly `run deterministic script → summarize JSON`, reduce blast radius by adding a no-space wrapper script under `~/.hermes/scripts/` and switching the job to `no_agent: true`:

```python
#!/usr/bin/env python3
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path.home() / ".hermes" / "scripts" / "target-script.py"
p = subprocess.run([sys.executable, str(SCRIPT)], text=True, capture_output=True, timeout=300)
print(json.dumps({
    "schema": "target_noagent_wrapper_v1",
    "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "status": "OK" if p.returncode == 0 else "ERROR",
    "returncode": p.returncode,
    "stdout_tail": (p.stdout or "")[-3000:],
    "stderr_tail": (p.stderr or "")[-1000:],
}, ensure_ascii=False, indent=2))
sys.exit(0 if p.returncode == 0 else 2)
```

Use this for nightly audits such as autonomous evolution or skill-steward graph checks when the LLM adds little value and has been causing timeout/provider-pinning failures. Keep the wrapper deterministic and auditable; do not let it create cron jobs recursively.

## Safe backup after cron hardening

If the task includes syncing the user's personal Hermes assistant, never commit live `~/.hermes` after cron/script edits. Export through the sanitized personal-brain backup path, then validate and push only that repo:

```bash
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/personal_hermes_brain_export.py --json
cd ~/personal-hermes-brain
bash bootstrap/validate_safe_tree.sh
bash bootstrap/verify.sh
git diff --check
git add -A && git commit -m "sync: <summary>"
HERMES_ALLOW_PUSH=1 git push -u origin HEAD:main
```

The export allowlist must include any new deterministic cron wrapper scripts that should survive machine restore. Raw memory, auth, `.env`, sessions, logs, state DBs, checkpoints, and tick artifacts remain excluded.

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
