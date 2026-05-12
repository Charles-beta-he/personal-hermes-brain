---
type: skill-mirror
layer: L4
status: active
created: 2026-05-06T08:10:29Z
canonical_skill: /Users/charles/.hermes/skills/note-taking/obsidian/SKILL.md
---

# Skill mirror: Obsidian sync and brain routing

Canonical operational source is the Hermes skill:

```text
/Users/charles/.hermes/skills/note-taking/obsidian/SKILL.md
```

This vault note is only a human-visible mirror/index card.

## Current routing rules

- Use `/Users/charles/Documents/brain` as canonical vault.
- Use `brainctl.py --json status/search/evidence/wal/sync/reindex` as primary control plane.
- Treat `~/.hermes/memory/index.sqlite` as rebuildable derived index.
- Sync Hermes notes through `sync-brain.py` into `99-hermes-notes/`.
- Skip only `~/.hermes/notes/brain/` mirror subtree; do not skip normal filenames containing `brain`.

## Verification commands

```bash
python3 ~/.hermes/scripts/brainctl.py --json status
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 /Users/charles/.hermes/scripts/test_sync_brain.py -v
```

Related:

- [[Obsidian Setup - Hermes Local Brain]]
- [[Hermes Local Brain Memory Hierarchy]]
