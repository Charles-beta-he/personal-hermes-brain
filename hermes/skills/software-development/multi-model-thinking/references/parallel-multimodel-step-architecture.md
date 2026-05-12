# Parallel Multimodel Step Architecture

## Problem

Serial multimodel-intervention-step processes 1 task per ~8min (T2 tier). With 18 triggered tasks, completion takes ~18h via 1h cron.

## Solution: ThreadPoolExecutor + Boundary Isolation

### Architecture

```
multimodel-intervention-parallel-step --max-workers 3
  ├── dry-run → select top-2N intervention tasks
  ├── boundary conflict check (unique parallel_boundary per task)
  ├── allowlist check per task
  └── ThreadPoolExecutor(max_workers=3)
      ├── worker 1: build_state → discussion → gate → mutate
      ├── worker 2: build_state → discussion → gate → mutate
      └── worker 3: build_state → discussion → gate → mutate
  └── aggregate: passed/failed/errors + convergence
```

### Key Design Decisions (from T3 4-model discussion)

**Claude proposal**: ThreadPoolExecutor keyed by parallel_boundary, per-provider semaphore (gpt=2, deepseek=2, mimo=2), boundary_check pre-flight.

**GPT-5.5 proposal**: Same core + max_parallel config + boundary conflict verifier.

**DeepSeek proposal**: Noop — existing agent_team_controller sufficient.

**Consensus**: ThreadPoolExecutor + boundary isolation (no provider semaphore needed for T2 with 3 models).

### Why ThreadPoolExecutor over alternatives

| Approach | Pros | Cons |
|----------|------|------|
| **ThreadPoolExecutor** ✅ | Shared process, low overhead, easy error handling | GIL (but I/O-bound, not an issue) |
| Subprocess spawning | Full isolation | High overhead, complex IPC |
| Chained cron | Simple | Idle time between tasks, no parallelism |
| Batch discussion | One call for multiple tasks | Complex prompt, model confusion |
| Subagent delegation | Leverages existing infra | Double scheduling, budget overhead |

### Boundary Isolation

Each task has a `parallel_boundary` field (frontmatter). Tasks with different boundaries can safely run concurrently:

```
workspace:/Users/charles/Desktop/folder/work/uvisa-backend  → 1 task
workspace:/Users/charles/Desktop/folder/work/uvisa-app-2.0  → 2 tasks
project:hermes-capability-router                              → 1 task
evolution:skill-learning:code-review                          → 1 task
```

The boundary check selects tasks with unique boundaries from the candidate list. Same-boundary tasks are skipped (not queued for next batch).

### Per-Task Pipeline

Each worker runs `_run_single_task_pipeline(plan, allowlist_active)`:

1. **Build state**: `consult_models.py state` with explicit `--claim` flags (120s timeout)
2. **Run discussion**: `consult_models.py run --discussion --tier T2 --quorum 3 --max-rounds 3` (1200s timeout)
3. **Gate**: `ratification_gate_result(discussion)` — 7 checks, fail-closed
4. **Mutate on PASS**: `write_multimodel_result_to_task()` — updates frontmatter

Each step is independent. Failure in one worker doesn't affect others.

### Tick-to-Discussion Matching

When multiple discussions run concurrently, each produces a `tick-*` directory. The pipeline matches ticks to tasks by checking `tick-*/state.json` for the task ID in the question field:

```python
tick_state = tick_dir / "state.json"
if tick_state.exists():
    tick_state_data = json.loads(tick_state.read_text())
    if task_id not in str(tick_state_data.get("question", "")):
        continue  # wrong tick
```

### Throughput

| Mode | Tasks/cycle | Time/cycle | 18 tasks |
|------|-------------|------------|----------|
| Serial | 1 | ~8min | ~144min |
| Parallel (3) | 3 | ~8min | ~48min |
| Parallel (5) | 5 | ~8min | ~32min |

### Configuration

```bash
# Cron job (every 60m)
python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-parallel-step --max-workers 3 --json

# Manual run
HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1 python3 ~/.hermes/scripts/brain_task_orchestrator.py multimodel-intervention-parallel-step --max-workers 5 --json
```

### Safety

- Each task independently gated (fail-closed)
- Boundary isolation prevents workspace conflicts
- Allowlist check per task
- env var gate (`HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1`)
- No shared state between workers
- task_mutation only on gate PASS

### Pitfalls

1. **Tick matching**: Must verify tick belongs to correct task (check state.json question field)
2. **API rate limits**: 3 concurrent discussions = 3× model calls. T2 uses 3 models, so 9 concurrent API calls max.
3. **Disk I/O**: Each discussion writes ~100KB of artifacts. 3 concurrent = ~300KB/write cycle.
4. **Memory**: Each `consult_models.py` subprocess uses ~50MB. 3 concurrent = ~150MB.
