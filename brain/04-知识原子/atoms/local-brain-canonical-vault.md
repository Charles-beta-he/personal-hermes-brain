---
type: atom
layer: L1
status: active
created: 2026-05-06T08:10:29Z
evidence:
  - ../02-证据与原文/evidence/2026-05-06-symphony-source-and-obsidian-cli-evidence.md
---

# Local brain canonical vault

The canonical human-readable local brain is:

```text
/Users/charles/Documents/brain
```

SQLite, FTS, embeddings, and WAL are derived/rebuildable layers. They may be used for retrieval and automation, but Markdown notes in the vault remain the source of truth.

Operational split:

- Obsidian.app = human visualization/editor.
- `brainctl.py`, `sync-brain.py`, cron, skills, and Hermes memory = agent control plane.

Related:

- [[Hermes Local Brain Memory Hierarchy]]
- [[Obsidian Setup - Hermes Local Brain]]
