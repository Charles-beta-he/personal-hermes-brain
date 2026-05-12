# Envelope Bus Implementation (SQLite)

## Overview

Lightweight SQLite envelope bus for task pipeline state management. Located at `~/.hermes/scripts/envelope_bus.py`.

## Schema

```sql
CREATE TABLE envelopes (
    id               TEXT PRIMARY KEY,
    type             TEXT CHECK(type IN ('TASK','PLAN','RESULT','VALIDATION')),
    status           TEXT CHECK(status IN ('PENDING','RUNNING','DONE','FAILED','SKIPPED','BLOCKED')),
    project          TEXT,
    assignee         TEXT,
    title            TEXT,
    payload          TEXT,           -- JSON
    trace            TEXT,           -- JSON array of events
    proof_sha        TEXT,           -- sha256 of proof artifact
    error            TEXT,
    retry_count      INTEGER DEFAULT 0,
    max_retries      INTEGER DEFAULT 3,
    appetite_seconds INTEGER DEFAULT 1800,   -- 30min default
    created_at       TEXT,
    updated_at       TEXT,
    started_at       TEXT,
    completed_at     TEXT
);
```

## API

```python
from envelope_bus import create, get, update_status, append_trace, increment_retry
from envelope_bus import list_by_status, count_by_status, check_timeout, human_escape_check, stats

# Create envelope
eid = create(type='TASK', title='fix bug', project='web-ui', appetite_seconds=1800)

# Update status
update_status(eid, 'RUNNING')
update_status(eid, 'DONE', proof_sha='abc123')
update_status(eid, 'FAILED', error='timeout')

# Track events
append_trace(eid, {'event': 'started', 'worker': 'frontend-eng'})

# Retry handling
retry_count, max_retries = increment_retry(eid)

# Timeout detection (finds RUNNING tasks that exceeded appetite)
timed_out = check_timeout()

# Human escape: 2 consecutive blocks OR 3 crashes
triggered, info = human_escape_check()  # {'blocks': 0, 'failures': 0}

# Stats
s = stats()  # {'total': 5, 'by_status': {'PENDING': 5}, 'timeouts': 0, ...}
```

## Pipeline Tick

`~/.hermes/scripts/pipeline_tick.py` connects brain_task_orchestrator with envelope_bus:

```bash
# Run one tick
python3 pipeline_tick.py tick

# Check stats
python3 pipeline_tick.py stats
```

Tick logic:
1. Check human escape threshold (2 blocks or 3 crashes → pause)
2. Read dispatchable tasks from brain_task_orchestrator
3. Create envelopes for new tasks (dedup by title)
4. Handle timed-out envelopes (retry or fail)
5. Return stats

## Cron Setup

```
cronjob(action='create', name='pipeline-tick-hourly', 
        schedule='every 1h', script='pipeline_tick.py tick',
        model={'model': 'mimo-v2.5-pro', 'provider': 'xiaomi'})
```

## Numeric Guardrails

| Parameter | Default | Source |
|-----------|---------|--------|
| appetite_seconds | 1800 (30min) | Shape Up methodology |
| max_retries | 3 | hermes-pipeline pattern |
| human_escape | 2 blocks / 3 crashes | safety valve |
| max_runtime | 3600s | per-task ceiling |
| lease_ttl | 900s | worker claim validity |
| heartbeat_interval | 120s | worker heartbeat |

These guardrails were 4-model certified (2026-05-10).
