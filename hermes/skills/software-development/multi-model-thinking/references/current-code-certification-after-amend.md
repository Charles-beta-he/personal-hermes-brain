# Current-code certification after post-ratification amendments

Use this when a T3/four-model certification was completed, but the implementation changes afterward (even a small safety, redaction, runbook, or test-only amend), or when a current-code T3 run returns `AMEND` / `not_certified` and must be closed without stale-certification claims.

## Rule

A certification artifact is bound to the exact state, evidence bundle, files, and commit-like code shape it reviewed. If any target file or safety-relevant evidence changes after the tick, the old artifact becomes provenance/advisory only for the previous state.

Do not say "current code is 4/4 certified" unless a fresh current-code tick has:
- `discussion_result.json` present;
- `final/certification_manifest.json` present;
- exact expected participants for this stack: `claude-opus-4-7`, `gpt-5.5`, `deepseek-v4-pro`, `mimo-v2.5-pro`;
- four unique approval votes, no rejects;
- truth gate grounded with all severity>=3 claims verified;
- manifest `can_claim_complete_certification=true`.

## Safe reporting wording

Good:
- "Old tick is 4/4 certified for pre-amend code; current-code rerun is in progress, not certified yet."
- "Seed fan-out has all four models and merged_plan exists, but no discussion_result/manifest yet; status is not_certified_yet."
- "Current-code artifact passed; manifest path: ..."

Bad:
- "Certified" when the only certified tick predates the latest amend.
- Treating `plans/*.json` + `merged_plan.json` as ratification.
- Treating a background process, old watch output, or self-attested status as a certification boundary.

## AMEND closure recipe

When a four-model current-code run returns `not_certified` with concrete `AMEND` blockers:

1. Read both `discussion_result.json` and `final/certification_manifest.json`; list unresolved severity>=3 issues and failed gates before changing code.
2. Convert reviewer blockers into deterministic regression tests first. Watch for vacuous tests: a redaction test that asserts absence of a substring never present in the input is not evidence.
3. Resolve ambiguous semantics explicitly in code and tests. Example: for token expiry, decide whether `expiresAt="0"` is legacy/unbounded or epoch-expired; fail closed for explicit epoch values unless a product contract says otherwise.
4. Re-run targeted tests, relevant broader tests, live/status probes, secret scans, `git diff --check`, and make/amend the scoped commit.
5. Build a fresh target-bound state with explicit claims and evidence for the amended code; include the prior not-certified tick only as provenance for what was fixed.
6. Run a new T3 `--quorum 4 --discussion --keep`; only claim current-code certification after the new `discussion_result.json` and `final/certification_manifest.json` pass.

If the new tick certifies a `no_action_certification` because all concrete amendments were already implemented before the rerun, that is valid only when the state/evidence points at the post-amend files/commit and the manifest gate `empty_patches_have_no_action_intent` is true.

## Handoff fields when interrupted

If tool/context budget ends before the fresh tick finishes, preserve:
- state path;
- tick dir;
- background process/session id if available;
- which artifacts exist (`plans`, `merged_plan`, `discussion_result`, `final/certification_manifest`);
- last cursor/heartbeat state if present;
- exact statement: `current_code_certification=not_certified_yet`.
