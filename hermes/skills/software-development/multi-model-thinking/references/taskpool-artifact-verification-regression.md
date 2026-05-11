# Taskpool artifact verification regression

Use when auditing or modifying local-brain taskpool multi-model flow, especially fields such as `multimodel_status`, `multimodel_ratification_artifact`, `certification_status`, or `ratification_artifact`.

## Incident pattern

A task note can claim `multimodel_status: certified` while the referenced `discussion_result.json` is not a valid certificate for that task:

- artifact has `status: certified` but only 3 votes, missing the canonical 4th model;
- artifact is `not_certified` but was copied into a certified-looking task note;
- artifact is from a different task/domain and lacks target binding;
- artifact predates an amend/code/task-note change and is only provenance for the old state;
- artifact is a structured string (`proof:`/`artifact:`) rather than a readable local JSON file.

For this user's taskpool/Lark closeout policy, any of the above is `not_certified_for_target`; do not let it unblock `done` or stop a PUA loop.

## Required verifier behavior

`task_multimodel_passed(task)` or equivalent taskpool pass logic must not trust frontmatter labels alone. It should:

1. Require `multimodel_status` / `certification_status` to be a pass status.
2. Require a local JSON artifact path (`/abs/path.json` or `file:/abs/path.json`); opaque `proof:`/`artifact:` labels are provenance only.
3. Load the JSON artifact.
4. Run the same fail-closed ratification gate used by the CLI, bound to the expected task, e.g. `ratification_gate_result(discussion, expected_task=task)`.
5. Return true only for `PASS` + `LOOP_DONE`.

The gate must validate at least:

- explicit binding candidates (`task_id`, `target_task_id`, `task_path`, nested `context`/`final_design.meta`, etc.) match the target task;
- no binding candidate points at another task;
- canonical four votes are present for closeout: `claude-opus-4-7`, `gpt-5.5`, `deepseek-v4-pro`, `mimo-v2.5-pro`;
- every vote approves and has `best_within_constraints: true`;
- agreement, truth/evidence, issue ledger, criteria, and final design checks pass.

## Task-note repair pattern

When an old task is found with a stale or wrong artifact:

1. Inspect the artifact before editing: status, votes, binding fields, target strings, and evidence claims.
2. If it is missing 4/4, lacks binding, or points at another task, downgrade frontmatter to `multimodel_status: not_certified` and, for mission envelopes, `certification_status: not_certified`.
3. Keep the old artifact path only as provenance/advisory; state explicitly why it cannot close the current task.
4. Update `acceptance_evidence` and Proof Log to require a fresh target-bound 4/4 ratification before closeout.
5. Re-run the taskpool status suite: unit test, `selfcheck`, `proof-check`, `boundary-check`, and `parallel-dispatch-dry-run`.

## Regression tests to add

Add tests that cover both positive and negative cases:

- a good local `discussion_result.json` with exact target task + 4 canonical model votes makes `multimodel_passed` true and suppresses intervention;
- replacing that artifact with a partial-model JSON (for example 2/4 or 3/4) makes `multimodel_passed` false and intervention true;
- a mismatched target artifact fails with `target_task_mismatch`;
- a certified label with no artifact or an opaque `proof:` label is false for pass state.

## End-to-end taskpool repair closeout

When repairing a broken taskpool flow, finish the whole loop rather than stopping at a code/test patch:

1. Release stale claims only after proving they are stale with `brain_task_orchestrator.py list --json` (`stale_claim: true` or expired `claim_expires_at`). Use `release TASK --force --reason <specific_flow_repair_reason> --json` and record the lifecycle note as flow repair, not task completion.
2. Repair task frontmatter conservatively: downgrade stale/wrong artifacts to `multimodel_status: not_certified` or `not_certified_for_target`; keep old artifact paths as provenance only.
3. Add a short proof-log / evidence note explaining why old artifacts are not closeout certificates and what fresh target-bound 4/4 gate is required next.
4. Re-run deterministic gates in this order: unit test, `selfcheck --json`, `proof-check --json`, `boundary-check --json`, then `parallel-dispatch-dry-run --max-agents 3 --json`.
5. Refresh derived views with `dashboard --write --json`, then `brainctl.py --json sync` and `brainctl.py --json reindex`.
6. Commit only the scoped Hermes code/skill files. The brain vault may be non-git; do not assume task-note/evidence edits can be committed from `~/Documents/brain`.
7. After commit, verify `git log -1 --oneline`, scoped `git status --short -- <files>`, and re-run the status suite if the code changed after the previous gate.

Successful repair posture looks like: `invalid_count=0`, selfcheck/proof/boundary all PASS, `parallel-dispatch-dry-run` returns an explicit non-conflicting dispatch plan, and convergence stats accurately show only genuinely target-bound 4/4 tasks as `multimodel_passed`.

## Reporting language

Use precise status language:

- `certified_for_target`: pass gate on current task/code/state.
- `provenance/advisory`: useful historical context but not a closeout certificate.
- `not_certified_for_target`: artifact exists but fails binding/model/gate checks.
- `not_certified_yet`: discussion still running or artifact missing.
