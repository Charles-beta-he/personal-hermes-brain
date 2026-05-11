# Fanout Certification Fail-Closed Hardening

Use this when changing `consult_models.py` fanout, discussion, truth-gate, ratification, or audit-certification logic.

## Core lesson

Multi-model fanout certification must be fail-closed in both places:

1. the certification object generator, and
2. the validator/auditor that accepts existing artifacts.

Do not rely on outer audit steps to catch impossible states. A generated object, a handcrafted artifact, or a mutated artifact must all be rejected or downgraded before anyone can claim multi-model certification.

Critical audit-path lesson: the RMCS/audit layer must call the same strict fanout validator on every certification-bearing artifact it consumes (discussion `fanout_certification` and merged `fanout_certification`). It is not enough for the generator and standalone validator tests to pass; `audit_certification()` can otherwise certify handcrafted invalid artifacts whose booleans look clean.

## Required count invariants

Reject malformed numeric fields without crashing. The validator should return `(False, errors)`, not raise. Treat `bool`, strings, `None`, floats, NaN/Infinity, and negative numbers as invalid for certification-critical counts.

Reject impossible fanout relationships:

- `success_count > planner_count`
- `fail_count > planner_count`
- `success_count + fail_count > planner_count`
- `planner_count == 0` with any success/certified/multi-model-certified state

For generated impossible relationships, prefer `status="degraded_not_certified"`, `certified=false`, `multi_model_certified=false`, plus an explicit reason such as `inconsistent fan-out counts`.

## Required cross-field invariants

A validator must reject handcrafted or mutated artifact states such as:

- `multi_model_certified=true` while `certified=false`
- `multi_model_certified=true` with `success_count < 2`
- `multi_model_certified=true` with `planner_count < 2`
- `multi_model_certified=true` while `certification_scope != "multi_model"`
- `status="single_model_quorum_met"` with `multi_model_certified=true`
- `status="fanout_quorum_met"` with `certified=false`
- `status="fanout_quorum_met"` with `success_count < min_quorum`
- `status="degraded_not_certified"` with `certified=true` or `multi_model_certified=true`
- `status="all_failed"` with `success_count != 0` or `certified=true`

Guard all comparisons behind strict count validation. If `success_count="2"` and `multi_model_certified=true`, the validator should report invalid count errors and continue collecting semantic errors where safe; it must not raise `TypeError`.

## Audit-certification fail-closed requirements

The audit/ratifier path must not trust certification booleans, counts, or self-attested participant names directly. `expected_participants` is the canonical identity contract for the planned panel; if it is present, every certification-bearing artifact must be checked against it rather than against family aliases or whatever `models_consulted` claims.

Before setting gates like `fanout_certified`, `multi_model_certified`, `merged_fanout_certified`, or `merged_multi_model_certified`, run:

```python
ok, errors = validate_fanout_certification_status(fanout)
merged_ok, merged_errors = validate_fanout_certification_status(merged_fanout)
```

Required behavior:

- If discussion `fanout_certification` validator errors exist, append an explicit reason such as `fanout_certification invalid: ...` and force `can_claim_complete_certification=false`.
- If merged `fanout_certification` validator errors exist, append `merged fanout_certification invalid: ...` and force `can_claim_complete_certification=false`.
- Certification gates should be schema-gated, e.g. `fanout_certified = fanout_schema_ok and strict_true(fanout.certified)`.
- Keep valid no-action certification fixtures using the real generator (`fanout_certification_status(...)`) rather than minimal dicts, otherwise newly strict audit validation will correctly reject missing schema fields.

Required participant-identity behavior when `expected_participants` exists:

