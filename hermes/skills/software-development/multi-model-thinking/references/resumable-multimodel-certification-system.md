# Resumable Multi-Model Certification System (RMCS)

Use this when multi-model discussion/ratification is becoming a long-running or recurring governance project, especially after `consult_models.py run --discussion` repeatedly leaves `plans/*.json` + `merged_plan.json` but no `discussion_result.json`.

## Core lesson

Do not treat “extend discussion timeout” as the long-term project. The durable project is a resumable, auditable certification state machine.

Certification must be artifact-based:

- `merged_plan.json` = fan-out / weak consensus evidence only.
- missing `discussion_result.json` = not fully certified.
- future complete certification should require `discussion_result.json` + `certification_manifest.json` + truth/issue-ledger gates.

## Minimum viable long-term architecture

Build RMCS in this order:

1. Checkpoint discussion state.
   - Persist each model response immediately.
   - Persist parse status, retry status, and per-round summaries.
   - Timeout or crash leaves `discussion_partial_uncertified`, not ambiguous artifacts.

2. Add `audit-certification <tick_dir>`.
   - Deterministic/read-only.
   - No model calls.
   - Returns statuses such as `fanout_complete_uncertified`, `discussion_partial_uncertified`, `discussion_complete_certified`, `timed_out_uncertified`, `corrupt_artifact_uncertified`.

3. Add `resume-discussion <tick_dir>`.
   - Reads cursor/checkpoint.
   - Does not repeat completed model calls unless explicitly forced.
   - Completes missing rounds and writes final ratification artifacts.

4. Add a background-safe runner.
   - Heartbeat/status JSON.
   - Process-group timeout handling.
   - Always emits non-empty status for cron/gateway.
   - Timeout is recorded as `timed_out_uncertified`.

5. Add evidence-first split workflow.
   - Models emit evidence_requests.
   - Orchestrator collects read-only evidence.
   - Final integration-level ratification happens centrally; do not merge multiple small “certifications” into a whole-system certificate.

6. Only then consider same-round parallel model calls.
   - Round N calls may run in parallel, but round N+1 must wait for deterministic join/summary of round N.

## What not to do

- Do not solve recurring timeouts by only raising `--timeout` or `--max-rounds`.
- Do not claim full certification from `merged_plan.json`.
- Do not let hooks, cron, or ralph consume partial discussion artifacts.
- Do not add unbounded retries/fanout.
- Do not parallelize before checkpoint/resume/audit exist.
- Do not chain `audit-certification <tick> && resume-discussion <tick>` for recovery: audit correctly exits non-zero for uncertified ticks, so `&&` prevents resume. Use `;`, explicit exit-code handling, or `rmcs-runner --resume-missing`.
- Do not write raw auth headers, API keys, tokens, passwords, or provider secrets into quota/log artifacts.

## Local-brain landing pattern

For a long-term RMCS landing, create these canonical brain artifacts:

- `05-实践与项目/projects/resumable-multimodel-certification/Project - Resumable Multi-Model Certification.md`
- `05-实践与项目/projects/resumable-multimodel-certification/P10 - Long-term Strategy.md`
- `05-实践与项目/projects/resumable-multimodel-certification/P9 - Implementation Backlog.md`
- `05-实践与项目/实践方案/10-可恢复多模型认证系统Playbook.md`
- `06-治理与评审/reviews/<date>-resumable-multimodel-certification-multimodel-selfcheck.md`
- `05-实践与项目/tasks/<date>-resumable-multimodel-certification-landing-log.md`
- `06-治理与评审/进化日志/<date>-可恢复多模型认证系统长期目标落地.md`

Add a local-first self-check, e.g.:

```bash
python3 ~/.hermes/scripts/resumable_multimodel_cert_selfcheck.py --json
```

The self-check should verify required files, index links, deferred high-risk features, source tick provenance, and no secret hits. It should state that it verifies local-brain landing only, not full multi-model certification.

## Deferring dependent high-risk automation

If a feature depends on reliable multi-model certification (for example `TaskCreate -> next-round ralph` hook/state continuation automation), explicitly defer it until RMCS P0-P2 pass:

- `audit-certification` exists;
- `resume-discussion` exists;
- background runner exists;
- partial discussion cannot be certified;
- runtime fixtures for the dependent feature can be ratified through RMCS.

