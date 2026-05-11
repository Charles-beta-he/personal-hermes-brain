# Grounded but not-certified amend loop

Use this when a T3/quorum-4 `consult_models.py --discussion` run has grounded truth evidence but the certification manifest says `not_certified`.

## Signal pattern

A run can have all of these at once:

- `truth_assessment.can_certify_truth=true`
- `evidence_coverage=1.0`
- all expected models participated
- `discussion.status=not_certified`
- `final/certification_manifest.json.can_claim_complete_certification=false`
- common manifest failures include approvals below quorum, agreement matrix below 0.85, unresolved severity>=3 issues, or empty merged patches while `planner_patch_summary.certification_intent=implementation_required`

This means the facts are grounded, but the current solution/closeout is not certified. Do not summarize it as success.

## Required loop

1. Open both artifacts, not only stdout:
   - `discussion_result.json`
   - `final/certification_manifest.json`
2. Read `reasons`, `issue_ledger`, `remaining_risks`, and `ratification_votes`.
3. Convert every severity>=3 AMEND into deterministic evidence:
   - add a regression test when a model says an existing test is vacuous;
   - clarify semantics in code/tests when a model warns a test may lock in a bug;
   - add entrypoint/integration coverage when a helper-only test does not prove runtime behavior.
4. Run focused deterministic checks and `git diff --check`.
5. Make a scoped local commit before rerunning certification.
6. Update the claim/evidence state so it binds to the current commits and the amended evidence.
7. Rerun a fresh T3/quorum-4 discussion. The old tick is provenance only.

## Example: Lark OAuth guard

A T3 run for `lark_oauth_guard.py` returned grounded evidence but `not_certified` because reviewers found:

- token-key redaction test used a too-short/vacuous token;
- `_is_unexpired("0")` semantics were ambiguous and might freeze a truthiness bug;
- entrypoint JSON redaction/no-spawn behavior needed direct coverage.

The correct response was not to reinterpret the run as approval. The loop was:

1. Strengthen redaction tests with a long token payload and assert shorter output, ellipsis, prefix/suffix retention, missing secret middle, and `redacted != original`.
2. Add `_is_unexpired` boundary tests documenting `None`/blank legacy behavior and fail-closed `0`/`"0"`/`now`/invalid semantics.
3. Add entrypoint coverage for `ensure_login` token-valid no-spawn and `main --json` redaction.
4. Commit the test/runbook amendments.
5. Rewrite `/tmp/...state.json` to reference the current commit set and rerun T3/quorum-4.

## Handling background completion notices

When the user or process wrapper reports that a background `consult_models.py` run completed, do not assume it is the active task the user originally asked about. First classify the completed session:

1. Match the process command/state path/tick directory to the target task or side-channel task.
2. Open the reported `discussion_result.json` and `final/certification_manifest.json` before summarizing.
3. If it is a side-channel run while the target task is still running, say so explicitly, then handle any actionable AMENDs from the side-channel without declaring the target done.
4. Poll the active target process separately and report its real state (`running`, `completed`, `timed out`, etc.).

This prevents a completed adjacent certification run from being conflated with the high-priority task under investigation.

## Low-risk AMEND closeout pattern

If a grounded-but-not-certified run contains provider/runtime failure or low agreement, but also names a concrete deterministic test gap, it is valid to land only that deterministic gap immediately:

- treat provider/runtime failures (for example a Claude CLI wrapper/stdin error) as certification blockers, not product blockers;
- extract concrete reviewer findings such as “redaction test token is too short/vacuous” or “boundary threshold lacks a test”;
- add the smallest regression/boundary test proving the intended behavior;
- run focused tests, compile, and `git diff --check`;
- make a scoped local commit;
- keep the run labeled `not_certified` until a fresh current-state T3 passes.

Do not wait for a perfect 4/4 rerun before committing deterministic safety-test improvements, but also do not upgrade the old run to certification.

## Pitfalls

- `fanout_certification.certified=true` is not closeout certification when ratification votes are AMEND or agreement < 0.85.
- `truth_can_certify=true` certifies the evidence facts, not that the patch is complete.
- Empty merged patches plus `implementation_required` is a contradiction; resolve it before claiming no-op certification.
- Do not let a post-amend rerun use a stale state file naming the pre-amend commit.
- A process-completed notification can belong to a different background run than the task the user is asking about; verify process id/command/tick before answering.
