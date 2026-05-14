# Hermes-hosted OpenClaw SE-AOS fusion pattern

Use when the user asks to make an OpenClaw-style self-evolving agent architecture real inside Hermes itself, or says “PUA-loop落地/融合”, “每轮P10检验”, “生成更优进化”, or “OpenClaw SE-AOS是否已融合自身”.

## Durable lesson

Do not stop at architecture prose. For this user, self-evolution work should become a runnable Hermes-hosted control plane with evidence:

1. Run a P10 check at the start of each strategic round.
2. Represent failures/corrections/evolution events as cases.
3. Generate proposals and dev/holdout benchmarks.
4. Run a benchmark pass/fail check.
5. Refresh a dashboard that states what is fused, what is partial, and what is missing.
6. Be explicit about boundaries: local Hermes MVP is not the same as full OpenClaw production runtime integration.

## Current local implementation

Primary script:

```bash
~/.hermes/scripts/pua_loop_self_optimize.py
```

Important commands:

```bash
python3 ~/.hermes/scripts/pua_loop_self_optimize.py p10-check \
  --goal "..." --boundary "..." --evidence "..." --next-action "..."

python3 ~/.hermes/scripts/pua_loop_self_optimize.py evolve-round \
  --goal "..." --boundary "..." --evidence "..." --next-action "..."

python3 ~/.hermes/scripts/pua_loop_self_optimize.py hook-ingest \
  --event self_evolution_fusion \
  --goal "..." --expected "..." --actual "..." --failure "..." \
  --evidence "..." --severity P2 --root-cause verification

python3 ~/.hermes/scripts/pua_loop_self_optimize.py run-benchmarks
python3 ~/.hermes/scripts/pua_loop_self_optimize.py seaos-status
```

State and evidence:

```text
~/.hermes/pua-loop/dashboard.md
~/.hermes/pua-loop/cases.jsonl
~/.hermes/pua-loop/proposals.jsonl
~/.hermes/pua-loop/benchmarks.jsonl
~/.hermes/pua-loop/benchmark_runs.jsonl
~/.hermes/pua-loop/p10_checks.jsonl
~/.hermes/pua-loop/seaos_status.json
```

Hook wrapper:

```bash
~/.hermes/agent-hooks/pua-loop-hook-ingest.sh
```

Registry note:

```text
~/.hermes/hooks/registry.yaml
post_tool_call matcher includes: error|failure|exception|user_correction|pua-loop|OpenClaw|self-evolution
```

Persona rule:

```text
~/.hermes/hermes-agent-persona.md
```

It requires `evolve-round` or `p10-check` for self-optimization / PUA-loop / OpenClaw SE-AOS work; bad cases use `hook-ingest`, benchmarks use `run-benchmarks`.

## SEAOS module mapping

- Memory OS: case/proposal/P10/benchmark memory is green locally; hard memory write gate and stale/conflict resolver remain missing.
- Harness Runtime: persona-level self-check and hook registry are present, but core runtime hard gates are still partial/yellow.
- Case-to-Capability Pipeline: ingest-case/hook-ingest/root-cause/proposal/benchmark synthesis are green locally.
- Dynamic Evolution Benchmark: registry + dev/holdout + local meta benchmark runner are green locally; full task replay and external OpenClaw oracle remain missing.

## P10 self-check contract

Every strategic round should check:

- direction: does the work serve the long-term goal?
- boundary: are non-goals/permissions/scope limits explicit?
- evidence: are files, commands, logs, dashboard, tests, or traces cited?
- leverage: did we improve Harness/Skill/Tool/Benchmark/Memory rather than only prompt text?
- next_action: is the next verifiable step explicit?

## Pitfalls

- Do not claim full OpenClaw production integration when only Hermes-hosted MVP exists.
- Do not treat a static readiness score as model capability improvement.
- Do not enable noisy cron/notifications unless explicitly requested.
- Do not write WIP/session progress to long-term memory; use PUA-loop jsonl/dashboard or session logs instead.
- Do not rely on multi-model agreement without evidence and benchmark gates.

## Verification command

Use this after changing the control plane:

```bash
python3 -m py_compile ~/.hermes/scripts/pua_loop_self_optimize.py && \
python3 ~/.hermes/scripts/pua_loop_self_optimize.py evolve-round \
  --goal "verify PUA-loop/SEAOS fusion" \
  --boundary "do not overclaim full production runtime integration" \
  --evidence "~/.hermes/scripts/pua_loop_self_optimize.py; ~/.hermes/pua-loop/dashboard.md" \
  --next-action "inspect seaos-status and benchmark pass rate"
```