A useful marker is:

`TASKCREATE_RALPH_DEFERRED_UNTIL_RESUMABLE_CERT_READY`

## Implementation slice pattern (consult_models.py)

When turning RMCS from a project plan into runnable infrastructure, use small TDD slices:

1. RED tests first:
   - `audit_certification()` fails closed when `discussion_result.json` is missing.
   - `run_discussion_rounds(..., checkpoint_dir=...)` writes `discussion/cursor.json`, `discussion/state.json`, `discussion/heartbeat.json`, and `discussion/round_001/round_summary.json`.
   - Per-model checkpointing writes `discussion/round_NNN/model_response_<model>.json` and `parse_status_<model>.json` immediately after each model returns; a SIGTERM after model 3/4 must leave auditable artifacts and a cursor with `next_model`.
   - Issue grouping normalizes equivalent target paths such as `consult_models.py` and `scripts/consult_models.py`; otherwise RMCS inflates one real concern into multiple unresolved blockers and cannot converge.
   - Online ratification can resolve earlier issue-ledger blockers only when the round has no novel severity>=3 critique, `approval_count >= N-1`, `reject_count == 0`, and votes set `best_within_constraints=true`.
   - `resume_discussion_from_tick_dir()` materializes missing `discussion_result.json` and `final/certification_manifest.json` from existing `plans/` + `merged_plan.json`.
   - `run_rmcs_runner()` is bounded (`max_ticks`, finite scan) and writes both `state/rmcs-runner-status.json` heartbeat/status and `state/rmcs-runner-last.json`.
2. GREEN implementation:
   - Atomic JSON writes for all RMCS artifacts.
   - `audit-certification`, `resume-discussion`, `discuss-existing`, and `rmcs-runner` CLI subcommands.
   - `certification_manifest_v1` with `can_claim_complete_certification`, reasons, gates, and artifact hashes.
3. Verification:
   - `python3 -m py_compile ~/.hermes/scripts/consult_models.py ~/.hermes/scripts/test_consult_models_integration.py`
   - `cd ~/.hermes && python3 -m unittest scripts/test_consult_models_integration.py -v`
   - `python3 ~/.hermes/scripts/resumable_multimodel_cert_selfcheck.py --json`
   - For final code-state certification, build a fresh evidence bundle from the post-review diff, run a fresh real T3 `consult_models.py run ... --tier T3 --quorum 4 --discussion --keep`, then run both `audit-certification <final_tick>` and `resumable_multimodel_cert_selfcheck.py --certification-tick <final_tick>`.
   - If the repo has unrelated historical whitespace/log churn, use scoped `git diff --check -- <task paths>` for this task and separately note that full-repo `git diff --check` failed on unrelated baseline files; do not let unrelated logs force edits outside the scoped commit.

## Pitfalls learned from RMCS PUA-loop certification

