# Real Run Benchmark — 2026-05-11

## Task

`2026-05-10-openai-openai-cli-沙箱评估与-hermes-api-自动化集成决策` (P1, evolution lane)

## Pipeline Execution

| Phase | Status | Duration | Notes |
|-------|--------|----------|-------|
| build_state | OK | ~30s | consult_models.py state → 1863 bytes |
| run_discussion | OK | ~17min | 5 rounds × 4 models |
| ratification_gate | FAIL | instant | 23 failures (correct) |
| task_mutation | SKIP | instant | gate not passed |

## Per-Round Timing

| Round | claude | gpt-5.5 | deepseek | mimo | Total |
|-------|--------|---------|----------|------|-------|
| 1 | ok | ok | retried | retried | ~3min |
| 2 | ok | ok | retried | retried | ~3min |
| 3 | ok | ok | retried | retried | ~3min |
| 4 | ok | ok | retried | retried | ~3min |
| 5 | ok | ok | retried | retried | ~3min |

mimo-v2.5-pro parse_status is consistently `retried` (JSON parsing needs retry) but
eventually succeeds. This is a known pattern — the model wraps output in ```json blocks.

## Gate Result

- status: not_certified
- agreement: {framing: 0.65, approach: 0.65, implementation_order: 0.65} (all below 0.85)
- votes: 4/4 amend (no approve)
- issues: 10 unresolved (severity 3-4)
- truth: no_claims
- gate failures: 23 total

## Key Takeaway

First-run not_certified is EXPECTED for complex tasks. The gate correctly identifies:
- Low inter-model agreement
- Unresolved high-severity issues
- Missing best_within_constraints declarations
- Truth gate failure (no grounded claims)

This validates the fail-closed design. The next step would be to address the specific
issues and re-run, or accept the not_certified status and proceed with advisory-only
recommendations.
