# Repository audit evidence packaging for multi-model review

Use this when the user asks for multi-model analysis/review of a GitHub repository or local codebase.

## Pattern

1. Do deterministic reconnaissance before model fan-out.
   - Capture exact repo state: `git rev-parse HEAD`, branch, remote, and any relevant GitHub metadata.
   - Read primary docs and manifests: README, package manifest, Rust/Cargo/Tauri config, CI workflows, Docker/install scripts, security/capability config.
   - Run available non-destructive gates when practical: frontend build/typecheck, package audit, cargo check/fmt/clippy/test, or project equivalents.
   - Inspect security-sensitive paths directly: token/credential models, serialization/write paths, crypto helpers, auth middleware, CORS, CSP/capabilities, installer/updater verification.

2. Build the multi-model state from evidence, not impressions.
   - Each high-severity claim must have a stable claim id.
   - Each evidence item must include file path + line range or exact command + result.
   - If using `consult_models.py state --evidence-json`, include explicit claim links where the current schema supports them (`supports: ["C-..."]`, `contradicts: [...]`). A raw JSON blob without links may leave `evidence_coverage=0.0` and force `truth_not_certified` even when the orchestrator has real evidence.
   - Keep secrets redacted; never put raw tokens/keys into state or planner context.

3. Interpret artifacts conservatively.
   - `fanout_certification` only means enough models returned; it is not truth certification.
   - If `merged_plan.json` has `consensus_verdict=dissent`, `arbitration_needed=true`, or no majority/unanimous patches, report weak consensus.
   - If `discussion_result.json` is missing or discussion times out, inspect `discussion/round_*/round_summary.json` and model responses, but do not claim full ratification.
   - If the truth gate says `needs_link_review` or `evidence_coverage=0.0`, present findings as orchestrator-verified facts only when you have separately read the cited files/commands in this session; otherwise mark as pending evidence review.

4. Final report shape for repository reviews.
   - Start with verified repo state and commands actually run.
   - Separate: verified facts, model consensus, model disagreement, inferred risks, pending verification.
   - Include P0/P1/P2 roadmap and map each P0 to concrete evidence.
   - For security claims, quote paths and line ranges rather than relying on model agreement.

## Pitfalls

- Do not pass one large unlinked `context-json`/`evidence-json` blob and expect the truth gate to certify claims. Link evidence to claims explicitly or run an evidence request loop.
- For `consult_models.py state --evidence-json`, pass each evidence item as its own JSON object with top-level `id`, `supports`, `summary`, etc. Do **not** wrap items as `{"items": [...]}` unless the state builder explicitly documents that shape; nested wrappers can collapse into a single candidate evidence item, yield `evidence_coverage=0.0`, and make discussion fail with `needs_link_review` even when the raw data is present. If this happens, rebuild the state with repeated `--evidence-json <item-json>` and rerun a smaller tier before task creation.
- Do not let an outer command timeout erase useful work. Search the latest `~/.hermes/tick-*` directory and summarize `plans/*.json`, `merged_plan.json`, `discussion/round_*/round_summary.json`, and `discussion/cursor.json`. If a round is partially checkpointed, report it as partial/advisory and prefer a repaired state + smaller rerun over treating the timed-out discussion as certification.
- Do not state “multi-model certified” just because four seed plans exist. Certification requires ratification stop conditions and a passing truth gate.
