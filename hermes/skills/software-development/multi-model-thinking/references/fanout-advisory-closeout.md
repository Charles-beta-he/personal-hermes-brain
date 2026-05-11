# Fanout Advisory Closeout

Use this when `consult_models.py run ... --discussion --keep` times out after planner fan-out or consensus, leaving `plans/*.json` and maybe `merged_plan.json`, but no `discussion_result.json`; also use it when a valid `discussion_result.json` exists but is `not_certified` for orchestration/metadata reasons unrelated to a source-code blocker (for example a staged implementation closeout gets misclassified as `noop-vs-implementation`).

## Rule

Do not upgrade fan-out to certification. Treat it as advisory provenance until a valid `discussion_result.json` exists and the ratification gates pass.

## Closeout pattern

1. Inspect the latest target-bound tick, not just the newest directory blindly:

```bash
find ~/.hermes -maxdepth 1 -type d -name 'tick-*' -mmin -60 | sort | tail -5
ls ~/.hermes/tick-*/plans/*.json ~/.hermes/tick-*/merged_plan.json ~/.hermes/tick-*/discussion_result.json 2>/dev/null || true
```

2. Verify the tick belongs to this task:
   - compare `merged_plan.json.meta.state_hash` when possible;
   - check `state.json` or `merged_plan.json` mentions the expected repo/task;
   - reject contaminated ticks that mention another project.

3. If `discussion_result.json` is missing:
   - report `weak_consensus` / `not fully ratified`;
   - read `merged_plan.json.merge_info` for `consensus_verdict`, `arbitration_needed`, `unanimous_count`, `majority_count`, `minority_count`;
   - inspect individual `plans/*.json` for `evidence_requests` and concrete reviewer suggestions.

3b. If `discussion_result.json` exists but is `not_certified` while the truth gate is grounded:
   - separate code/product blockers from ratification-metadata blockers;
   - if unresolved issues only say `noop-vs-implementation`, `certification_intent=implementation_required`, or “concrete patch on evidence note” while the actual candidate staged diff is already implemented and claim-linked evidence coverage is 1.0, classify as `truth_grounded_but_not_fully_ratified` rather than a source blocker;
   - rebuild the state with explicit wording such as `certification_intent: no_action_certification_of_staged_implementation` and “candidate solution is the staged diff; models should approve/amend/reject closeout, not invent patches” if there is enough budget;
   - if reruns keep looping on the same metadata issue, stop the background process by PGID, preserve the tick path, and proceed with deterministic closeout only if the task risk and user preference allow it. If the user explicitly requires 4/4 full certification, report the certification blocker honestly and do not claim full ratification.

4. Fulfill actionable evidence requests with deterministic local gates before committing, especially:
   - tests/compile/lint;
   - source no-writeback scans for read-only helpers;
   - no hardcoded secret scans;
   - scoped git status/diff checks.

5. Commit only after deterministic gates pass. In the final report, say explicitly:
   - fanout status: plans/merged available;
   - discussion/ratification status: missing/timeout/not certified;
   - which reviewer suggestions were adopted;
   - deterministic gates that actually justify the commit.

## Pitfalls

- `fanout_certification.certified=true` only proves planner quorum, not final multi-model certification.
- `truth_status=no_claims` means the truth gate had no claim-linked evidence; do not cite it as factual certification.
- Reviewer text such as "implementation_required" can be useful even when not ratified; treat it as advisory and resolve via tools/tests.
- Do not rerun expensive T3/T2 discussion automatically if deterministic evidence is sufficient for a low-risk scoped closeout.
- No-writeback/no-secret guard tests can accidentally contain the forbidden strings they later search for; build patterns dynamically in the test or restrict the grep to production files.
- For code already staged and verified, do not phrase the multi-model state as if no implementation exists. Phrases like `implementation_required` can trigger a false contradiction where three models vote noop/no-change, one model proposes a patch to the evidence note, and the ratification gate remains `not_certified` despite `truth_gate.can_certify_truth=true`. Bind the candidate to the staged diff and ask for closeout readiness instead.
