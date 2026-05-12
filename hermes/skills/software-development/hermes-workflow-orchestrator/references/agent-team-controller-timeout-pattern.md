# Agent Team Controller Timeout Pattern

> Diagnosis from 3 consecutive sessions (May 11, 2026: 00:57, 03:59, 05:09 AM) where the same cron job timed out with identical root cause.

## Symptom

Cron job runs `agent_team_controller.py cycle` and reports either:
- `Script not found: /path/to/agent_team_controller.py cycle` (misleading — script exists but cron runner misparses args)
- Command times out after 60-120s+

Meanwhile, `agent_team_controller.py status` returns instantly with valid JSON.

## Root Cause

The `cycle` command mixes claim+enqueue with synchronous execution:

```python
# run_dynamic_cycle() flow:
1. get_all_dispatchable()        # fast (~1s) — calls orchestrator list --json
2. classify_batch()              # fast — deterministic
3. get_smoothed_n()              # fast
4. get_parallel_schedule()       # fast
5. claim_task()                  # fast (~1s) — calls orchestrator claim
6. create envelope               # fast — envelope_bus.create()
7. delegate_to_worker()          # BLOCKS 300-600s — calls hermes chat -q
8. verify_with_models()          # BLOCKS — LLM call
9. update envelope status        # fast
```

Step 7 spawns a full `hermes chat -q` session per task with:
```python
timeout_s = 600 if needs_code else 300
```

With `applied_n=3`, the cycle can block for up to 30 minutes.

## Observed Consequences

| Metric | Trend across 3 sessions (May 11) | May 12 confirmation |
|---|---|---|
| PENDING envelopes | 17 → 21 → 24 (monotonically increasing) | 49 (still growing) |
| DONE envelopes | 11 → 11 → 11 (flat — no work completing) | 18 |
| FAILED | 2 → 2 → 2 (unchanged) | 10 |
| Timeouts | 2 → 2 → 2 (unchanged) | 2 |
| Dispatchable tasks | ~20 → 20 → 18 (slowly decreasing via other paths) | 25 |
| Conflict groups | — | 19 |
| Applied N | — | 3 (formula: min(ceil(25/7), 19, 3)) |

The system produces work items faster than it can consume them. PENDING grows while DONE stays flat because the cycle never completes.

## Fix: Claim/Execute Separation

### Phase 1: Fast Claim (cron-safe, <5s)

```python
def claim_cycle():
    """Claim-only phase. Returns in <5s."""
    all_tasks = get_all_dispatchable()
    groups = classify_batch(all_tasks)
    n_result = get_smoothed_n(len(all_tasks), len(groups))
    applied_n = n_result['applied_n']
    schedule = get_parallel_schedule(all_tasks, applied_n)
    
    claimed = []
    for group_info in schedule['schedule'][:applied_n]:
        task = pick_highest_priority(group_info, all_tasks)
        result = claim_task(task['id'])
        if result['ok']:
            eid = create_envelope(task)
            claimed.append({'task_id': task['id'], 'envelope_id': eid, 'group': group_info['conflict_group']})
            # Write to queue file, NOT execute
            enqueue(eid, task, group_info['conflict_group'])
    
    return {'status': 'claimed', 'tasks_claimed': len(claimed), 'groups': claimed}
```

### Phase 2: Background Execute (separate process/cron)

```python
def execute_cycle():
    """Dequeue and execute. Can run as separate long-lived process."""
    pending = read_queue()
    for item in pending:
        result = delegate_to_worker(item['task'], item['group'], item['eid'])
        handle_result(item, result)
```

### Alternative: Use `hermes-pipeline` pattern

Instead of building custom claim/execute split, use the `hermes-pipeline` skill which handles exactly this pattern — enqueue work items, process them in bounded sessions, write back results.

## Diagnosis Checklist for Similar Issues

When a cron job times out or reports "script not found":

1. **Verify script exists**: `ls -la /path/to/script.py`
2. **Test fast subcommands**: If the script has `status`, `list`, or `--dry-run` modes, test those first
3. **Check for blocking calls**: Search for `subprocess.run(..., timeout=` values > 30s
4. **Check for `hermes chat -q`**: This is the most common blocking call in orchestrator scripts
5. **Separate read from write**: Status/list commands are usually fast; claim/execute/delegate are slow
6. **Look at envelope/task trends**: If PENDING grows while DONE stays flat, the executor is broken
7. **Check stale claims**: `agent-team-controller` claims cannot be released without `--force` — `brain_task_orchestrator.py release <id>` will refuse with "task claimed by agent-team-controller; hermes cannot release without --force". This is by design (safety) but means orphaned claims from timed-out cycles persist until manually force-released.

## Related Scripts

- `~/.hermes/scripts/agent_team_controller.py` — the controller (cycle/status/enable/disable)
- `~/.hermes/scripts/brain_task_orchestrator.py` — task orchestrator (list/claim/release/next)
- `~/.hermes/scripts/envelope_bus.py` — envelope state management
- `~/.hermes/scripts/dynamic_n.py` — adaptive parallelism sizing
- `~/.hermes/scripts/task_classifier.py` — conflict group classification