- If a tool/call limit interrupts a PUA-loop certification, do not summarize it as complete. Final response must explicitly say certification is incomplete unless the latest tick has both `discussion_result.json` and `final/certification_manifest.json` with `can_claim_complete_certification=true`; include the exact background process/session id and tick dir for continuation.
- A true T3 certification can be in three distinct states: (1) four-model `plans/*.json` fanout complete; (2) `merged_plan.json` written; (3) `discussion_result.json` + final manifest certified. Only state (3) can support “fully certified”.
- If `run_fanout()` mutates `merged` after initially writing `merged_plan.json` (for example adding `merged["discussion"]`), write `merged_plan.json` again. Stdout showing the field is not enough; the tick artifact must be self-contained.
- Do not treat an older certified tick as certifying later code. If you patch RMCS after a real T3 certification, rerun certification for the final code state.
- A real T3 result may fail because one model proposes low-risk follow-up patches while others vote noop. Treat balanced noop/change splits as real issue-ledger items (`mixed-noop-vs-change`): either implement the pure-gain follow-up with tests or explicitly mark it deferred/accepted-risk and rerun ratification.
- However, do not let a noop/no-change supermajority manufacture a false severity>=3 blocker from a minority advisory patch. For N>=3, when N-1 models explicitly sign `noop`/no-change and only one model proposes an optional follow-up, the mixed-noop blocker can be suppressed while target-specific real patch conflicts still remain blocking. Add regression coverage for both sides: balanced 1-vs-1 remains blocking; 3-vs-1 noop supermajority is non-blocking.
- Path aliases create fake disagreement: normalize `consult_models.py` vs `scripts/consult_models.py` before building issue ledgers.
- Per-round checkpointing is not enough for crash recovery. Persist each model response and parse status immediately; otherwise a 3/4-complete round still vanishes on timeout.
- Shadow/offline certification is useful as a deterministic smoke test, but it is not a substitute for real T3 when the user asked for multi-model self-check completeness.
- Latest `final/certification_manifest.json` is the source of truth. If it says `not_certified` or `can_claim_complete_certification=false`, the loop is not complete even if tests pass and an earlier tick was certified.
- A certified tick is only valid for the exact code/evidence scope it reviewed. If an independent reviewer later finds a false-certification path, immediately downgrade the current loop status, fix the gate, add regression tests, and rerun T3 certification for the new code; do not rely on the pre-fix certified tick.
- `audit_certification()` must not trust `discussion_result.status` by itself. It must independently fail closed on missing/false `fanout_certification.certified`, missing/false `fanout_certification.multi_model_certified`, missing/false `truth_assessment.can_certify_truth`, empty/single-model votes, approval_count below N-1, any reject vote, any non-boolean-true `best_within_constraints`, missing/low agreement matrix, or unresolved severity>=3 issues.
- Never coerce model JSON booleans with `bool(value)`: strings like `"false"` become true in Python. RMCS vote signatures must use a strict `value is True` check, and malformed severities/agreement scores should parse through safe helpers and fail closed rather than crash or certify.
- The local self-check `--certification-tick` gate must repeat the same independent certification checks as the manifest audit; it must not simply trust a manifest that claims `can_claim_complete_certification=true`.
- Evidence kinds matter: a `gate_requirement`, policy, obligation, or acceptance criterion is not proof that the required action happened. Truth gates must not count those evidence kinds as verifying evidence for factual claims; record them as non-verifying provenance/requirements and require tool/file artifacts for verification.
- Approval votes must not blanket-resolve existing issue-ledger blockers. A blocker needs per-issue resolution evidence, explicit accepted-risk/defer semantics, or a code/test change that removes the issue; otherwise keep it unresolved and `not_certified` even if later aggregate votes are positive.
- Fanout completeness must be checked structurally, not just by boolean claims. Require strict integer `planner_count`/`success_count`, consistency with plan file count, expected unique model votes, and strict `multi_model_certified=true` before allowing complete certification. Check both the discussion artifact and `merged_plan.json`: a clean/generated discussion gate must not mask malformed or inconsistent merged fanout counts. A tick with `planner_count=4` but `success_count=3` is degraded/not fully certified even if four later ratification votes approve.
- Certification manifest artifact metadata must reflect the write mode honestly. If `audit_certification(..., write=True)` is about to materialize `final/certification_manifest.json`, report the manifest artifact as existing in the returned artifact map; otherwise reviewers can flag a self-contradictory certified manifest that claims its own output file is missing.
- Numeric parser hardening must reject JSON booleans and non-finite values explicitly. In Python, `bool` is a subclass of `int`, `float("nan")`/`float("inf")` can parse successfully, and `int(float("inf"))` raises `OverflowError`. Certification-critical `_safe_int`/`_safe_float` helpers should reject `bool`, require `math.isfinite(...)`, catch `OverflowError`, and have named regression tests in both runtime audit and standalone selfcheck paths.
- Evidence kind/type canonicalization must be independent. Do not write `kind = evidence.kind or evidence.type`: a whitespace-only `kind` can mask a non-proof `type` like `gate_requirement`. Strip/lower both fields separately and treat either field matching `gate_requirement`, `policy`, `obligation`, `requirement`, or `acceptance_criterion` as non-verifying.
- Top-level and nested certification artifacts must fail closed on malformed JSON shapes. `merged_plan.json`, `discussion_result.json`, `final/certification_manifest.json`, `fanout_certification`, `truth_assessment`/`truth_gate`, `agreement_matrix`, ledgers, and votes must be `dict`/`list` as appropriate before any `.get()` or iteration. If the discussion artifact contains a malformed nested gate, record a malformed reason and do **not** fallback to merged-plan gates; otherwise the audit can mask a corrupt discussion result.
- Reviewer-driven RMCS loops need enumerable verifier tests, not just aggregate “tests OK”. When a reviewer or T3 discussion flags a false-certification path, add named tests for the exact helper/gate surface (for example parser bool/nonfinite rejection, independent evidence kind/type canonicalization, malformed top-level/nested artifacts), then rerun deterministic checks and a fresh target-bound T3.
- Conditional/advisory patch detection must be narrow and evidence-backed. Do not classify `add_verifier` patches as advisory with a generic substring like `"if "`; that can suppress concrete verifier work such as “add regression for if statement parsing.” Use explicit conditional/evidence-request phrases (`only if`, `if missing`, `if fresh`, `verify whether`, etc.) and add negative regression tests proving concrete domain text containing “if” or process wording like “before deciding” still creates a mixed noop/change blocker unless it explicitly makes the verifier conditional.
- Empty merged `patches=[]` can be legitimate in certification-only ticks, but only if the artifact makes planner intent explicit. Add a `planner_patch_summary` or equivalent that counts noop, conditional-advisory, and concrete patches; expose it in discussion packets; instruct reviewers that empty `current_best.patches` is not a dropped-patch contradiction when `certification_intent=no_action_certification` and `concrete_patch_count=0`. Without that explicit summary, T3 reviewers may correctly fail closed as “patches dropped”.
- Missing or non-list `merged_plan.patches` is not equivalent to an empty no-action list. Treat missing/non-list patch fields as malformed and uncertified in both `consult_models.py audit-certification` and standalone `resumable_multimodel_cert_selfcheck.py --certification-tick`; only a real empty list plus explicit no-action summary can pass.
- `plans/*.json` artifacts are part of the certificate chain. Any unreadable, non-JSON, or non-dict planner artifact must add a fail-closed reason instead of falling back silently to the filename/model stem; otherwise a corrupt plan can still match votes and falsely certify.
- Planner patch fields inside otherwise-readable `plans/*.json` must also be structurally validated. A dict plan with missing `patches`, non-list `patches`, or a non-dict patch entry must not be silently treated as an empty no-action planner. Count these as malformed planner patch data, set/recompute intent as malformed rather than `no_action_certification`, add named regressions in both runtime audit and standalone selfcheck, and require empty merged patches to fail closed when any planner patch artifact is malformed.
- Independent staged-diff review is a useful RMCS guardrail, but its findings are not just commentary. If a reviewer flags a false-certification path, immediately downgrade the current loop, add a minimal repro that proves the old gate would false-pass, patch the certification gate, add named tests for the exact artifact shape, rerun deterministic gates, and then start a fresh T3 tick for the post-fix staged diff. Do not rely on a pre-fix certified tick.
- When building evidence bundles via `consult_models.py state`, verify the claim IDs actually written into `state.json`. The state builder may normalize `C1`/`C2` into `C-001`/`C-002`; evidence `supports` must reference the normalized IDs or the truth gate will correctly mark claims unsupported and produce a non-certified tick.
- If a tick fails because reviewers misinterpret an empty patch set, do not just rerun. Fix the artifact/communication contract so the next tick contains the missing intent evidence, add regression coverage for the packet/summary, then run a fresh T3.

## Verification checklist

After landing RMCS as a project:

```bash
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "Resumable Multi-Model Certification" --limit 10
python3 ~/.hermes/scripts/brainctl.py --json search "TASKCREATE_RALPH_DEFERRED_UNTIL_RESUMABLE_CERT_READY" --limit 10
python3 ~/.hermes/scripts/resumable_multimodel_cert_selfcheck.py --json
python3 ~/.hermes/scripts/local_brain_exhaustive_audit.py --sample-limit 20
```

Audit gate target:

- empty dirs = 0;
- top-level dirs without direct index = 0;
- broken wikilinks = 0;
- secret pattern hits = 0;
- RMCS self-check PASS.

If the canonical brain is not a git repo, commit the scoped mirrored files under `~/.hermes/notes/brain/...` plus the self-check script in `~/.hermes` only; do not stage unrelated `.env`, auth, cache, screenshots, or checkpoint noise.
