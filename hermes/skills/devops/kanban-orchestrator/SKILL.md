---
name: kanban-orchestrator
description: Use when you need guidance on decomposition playbook + specialist-roster conventions + anti-temptation rules for an orchestrator profile routing work through Kanban.
version: 2.0.0
author: Hermes Agent
license: MIT
platforms:
- linux
- macos
- windows
metadata:
  hermes:
    tags:
    - kanban
    - multi-agent
    - orchestration
    - routing
    related_skills:
    - kanban-worker
---

# Kanban Orchestrator — Decomposition Playbook

## Overview


> The **core worker lifecycle** (including the `kanban_create` fan-out pattern and the "decompose, don't execute" rule) is auto-injected into every kanban process via the `KANBAN_GUIDANCE` system-prompt block. This skill is the deeper playbook when you're an orchestrator profile whose whole job is routing.

## When to Use

- You need guidance on decomposition playbook + specialist-roster conventions + anti-temptation rules for an orchestrator profile routing work through Kanban
- Don't use for: requests that do not need you need guidance on decomposition playbook + specialist-roster conventions + anti-temptation rules for an orchestrator profile routing work through Kanban; choose a more specific child skill or a broader routing skill that actually matches the task.
## When to use the board (vs. just doing the work)

Create Kanban tasks when any of these are true:

1. **Multiple specialists are needed.** Research + analysis + writing is three profiles.
2. **The work should survive a crash or restart.** Long-running, recurring, or important.
3. **The user might want to interject.** Human-in-the-loop at any step.
4. **Multiple subtasks can run in parallel.** Fan-out for speed.
5. **Review / iteration is expected.** A reviewer profile loops on drafter output.
6. **The audit trail matters.** Board rows persist in SQLite forever.

If *none* of those apply — it's a small one-shot reasoning task — use `delegate_task` instead or answer the user directly.

## The anti-temptation rules

Your job description says "route, don't execute." The rules that enforce that:

- **Do not execute the work yourself.** Your restricted toolset usually doesn't even include terminal/file/code/web for implementation. If you find yourself "just fixing this quickly" — stop and create a task for the right specialist.
- **For any concrete task, create a Kanban task and assign it.** Every single time.
- **If no specialist fits, ask the user which profile to create.** Do not default to doing it yourself under "close enough."
- **Decompose, route, and summarize — that's the whole job.**

## The standard specialist roster (convention)

Unless the user's setup has customized profiles, assume these exist. Adjust to whatever the user actually has — ask if you're unsure.

| Profile | Does | Typical workspace |
|---|---|---|
| `researcher` | Reads sources, gathers facts, writes findings | `scratch` |
| `analyst` | Synthesizes, ranks, de-dupes. Consumes multiple `researcher` outputs | `scratch` |
| `writer` | Drafts prose in the user's voice | `scratch` or `dir:` into their Obsidian vault |
| `reviewer` | Reads output, leaves findings, gates approval | `scratch` |
| `backend-eng` | Writes server-side code | `worktree` |
| `frontend-eng` | Writes client-side code | `worktree` |
| `ops` | Runs scripts, manages services, handles deployments | `dir:` into ops scripts repo |
| `pm` | Writes specs, acceptance criteria | `scratch` |

## Decomposition playbook

### Step 1 — Understand the goal

Ask clarifying questions if the goal is ambiguous. Cheap to ask; expensive to spawn the wrong fleet.

### Step 2 — Sketch the task graph

Before creating anything, draft the graph out loud (in your response to the user). Example for "Analyze whether we should migrate to Postgres":

```
T1  researcher        research: Postgres cost vs current
T2  researcher        research: Postgres performance vs current
T3  analyst           synthesize migration recommendation       parents: T1, T2
T4  writer            draft decision memo                       parents: T3
```

Show this to the user. Let them correct it before you create anything.

### Step 3 — Create tasks and link

