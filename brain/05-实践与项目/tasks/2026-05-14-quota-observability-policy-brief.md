---
type: proof
lane: evolution
status: accepted
created: 2026-05-14T17:32:00+08:00
source_task: 2026-05-14-为-2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略-细化-quota-observability-收敛前置任务
parent_task: 2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略
concepts: ["budget-exhaustion", "quota-observability", "quota-state", "unknown-handling"]
---

# Quota Observability Policy Brief

## Scope

This brief only defines how Hermes should observe and classify `quota_state` for budget-exhaustion handoff decisions. It does not implement provider adapters, relay ordering, or automatic retry/handoff.

## Quota State Contract

A quota observation should normalize raw signals into one of five states:

| quota_state | Meaning | Parent policy use |
| --- | --- | --- |
| `healthy` | No evidence of provider quota, rate-limit, context, or circuit pressure. | Continue normal execution; fallback threshold may remain GREEN. |
| `degraded` | Soft warning or first transient issue: latency spike, first 429/rate-limit, one model/provider unavailable, or context compression risk. | Treat as AMBER unless task is trivial and recoverable. |
| `limited` | Repeated quota/rate-limit/cooldown or insufficient model/provider capacity for remaining work. | Treat as RED; produce checkpoint/continuation before further broad work. |
| `exhausted` | Required provider/model/authority tier cannot continue now. | Treat as BLACK; stop risky work and route to retry/backoff/manual decision. |
| `unknown` | No reliable observation source or conflicting data. | Fail conservative: do not assume healthy; require local proof or explicit bounded retry. |

## Source Evidence Hierarchy

Use the most deterministic source available. Lower-priority sources can support but should not override higher-priority evidence.

1. Direct provider/tool error evidence
   - Examples: 429/rate-limit, quota exceeded, circuit open, cooldown remaining, APIConnectionError after bounded retries.
   - Confidence: high when timestamped and attached to provider/model/tool call.

2. Hermes tool/delegation result envelope
   - Examples: delegate_task status timeout, API call failed after retries, tokens object, model/provider field, exit_reason.
   - Confidence: high for the specific call; medium for global quota.

3. Gateway/runtime status surfaces
   - Examples: gateway status endpoint, provider health/circuit state, process/session liveness.
   - Confidence: medium/high depending on freshness and provider specificity.

4. Local command/process evidence
   - Examples: process timeout, py_compile/test pass while model path failed, retry logs.
   - Confidence: medium; proves local execution state, not provider quota by itself.

5. Human/session observation
   - Examples: visible model degradation, repeated assistant interruptions, user-reported quota message.
   - Confidence: low/medium; requires corroborating evidence before durable state change.

## Confidence Levels

Each quota observation should carry:

- `confidence: high` when source is direct provider/tool error or fresh Hermes runtime status.
- `confidence: medium` when inferred from repeated call failures, timeouts, or partial telemetry.
- `confidence: low` when based on a single ambiguous symptom.
- `confidence: unknown` when no source is available.

Recommended normalized record:

```json
{
  "quota_state": "limited",
  "confidence": "high",
  "source": "delegate_task",
  "provider": "openai-codex",
  "model": "gpt-5.5",
  "signal": "circuit open cooldown 115s",
  "observed_at": "ISO-8601 timestamp",
  "task_id": "...",
  "evidence_ref": "path or tool output hash"
}
```

## Unknown / Unobservable Handling

`unknown` must not silently downgrade risk to GREEN.

If quota_state is unknown:

1. Prefer deterministic local checks that do not consume scarce model budget.
2. Allow one bounded retry only when the task is idempotent and no side effect is pending.
3. If retry still gives no signal, classify as `degraded` for planning and require a continuation checkpoint before broad work.
4. Do not create duplicate tasks solely because quota is unknown.
5. Do not mark parent handoff strategy complete without stating what source remains unobservable.

## File-backed Evidence Locations

For taskpool/brain workflows, evidence should be file-backed where possible:

- Task proof log: current task Markdown under `/Users/charles/Documents/brain/05-实践与项目/tasks/`.
- Policy proof artifact: this brief or a sibling proof file in the same task directory.
- Tool output cache: `/Users/charles/.hermes/cache/tool_outputs/` when a tool returns a spilled output hash.
- Runtime benchmark/check evidence: `/tmp/...json` for ephemeral run output, then cite it in the task proof log if used for completion.
- Persistent operational dashboard: `/Users/charles/Documents/brain/07-仪表盘/待完成任务运行态.md` for derived taskpool state, not raw quota truth.

## Noop vs State Change For Quota Observability

NOOP is justified when:

- quota_state is `healthy` or a single low-confidence degraded signal;
- no side effect is pending;
- retry would consume more budget than the next local deterministic check;
- existing task status is already accurate.

State CHANGE is justified when:

- quota_state is `limited` or `exhausted` with medium/high confidence;
- repeated failures/cooldowns appear;
- current task would lose state without a continuation packet;
- a parent/child task dependency would be misleading without a status/evidence update;
- quota_state remains unknown after bounded retry and the task is not safely idempotent.

## Integration Contract For Parent Task

The parent automatic handoff strategy should consume this brief as the quota signal layer only.

- fallback-threshold policy maps quota_state into GREEN/AMBER/RED/BLACK decisions.
- relay-ordering policy decides when to checkpoint, claim/release, split, retry, or hand off.
- parent task composes these into the final state machine.

This prevents quota observability from drifting into retry orchestration or model-routing implementation.

## Acceptance Mapping

- quota_state source: hierarchy defined.
- confidence: levels and normalized record defined.
- unknown/unobservable handling: conservative fallback rules defined.
- file-backed evidence: canonical locations listed.
