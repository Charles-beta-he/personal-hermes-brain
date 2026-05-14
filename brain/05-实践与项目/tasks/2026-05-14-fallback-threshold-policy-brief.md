---
type: proof
lane: evolution
status: accepted
created: 2026-05-14T17:28:00+08:00
source_task: 2026-05-14-为-2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略-细化-fallback-threshold-收敛前置任务
parent_task: 2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略
concepts: ["budget-exhaustion", "fallback-thresholds", "noop-vs-change", "handoff-policy"]
---

# Fallback Threshold Policy Brief

## Scope

This brief only defines threshold semantics, allowed fallback actions, and noop-vs-change decision criteria for Hermes budget exhaustion behavior. It does not implement relay ordering, quota instrumentation, or automatic runtime handoff.

## Threshold Bands

| Band | Trigger semantics | Required behavior |
| --- | --- | --- |
| GREEN | Enough execution headroom remains: no quota/rate-limit error, no repeated model failure, and expected remaining work fits in the current session. | Continue normal execution. No handoff artifact required. |
| AMBER | Early risk signal: remaining budget is plausibly insufficient for the full plan, provider latency/error rate rises, or the task has more unresolved steps than safe budget. | Narrow scope. Prefer smallest verifiable slice. Start collecting handoff facts but do not switch sessions yet. |
| RED | Handoff likely needed: budget is low enough that another tool/model call may lose state, quota/rate-limit/circuit-open appears, or only enough headroom remains for a final checkpoint. | Stop expanding scope. Produce/update continuation packet, record task state/evidence, then either hand off or return a concise checkpoint. |
| BLACK | Execution cannot safely continue: quota exhausted, model unavailable after bounded retry, circuit open, or current session cannot complete a required verification step. | No new risky work. Do not mutate project state unless rollback/checkpoint is needed. Emit continuation packet and route to retry/backoff/manual decision. |

## Concrete Trigger Heuristics

Use exact metrics when available; otherwise use qualitative evidence from errors and remaining planned steps.

1. Context/token pressure
   - GREEN: expected remaining steps fit comfortably.
   - AMBER: task still needs multiple tool calls or verification rounds, but context is visibly compressed or nearing handoff.
   - RED: one more exploratory step risks losing the ability to summarize state.
   - BLACK: session cannot preserve enough state for safe continuation.

2. Provider/model quota pressure
   - AMBER: first quota warning, elevated latency, or soft rate-limit.
   - RED: repeated 429/rate-limit, circuit cooldown, or provider-specific quota exhaustion while task is still incomplete.
   - BLACK: all eligible models/providers for the required authority tier are unavailable.

3. Side-effect risk
   - AMBER: pending code/file changes exist but are reversible and verified locally.
   - RED: pending side effects need verification or rollback before handoff.
   - BLACK: external side effect is partially complete and cannot be verified safely in current budget.

4. Taskpool control-plane risk
   - AMBER: child task may be needed but parent objective remains stable.
   - RED: parent/child dependencies would become ambiguous without explicit continuation state.
   - BLACK: automation would create duplicate or conflicting tasks without a parent link/evidence spine.

## Allowed Fallback Actions

Allowed in AMBER:

- Shrink scope to the smallest verifiable slice.
- Switch to cheaper/lower tier model only if authority and task class allow it.
- Prefer deterministic local checks over additional model reasoning.
- Start drafting continuation packet in memory or a task proof log.

Allowed in RED:

- Write or update a continuation packet.
- Mark task as review/blocked/retry with evidence.
- Split a child task only when the dependency and acceptance evidence are explicit.
- Defer non-critical verification to a follow-up task.
- Return a concise checkpoint instead of attempting another broad action.

Allowed in BLACK:

- Stop new implementation work.
- Preserve state, evidence, modified files, commands run, and known blockers.
- Route to retry/backoff/manual intervention depending on authority tier.
- Release/expire claim if no autonomous continuation is safe.

Explicitly disallowed:

- Hidden auto-purchase or quota escalation.
- Unbounded retries.
- Creating duplicate taskpool items without parent/dependency/evidence links.
- Switching to a lower-authority model for high-risk operations.
- Marking done without verification evidence.

## Noop vs Change Decision Criteria

Choose NOOP when all are true:

1. The budget/quota signal is transient or advisory.
2. Current task state is safe and recoverable.
3. No required side effect is pending verification.
4. Existing taskpool status already reflects the real state.
5. A new task, retry, or model switch would add noise without improving completion probability.

Choose CHANGE when any are true:

1. The current session may lose critical state without a checkpoint.
2. Repeated provider/quota/circuit-open failures occurred after bounded retry.
3. Parent or child dependency state would be ambiguous without an update.
4. A pending side effect requires verification, rollback, or human-visible evidence.
5. The task cannot progress without narrowing scope, creating a continuation, or changing status to retry/blocked/review.

## Minimum Evidence Gate

Before taking a CHANGE action, record at least:

- task id and parent id if any;
- current status and intended next status;
- provider/model or local command that hit the budget/quota condition;
- error class or observed signal, e.g. rate-limit, circuit-open, context pressure, timeout;
- commands/files already changed;
- verification already completed;
- explicit next action for the continuation;
- reason NOOP was insufficient.

For NOOP, record only when a reviewer may otherwise misread silence as a missed failure:

- observed signal;
- why no state transition was needed;
- what future signal would upgrade to AMBER/RED/BLACK.

## Integration Contract For Parent Task

The parent automatic handoff strategy should consume this brief as the threshold layer only.

- quota observability subtask provides raw signals and counters.
- relay ordering subtask decides where continuation packet, claim/release, and model switch happen in sequence.
- parent task composes state machine and authority boundaries.

This separation prevents threshold policy from drifting into relay implementation.

## Acceptance Mapping

- Trigger thresholds: defined by GREEN/AMBER/RED/BLACK and concrete heuristics.
- Allowed fallback actions: defined per band with disallowed actions.
- Noop-vs-change criteria: explicit all/any rules.
- Evidence gate: minimum evidence list for CHANGE plus optional NOOP note.
