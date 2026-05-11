---
type: template
status: active
created: 2026-05-11T20:26:00+08:00
concepts: [mission-artifact, opord, local-first, knowledge-graph, evidence-bundle]
---

# Mission Artifact Template

This template defines the canonical Markdown format for Mission notes in the
Hermes local-brain vault. Missions are persistent, inspectable, local-first
knowledge-graph nodes — not transient session state.

OPORD mapping: Situation → context, Mission → objective, Execution → plan/dag,
Sustainment → dependencies/resources, Command-Control → gates/handoff/escalation.

```markdown
---
type: mission
status: proposed  # proposed|active|paused|completed|abandoned
priority: P1
created: YYYY-MM-DDTHH:MM:SS+08:00
updated: YYYY-MM-DDTHH:MM:SS+08:00
project: project-slug
mission_id: mission-<short-slug>
mission_title: <one-line title>
layer: L3
workflow_contract: [[08-模板/task-workflow-contract-template]]
parent_mission:          # optional: [[link to parent mission]]
child_missions: []       # optional: [[links to child missions]]
depends_on: []           # mission_ids this blocks on
concepts: [mission]
---

# Mission: <title>

## 1. Situation (SITUATION)

<What is the current state of the world? What problem or opportunity exists?
What constraints and context does the commander need to understand?>

Key facts:
- <fact 1>
- <fact 2>

## 2. Mission (MISSION)

### Objective
<What must be true when this mission is complete?>

### Commander's Intent
<The single most important thing to achieve, even if all else fails.>

### End State
<Observable description of "done".>

### Constraints
- <constraint 1>
- <constraint 2>

### Red Lines
- <must not do X>
- <must not do Y>

### Non-Goals
- <explicitly out of scope>

## 3. Execution (EXECUTION)

### Concept of Operations
<High-level approach.>

### DAG Nodes / Tasks
| Node | Description | Status | Depends On |
|------|-------------|--------|------------|
| node-1 | <desc> | pending | — |
| node-2 | <desc> | pending | node-1 |

### Checkpoints
- [ ] checkpoint-1: <what must be true>
- [ ] checkpoint-2: <what must be true>

## 4. Sustainment (SUSTAINMENT)

### Dependencies
- <tool/script/service needed>
- <data source>

### Resources
- <time budget, compute, model tokens>

### Evidence Manifest
| Evidence ID | Path / URI | SHA-256 | Type | Created |
|-------------|-----------|---------|------|---------|
| ev-001 | file:/path/to/evidence.json | <hash> | command-output | YYYY-MM-DD |
| ev-002 | file:/path/to/screenshot.jpg | <hash> | screenshot | YYYY-MM-DD |

## 5. Command & Control (COMMAND_CONTROL)

### Permission Gates
- [ ] gate-1: <what must pass before proceeding>
- [ ] gate-2: <what must pass before completion>

### Handoff Artifacts
- artifact:<name> — <what it contains>

### Proof Artifacts
- artifact:<name> — <what it proves>

### Rollback Signal
<How to detect this mission has gone wrong and needs rollback.>

### Escalation Path
<When/how to escalate to human or multi-model review.>

## 6. Proof Log

- YYYY-MM-DDTHH:MM:SS+08:00: Mission created.
- YYYY-MM-DDTHH:MM:SS+08:00: <action>, <result>, <evidence link>

## 7. Run Log

| Run ID | Started | Ended | Status | Artifacts |
|--------|---------|-------|--------|-----------|
| run-001 | YYYY-MM-DD | YYYY-MM-DD | pass | <links> |

## 8. Decision Log

| Date | Decision | Rationale | Alternatives Rejected |
|------|----------|-----------|----------------------|
| YYYY-MM-DD | <decision> | <why> | <what else was considered> |

## 9. Knowledge Graph Links

Extracted entities and relations from this mission are stored in
`~/.hermes/state/kg_graph.sqlite` and can be queried with:
  python3 ~/.hermes/scripts/kg_entity_extractor.py query

### Entity Links
- [[related-note-1]] — relation_type
- [[related-note-2]] — relation_type

## Final Handoff

- Status:
- Evidence:
- Residual risk:
```

## Rules

1. Mission notes are canonical data, not executable scripts.
2. Evidence paths must point to real files; SHA-256 hashes enable tamper detection.
3. SQLite/FTS/graph indices are derived caches — rebuildable from canonical Markdown.
4. Each mission is a knowledge-graph node: link to related notes, projects, people.
5. The proof log is append-only; never rewrite history.
6. Sidecar evidence manifest (`.evidence.json`) lives next to the mission note
   in the project's `evidence/` directory.
7. Mission status transitions: proposed → active → completed/abandoned.
   Paused is allowed for blocked missions.
8. DAG nodes track granular task progress within a mission.
9. Decision log captures why, not just what — enables future reasoning replay.
10. Run log links to execution artifacts (session IDs, tick dirs, proof bundles).
