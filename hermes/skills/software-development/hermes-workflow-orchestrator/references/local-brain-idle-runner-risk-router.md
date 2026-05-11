# Local-brain idle-runner risk router — fail-closed notes

Use when adding or reviewing any idle/autorun/background runner for the local brain task pool.

## Core invariant

An idle detector is not an executor. Default behavior must be observe-only:

- no Markdown task-body execution
- no claim mutation
- no done/retry/review transition
- optional state writes may only write detector artifacts, never task notes
- kill switch default disabled (`HERMES_LOCAL_BRAIN_IDLE_RUNNER != 1`)

## Active/busy detection pitfall

Do not duplicate a partial status set. The task orchestrator treats these as claim-bound:

- `claimed`
- `running`
- `review`

A detector that only checks `claimed/running` can incorrectly schedule another handoff while a task is waiting in `review` with a live lease.

Also fail closed on partial lease metadata, even if status is `pending`:

- `claimed_by`
- `claim_expires_at`
- `run_id`

If `list --json` rows omit a metadata field (notably `run_id` in one session), merge from task frontmatter before making the idle decision, or extend the canonical row schema and add tests. A compact detector-side guard is:

```python
def frontmatter_or_row(row, fm, key):
    value = row.get(key)
    if value is not None and value != "":
        return value
    return fm.get(key)
```

Use it for `claimed_by`, `claim_expires_at`, and `run_id` before computing `active_count` / `next_action`; then assert `pending + run_id + pending candidate` yields `active_count > 0` and `next_action == "observe_only"`.

## Required adversarial tests

For an idle runner, include regression tests for:

1. default disabled/read-only: pending task remains pending, `next_action=observe_only`
2. enabled but active `claimed` lease: blocks handoff
3. enabled but active `review` lease plus separate pending candidate: blocks handoff
4. pending task with only `run_id` metadata plus separate pending candidate: blocks handoff
5. high-risk task (`P0`, delete/deploy/secret/token/password keywords): manual gate
6. scalar `blocked_by`: DAG blocker
7. multiline `blocked_by`: DAG blocker
8. `--write-state`: task Markdown before/after bytes unchanged
9. subprocess diagnostics: redact `api_key`, `token`, `secret`, `password`, `passwd`, `proxy`, `auth_token`, `ct0`, and common auth headers if surfaced

## Verification bundle

```bash
python3 -m py_compile ~/.hermes/scripts/brain_task_idle_runner.py ~/.hermes/scripts/test_brain_task_idle_runner.py
python3 ~/.hermes/scripts/test_brain_task_idle_runner.py
python3 ~/.hermes/scripts/test_brain_task_orchestrator.py
python3 ~/.hermes/scripts/test_brain_task_dispatch_tick.py
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
git -C ~/.hermes diff --cached --check
```

## Review gate

After any reviewer-requested hardening, the previous review verdict no longer covers the final diff. Rerun deterministic gates and a final scoped adversarial review before committing.
