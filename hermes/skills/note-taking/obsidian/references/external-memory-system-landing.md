# External memory/retrieval system landing into the local brain

Use this when evaluating or landing an external memory, RAG, knowledge graph, retrieval, or agent-memory project into the canonical local brain.

## Principle

Do not promote an external memory runtime into the source of truth by default. For this user, `~/Documents/brain` remains the canonical Markdown vault; vector DBs, Chroma/SQLite indexes, KG tables, and external project caches are derived and rebuildable unless explicitly decided otherwise.

## Landing pattern

1. Evidence-first audit:
   - Pin upstream URL and commit/hash.
   - Read core docs and implementation files for data model, CLI side effects, LLM/network behavior, embedding defaults, source adapters, and export/rollback paths.
   - Record risks around second source of truth, lossy summaries, stale facts, external API calls, and language/embedding quality.
2. P10 decision:
   - Prefer methodology extraction over runtime adoption.
   - State invariants: Markdown vault is canonical; derived indexes are disposable; no direct `init`/migration on the vault.
   - If the external tool has a global data/cache path flag, require it before subcommands in examples and use `/tmp` or another isolated path.
3. Local-brain artifact package:
   - `20-projects/<project>/Project - ...md`
   - `20-projects/<project>/P10 - Long-term Strategy.md`
   - `20-projects/<project>/P9 - Implementation Backlog.md`
   - `08-实践方案/<playbook>.md`
   - `60-reviews/<date>-...-multimodel-selfcheck.md`
   - `30-tasks/<date>-...-landing-log.md` with `expires_at`
   - `05-进化日志/<date>-....md`
   - atoms for durable principles such as evidence boundary and model-authority caveats.
4. Deterministic self-check:
   - Add a local-first stdlib script under `~/.hermes/scripts/<project>_selfcheck.py`.
   - Check required files, required phrases/contracts, broken wikilinks, empty dirs, top-level MOCs, hollow parents, and narrow secret patterns.
   - The script must not call external LLMs, network APIs, or run destructive/import commands against the canonical vault.
5. Verification loop:
   ```bash
   python3 ~/.hermes/scripts/<project>_selfcheck.py --json
   python3 ~/.hermes/scripts/brainctl.py --json sync
   python3 ~/.hermes/scripts/brainctl.py --json reindex
   python3 ~/.hermes/scripts/brainctl.py --json search "<project key phrase>" --limit 8
   python3 ~/.hermes/scripts/brainctl.py --json search "<principle key phrase>" --limit 8
   ```
6. Proof ledger:
   - Append observed sync/reindex/search/self-check outputs to the task log.
   - Run sync/reindex/self-check again after proof edits, because proof edits change the index.
7. Git hygiene:
   - If `~/Documents/brain` is not a git repo but sync mirrors it under `~/.hermes/notes/brain`, commit the scoped mirror files plus any self-check script in `~/.hermes`.
   - Do not include unrelated dirty files, credentials, caches, or screenshots.

## Multi-model caveat

If `consult_models.py --discussion` times out, returns invalid JSON from a reviewer, or produces `not_certified`, record that status in `60-reviews/`. Use the seed plans as provenance only. P10 closure can still pass if deterministic local gates pass and the strategy does not depend on model agreement.

## Pitfalls

- A search query that mixes too many English/Chinese terms may miss a newly indexed atom even when indexing is healthy. Verify with narrower representative queries for each artifact class.
- Secret scanners should be narrow enough to avoid false positives like `task-log-template`; prefer key-family-specific patterns such as `sk-proj-...`, `ghp_...`, `AKIA...`, and private-key headers.
- Never write real API keys into notes. If credentials appear in source material, redact as `[REDACTED]`.
