---
type: proof
lane: evolution
status: accepted
created: 2026-05-14T17:35:00+08:00
source_task: 2026-05-14-为-2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略-细化-relay-ordering-收敛前置任务
parent_task: 2026-05-14-为-hermes-设计预算耗尽后的自动接力与回退策略
concepts: ["budget-exhaustion", "relay-ordering", "continuation-packet", "handoff-control-plane"]
---

# Relay Ordering Policy Brief

## Scope

This brief defines ordering only: when to write a continuation packet, when to update taskpool state, when to switch/hand off, and where the parent state machine should re-enter. It assumes fallback thresholds and quota observability have already classified risk.

## Inputs

Required inputs before relay ordering runs:

1. `fallback_band`: GREEN, AMBER, RED, or BLACK.
2. `quota_state`: healthy, degraded, limited, exhausted, or unknown.
3. `confidence`: high, medium, low, or unknown.
4. `task_id` and parent id if any.
5. pending side effects and verification state.
6. current claim/authority tier.
7. known next action.

If inputs are missing, relay ordering must not invent them. It should request/record a conservative checkpoint instead.

## Ordering By Band

### GREEN

1. Continue current execution.
2. Do not create a continuation packet.
3. Do not alter task status solely for budget concerns.
4. Record nothing unless an auditor would misread a transient signal.

### AMBER

1. Finish the current smallest safe verification step.
2. Avoid starting broad new work.
3. Prepare continuation facts in the workpad/proof log if task is likely to cross into RED.
4. Keep claim active if enough headroom remains.
5. Re-evaluate after the local check.

### RED

1. Stop exploratory work.
2. Write/update continuation packet before any model/provider switch.
3. Record:
   - task id and parent id;
   - current objective and narrowed scope;
   - completed evidence;
   - modified files/commands;
   - next atomic action;
   - failure/quota signal;
   - authority boundary.
4. Update taskpool state:
   - `review` if slice is complete and needs human/multimodel review;
   - `retry` if same task can resume after cooldown;
   - `blocked` if dependency or authority is missing;
   - child task only if scope must be split and parent link is explicit.
5. Only then switch provider/model/session or release claim.

### BLACK

1. Stop all non-checkpoint side effects.
2. Capture continuation packet immediately.
3. Verify whether any partial side effect needs rollback or warning.
4. Mark task as `retry`/`blocked` with evidence, or return final checkpoint if no safe automation remains.
5. Release claim only after the continuation packet and status update are durable.

## Continuation Packet Timing

Continuation packet is required before:

- provider/model switch caused by RED/BLACK signal;
- creating a child task;
- releasing claim due to budget/quota pressure;
- marking parent/child blocked;
- returning a final checkpoint instead of finishing acceptance.

Continuation packet is optional when:

- AMBER risk exists but local deterministic verification can finish first;
- the task is idempotent and no state would be lost;
- existing proof log already contains all required re-entry information.

Continuation packet is disallowed/noisy when:

- GREEN state and no recoverability risk;
- it would duplicate an existing current packet without adding evidence;
- it would create a new task instead of updating the current one.

## Parent Handoff Re-entry Points

The parent automatic handoff state machine should re-enter at one of these stable points:

1. `observe_quota`
   - Read quota_state/confidence and fallback band.

2. `decide_threshold`
   - Map quota/fallback state to continue, narrow, checkpoint, retry, or block.

3. `checkpoint`
   - Write continuation packet and evidence spine.

4. `transition_task`
   - Update taskpool status/claim/dependency.

5. `handoff_or_retry`
   - Switch model/session, schedule retry, or request human decision.

6. `resume_from_packet`
   - New session reads packet, validates authority, resumes next atomic action.

## Minimum Continuation Packet Schema

```yaml
continuation_packet:
  task_id: "..."
  parent_id: "..."
  fallback_band: RED
  quota_state: limited
  confidence: high
  authority: budget-handoff
  completed:
    - "..."
  pending:
    - "..."
  modified_files:
    - "..."
  verification:
    passed:
      - "..."
    missing:
      - "..."
  next_atomic_action: "..."
  blocked_reason: "..."
  resume_instructions: "..."
```

## Noop vs Relay Change

NOOP relay when:

- fallback band is GREEN;
- quota_state is healthy;
- no pending side effect or ambiguous dependency exists;
- existing task status already communicates the truth.

CHANGE relay when:

- fallback band is RED/BLACK;
- quota_state is limited/exhausted;
- confidence is medium/high and repeated failures happened;
- release/switch/retry would otherwise lose task state;
- parent or child dependency needs durable evidence.

## Integration Contract

- quota observability supplies `quota_state` and `confidence`.
- fallback threshold policy supplies GREEN/AMBER/RED/BLACK and noop-vs-change pressure.
- relay ordering defines durable sequence of checkpoint → task transition → handoff/retry.
- parent task composes all three; this brief must not implement provider routing itself.

## Acceptance Mapping

- continuation packet timing: defined as required/optional/disallowed cases.
- relay ordering: defined per GREEN/AMBER/RED/BLACK.
- parent handoff integration points: six stable re-entry points defined.
