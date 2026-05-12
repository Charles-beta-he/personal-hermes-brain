# Local Brain Keypoint Coverage Audit

Use this when the user asks how much of a framework/protocol/theory is covered in the canonical local brain, or asks to cover/fill missing points.

## Goal

Do not equate keyword file count with conceptual coverage. Report both:

- file coverage: how many Markdown files mention relevant terms;
- keypoint coverage: how many protocol/theory key points have explicit, searchable notes and evidence.

## Workflow

1. Confirm canonical vault and current index:

```bash
python3 ~/.hermes/scripts/brainctl.py --json status
```

2. Define a bounded keypoint list for the framework being audited. Keep it explicit and reviewable. For multi-model thinking, include at least: model diversity, fanout/provenance vs certification, evidence-first, truth gate, state/state_hash, blind seed proposals, disagreement ledger, cross-critique, rebuttal/revision, red-team, ratification/stop condition, communication budget, not_certified caveat, local-brain landing, sync/reindex/search proof, minority-opinion/model-authority governance, final synthesis/provenance/risks.

3. Run a deterministic scan over `~/Documents/brain/**/*.md` with regexes for each keypoint. Output:

```json
{
  "defined_key_points": 22,
  "covered_key_points": 21,
  "coverage_pct": 95.5,
  "uncovered": [...],
  "top_evidence": [...]
}
```

3b. When the user asks for a hard completion state such as “无缺失配对”, “全部 A+”, “0 gap”, or “直至无后续建议”, add a machine-readable contract to the canonical matrix/dashboard and a small local-first self-check script. Do not rely on prose tables alone. Recommended pattern:

```markdown
<!-- <PROJECT>_CONTRACT_START -->
```json
{
  "status": "A_PLUS_COMPLETE",
  "required_pairings_count": 24,
  "missing_pairs": 0,
  "below_a_plus": 0,
  "required_domains": ["control theory", "cognitive science", "epistemology"],
  "rubric_gates": ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
}
```
<!-- <PROJECT>_CONTRACT_END -->
```

Then create `~/.hermes/scripts/<project>_selfcheck.py --json` that verifies required files, parses the contract, counts matrix rows, checks all rows are paired/A+, and reports `PASS/FAIL` with fields such as `missing_pairs`, `below_a_plus`, `missing_domains`, and `missing_rubric`. Store observed self-check output back into the task proof log before final sync/reindex/search.

4. If there are gaps, fill them as knowledge artifacts, not just prose in the final answer:

- stable principle -> `10-atoms/`
- task proof -> `30-tasks/`
- review matrix -> `60-reviews/`
- evolution event -> `05-进化日志/`
- update affected `00-...索引.md` MOCs.

5. Preserve caveats. If old multi-model artifacts were `not_certified`, `dissent`, or timed out, do not rewrite them as certified just because knowledge coverage is now complete. Say: “knowledge coverage is complete; historical ratification remains unchanged.”

6. Verify after writing:

```bash
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "<new keypoint query>" --limit 10
```

7. Check new files for avoidable defects:

- new-file wikilinks resolve;
- no secret-like patterns;
- search returns the new artifact as a top hit for the intended query.

8. If working in `~/.hermes`, make a scoped local commit of only the relevant brain mirror/log files. Avoid staging unrelated runtime/cache/config churn.

## Pitfalls

- A high keyword hit count can still miss a core concept; always inspect uncovered keypoints.
- Obsidian wikilinks with aliases still need the target before `|` to resolve; prefer full relative paths when duplicate note names are possible.
- Search snippets can hit task acceptance criteria instead of the actual atom. If needed, put the key phrase in the atom title so it ranks first.
- Compound bilingual queries can return no results even when the content exists. After a miss, retry with atomic tokens such as `missing_pairs`, `below_a_plus`, `weak_consensus`, or the exact dashboard title before concluding coverage is absent.
- Generic secret regexes can false-positive on Markdown frontmatter (`type: task-log` matching `sk-`). For added-line scans, use stricter patterns such as `sk-[A-Za-z0-9]{20,}` and inspect matches before blocking a clean commit.
- Do not save WIP task state to durable memory; write task logs with expiry under `30-tasks/`.
