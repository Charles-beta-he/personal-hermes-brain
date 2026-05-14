# PUA-loop + P10 self-check for Hermes self-optimization

Use when the user asks to improve Hermes/OpenClaw/agent behavior, land a PUA-loop, add self-evolution, or ensure each strategic round stays directionally correct.

## Definition

PUA-loop is explicitly non-manipulative:

- Positive signal: identify what worked or what durable failure signal was exposed.
- Useful action: convert the signal into a concrete memory / skill / harness / tool / benchmark proposal.
- Accountability verification: bind the proposal to evidence, regression cases, and a dashboard/check result.

Do not treat PUA-loop as praise, motivational language, or manipulative persuasion. It is an engineering accountability loop.

## Local MVP landed in the May 2026 session

Script:

```bash
python3 ~/.hermes/scripts/pua_loop_self_optimize.py
```

State/dashboard:

```text
~/.hermes/pua-loop/
~/.hermes/pua-loop/dashboard.md
~/.hermes/pua-loop/cases.jsonl
~/.hermes/pua-loop/benchmarks.jsonl
~/.hermes/pua-loop/proposals.jsonl
~/.hermes/pua-loop/p10_checks.jsonl
```

Architecture note:

```text
~/.hermes/scripts/pua-loop-self-optimization-architecture.md
```

## Mandatory P10 self-check pattern for this class of task

For self-optimization / PUA-loop / Harness / Memory / Benchmark work, run a P10 check during the round and report the dashboard as evidence:

```bash
python3 ~/.hermes/scripts/pua_loop_self_optimize.py p10-check \
  --goal "本轮战略目标" \
  --boundary "本轮不做什么/权限红线/防范围蔓延" \
  --evidence "本轮产物或验证证据路径" \
  --next-action "下一步可执行动作"
```

The check scores five dimensions:

1. direction — whether the round serves the long-term goal.
2. boundary — whether non-goals, permissions, and anti-scope-creep are explicit.
3. evidence — whether there is file/log/test/tool evidence.
4. leverage — whether the work improves Harness / Skill / Tool / Benchmark / Memory, not just prompt text.
5. next_action — whether a verifiable next step exists.

## Bad-case ingestion pattern

When a self-optimization round exposes a failure or missing behavior, ingest it instead of only discussing it:

```bash
python3 ~/.hermes/scripts/pua_loop_self_optimize.py ingest-case \
  --goal "用户目标" \
  --expected "期望行为" \
  --actual "实际行为" \
  --failure "失败/风险描述" \
  --stage "阶段" \
  --severity P1 \
  --evidence "证据路径/命令输出/日志" \
  --root-cause verification
```

Then run:

```bash
python3 ~/.hermes/scripts/pua_loop_self_optimize.py run
python3 ~/.hermes/scripts/pua_loop_self_optimize.py report
```

## Guardrails

- Do not write WIP/task progress into long-term memory.
- Do not use multi-model consensus as evidence; require tool/test/log/file/screenshot evidence.
- Do not expose holdout benchmark content to prompt/skills/training examples.
- Prefer Harness / Skill / Tool / Benchmark patches over prompt-only fixes.
- Do not enable noisy cron or notifications unless explicitly requested.
- Keep user-facing output concise: state what changed, where it lives, and the verification result.
