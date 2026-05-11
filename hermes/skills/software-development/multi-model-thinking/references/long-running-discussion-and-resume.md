# Long-running discussion and resumable ratification

Use this when `consult_models.py run --discussion` times out after producing `plans/*.json` and `merged_plan.json`, or when the user asks to extend discussion to complete full multi-model certification.

## Key lesson

Increasing `--max-rounds` alone is not enough. Discussion calls can exceed the outer terminal timeout because online discussion is effectively:

```
max_rounds × model_count × per_model_timeout × up_to_2_attempts
```

`--timeout` is passed to both planner calls and discussion model calls. Each discussion round calls models serially; if JSON extraction fails, the script retries with a strict JSON prompt. A 4-model, 5-round, 300s run can therefore take far longer than a 600s foreground tool timeout.

If the process is killed before `discussion_result.json` is written, treat artifacts as useful weak evidence only, not certification.

## Safe operating pattern

1. Build an evidence-first state file with claims/evidence/constraints.
2. Run long discussion in the background, not in a foreground command with a short tool timeout:

```bash
python3 ~/.hermes/scripts/consult_models.py run /tmp/state.json \
  --tier T3 \
  --quorum 4 \
  --discussion \
  --max-rounds 5 \
  --timeout 300 \
  --keep
```

When using a terminal tool, prefer `background=true` and `notify_on_complete=true`.

3. After completion, inspect the latest tick directory:

```bash
find ~/.hermes -maxdepth 1 -type d -name 'tick-*' -mmin -180 | sort | tail -5
ls ~/.hermes/tick-*/plans/*.json ~/.hermes/tick-*/merged_plan.json ~/.hermes/tick-*/discussion_result.json 2>/dev/null
```

4. Only call it full certification if `discussion_result.json` exists and the ratification gates pass.
5. When multiple `consult_models.py` jobs may run concurrently, never bind a timeout/retry to “latest `tick-*/discussion_result.json`” by mtime alone. Match the tick’s `state.json` to the launched state identity (at minimum `question` plus claim texts/state hash). If the matching artifact is absent, fail closed as `discussion_result_missing`; an unrelated certified tick is contamination, not evidence.

## Recommended parameters

- T2 medium-risk: `--quorum 4 --discussion --max-rounds 3 --timeout 240`
- T3 high-risk: `--quorum 4 --discussion --max-rounds 5 --timeout 300`
- Formal/high-stakes certification: `--quorum 4 --discussion --max-rounds 7 --timeout 360`, run in background and expect long wall-clock time.

## Evidence-first beats more rounds

If the blocker is missing runtime evidence (hook payloads, schemas, state contracts, file fixtures), do not just add rounds. Run an Evidence Request Fulfillment Loop:

1. Fan out planners and collect `evidence_requests`.
2. The orchestrator executes read-only evidence collection.
3. Feed the evidence back into a new state file.
4. Rerun discussion for ratification.

Model agreement is not evidence; extra rounds without new evidence often only produce repeated caveats.

## Long-term infrastructure: RMCS

If long-running discussion is recurring, do not keep tuning only `--timeout` / `--max-rounds`. Promote the work to RMCS: Resumable Multi-Model Certification System. See `references/resumable-multimodel-certification-system.md`.

Minimum durable architecture:

1. Checkpoint after each model response and each round.
2. Add `audit-certification <tick_dir>` as deterministic/read-only status inspection.
3. Add `resume-discussion <tick_dir>` to continue from checkpoint/cursor.
4. Add a background-safe runner with heartbeat/status and timeout markers.
5. Add evidence-first split workflow for high-risk runtime/API/schema claims.
6. Only later consider same-round parallel model calls.

Desired commands:

```bash
python3 ~/.hermes/scripts/consult_models.py audit-certification ~/.hermes/tick-YYYYMMDD-HHMMSS
python3 ~/.hermes/scripts/consult_models.py resume-discussion ~/.hermes/tick-YYYYMMDD-HHMMSS \
  --max-rounds 5 \
  --timeout 300 \
  --keep
```

Until RMCS exists, do not rerun expensive T3 discussion blindly if existing artifacts are enough to answer the user; summarize the weak consensus / not-certified status honestly.

If a dependent high-risk feature needs certification (for example `TaskCreate -> next-round ralph` hook/state automation), explicitly defer it until RMCS P0-P2 pass rather than trying to certify it through a repeatedly timing-out foreground discussion.