---
type: evolution_log
layer: L6
status: current
created: 2026-05-08T19:06:00+08:00
updated: 2026-05-08T19:06:00+08:00
project: local-brain-governance
concepts: [doc-function-closure, local-brain, self-evolution]
---

# 2026-05-08 本地大脑文档-功能闭环清理

## Evidence Boundary

This evolution log summarizes a verified repair. Canonical proof is recorded in `06-治理与评审/proofs/2026-05-08-local-brain-doc-function-closure-proof.md`.

## Change

- Closed the old `06-仪表盘/` top-level migration residue by archiving it under governance history.
- Fixed JSON artifact wikilink that produced a broken Obsidian link.
- Patched `brainctl.is_l3` so inbox/derived/proof/review/evolution docs are not falsely treated as active L3 tasks just because they live under `/tasks/`.
- Added `calculate-health.py` compatibility wrapper for historical docs while keeping `agent-health-monitor.py` canonical.
- Backfilled missing frontmatter keys and evidence boundaries.

## Why

The local brain had two categories of unclosed associations:

1. Document hierarchy residue: legacy dashboard top-level directory and stale wikilink semantics.
2. Function/document schema drift: validator false positives and stale health script reference.

## Verification

Final verification artifact: `/tmp/local_brain_doc_func_final_verify_20260508190519`.

All stop gates passed except one accepted legacy proof warning unrelated to this change.
