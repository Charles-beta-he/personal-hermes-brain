# Kanban Watch + Local Taskpool Bridge Advisory

Use this when evaluating whether `hermes kanban watch` helps an existing non-Kanban task management system (for example a local-brain Markdown taskpool).

## Key distinction

`hermes kanban watch` is an observability surface, not a task-management controller.

Observed CLI/help behavior:

```bash
hermes kanban watch --help
# Live-stream task_events to the terminal
# filters: --assignee, --tenant, --kinds, --interval
```

Observed implementation shape in `hermes_cli/kanban.py`:
- initializes cursor at `SELECT COALESCE(MAX(id), 0) FROM task_events`
- loops over `SELECT ... FROM task_events e LEFT JOIN tasks t ... WHERE e.id > ?`
- filters by event kind / assignee / tenant
- prints events and sleeps
- performs no task writes, no scheduling, no claim/complete/block transitions

Therefore: Watch helps humans and scripts see board activity, blocked/crashed/timed-out workers, and completion events. It does not create tasks, dispatch workers, or advance status.

## Adoption decision pattern

1. Check whether the Kanban board has signal before recommending Watch:

```bash
hermes kanban boards list --json
hermes kanban stats --json
```

If the board is empty, Watch has little immediate value until tasks are created or mirrored into Kanban.

2. Check the existing source-of-truth task system health before recommending replacement:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
```

If it passes, keep it as source-of-truth unless there is explicit migration evidence.

3. Recommend a staged approach:

- P0: use Watch only for live observability on actual Kanban pilot tasks.
- P1: add a one-way bridge from the current taskpool to Kanban for visibility/audit only. Requirements: stable idempotency key, duplicate protection, kill switch, and no reverse status writes.
- P2: consider dispatcher/source-of-truth migration only after measured pilot gains and fail-closed proof gates.

## Safe Watch commands

```bash
hermes kanban watch --kinds completed,blocked,crashed,timed_out,gave_up --interval 1
hermes kanban watch --assignee frontend-eng --kinds completed,blocked,crashed,timed_out,gave_up --interval 1
```

Do not assume `watch` has JSON output unless the installed version's help explicitly shows it. For automation, prefer a dedicated read-only event query, notify subscription, dashboard/WebSocket API, or a small bridge script with schema tests.

## Fail-closed boundaries

- Do not let `kanban watch` output mark a local-brain task done.
- Do not replace `brain_task_orchestrator.py` just because Kanban has a durable board.
- Do not enable bidirectional sync without conflict resolution, idempotency, and proof-check integration.
- Keep work-lane priority: Kanban/evolution pilots must not starve active product/work tasks.
- Treat model fanout without all expected participants (for example MiMo adapter failure) as advisory, even if truth evidence is grounded.
