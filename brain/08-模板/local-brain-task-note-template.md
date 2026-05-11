---
type: template
status: active
created: 2026-05-08T00:06:02+08:00
concepts: [task-note, lease, retry, evidence]
---

# Local Brain Task Note Template

```markdown
---
type: task
layer: L3
status: pending # proposed|pending|claimed|running|retry|review|blocked|done|archived|expired
priority: P1 # P0|P1|P2|P3
created: YYYY-MM-DDTHH:MM:SS+08:00
updated: YYYY-MM-DDTHH:MM:SS+08:00
expires_at: YYYY-MM-DDTHH:MM:SS+08:00
project: project-slug
workflow_contract: [[08-模板/task-workflow-contract-template]]
claimed_by:
claim_expires_at:
run_id:
retry_count: 0
next_attempt_at:
workspace:
evidence: []
concepts: [task]
---

# Task - <short title>

## Objective

<What must be true when this task is done.>

## Acceptance Criteria

- [ ] <observable criterion>
- [ ] <verification command/search/evidence link>

## Plan / Workpad

- [ ] Step 1
- [ ] Step 2

## Validation

| Command / Check | Status | Evidence |
|---|---|---|
|  | pending |  |

## Proof Log

- <timestamp>: <action>, <output summary>, <link>

## Blockers / Confusions

- None.

## Final Handoff

- Status:
- Evidence:
- Residual risk:
```

## Rules

- The note is the persistent workpad for this task.
- Do not create a second progress source unless it links back here.
- If the task is WIP, it must have `expires_at` or a terminal status.
- `claim_expires_at` is a lease, not ownership forever.
- Completed tasks keep proof links but must not be injected into future prompts as current state.
