---
type: strategy
status: active
created: 2026-05-07
project: resumable-multimodel-certification
level: P10
---

# P10 - Long-term Strategy

## Strategic Decision

把“可恢复多模型认证系统”列为 Hermes 多模型治理 P0 基础设施；`TaskCreate -> ralph` 延后，直到该认证系统能稳定产出 `discussion_result.json + certification_manifest.json`。

## Architecture Principles

1. Certification is artifact state, not model agreement.
   - 没有 `discussion_result.json` 与 `certification_manifest.json` 就不是 certified。

2. Discussion is a resumable state machine.
   - 每个模型响应、parse status、round summary 都必须 checkpoint。

3. Ratifier is deterministic and re-runnable.
   - `audit-certification` 不调用模型，只读 tick artifacts。

4. Foreground is for quick review, background is for long ratification.
   - T2/T3 discussion 必须可 background/cron 化。

5. Evidence-first before debate.
   - runtime/API/hook/schema claim 只能由 orchestrator evidence 支撑，模型只能请求证据与评审。

6. Fail closed.
   - partial、timeout、parse failure、quota unknown、missing evidence 都不能被包装成 certified。

## Phases

### Phase 0 — Contract Freeze

产物：

- certification state enum；
- tick artifact manifest；
- current reader/writer map；
- partial run audit baseline。

### Phase 1 — Checkpoint + Audit

产物：

- `discussion/state.json`
- `discussion/round_N/*.json`
- `audit-certification <tick_dir>`

### Phase 2 — Resume

产物：

- `discussion/cursor.json`
- `resume-discussion <tick_dir>`
- forced-timeout resume test。

### Phase 3 — Background-safe Runner

产物：

- heartbeat/status JSON；
- timeout/degraded markers；
- cron-safe wrapper；
- non-empty final output invariant。

### Phase 4 — Evidence-first Split Workflow

产物：

- evidence_requests export；
- claims/evidence refill loop；
- integration-level ratification。

### Phase 5 — Optional Per-round Parallelism

只在 Phase 1-4 稳定后考虑。同一 round 内可并行，round 间必须保持因果顺序。

## Risk Analysis

1. False certification — P0。
   - 缓解：certification manifest 必须同时验证 discussion_result、truth gate、issue ledger、model votes。

2. Checkpoint corruption — P0。
   - 缓解：atomic write + schema validation + audit command。

3. Resume duplicate model calls — P1。
   - 缓解：cursor + per-model completion ledger。

4. Cost/quota runaway — P1。
   - 缓解：per-model call budget、wall-clock budget、quota snapshot、degraded_not_certified。

5. Overengineering — P1。
   - 缓解：先 checkpoint/audit/resume，不先并行/自动 evidence loop。

## Stop Condition

本项目完成的最低标准：

- `audit-certification` 能对现有 tick 做 fail-closed 判断；
- `resume-discussion` 能从人工中断后继续；
- background runner 能在 timeout 时输出 `timed_out_uncertified`；
- self-check PASS；
- 本地测试覆盖 forced timeout / corrupt checkpoint / missing discussion_result / certified happy path。
