# Methodology / framework multi-model advisory → local taskpool

Use when the user asks to analyze a methodology, operating doctrine, framework idea, screenshot, or loosely named concept (for example Missions / mission-command / OPORD) and add landing work to the local brain taskpool.

## Pattern

1. Resolve the source conservatively:
   - Search local brain/session history and the web if the methodology name is ambiguous.
   - If no exact authoritative source is found, label the interpretation explicitly (for example `Missions interpreted as mission-command / OPORD`) and do not imply product-level certification.
   - Package authoritative excerpts as claim-linked evidence; for broad public concepts, short excerpts from stable sources are enough for advisory seeding.
2. Inspect the current canonical taskpool before adding anything:
   ```bash
   python3 ~/.hermes/scripts/brain_task_orchestrator.py list --json > /tmp/taskpool-before.json
   python3 ~/.hermes/scripts/brainctl.py --json search '<simple-slug-or-keyword>' --limit 10
   ```
   Search simple slugs/keywords rather than Boolean/natural-language phrases; FTS can return zero for mixed Chinese/English or Boolean-looking queries.
3. Build a claim-linked multi-model state:
   - Claims should cover current-system facts, methodology facts, gap/conclusion, and landing slices.
   - Evidence must use exact claim IDs in `supports`.
   - If `consult_models.py run` times out after planner fanout, inspect `~/.hermes/tick-*` and report `weak_consensus` / `dissent` / `not fully ratified`; do not upgrade to certification.
4. De-duplicate before writing new tasks:
   - If equivalent tasks already exist, patch the canonical task notes with new evidence and constraints.
   - If duplicates were created, archive the duplicates and add a proof-log line saying which canonical task absorbed them.
   - Prefer a small set of class-level tasks (P0 schema/gates, P1 router/dashboard/artifacts, P2 proof-gated runner) over one task per model suggestion.
5. Add or patch canonical tasks with architecture alignment fields:
   - `--lane evolution`
   - `--architecture-target taskpool|local-brain|skill-graph|provider-quota|LX|...`
   - `--capability-delta`, `--anti-drift-check`, `--acceptance-evidence`
   - Include the advisory status and artifact paths in the body.
6. Verify against the real canonical vault:
   ```bash
   python3 ~/.hermes/scripts/brain_task_orchestrator.py list --json
   python3 ~/.hermes/scripts/brain_task_orchestrator.py lifecycle --json
   python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
   python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
   python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write
   python3 ~/.hermes/scripts/brainctl.py --json reindex
   python3 ~/.hermes/scripts/brainctl.py --json search '<simple-slug>' --limit 10
   ```
   `dispatch-dry-run` may return a global `reconcile required` gate even when individual rows in `list --json` are `dispatchable=true`; report both facts rather than hiding the gate.
7. Commit only when the target vault/repo is actually a git repo. If `~/Documents/brain` has no `.git`, say task notes were written/reindexed but no local brain git commit was possible.

## Output requirements

- State whether the result is `certified`, `certified_with_minor_risks`, `truth_grounded_advisory`, or `not_certified`.
- Name the canonical task paths added/patched.
- Mention duplicates archived/absorbed, if any.
- Include verification commands and any remaining blocker such as missing `discussion_result.json` or provider adapter failure.