```python
t1 = kanban_create(
    title="research: Postgres cost vs current",
    assignee="researcher",
    body="Compare estimated infrastructure costs, migration costs, and ongoing ops costs over a 3-year window. Sources: AWS/GCP pricing, team time estimates, current Postgres bills from peers.",
    tenant=os.environ.get("HERMES_TENANT"),
)["task_id"]

t2 = kanban_create(
    title="research: Postgres performance vs current",
    assignee="researcher",
    body="Compare query latency, throughput, and scaling characteristics at our expected data volume (~500GB, 10k QPS peak). Sources: benchmark papers, public case studies, pgbench results if easy.",
)["task_id"]

t3 = kanban_create(
    title="synthesize migration recommendation",
    assignee="analyst",
    body="Read the findings from T1 (cost) and T2 (performance). Produce a 1-page recommendation with explicit trade-offs and a go/no-go call.",
    parents=[t1, t2],
)["task_id"]

t4 = kanban_create(
    title="draft decision memo",
    assignee="writer",
    body="Turn the analyst's recommendation into a 2-page memo for the CTO. Match the tone of previous decision memos in the team's knowledge base.",
    parents=[t3],
)["task_id"]
```

`parents=[...]` gates promotion — children stay in `todo` until every parent reaches `done`, then auto-promote to `ready`. No manual coordination needed; the dispatcher and dependency engine handle it.

### Step 4 — Complete your own task

If you were spawned as a task yourself (e.g. `planner` profile was assigned `T0: "investigate Postgres migration"`), mark it done with a summary of what you created:

```python
kanban_complete(
    summary="decomposed into T1-T4: 2 researchers parallel, 1 analyst on their outputs, 1 writer on the recommendation",
    metadata={
        "task_graph": {
            "T1": {"assignee": "researcher", "parents": []},
            "T2": {"assignee": "researcher", "parents": []},
            "T3": {"assignee": "analyst", "parents": ["T1", "T2"]},
            "T4": {"assignee": "writer", "parents": ["T3"]},
        },
    },
)
```

### Step 5 — Report back to the user

Tell them what you created in plain prose:

> I've queued 4 tasks:
> - **T1** (researcher): cost comparison
> - **T2** (researcher): performance comparison, in parallel with T1
> - **T3** (analyst): synthesizes T1 + T2 into a recommendation
> - **T4** (writer): turns T3 into a CTO memo
>
> The dispatcher will pick up T1 and T2 now. T3 starts when both finish. You'll get a gateway ping when T4 completes. Use the dashboard or `hermes kanban tail <id>` to follow along.

## Common patterns

**Fan-out + fan-in (research → synthesize):** N `researcher` tasks with no parents, one `analyst` task with all of them as parents.

**Pipeline with gates:** `pm → backend-eng → reviewer`. Each stage's `parents=[previous_task]`. Reviewer blocks or completes; if reviewer blocks, the operator unblocks with feedback and respawns.

**Same-profile queue:** 50 tasks, all assigned to `translator`, no dependencies between them. Dispatcher serializes — translator processes them in priority order, accumulating experience in their own memory.

**Human-in-the-loop:** Any task can `kanban_block()` to wait for input. Dispatcher respawns after `/unblock`. The comment thread carries the full context.

**Watch as observability, not control:** `hermes kanban watch` live-streams `task_events` for humans/operators and supports filters like `--assignee`, `--tenant`, `--kinds`, and `--interval`. It does not schedule, claim, create, complete, or manage tasks. Before recommending it for an existing taskpool, check whether the board has events (`hermes kanban stats --json`) and whether the existing task system is healthy. For local-brain taskpools, keep `brain_task_orchestrator.py` as source-of-truth unless a one-way bridge/migration has explicit gate evidence. See `references/watch-and-local-taskpool-bridge.md`.

**Local-brain taskpool status triage:** When the user asks to “检查任务池任务状态”, use the local-brain taskpool triage checklist in `references/local-taskpool-status-triage.md`: read `brain_task_orchestrator.py list/next/proof-check/selfcheck`, run guardian health, inspect envelope escape/failures separately, and report cron delivery/script-wrapper blockers without treating Kanban watch as canonical.

**Local-brain taskpool system repair:** When a status check finds proof/selfcheck/evidence-spine failures, envelope `human_escape`, summary tick cron errors, or orphan agent-team workers and the user asks to solve them, use `references/local-taskpool-system-repair.md`: normalize task metadata/evidence instead of lowering validators, preserve FAILED envelope audit rows, ack escape only after deterministic gates pass, clean orphan workers/claims carefully, and re-certify current state if using multi-model.