- `discussion_result.json` should include `expected_participants` from the planned model set at generation time.
- Parse `expected_participants` and `models_consulted` as strict non-empty string lists; non-list, non-string, blank, or duplicate identities fail closed.
- `plans/*.json` model identities, `models_consulted`, ratification vote models, and approving vote models must match the expected participant set exactly.
- Missing expected participants, unexpected aliases, duplicate vote identities, or fake/unconsulted voters must all append explicit reasons and force `can_claim_complete_certification=false`.
- Family/role aliases such as `claude`, `codex`, `deepseek`, `mimo` cannot satisfy canonical full-panel certification for this stack (`claude-opus-4-7`, `gpt-5.5`, `deepseek-v4-pro`, `mimo-v2.5-pro`) unless those aliases are the explicitly configured expected IDs.
- If `expected_participants` is absent in historical artifacts, fallback to the plan model set for backward compatibility, but do not lower the requirement when a canonical expected set is present.

Add audit-level regression tests, not only standalone validator tests, for:

- alias plan/vote identities with canonical `expected_participants` must produce `status="not_certified"` and reasons for plan mismatch, consulted mismatch, missing expected votes/approvals, and unexpected vote models
- discussion fanout with `success_count + fail_count > planner_count`
- discussion fanout `status="single_model_quorum_met"` and `multi_model_certified=true`
- merged fanout `status="degraded_not_certified"` and `certified=true`
- merged fanout `status="fanout_quorum_met"` and `certified=false`

## Deterministic selfcheck pattern

Add a local/offline selfcheck command for certification infrastructure:

```bash
python3 scripts/consult_models.py selfcheck --json
```

The selfcheck should be model-free and network-free. It should create temporary fixtures for fanout, truth/evidence, offline discussion/ratification, audit certification, and canonical participant identity mismatch. Include at least one negative fixture where `expected_participants` is canonical but plans/votes/models_consulted use aliases; this fixture must stay `not_certified`.

Global self-test should call the local selfcheck and require `status == "PASS"`.

## Regression probes

Keep explicit tests/probes for:

- bad numeric input: strings, bool, None, floats, NaN/Infinity
- ratification numeric fields beyond fanout counts: `agreement_matrix.*`, `truth_assessment.evidence_coverage`, and issue/risk `severity` must reject bool/NaN/Infinity without raising or silently passing
- malformed certified shells: `status="certified"` with missing agreement/votes/truth/evidence fields must be converted to a fail-closed/malformed artifact, never `LOOP_DONE`
- explicitly `not_certified` advisory artifacts with schema gaps should remain not-certified rather than being rewritten as malformed; preserve their original status as evidence
- impossible counts: `(3, 2, 2, 0)`, `(2, 0, 1, 0)`, `(1, 2, 1, 2)`
- handcrafted mutation: certified false while multi-model certified true
- single-model status with multi-model flag true
- fanout quorum status with certified false
- valid multi-model quorum: e.g. `(2, 2, 2, 0)` remains certified

## Verification bundle

Before committing multi-model certification changes, run at minimum:

```bash
python3 -m py_compile scripts/consult_models.py scripts/test_consult_models_integration.py scripts/self-test.py
python3 scripts/test_consult_models_integration.py
python3 scripts/consult_models.py selfcheck --json
python3 -m py_compile scripts/consult_models.py scripts/test_consult_models_integration.py
python3 scripts/self-test.py
bash scripts/p10-health.sh --json
git diff --check -- scripts/consult_models.py scripts/test_consult_models_integration.py scripts/self-test.py
```

For final ratification, also run an offline/shadow T3 smoke and audit the tick:

```bash
HERMES_MULTI_BRAIN_OFFLINE=1 python3 scripts/consult_models.py run /tmp/state.json --tier T3 --quorum 4 --shadow --discussion --max-rounds 2 --keep
python3 scripts/consult_models.py audit-certification /path/to/tick-dir
```

Note: `audit-certification` may output JSON without accepting a `--json` flag; check the current CLI before adding flags.

## Commit hygiene

Certification work often produces tick dirs, logs, `/tmp` files, and unrelated config dirtiness. Stage only intended source/test files. Never stage credential-bearing files such as `.env` or `auth.json`, and do not summarize their values.