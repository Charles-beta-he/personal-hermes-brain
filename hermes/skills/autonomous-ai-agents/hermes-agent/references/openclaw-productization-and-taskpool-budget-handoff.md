# OpenClaw-informed Hermes productization and taskpool budget handoff

Use this reference when productizing OpenClaw-inspired control-plane ideas inside Hermes and when advancing taskpool items related to budget exhaustion, automatic handoff, continuation packets, or multi-model certification gates.

## Durable workflow: productize first, then automate

1. Keep Hermes as the runtime owner. Treat OpenClaw as an architectural reference only; do not import OpenClaw runtime or call a live OpenClaw service.
2. Make all runtime behavior default-off and fail-soft. Productized helpers may live in `agent/` or `scripts/`, but config flags must remain false unless explicitly enabled.
3. Add deterministic regression to `~/.hermes/scripts/post-update-check.py` so the behavior survives Hermes upstream updates. Preferred check shape:
   - verify key files exist;
   - `py_compile` touched Python modules;
   - run a deterministic benchmark/CLI selfcheck;
   - use pytest if installed, otherwise a direct test-function fallback;
   - assert default-off config is still false.
4. Record acceptance as proof artifacts under the brain/task directory, not only in chat.

## Taskpool budget handoff convergence pattern

For parent tasks such as “设计预算耗尽后的自动接力与回退策略”, avoid trying to solve the whole parent in one pass. Split or finish convergence slices in this order:

1. `fallback threshold` — define GREEN/AMBER/RED/BLACK, allowed fallback actions, and noop-vs-change criteria.
2. `quota observability` — define `quota_state` (`healthy`, `degraded`, `limited`, `exhausted`, `unknown`), confidence levels, source evidence hierarchy, and unknown handling.
3. `relay ordering` — define continuation packet timing, taskpool transition order, claim/release order, and parent re-entry points.
4. Parent final design — compose the three slices into state machine, triggers, automatic/manual boundary, failure fallback, observability metrics, and minimum landing plan.

Canonical proof artifacts from the session:

- `2026-05-14-fallback-threshold-policy-brief.md`
- `2026-05-14-quota-observability-policy-brief.md`
- `2026-05-14-relay-ordering-policy-brief.md`
- `2026-05-14-budget-exhaustion-auto-handoff-final-design.md`

These are examples of the evidence shape; future sessions should create fresh artifacts for the current task rather than editing these exact files.

## Continuation packet minimum schema

```yaml
continuation_packet:
  task_id: "..."
  parent_id: "..."
  fallback_band: RED
  quota_state: limited
  confidence: high
  authority: budget-handoff
  completed: []
  pending: []
  modified_files: []
  verification:
    passed: []
    missing: []
  next_atomic_action: "..."
  blocked_reason: "..."
  resume_instructions: "..."
```

Ordering rule: checkpoint first, then task transition/claim update, then provider/model/session handoff or claim release. Never release/switch before a durable packet exists.

## Taskpool CLI pitfalls discovered

- `brain_task_orchestrator.py claim` does not accept `--authority`; authority belongs to `transition`/`done` commands.
- `done` for evolution/review gates may reject evidence unless the evidence string contains deterministic proof language such as `proof:` or `selfcheck:`. Provide a file-backed proof artifact plus a short deterministic selfcheck summary.
- `ratification-gate --discussion-result` expects a JSON file or JSON-shaped artifact, not Markdown. Passing a Markdown file yields `discussion_result_unreadable`.
- The ratification gate is fail-closed. It expects positive truth/certification fields and real model votes for canonical models (`claude-opus-4-7`, `deepseek-v4-pro`, `gpt-5.5`, `mimo-v2.5-pro`) when the task requires multi-model certification.
- Do not fabricate model votes to pass the gate. If the task has `economy_pause` after repeated T3 failures, move the parent to `review` with deterministic evidence and call out that real multi-model/human ratification remains.
- `blocked-resolve-step` may keep a parent blocked even after child slices are done if `multimodel_status` is still not certified. Treat this as a certification/review problem, not as missing child content.

## Safe status progression for budget-handoff parents

1. Claim the parent with a reason; do not pass unsupported flags.
2. Write a parent final design artifact that maps all acceptance criteria.
3. Update the parent task proof log and evidence refs.
4. If certification cannot pass because real model votes are missing or economy pause is active, set/leave the parent in `review`, not `done`.
5. Only mark done after ratification/certification or explicit human acceptance.

## Default-safe boundaries

Allowed automation:

- write continuation packets;
- write proof logs/evidence refs;
- transition to review/retry/blocked with evidence;
- create child tasks only with parent/dependency/evidence links;
- retry after bounded cooldown;
- switch to same-or-higher authority model/provider when no high-risk side effect is pending.

Never automate:

- quota purchase or paid capacity escalation;
- unbounded retries;
- high-risk side effects with a lower-authority model;
- task duplication without parent/evidence links;
- `done` without evidence;
- treating `quota_state: unknown` as healthy.