**Local-brain taskpool permission taxonomy:** When checking progress or comparing Lark/product tasks with Hermes self-evolution tasks, use `references/local-taskpool-permission-taxonomy.md`. Explicitly separate lane semantics from stuck-state diagnosis, and enforce the invariant that `--yolo` / `yolo-execution` is the highest command-approval tier but not a task completion proof. Completion still requires lifecycle/evidence/review gates.

**Local-brain auto-completer semantics:** When the user asks whether non-`work` tasks complete automatically, distinguish automatic *progression* from automatic *closure*. `local-brain-taskpool-auto-completer` / `taskpool_dynamic_runner.py` can scan, reconcile, dashboard, dispatch-hint, run bounded allowlisted steps, and opportunistically start multi-model intervention. `brain_task_autorun_step.py` is review-only: successful bounded execution stops at `review`, never `done`. Multi-model intervention writes `multimodel_status` / ratification artifact fields, but does not perform lifecycle `review -> done`. Final closeout still requires the lane-specific proof gate (`project-evidence-review-done`, `ratification-or-selfcheck-review-done`, or `advisory-evidence-review-done`) and a legal lifecycle transition from `review` to `done`.

**4-model certified (2026-05-10):** Kanban Watch was ratified as observability-only by all 4 models (Claude + GPT-5.5 + DeepSeek + MiMo). Decision: one-way bridge from brain_task_orchestrator with kill switch. No auto-done from watch. Full ratification artifact: `~/.hermes/memory/docs/adr/kanban-watch-mm-ratification-v1.json`.

## Common Pitfalls

**`hermes kanban watch` is observability, not orchestration.** Watch live-streams `task_events` for humans and supports filters such as `--assignee`, `--tenant`, `--kinds`, and `--interval`, but it does not claim, dispatch, complete, or mutate tasks. In the current CLI it is a human-readable stream, not a structured `--json` automation API. For automation, use the kanban tools/DB/notify/dashboard surfaces explicitly, and keep source-of-truth transitions proof-gated.

**Kanban create output parsing.** `hermes kanban create` outputs `Created t_xxxx (ready, assignee=xxx)`. Extract the task ID with `re.search(r'Created\s+(t_[a-f0-9]+)', output)`. Do NOT use `output.split()[-1]` — it will capture `assignee=brain-mirror)` instead of the task ID.

**Reassignment vs. new task.** If a reviewer blocks with "needs changes," create a NEW task linked from the reviewer's task — don't re-run the same task with a stern look. The new task is assigned to the original implementer profile.

**Argument order for links.** `kanban_link(parent_id=..., child_id=...)` — parent first. Mixing them up demotes the wrong task to `todo`.

**Don't pre-create the whole graph if the shape depends on intermediate findings.** If T3's structure depends on what T1 and T2 find, let T3 exist as a "synthesize findings" task whose own first step is to read parent handoffs and plan the rest. Orchestrators can spawn orchestrators.

**Tenant inheritance.** If `HERMES_TENANT` is set in your env, pass `tenant=os.environ.get("HERMES_TENANT")` on every `kanban_create` call so child tasks stay in the same namespace.
1. Skipping prerequisite checks and assuming the environment already matches the workflow.
2. Applying the workflow mechanically without confirming that the request still matches this skill's trigger class.
3. Reporting success before reading back the actual outputs, files, or external side-effects.
## Recovering stuck workers

When a worker profile keeps crashing, hallucinating, or getting blocked by its own mistakes (usually: wrong model, missing skill, broken credential), the kanban dashboard flags the task with a ⚠ badge and opens a **Recovery** section in the drawer. Three primary actions:

1. **Reclaim** (or `hermes kanban reclaim <task_id>`) — abort the running worker immediately and reset the task to `ready`. The existing claim TTL is ~15 min; this is the fast path out.
2. **Reassign** (or `hermes kanban reassign <task_id> <new-profile> --reclaim`) — switch the task to a different profile and let the dispatcher pick it up with a fresh worker.
3. **Change profile model** — the dashboard prints a copy-paste hint for `hermes -p <profile> model` since profile config lives on disk; edit it in a terminal, then Reclaim to retry with the new model.

Hallucination warnings appear on tasks where a worker's `kanban_complete(created_cards=[...])` claim included card ids that don't exist or weren't created by the worker's profile (the gate blocks the completion), or where the free-form summary references `t_<hex>` ids that don't resolve (advisory prose scan, non-blocking). Both produce audit events that persist even after recovery actions — the trail stays for debugging.

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

