# Local-brain adoption audit for AI memory repos

Use this when evaluating an AI memory / RAG / MCP memory repository for the user's canonical local brain (`~/Documents/brain`). The goal is not just "is the repo good?" but "does it improve the Obsidian/Hermes local-brain hierarchy without creating a second source of truth?"

## Minimum workflow

1. Fixed upstream evidence
   - Clone with a pinned commit SHA.
   - Record branch, version, file count, size, license, and current GitHub signals.
   - Read README, package metadata, architecture files, MCP/tool surface, and benchmark methodology.

2. Inspect the user's current local-brain shape before judging fit
   - `python3 ~/.hermes/scripts/brainctl.py --json status`
   - List top-level directories and markdown counts under `~/Documents/brain`.
   - Read `~/Documents/brain/00-索引/00-大脑索引.md` when mapping hierarchy.
   - Treat `~/Documents/brain` Markdown as canonical unless the user explicitly says otherwise.

3. Recompute committed benchmark headline numbers when possible
   - For JSONL result files, inspect whether metrics are embedded under each row, e.g. `retrieval_results.metrics.session.recall_any@5`.
   - Distinguish retrieval recall / evidence hit / session hit from end-to-end QA accuracy.
   - Flag doc drift when README claims differ from committed result files or methodology notes.

4. Map external concepts to local-brain layers
   - L0 identity / hard constraints → `00-system`, `50-prefs`.
   - L1 essential story / wake-up context → `00-索引`, `06-仪表盘`.
   - L2 on-demand topic context → folder MOCs (`00-xxx索引.md`).
   - L3 deep search → `brainctl search`, derived indexes, full-text/evidence search.
   - Verbatim evidence/drawers → `00-evidence`, `09-引用原文`, `99-hermes-notes`.
   - MOCs/closets → compressed pointers only; never the fact source.
   - Temporal KG → valid_from/valid_to facts for prefs, project state, tasks, reviews.
   - Tunnels/graphs → cross-domain bridge matrix linking theory → practice → project → evidence.

5. Adoption decision default
   - Prefer selective extraction/Hermes-native implementation over whole-system adoption.
   - Never let a Chroma/vector palace, RAG DB, or memory server become canonical for the local brain without an explicit user decision.
   - If trialing, use an isolated sample copy and isolated storage path. Do not run repo init/mine directly on `~/Documents/brain` until side effects are understood.

## Common useful outputs

- Decision: adopt / selective / reject.
- Score with the framework-audit rubric.
- What improves the local-brain hierarchy vs what only improves retrieval.
- Source-of-truth boundary: Markdown canonical; external index derived/rebuildable.
- Safe pilot commands with isolated paths.
- Risks: duplicate memory stack, stale index, metric mismatch, multilingual retrieval unknowns, external API/privacy defaults.

## Pitfalls

- Do not equate better retrieval recall with better knowledge structure. Local brain also needs atoms, reviews, theory mapping, evidence boundaries, and task/project lifecycle.
- Do not let auto-generated tags/rooms rewrite the user's curated Obsidian hierarchy.
- For Chinese-heavy vaults, do not assume English benchmark performance transfers. Require a Chinese query A/B test against `brainctl search` / grep / existing indexes.
- If a tool advertises "verbatim" plus a lossy index/compression layer, verify the lossy layer points back to original evidence and is not used as the canonical fact.