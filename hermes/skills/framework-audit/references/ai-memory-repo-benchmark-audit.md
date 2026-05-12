# AI Memory Repository Benchmark Audit Notes

Use this reference when evaluating local-first AI memory / RAG / agent-memory repositories that publish recall or benchmark claims.

## Evidence collection checklist

1. Clone and pin the exact commit.
   - Record branch, commit SHA, file count, package metadata, CLI entry points.
2. Read public claims first, then verify against committed artifacts.
   - README benchmark tables.
   - `benchmarks/README.md`, `BENCHMARKS.md`, methodology docs.
   - committed `results_*.json`, `results_*.jsonl`, split files, scripts.
3. Recompute headline numbers from result files instead of trusting docs.
   - Count records.
   - Recompute hit/recall/ndcg averages.
   - Break down by category, not only overall score.
   - Verify held-out result IDs match split files and do not overlap dev IDs.
4. Inspect metric definitions in benchmark scripts.
   - Distinguish retrieval recall / evidence hit from end-to-end QA accuracy.
   - Check whether session-level hit is counted as success without answer-span verification.
   - Check top-k defaults and whether reproduction commands explicitly set them.
5. Audit comparison fairness.
   - Do not compare retrieval recall with another system's QA accuracy as if equal.
   - Flag side-by-side tables that mix metrics, splits, rerankers, or test-time tuning.
   - Treat "100%" claims as suspect unless a full committed result file supports the exact metric.
6. Check product-safety boundaries.
   - Local-first / no-API claims: inspect default provider selection and consent gates.
   - Auto-ingest hooks: assess whether users may silently persist private transcripts.
   - MCP write/delete tools: require policy gates before exposing to autonomous agents.

## Red flags seen in real audits

- README headline numbers are correct, but deeper benchmark docs contain older or more aggressive internal claims.
- "All categories" wording when committed results omit a category.
- Overall score hides weak categories such as noisy / conditional / post-processing cases.
- Reproduction guide omits `--top-k`, while script default differs from the table.
- Held-out results are committed per-question; future tuning against those files contaminates the held-out set.
- A local-first tool defaults to trying local LLM first, but can fall through to external providers if configured; require explicit consent and preferably `--no-llm` for audits.

## Adoption guidance for Hermes-like agents

For full AI memory systems, prefer "selective borrowing" over direct replacement unless the user explicitly wants migration.

Good candidates to borrow:
- query sanitizer for prompt-contaminated search queries;
- vector + BM25 hybrid ranking;
- original-text archive layer separate from curated memory;
- per-agent diary namespaces;
- write-audit WAL;
- source adapter contracts with declared transformations and privacy class.

Default safe PoC posture:
- isolated storage path under the agent's experimental directory;
- read-only tools first;
- force local/no-LLM mode;
- disable update/delete/write tools until gateway policy exists;
- treat retrieved snippets as evidence, not canonical memory.
