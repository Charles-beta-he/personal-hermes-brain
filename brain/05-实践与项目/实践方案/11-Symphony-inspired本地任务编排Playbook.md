---
type: playbook
layer: L2
status: active
created: 2026-05-08T00:06:02+08:00
concepts: [symphony-inspired, task-orchestration, pua-loop, reconcile-before-dispatch]
---

# Symphony-inspired 本地任务编排 Playbook

## Trigger

Use when the user says: `待完成任务规划`, `本地大脑任务队列`, `pua-loop落地`, `自动执行 backlog`, `Symphony 借鉴`, or when a long-running Hermes loop needs a safe task control plane.

## Control Loop

```
observe -> reconcile -> select -> claim -> execute -> verify -> record proof -> release/archive -> dashboard
```

### 1. Observe

- Read [[05-实践与项目/tasks/00-tasks索引]].
- Parse task-note frontmatter from `05-实践与项目/tasks/*.md`.
- Treat missing `expires_at` as governance warning, not automatic deletion.

### 2. Reconcile before dispatch

- Release expired claims where `claim_expires_at < now`.
- Move over-retried tasks to `blocked` or `review`.
- Regenerate [[07-仪表盘/待完成任务运行态]].
- Never start new work before reconciliation.

### 3. Select

Selection order:

1. status in active set: `pending`, `retry`.
2. no active claim.
3. `next_attempt_at <= now` when retrying.
4. priority ascending: P0 before P1 before P2.
5. oldest `created` first.
6. bounded by workflow `max_concurrent` and model/tool budget.

### 4. Claim

Write a lease before any execution:

```yaml
status: claimed
claimed_by: hermes
claim_expires_at: 2026-05-08T01:00:00+08:00
run_id: symphony-task-orchestrator-<timestamp>
```

If a claim already exists and is not expired, skip the task. Owner consciousness means preventing duplicate work, not racing yourself.

### 5. Execute

- Load project-specific workflow contract if present.
- Work only in the task/project allowed paths.
- Use isolated worktree/workdir for code work.
- High-risk design or self-evolution routes to T2/T3 multi-model review.
- If blocked by missing credential/permission, write a blocker note and release/mark review.

### 6. Verify

Minimum gates:

- deterministic command output for changed scripts/docs/indexes;
- `brainctl sync`, `brainctl reindex`, and representative `brainctl search` for local-brain changes;
- self-check script for this project;
- multi-model review only counts as certification when ratification/truth gate passes.

### 7. Record proof

Append to the task log:

- command run;
- timestamp;
- exit code/status;
- observed output summary;
- evidence links;
- unresolved risks or accepted risks.

### 8. Release/archive

- On success: `status: done` or archive according to expiry policy.
- On retryable failure: `status: retry`, increment `retry_count`, set `next_attempt_at`.
- On non-retryable blocker: `status: review` or `blocked`, write exact unblock condition.

## PUA Loop Quality Bar

You are not allowed to call the loop done until:

- self-check PASS;
- sync/reindex/search proof exists;
- severity >=3 model issues are resolved or accepted as explicit non-blocking risk;
- stale/duplicate task state is not introduced;
- scoped local commit exists when files changed.

## Failure Modes

| Failure | Signal | Response |
|---|---|---|
| Second source of truth | Linear/GitHub has state not reflected in Markdown | Treat external state as derived; update Markdown or stop |
| Ghost WIP | task has no expiry/terminal state | add expiry/status or move to review |
| Hook overreach | note attempts to run arbitrary shell | reject unless allowlisted in workflow contract |
| Model agreement without evidence | no discussion_result/truth gate | record as provenance only |
| Dashboard drift | dashboard manually edited as truth | regenerate from task notes; dashboard is derived |

## Related Artifacts

- [[05-实践与项目/projects/symphony-inspired-local-task-orchestrator/Project - Symphony-inspired Local Task Orchestrator]]
- [[08-模板/local-brain-task-note-template]]
- [[08-模板/task-workflow-contract-template]]
- [[07-仪表盘/待完成任务运行态]]
