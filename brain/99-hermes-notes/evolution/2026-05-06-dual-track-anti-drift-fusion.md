# Dual-track anti-drift + Hermes fusion landing

Date: 2026-05-06

## Source reviewed

`/Users/charles/Desktop/dual-track-anti-drift-and-hermes-fusion.md`

## Review verdict

The document's core diagnosis is sound: long-running autonomous development drifts because estimation and control are coupled inside the same model. The practical fix is not “more prompting”; it is a two-estimator control loop:

- Track A: deterministic oracles that run without LLMs and emit reproducible JSON.
- Track B: heterogeneous LLM critics via `consult_models.py`, used for semantic/scope/architecture smell detection.
- Judge: asymmetric truth table. Track A fail blocks; Track B fail asks/escalates; warnings proceed with audit log.

## Landed Hermes-native slice

Implemented a small, profile-light landing slice instead of copying a full `.omc` hook runtime:

- `/Users/charles/.hermes/scripts/anti_drift_guard.py`
  - `init`: create `.omc` skeleton and immutable anchor lock.
  - `lock`: hash anchors into `.omc/anchors/.lock`.
  - `check-anchors`: detect anchor drift.
  - `scope`: enforce task contract JSON with expected files, forbidden globs, loc budget, and audited globs.
  - `judge`: merge Track A/Track B via truth table.
  - `precondition`: check git/anchor lock/commands/optional macOS AX.
  - `consult-state`: produce evidence-first `multi_model_state_v1` for `consult_models.py`.
- `/Users/charles/.hermes/scripts/test_anti_drift_guard.py`
  - 11 tests covering anchors, scope, loc budget, noisy repo filtering, truth table, preconditions, and consult-state.
- `consult_models.py`
  - No-op patches no longer create false blockers when all models vote noop.
  - Mixed noop-vs-real-change now creates an unresolved `<mixed-noop-vs-change>` issue.
  - Discussion JSON parse failure gets one strict JSON retry, then fail-closed.
- `obsidian` skill
  - Canonical vault remains `~/Documents/brain`.
  - `HERMES_BRAIN_VAULT` now takes priority over legacy `OBSIDIAN_VAULT_PATH` in shell snippets.
  - Sync section now asks for status/audit before large syncs.
- `multi-model-thinking` skill
  - Added dual-track anti-drift landing protocol and `anti_drift_guard.py` commands.

## Verification evidence

- `test_anti_drift_guard.py`: 11 tests OK.
- `test_brainctl.py`: 10 tests OK.
- `test_consult_models_integration.py`: 26 tests OK.
- `py_compile`: OK for changed Python files.
- Static scan: hardcoded-sensitive-value=0, shell_true=0, eval_exec=0, pickle=0.
- Track A scope oracle over 8 audited files: passed=True, violations=0, loc_delta=200.
- Dual-track judge: action=proceed.
- Independent reviewer: passed=true, no blockers.
- Four-model final certification:
  - result: certified
  - models: Claude Opus, gpt-5.5, DeepSeek, MiMo
  - artifact: `/Users/charles/.hermes/tick-20260506-050542/discussion_result.json`
  - truth_status: grounded
  - evidence_coverage: 1.0

## Deferred non-blockers

- Full `.omc` hook runtime installation.
- Native Obsidian CLI integration.
- Local REST API plugin integration.
- Temporal KG extraction.
- Per-project recurring cron around `anti_drift_guard.py`.
