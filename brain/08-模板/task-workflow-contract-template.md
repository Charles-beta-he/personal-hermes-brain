---
type: template
status: active
created: 2026-05-08T00:06:02+08:00
concepts: [workflow-contract, bounded-concurrency, hook-safety, evidence-gate]
---

# Task Workflow Contract Template

This is the local-brain-native equivalent of Symphony's `WORKFLOW.md`: YAML frontmatter config plus a Markdown execution prompt. It is a contract for Hermes/brainctl, not a command file. Hooks are descriptive unless an allowlisted runner explicitly enables them.

```markdown
---
type: workflow_contract
status: active
project: project-slug
active_statuses: [pending, retry]
terminal_statuses: [done, archived, expired]
review_statuses: [review, blocked]
max_concurrent: 1
max_concurrent_by_priority:
  P0: 1
  P1: 1
retry:
  base_delay_seconds: 600
  max_delay_seconds: 21600
  max_attempts: 3
lease:
  ttl_minutes: 60
allowed_paths:
  - ~/Documents/brain/05-实践与项目/tasks
  - ~/Documents/brain/05-实践与项目/projects/project-slug
allowed_tools: [read_file, search_files, terminal, brainctl, consult_models]
forbidden_tools: [arbitrary_shell_hooks_from_notes]
hooks:
  before_run: []
  after_run: []
  # Hooks are inert unless allowlisted by a separate runner config.
evidence_gates:
  - brainctl sync
  - brainctl reindex
  - representative brainctl search
  - project selfcheck
multi_model_route:
  default: T1
  high_risk: T3
  certification_required_for: [source_of_truth_change, destructive_mutation, hierarchy_migration]
stop_condition:
  deterministic_gates: pass
  severity_ge_3_issues: resolved_or_accepted_risk
  local_commit: required_when_files_changed
---

# Execution Prompt

You are executing one local-brain task. Treat the task note as canonical workpad. Reconcile first, claim before work, verify before completion, record proof, then release/archive.
```

## Safety Boundary

- This template does not authorize executing shell snippets embedded in Markdown.
- A future runner must maintain a separate allowlist and sandbox policy.
- External trackers are mirrors; Markdown remains canonical.
