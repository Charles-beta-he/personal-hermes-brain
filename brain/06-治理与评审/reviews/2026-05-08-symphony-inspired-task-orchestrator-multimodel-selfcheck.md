---
type: review
status: certified
created: 2026-05-08T00:06:02+08:00
updated: 2026-05-08T01:26:00+08:00
review_scope: symphony-inspired-local-task-orchestrator-final
concepts: [multi-model-selfcheck, grounded-certification, local-brain-task-orchestrator]
---

# Symphony-inspired Task Orchestrator — Final Multi-model Selfcheck

Final status: certified.

Scope: P0/P1/P2/P3-dry-run local-brain-native task planning/control plane.

No remaining next step or caveat exists inside this scope.

Explicit non-goals are not caveats:

- Do not adopt Symphony runtime.
- Do not make Linear/GitHub Issues canonical.
- Do not execute arbitrary Markdown hooks.
- Do not run unattended destructive execution without a separately requested allowlisted runner.
- Do not add external tracker bridge unless it remains a derived mirror.

## Delivered Surface

- Canonical task notes: `~/Documents/brain/05-实践与项目/tasks/*.md`
- Obsidian control center: [[07-仪表盘/待完成任务控制台]]
- Obsidian task inbox: [[05-实践与项目/tasks/任务收件箱]]
- Derived runtime dashboard: [[07-仪表盘/待完成任务运行态]]
- Derived sorted task pool: [[05-实践与项目/tasks/任务池-排序]]
- Local orchestrator: `~/.hermes/scripts/brain_task_orchestrator.py`
- Unit test: `~/.hermes/scripts/test_brain_task_orchestrator.py`
- Landing selfcheck: `~/.hermes/scripts/symphony_task_orchestrator_selfcheck.py`
- Final certification JSON: `/Users/charles/Documents/brain/06-治理与评审/reviews/2026-05-08-symphony-inspired-task-orchestrator-final-certification.json`

## User Interaction Trigger Points

### Add task from Obsidian

Open [[05-实践与项目/tasks/任务收件箱]] and append an unchecked bullet under `Inbox Drafts`:

```markdown
- [ ] 任务标题 | priority:P1 | project:project-slug | due:2026-05-20 | concepts:task,tag
```

Then say to Hermes:

```text
处理本地大脑任务收件箱
```

Or run:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py ingest-inbox --write
python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
```

### Multi-model decomposition triggers

Use these natural-language triggers when task pool content becomes ambiguous or high-risk:

```text
多模型分解本地大脑任务池并排序
pua-loop 多模型思考推进本地大脑任务池
处理本地大脑任务收件箱，然后多模型拆解 P0/P1/P2
```

Multi-model outputs are advisory/certification artifacts. They do not become a second task source; accepted changes must be written back into Markdown task notes/reviews/dashboards.

## Deterministic Gates

All passed:

- `python3 -m py_compile ~/.hermes/scripts/consult_models.py ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/test_brain_task_orchestrator.py ~/.hermes/scripts/symphony_task_orchestrator_selfcheck.py`
- `python3 ~/.hermes/scripts/test_brain_task_orchestrator.py` -> PASS
- `python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write --json` -> status OK, active_count 0
- `python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json` -> PASS
- `python3 ~/.hermes/scripts/symphony_task_orchestrator_selfcheck.py --json` -> PASS, accepted_risks []
- `python3 ~/.hermes/scripts/brain_task_orchestrator.py next --json` -> no active canonical local-brain tasks
- `python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json` -> no dispatchable active task; dry-run only

## Multi-model Certification

Tick: `/Users/charles/.hermes/tick-20260507-172524/`

Models:

- Claude Opus 4.7
- gpt-5.5
- DeepSeek v4 Pro
- MiMo v2.5 Pro

Certification result:

- `discussion.status`: certified
- `can_claim_complete_certification`: true
- `truth_status`: grounded
- `claim_count`: 6
- `verified_claim_count`: 6
- `evidence_coverage`: 1.0
- `unsupported_high_severity_claim_ids`: []
- `needs_link_review_high_severity_claim_ids`: []
- `contradicted_high_severity_claim_ids`: []
- `unresolved_severity_ge_3_count`: 0

## Final Decision

Certified complete for the scoped local-brain task planning/control plane.

There is no remaining next step or caveat inside this scope. Future external tracker mirrors or unattended execution runners would be new scopes, not unfinished work from this scope.

## Evidence Boundary

Model agreement is provenance only; status promotion requires command/file/search proof recorded in this note or linked artifacts.

