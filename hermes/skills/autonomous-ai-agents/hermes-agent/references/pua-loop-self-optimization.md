# PUA-loop self-optimization pattern

Use this reference when the user asks for agent self-optimization, self-evolution, bad-case learning, or “pua-loop” style improvement.

## Definition

PUA-loop is intentionally non-manipulative:

- Positive signal: identify what worked or what failure signal is useful.
- Useful action: convert the signal into a concrete memory / skill / harness / tool / benchmark proposal.
- Accountability verification: bind the change to evidence, regression cases, holdout cases, and metrics.

Do not treat PUA-loop as praise, motivational language, or persuasion. It is an engineering loop for turning production failures and user corrections into verified system improvements.

## Minimal architecture

1. Case ledger
   - Store normalized bad cases or self-optimization cases.
   - Required fields: goal, expected, actual, failure, stage, severity, evidence, root_cause.

2. Root-cause taxonomy
   - memory: missing/stale/wrong scoped memory.
   - planning: wrong decomposition, order, dependencies, or premature stopping.
   - tool_use: wrong/missing tool, bad parameters, no fallback.
   - verification: no test/build/browser/API evidence.
   - context: lost constraints or cross-project contamination.
   - safety: side-effect, permission, deletion, publishing, or leakage issue.
   - capability: missing skill/tool/model capability.

3. Proposal registry
   - Convert each case into accountable proposals.
   - Prefer Harness / Skill / Tool fixes before prompt-only fixes.
   - Model routing or training should be last, after repeated capability failures.

4. Dynamic benchmark registry
   - Generate at least dev regression variants and a holdout variant for important cases.
   - Holdout must not be injected into prompts, skills, or training examples.

5. Dashboard / metrics
   - Track evidence_rate, benchmark_density, target_coverage, regression_count, pass_rate, verification_coverage, and self_evolution_efficiency = Δbenchmark_score / evolution_cost.

## Implementation checklist

When landing PUA-loop in Hermes-like systems:

1. Create or locate a persistent local state directory.
2. Add JSONL ledgers: cases, proposals, benchmarks, runs.
3. Implement ingest-case, synthesize, run, and report commands.
4. On ingest, classify root cause and generate fix targets.
5. Only generate benchmark items when evidence is complete enough.
6. Write a dashboard that is human-readable and evidence-oriented.
7. Connect lifecycle hooks later: after_failure, after_user_correction, after_success_reflection, benchmark_regression_detected.
8. Keep cron/reporting quiet by default; escalate only P1/P2 or regressions.

## Guardrails

- Do not save WIP/task progress into long-term memory.
- Do not use multi-model agreement as a substitute for evidence.
- Do not expose holdout cases to prompts, skills, or training data.
- Do not create self-reinforcing praise loops; every positive signal must lead to a useful action and accountability check.
- Do not over-notify the user; run low-risk scoring silently unless regression or high severity occurs.

## Local MVP from session 2026-05-14

A concrete MVP was implemented locally:

- Script: `/Users/charles/.hermes/scripts/pua_loop_self_optimize.py`
- Architecture doc: `/Users/charles/.hermes/scripts/pua-loop-self-optimization-architecture.md`
- State/dashboard: `/Users/charles/.hermes/pua-loop/`

Commands:

```bash
python3 ~/.hermes/scripts/pua_loop_self_optimize.py init
python3 ~/.hermes/scripts/pua_loop_self_optimize.py ingest-case \
  --goal "task goal" \
  --expected "expected behavior" \
  --actual "actual behavior" \
  --failure "failure description" \
  --stage "failure stage" \
  --severity P1 \
  --evidence "evidence path/log/output" \
  --root-cause verification
python3 ~/.hermes/scripts/pua_loop_self_optimize.py run
python3 ~/.hermes/scripts/pua_loop_self_optimize.py report
```

The MVP score is a static readiness score only. It proves cases/proposals/benchmarks/dashboard exist; it does not prove model capability improved until connected to a real runner and regression suite.
