# Code Review 多 Agent 并行审查与置信度过滤评估

Date: 2026-05-13
Task: 2026-05-10-skill学习路线code-review-多-agent-并行审查与置信度过滤评估

## Decision

Borrow and internalize the pattern as a Hermes skill reference, not as an external dependency.

Source/license:
- Source of candidate idea: screenshot-level concept only: "多 Agent 并行审查，置信度过滤减少假阳性".
- No external package/code was installed or imported for this evaluation.
- Existing Hermes skill artifact: /Users/charles/.hermes/skills/software-development/multi-agent-code-review/SKILL.md
- Skill license in frontmatter: MIT.

## Rubric

Default review decomposition:
1. Security: credentials, injection, authorization, persistence leaks.
2. Logic/correctness: state transition semantics, stale data, error paths, edge cases.
3. Performance/maintainability: complexity, repeated I/O, maintainability risk.

Aggregator formula:
- score = agreement_ratio * 0.6 + avg_confidence * 0.4
- default thresholds: critical=0.3, high=0.5, medium=0.7, low=0.7

Evidence-first override added by this replay:
- A single-agent finding that includes a deterministic reproduction/test can be promoted to the issue ledger even when agreement_ratio is low.
- Cross-agent agreement is a noise filter, not truth authority.
- Medium security/correctness findings near threshold must not be discarded when a local test can prove the defect.

## Historical Diff Replay

Replay diff:
- commit: 6ad7841 fix: sanitize model quota evidence
- patch: /tmp/multi_agent_code_review_historical_diff_6ad7841.patch
- files: /Users/charles/.hermes/scripts/model_quota.py, /Users/charles/.hermes/scripts/test_model_quota.py

Raw findings:
1. security agent, medium, confidence 0.73
   - Finding: sanitizer redacted sensitive key values but preserved sensitive dictionary key text.
   - Risk: a key such as "Authorization: Bearer <token>" or "api_key=<key>" could persist the secret in JSON object keys.

2. logic agent, medium, confidence 0.86
   - Finding: record_snapshot loaded sanitized state in memory, but when preserving a higher-confidence existing snapshot, it returned without save_state, leaving old unsanitized state on disk.

3. logic agent, low, confidence 0.74
   - Finding: same key-redaction issue as #1.

4. performance agent
   - No actionable finding.

Strict confidence-filter outcome:
- Key-redaction cluster: 2/3 agents, avg_conf≈0.735, score≈0.694. This is just below the medium threshold 0.7, so a strict formula would suppress it.
- Preserve-path stale-state cleanup: 1/3 agents, conf=0.86, score≈0.544. Strict formula would suppress it.

Ground-truth outcome:
- Both issues were real and reproducible.
- This replay proves the skill must keep a deterministic evidence override path; otherwise confidence filtering reduces false positives at the cost of missing real medium-severity sanitizer bugs.

## Implemented Fixes

Files changed:
- /Users/charles/.hermes/scripts/model_quota.py
- /Users/charles/.hermes/scripts/test_model_quota.py

Fix 1: dictionary key redaction
- Added deterministic redacted-key dedupe.
- Sensitive-looking dict keys are replaced with [REDACTED_KEY].
- All dict key text is also pattern-redacted.
- Safe quota field names such as remaining_tokens remain intact.

Fix 2: preserved snapshot path sanitizes disk state
- record_snapshot now persists the sanitized load_state result before deciding whether to preserve an existing higher-confidence snapshot.
- This prevents old secrets/prompt text from surviving on disk when an incoming lower-quality snapshot is ignored.

Fix 3: persisted usage cleanup for old state
- Generic quota evidence sanitization now treats usage dicts with sanitize_usage, keeping only numeric metering fields and dropping prompt/completion text.

New tests:
- test_sanitizer_redacts_secret_bearing_dictionary_keys
- test_record_snapshot_rewrites_sanitized_state_when_preserving_existing_snapshot

Validation:
- python3 /Users/charles/.hermes/scripts/test_model_quota.py => 33 tests OK
- python3 -m py_compile /Users/charles/.hermes/scripts/model_quota.py /Users/charles/.hermes/scripts/test_model_quota.py => PASS

## Confidence Gate and Evidence Bundle Spec

For future multi-agent code review runs, every accepted finding should bind:
- diff or commit path
- reviewer agent and scope
- severity, confidence, and agreement score
- deterministic evidence when available: test name, command, repro script, or exact file/line proof
- final disposition: accepted, suppressed_false_positive, accepted_by_deterministic_override, or accepted_risk

Noise policy:
- Suppress low/medium findings that have only single-agent assertion and no repro.
- Promote single-agent security/correctness findings when a deterministic test proves them.
- Treat model consensus as routing evidence only; truth still comes from files, commands, and tests.

## Final Assessment

Adopt pattern as a guarded Hermes workflow:
- Good for decomposing review cognition and surfacing issues a single pass may miss.
- Confidence filtering is useful for noise reduction but unsafe as a hard truth gate.
- Deterministic evidence override is required for sanitizer/security/correctness review.
