# Local Brain Taskpool System Repair Runbook

Use this when a status check finds system-level taskpool issues and the user asks to analyze/solve them (not merely report status): proof/selfcheck failures, evidence-spine errors, `human_escape_triggered`, summary tick cron errors, or orphan agent-team workers.

## Safety principles

- Treat canonical Markdown tasks as source of truth; do not mutate task statuses unless repair requires it and evidence identifies an orphan/stale claim.
- Do not delete `FAILED` envelope rows. Preserve terminal audit history.
- Do not lower validator strictness to make gates pass. Normalize bad task metadata/evidence instead.
- For P0/Lark closeout, do not mark done from system-health recovery alone; closeout still needs target-bound ratification and acceptance evidence.
- If a manual `agent_team_controller.py cycle` is used, expect long-running workers; be prepared to clean orphan workers if the tool wrapper times out.

## Evidence package before repair

Run and save/quote the key outputs:

```bash
date '+%Y-%m-%d %H:%M:%S %Z'
python3 ~/.hermes/scripts/brain_task_orchestrator.py list --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json || true
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json || true
python3 ~/.hermes/scripts/brain_task_orchestrator.py evidence-spine --json || true
python3 ~/.hermes/scripts/envelope_bus.py stats
python3 ~/.hermes/scripts/task_pool_guardian.py health
hermes cron list
```

If `human_escape_triggered=true`, inspect the terminal envelopes:

```bash
python3 - <<'PY'
import json, sqlite3
from pathlib import Path
p = Path.home()/'.hermes/state/envelope_bus.db'
conn = sqlite3.connect(p); conn.row_factory = sqlite3.Row
rows = conn.execute("""
SELECT id,status,type,project,assignee,title,error,retry_count,max_retries,created_at,updated_at,completed_at
FROM envelopes
WHERE status IN ('FAILED','BLOCKED','RUNNING')
ORDER BY updated_at DESC LIMIT 20
""").fetchall()
print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))
PY
```

## Common root causes and safe fixes

### Unstructured evidence in completed task notes

Symptom: `proof-check` reports unstructured evidence / legacy body evidence.

Safe fix:
- Convert raw file paths that still exist to `file:/absolute/path`.
- Convert historical, garbage-collected artifacts to structured `artifact:<id> (historical provenance; source file GC'd)` rather than leaving a bare dead path.
- Preserve the evidence history; do not remove lines just to satisfy the checker.

### Mission-envelope false positive

Symptom: `selfcheck` reports `mission_envelope_missing` for a standalone evolution/advisory task.

Safe fix:
- Remove or blank mission-only markers such as `certification_status: certified` when the task is not a mission envelope.
- Preserve canonical multi-model fields such as `multimodel_status` and `multimodel_ratification_artifact` if they remain true.
- Add an audit-log note explaining this is metadata repair, not task closeout.

### Summary tick cron errors caused by proof/evidence gates

Symptom: safe/autorun summary tick exits non-zero with `proof_check` or `evidence_spine` ERROR.

Safe fix:
- Fix the underlying proof/selfcheck/evidence metadata first.
- Then verify both wrappers directly:

```bash
python3 ~/.hermes/scripts/brain_task_dispatch_summary_tick.py
python3 ~/.hermes/scripts/brain_task_dispatch_autorun_summary_tick.py
```

Cron `last_status` may lag until the next scheduled/manual run. If needed, trigger the cron job and re-list it, but still use the direct wrapper output as deterministic evidence.

### Envelope human escape from reviewed failed rows

Symptom: `envelope_bus.py stats` shows `human_escape_triggered=true` and `since_ack.failures > 0` from already-reviewed FAILED envelopes.

Before acking, classify the rows and prove this is a watermark/escape issue rather than active work:
- `proof-check`, `selfcheck`, `evidence-spine`, summary ticks, and guardian pass.
- `envelope_bus.py stats` shows `timeouts=0` or the timeout has already been reset/classified.
- SQLite inspection of `FAILED`/`BLOCKED`/`RUNNING` rows shows the post-ack rows are terminal `FAILED` rows, not active `RUNNING`/`BLOCKED` work.
- Process scan for `team-worker-`, `agent_team_controller.py cycle`, `brain_task_auto*`, `brain_task_orchestrator.py claim`, and `hermes-taskpool-auto` is empty or explicitly explained.

Safe fix only after deterministic gates pass and failures are classified:

```bash
python3 ~/.hermes/scripts/envelope_bus.py ack-escape \
  'reviewed post-ack failed envelopes after proof/selfcheck gates repaired; preserve FAILED terminal audit rows; no task done/status mutation'
python3 ~/.hermes/scripts/envelope_bus.py stats
```

