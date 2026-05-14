# Hermes-hosted self-evolution / PUA-loop pattern

## Session update: OpenClaw trace integration via Hermes

When asked to make OpenClaw production trace integration "depend on Hermes" or "reimplement through Hermes", use this class pattern:

- OpenClaw is a trace producer; Hermes is the evolution control plane.
- Land a Hermes-side trace ingestion MVP first: JSONL/webhook → redaction → normalized TraceEvent → case candidate → PUA-loop `hook-ingest` → benchmark/proposal → replay spec → deterministic replay → `pending_review` learning artifact → dashboard → `record-review` → `final-gate`.
- Keep claims bounded: local JSONL MVP is complete only within that boundary; do not claim live OpenClaw production connection until a real trace path/webhook, auth/signature verification, and runtime event source are configured and verified.
- Require credentials/PII redaction before any case/memory write. Learning artifacts remain `pending_review` unless a reviewed export/publish path with rollback exists.
- Useful local commands from the landed pattern:
  - `python3 ~/.hermes/scripts/pua_loop_self_optimize.py evolve-round ...`
  - `python3 ~/.hermes/scripts/pua_loop_self_optimize.py final-gate ... --require-multimodel-accept`
  - `python3 ~/.hermes/scripts/openclaw_trace_ingest.py ingest --input <trace.jsonl> --project openclaw-prod`
  - `python3 ~/.hermes/scripts/openclaw_trace_ingest.py replay`
  - `python3 ~/.hermes/scripts/openclaw_trace_ingest.py promote --case-id <case_id>`

See also `references/hermes-hosted-seaos-pua-loop.md` for the detailed checklist and state files.

Use this reference when the user asks to land or harden a self-evolution loop, PUA-loop, OpenClaw SE-AOS-style architecture, or every-round P10 self-check inside Hermes itself.

## Scope and boundary

PUA here means non-manipulative engineering feedback:

- Positive signal: identify what worked or what failure exposed a useful capability gap.
- Useful action: convert the signal into memory/skill/harness/tool/benchmark proposals.
- Accountability verification: require evidence, benchmark results, final gate, and review ledger before claiming completion.

Do not overclaim. If implemented only as local scripts/persona/hook registry, call it a Hermes-local MVP, not production OpenClaw integration or Hermes core runtime modification.

## Minimum local control plane

A complete Hermes-local MVP needs these callable commands or equivalents:

- `p10-check`: record per-round strategic self-check: direction, boundary, evidence, leverage, next action.
- `evolve-round`: run P10 self-check, static readiness, benchmarks, SEAOS/fusion status, and dashboard refresh.
- `hook-ingest`: convert lifecycle events, user corrections, failures, or self-evolution events into case ledger entries.
- `run-benchmarks`: execute local benchmark oracle and write pass/fail ledger.
- `seaos-status`: map the four modules to current evidence: Memory OS, Harness Runtime, Case-to-Capability Pipeline, Dynamic Evolution Benchmark.
- `record-review`: persist multi-view/multi-model review verdicts.
- `final-gate`: pre-final accountability check that blocks if P10, benchmark, SEAOS status, evidence, or required review is missing.

Recommended ledgers under `~/.hermes/pua-loop/`:

- `cases.jsonl`
- `benchmarks.jsonl`
- `proposals.jsonl`
- `runs.jsonl`
- `p10_checks.jsonl`
- `benchmark_runs.jsonl`
- `multimodel_reviews.jsonl`
- `final_gates.jsonl`
- `seaos_status.json`
- `dashboard.md`
- `final-acceptance.md`

## Every-round flow

1. Start with P10 self-check before making claims or changes.
2. If a failure/correction/evolution event exists, ingest it as a case.
3. Generate or update proposals and dev/holdout benchmarks.
4. Run benchmarks and refresh status/dashboard.
5. Run multi-view review if the user asks for multi-model confidence or complete landing.
6. Write final acceptance boundaries explicitly.
7. Run `final-gate` immediately before the final answer.

## Final acceptance boundary template

Bind every verdict to scope:

- Complete within: Hermes local MVP loop.
- Not claimed: real OpenClaw production integration, Hermes vendor runtime core-loop patch, production full replay benchmark, model weight training.

A safe final verdict says: “complete within the stated Hermes-local MVP boundary; next stage is production hardening.”

## Acceptance criteria

- P10 latest verdict is pass.
- Benchmark latest pass_rate is 1.0 for the local benchmark set.
- SEAOS/fusion status is at least `mvp_fused`.
- Latest final gate verdict is pass with no blocked checks.
- Multi-view review ledger exists and the latest required review is accept.
- Dashboard and final acceptance document contain the boundary to prevent overclaiming.

## Pitfalls

- Do not treat a static dashboard score as model capability improvement.
- Do not call registry-level hook documentation a Hermes core hard gate unless the runtime actually enforces it.
- Do not expose holdout items into prompt/skill content.
- Do not save WIP/task progress into durable memory; use case ledgers or session search instead.
- Prefer Harness/Skill/Tool/Benchmark patches before prompt-only changes.
