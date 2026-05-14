# Taskpool pre-ingest multimodel triage

Use when the user is dropping external repos/articles/ideas into Hermes taskpool and wants the queue itself to remain independent, stable, and self-explanatory.

## Why this exists
The user corrected the workflow: priority analysis should happen before formal task creation, not after tasks are already in the pool. Taskpool should hold already-governed work items rather than raw intake.

## Default policy
For external repository/article intake:
1. Treat the incoming links as raw capture, not final task records.
2. Run fixed multimodel triage before `brain_task_orchestrator.py add`.
3. Assign P1/P2/P3 plus a short rationale and architecture/lane recommendation.
4. Only after triage, create the formal taskpool entry with the chosen fields and evidence.
5. If the user drops a batch of links, do not skip triage just to bulk-add faster. Batch creation is fine only after each item has a priority bucket and short rationale.

   - lane
   - priority rationale
   - duplicate/overlap notes
   - whether to formalize as a task vs keep as observation
4. Only then write the formal task into taskpool.

## Practical implications
- Avoid bulk-adding a batch of links as uniform P2 by default.
- If the user explicitly wants pure capture, label it as raw intake and note that prioritization is deferred by request.
- If add/create times out but the task may already exist, verify task files / sorted pool before retrying, to avoid `-2` duplicate task artifacts.

## Heuristic for P1 vs P2 vs P3
- P1: likely to change Hermes control plane, taskpool, context/prompt assembly, permission model, loop engine, recovery, or other system-wide leverage points.
- P2: clearly useful and actionable, but not the first control-plane leverage batch.
- P3: interesting research, inspiration, or lower-certainty transfer candidates.

## Verification
After add:
- verify the created markdown task file exists
- verify the task appears in `任务池-排序.md`
- verify whether event hook failure is cosmetic or blocked the actual write

## Pitfall
Do not postpone all prioritization until after tasks are already inside the pool unless the user explicitly asked for raw intake. That makes the queue less independent and weakens downstream dispatch semantics.