If the user asks for "人工确认由多模型思考确认" or equivalent, do not treat your own judgment as the human ack. Build a claim-linked `consult_models.py state` first and run T3 quorum 4 discussion against the exact proposed ack action. Require the canonical four participants (Claude + GPT/Codex + DeepSeek + MiMo) to approve before `ack-escape`. Bind the ack reason to the resulting `discussion_result.json` path.

Acceptance:
- `human_escape_triggered=false`
- `since_ack.failures=0`
- `historical.failures` still reflects preserved FAILED rows
- No FAILED rows were deleted.
- No validator strictness was weakened.
- No product/Lark task was marked done or status-mutated by the ack.

Do not use ack as a way to hide active failures before reading and classifying them.

### Manual agent-team cycle timeout / orphan workers

Symptom: a manual `agent_team_controller.py cycle` times out; guardian shows RUNNING timeouts or tasks remain claimed by `agent-team-controller` while worker processes are orphaned.

Safe cleanup:

```bash
python3 ~/.hermes/scripts/task_pool_guardian.py run
ps -ax -o pid,pgid,etime,command | grep -E 'team-worker-|agent_team_controller.py cycle' | grep -v grep || true
```

If the corresponding envelopes were reset to PENDING and the worker processes are now orphaned, terminate the worker process group, not unrelated `consult_models.py` jobs:

```bash
# Inspect first; then TERM specific process groups only.
ps -ax -o pid,pgid,etime,command | grep -E 'team-worker-' | grep -v grep
kill -TERM -<PGID>
```

If SIGTERM does not exit after a short wait, use SIGKILL on the same PGID. Then release only the orphan task claims back to `pending`:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py release TASK_ID \
  --actor hermes --to-status pending \
  --reason orphan_worker_cleaned_after_manual_agent_cycle_timeout \
  --force --json
```

Do not release legitimate `review` claims that represent closeout/review gates.

## Verification gate

Before declaring repair complete, run:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py evidence-spine --json
python3 ~/.hermes/scripts/brain_task_dispatch_summary_tick.py
python3 ~/.hermes/scripts/brain_task_dispatch_autorun_summary_tick.py
python3 ~/.hermes/scripts/envelope_bus.py stats
python3 ~/.hermes/scripts/task_pool_guardian.py run
ps -ax -o pid,pgid,etime,command | grep -E 'team-worker-|agent_team_controller.py cycle' | grep -v grep || true
```

Expected current-operational pass:
- proof-check PASS
- selfcheck PASS
- evidence-spine OK/PASS
- summary ticks `status=OK`, `error_count=0`
- envelope `human_escape_triggered=false`, `timeouts=0`
- guardian HEALTHY with `issues_found=0` after cleanup
- no orphan worker/cycle processes
- claimed/running tasks are either zero or explainable review gates

## Multi-model certification pattern

For system repairs with non-trivial policy choices, use two-stage multi-model:

1. **Diagnosis/repair-plan review**: package claims/evidence for root cause and proposed safe repair. If models return `not_certified` due packaging/intent issues but truth gate is grounded, do not blindly stop; perform only deterministic low-risk repairs that the evidence supports.
2. **Pre-action authorization for human-ack operations**: when the repair is an operational acknowledgement such as `ack-escape`, build claims around the exact action and explicit non-actions (no FAILED deletion, no validator weakening, no task done/status mutation). Evidence should include gate outputs, terminal envelope rows, process scan, task list, and proposed acceptance conditions. Run `consult_models.py run ... --tier T3 --quorum 4 --discussion --keep`; require the canonical 4/4 participant set before executing the ack.
3. **Post-repair current-state certification**: after gates pass, run a fresh state that asks models to certify the actual current state, not to plan new patches. Require 4/4 approval for this user's full certification standard.

Useful claim shape:
- metadata normalization fixed proof/selfcheck without lowering validators;
- summary ticks resolve because proof/evidence gates now pass;
- human_escape is resolved while historical FAILED rows are preserved;
- manual taskpool work is safe to continue, while automatic agent-team execution remains cautious if timeout history exists;
- no product/Lark task closeout occurred as part of system-health recovery.

For post-repair certification, include claims for:
- proof/selfcheck/evidence-spine/summary ticks are PASS/OK;
- `human_escape_triggered=false`, `since_ack.failures=0`, `timeouts=0`, historical failures preserved;
- guardian `issues_found=0`, `issues_fixed=0`, grade healthy;
- no orphan worker/controller processes;
- current review/next-dispatch task state is unchanged except for expected scheduling visibility.

## Reporting shape

Report separately:
- what changed (files/metadata/ack/released orphan claims);
- what was deliberately not changed (no failed-row deletion, no validator weakening, no P0 closeout);
- final gate outputs;
- remaining review tasks and next dispatch hint;
- multi-model artifact path if certification was run.
