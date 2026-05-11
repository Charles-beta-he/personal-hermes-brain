---
type: model-review
status: fanout_completed_discussion_timeout
created: 2026-05-06T07:41:43Z
tick_dir: /Users/charles/.hermes/tick-20260506-073039
state_file: /tmp/hermes-brain-hierarchy-mm-state.json
models:
  - claude-opus-4-7
  - gpt-5.5
  - deepseek-v4-pro
  - mimo-v2.5-pro
---

# Multi-model review - Hermes brain hierarchy

## Scope

Question: design Hermes/Obsidian local brain memory hierarchy and absorb OpenAI Symphony/Codex orchestration ideas into Hermes self-evolution.

## Certification status

Four-model seed fanout completed. `consult_models.py --discussion` timed out during consensus before discussion ratification completed. Treat this as multi-model input, not full certification.

Artifact directory:

`/Users/charles/.hermes/tick-20260506-073039`

## Shared conclusions

- Keep `/Users/charles/Documents/brain` as canonical markdown vault.
- Keep `/Users/charles/.hermes/memory/index.sqlite` as derived/rebuildable index.
- Do not put WIP/session-local task state into Hermes durable memory.
- Separate evidence, atomic notes, project knowledge, task state, skills/procedures, preferences, and model reviews.
- Additive evolution only: do not break existing `brainctl.py status/search/evidence/wal/sync/reindex` or `sync-brain.py`.
- Absorb Symphony as governance primitives: task state machine, per-task workspace, workflow contract, proof-of-work, observability.

## Planner highlights

Claude emphasized typed vault layers, frontmatter schemas, mandatory expiry for task state, and additive `brainctl` commands.

GPT-5.5 emphasized verifier gaps, evidence-first claims, SQLite-only drift guards, and routing policy between Obsidian/Hermes memory/skills/index.

DeepSeek emphasized documenting the hierarchy before implementation and mapping Symphony concepts without replacing Hermes runtime.

MiMo emphasized simple 7-layer spec, governance config, artifact routing table, and incremental `brainctl` extensions.

## Accepted design

See `[[Hermes Local Brain Memory Hierarchy]]`.

## Open risks

- Discussion ratification timed out; if this becomes code changes, run another bounded multi-model review with evidence bundle.
- Obsidian official CLI is installed but requires manual app setting toggle: Settings > General > Advanced > Command line interface.
- Future `brainctl` extensions must be additive and dry-run by default.

## Evidence Boundary

- Added by backlog-zero loop at `2026-05-06T13:32:29Z`.
- This review is provenance, not truth proof. Its claims may support promotion only when linked tool/file/search evidence is satisfied.
- Model agreement, dissent, timeout, or not_certified labels must remain visible; do not treat review consensus as deterministic evidence.
