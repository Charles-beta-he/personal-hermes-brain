# Hermes-hosted SE-AOS / PUA-loop control plane

Use this reference when the user asks to make Hermes self-evolve, land PUA-loop, add per-round P10 checks, or use Hermes as the host/control plane for OpenClaw trace ingestion.

## Boundary language

Be precise about completion claims:

- "Complete" can mean the Hermes-local MVP loop is complete.
- Do not claim live OpenClaw production is connected unless a real trace path/webhook and auth are configured and verified.
- Do not claim Hermes core has native hard gates when only a callable fail-closed shim or registry entry exists.
- Learning artifacts should remain `pending_review` unless a reviewed publish/export path is explicitly implemented.

## Hermes-local PUA / SE-AOS MVP loop

Canonical local script:

```bash
python3 ~/.hermes/scripts/pua_loop_self_optimize.py <command>
```

Important commands:

- `evolve-round`: P10 self-check + benchmark + SE-AOS status refresh.
- `p10-check`: direction / boundary / evidence / leverage / next action check.
- `hook-ingest`: turn a lifecycle event or bad case into the PUA-loop case pipeline.
- `run-benchmarks`: run local meta benchmark oracle and write `benchmark_runs.jsonl`.
- `seaos-status`: report Memory OS / Harness Runtime / Case-to-Capability / Dynamic Benchmark fusion status.
- `record-review`: persist multi-view review verdicts.
- `final-gate`: fail-closed completion shim checking P10, evidence, benchmark, SE-AOS status, and optional multimodel accept.

Before final claims on this class of work, run `final-gate` and cite the dashboard or acceptance file as evidence.

## OpenClaw trace integration pattern

Treat OpenClaw as producer and Hermes as control plane:

```text
OpenClaw trace producer
→ JSONL/webhook trace
→ Hermes ingest/redaction
→ normalized TraceEvent
→ case candidate
→ PUA-loop hook-ingest
→ benchmark/proposal
→ replay spec
→ deterministic replay
→ pending_review learning artifact
→ dashboard + review + final-gate
```

Canonical local trace integration script:

```bash
python3 ~/.hermes/scripts/openclaw_trace_ingest.py ingest --input <trace.jsonl> --project openclaw-prod
python3 ~/.hermes/scripts/openclaw_trace_ingest.py replay
python3 ~/.hermes/scripts/openclaw_trace_ingest.py promote --case-id <case_id>
python3 ~/.hermes/scripts/openclaw_trace_ingest.py dashboard
```

Expected state files:

- `~/.hermes/openclaw-traces/ingested_events.jsonl`
- `~/.hermes/openclaw-traces/case_candidates.jsonl`
- `~/.hermes/openclaw-traces/replay_specs.jsonl`
- `~/.hermes/openclaw-traces/replay_runs.jsonl`
- `~/.hermes/openclaw-traces/learning_artifacts.jsonl`
- `~/.hermes/openclaw-traces/dashboard.md`
- `~/.hermes/openclaw-traces/final-acceptance.md`

## Safety rules

- Redact credentials and PII before case/memory write.
- OpenClaw traces start as case memory, not semantic memory.
- Use dev/synthetic/holdout benchmark split for capability claims.
- Do not auto-publish learning artifacts back to OpenClaw without review, rollback, and acceptance evidence.
- If a review returns `accept_with_conditions`, either satisfy the conditions or bind the final verdict to a narrower acceptance boundary.

## Acceptance checklist

For Hermes-local complete landing:

1. `evolve-round` passes P10.
2. Ingest/replay/promote commands run successfully.
3. PUA-loop receives forwarded cases.
4. Benchmark/replay pass rate is recorded.
5. `record-review` has multi-view accept or bounded accept.
6. `final-gate` passes.
7. A final acceptance document states what is and is not claimed.
