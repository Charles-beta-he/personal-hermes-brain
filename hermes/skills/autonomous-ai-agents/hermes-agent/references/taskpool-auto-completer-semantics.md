# Taskpool auto-completer semantic ratchet

Use this when local-brain/task-pool health gates fail because `local-brain-taskpool-auto-completer` has `last_status=error`.

## Core lesson

Do not equate every auto-completer cron `error` with scheduler health failure. Some errors are task-level certification states and should keep the scheduler/evidence-spine healthy while the task remains blocked/retryable.

Known scheduler-safe semantic statuses:

- `ok`
- `ok_with_task_blocker`
- `retryable_runtime_timeout`
- `truth_grounded_advisory_not_ratified`
- `certification_not_certified`
- `certification_long_running`
- `recursive_evidence_spine_self_lock`

Unknown auto-completer errors should still fail closed. Do not add a new safe semantic without at least one positive fixture and several negative fail-closed fixtures that prove the classifier is not masking real scheduler/evidence failures.

## Classification signals

Treat as `retryable_runtime_timeout` when the cron tail contains:

- `Request timed out`
- `RuntimeError: Request timed out`
- `subprocess_timeout`
- `timeout_recorded`

Treat as `truth_grounded_advisory_not_ratified` when advisory evidence exists but ratification is still blocked/pending, for example:

- `truth_grounded_advisory_not_ratified`
- `advisory evidence` / `advisory report` / `evidence化 advisory`
- missing or pending `discussion_result.json`
- `cannot closeout`, `cannot done`, `不能 closeout`, `不能 done`
- `T3 still running`, `T3 仍在运行`

Treat as `certification_not_certified` when ratification explicitly failed:

- `not_certified`
- `not certified`
- `vote_reject`
- `agreement_low`
- `ratification failed`
- `未通过认证` / `认证失败`

Treat as `certification_long_running` when certification is still running:

- `still running`
- `background process`
- `waiting for ratification`
- pending `certification_manifest.json`

## Self-referential feedback-loop failure

A common trap: `evidence-spine` can fail only because `local-brain-taskpool-auto-completer` has `last_status=error`, while that auto-completer error was itself produced by a dispatch tick whose only failing step was `evidence_spine`. This creates a self-locking health gate:

- `taskpool_dynamic_runner_v1` reports `summary.status: ERROR` and `summary.error_count: 1`.
- The embedded `tick.cmd` is a list whose basename includes exactly `brain_task_dispatch_tick.py` and whose arguments include exactly `--summary`. Do not accept substring matches such as `/tmp/not_brain_task_dispatch_tick.py` or joined-command text.
- The embedded `tick.returncode` is exactly numeric `2` (or string `"2"` after JSON/string coercion). Do not accept broad strings such as `"ERROR"`, `"error"`, `"timeout"`, missing return codes, or returncode `1`.
- The embedded tick stdout is valid JSON with `status: ERROR`, `error_count: 1`, and either:
  - a structured `evidence_spine` summary pointing back to `auto_completer_semantic_status: error` / `auto_completer_safe_for_next_tick: false`, or
  - the legacy empty-summary shape with `evidence_spine.status: ERROR`, empty/None `gate_status`, empty summary, and a `recovery_command` that names `brain_task_dispatch_tick.py`.
- No other hard gates fail (`selfcheck`, `proof_check`, `boundary_check`, `permission_audit`, and `cron_status` are OK/PASS).

Do not classify this as an unknown scheduler crash when all proof above is present. Add a distinct safe semantic such as `recursive_evidence_spine_self_lock` (or map to `ok_with_task_blocker` if keeping the existing enum small), record a blocker like `evidence_spine_auto_completer_feedback_loop`, and keep genuinely unknown errors fail-closed. Add a regression fixture where the cron `last_error` contains nested JSON for this loop.

Required negative fixtures for this classifier:

- nested tick command is not `brain_task_dispatch_tick.py --summary`;
- root summary has error_count other than 1;
- embedded tick stdout has schema missing/wrong or `error_count` other than 1, including the structured summary path;
- legacy empty-summary shape has a recovery command that does not name `brain_task_dispatch_tick.py`;
- tick returncode is `"ERROR"`, `"error"`, `"timeout"`, `1`, or missing;
- malformed/non-object JSON appears before the real payload.

## Structured subprocess error handling

Dispatch tick wrappers should parse stdout JSON even when a subprocess exits non-zero. Otherwise a child command can emit useful structured diagnostics (`status`, `gate_status`, `summary`, `errors`) but the parent collapses it to opaque stdout/stderr and loses the semantic signal needed for health gates. On non-zero return code:

1. Try to parse stdout as JSON first.
2. If it is an object, preserve its diagnostic fields and add `cmd` / `returncode` / `stdout` / `stderr` if absent.
3. Force the parent-level status to `ERROR` for any non-zero return code, even if the child JSON claimed `OK`, `PASS`, or `SKIP`; keep the child claim only in a separate field such as `reported_status`.
4. If parsing fails or the payload is not an object, return the opaque error shape with `parse_error`.
5. Avoid double-counting a gate-specific error again in the generic status loop; track `errored_steps`.

Required tests:

- non-zero child emits structured `FAIL` JSON: parent status is `ERROR`, diagnostics remain available;
- non-zero child emits `{"status":"OK"}`: parent status is still `ERROR` and `reported_status` is `OK`;
- non-object JSON stdout is an error with `parse_error`; and
- a gate-specific evidence-spine failure is counted once, not once as a gate and again as a generic step.

## Patch pattern

1. Centralize scheduler-safe semantics in a shared constant such as `SAFE_AUTO_COMPLETER_SEMANTIC_STATUSES`.
2. Use the same constant in both:
   - `build_taskpool_evidence_spine()` gate logic
   - `command_autonomy_readiness()` / CHK-AUTO-COMPLETER-SEMANTICS
3. Extend C-TP/E-TP evidence claims so the proof spine states these are task-level blockers, not scheduler crashes.
4. Add regression fixtures for every safe error class, the recursive evidence-spine self-lock class, plus one missing/unknown cron case that still fails closed. For self-lock fixtures, include both positive and negative cases listed above before marking the semantic scheduler-safe.
5. When raw cron errors are needed for classification, keep them in internal underscore-prefixed fields (for example `_last_error_raw`) and sanitize them out of all evidence payloads before printing JSON or writing reports; add an assertion that `E-TP-AUTO-COMPLETER` and `E-TP-CRON` contain no underscore-prefixed raw fields.
6. Run real gates, not just unit tests:

```bash
python3 ~/.hermes/scripts/test_brain_task_orchestrator.py
python3 ~/.hermes/scripts/test_brain_task_dispatch_tick.py
python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/test_brain_task_orchestrator.py ~/.hermes/scripts/brain_task_dispatch_tick.py ~/.hermes/scripts/test_brain_task_dispatch_tick.py ~/.hermes/scripts/autonomy-precondition.py ~/.hermes/scripts/autonomy-write-guard.py ~/.hermes/scripts/permission_taxonomy.py
python3 ~/.hermes/scripts/brain_task_orchestrator.py evidence-spine --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py lifecycle --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py boundary-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py autonomy-readiness --json
python3 ~/.hermes/scripts/brain_task_dispatch_tick.py --summary --no-state
```

Expected healthy real-gate shape:

- evidence-spine: `status=OK`, `gate_status=PASS`
- selfcheck: `status=PASS`, failures=0
- proof-check: `status=PASS`, failures=0
- lifecycle: `status=PASS`, invalid_count=0
- boundary-check: `status=PASS`, invalid_count=0
- autonomy-readiness: `status=PASS`, `architecture_complete=true`
- dispatch tick summary: `status=OK`, `error_count=0`

## Taskpool progress checks

For user-facing "检查任务池进度" requests, report a concise state snapshot from live gates: total/active/pending/review/done/dispatchable, current `dispatch_hint.next_task_id`, gate health (`selfcheck`, `proof_check`, `boundary_check`, `evidence-spine`, cron/autocompleter), and any scheduling implication such as work-lane preemption. Avoid re-running broad discovery unless the user specifically asks for a live upstream refresh.

## Work-lane preemption when checking taskpool progress

When the user asks whether to temporarily prioritize Hermes self-evolution, ground the answer in the live taskpool gates rather than preference or recency:

1. Run/read `brain_task_orchestrator.py evidence-spine --json` or `boundary-check` / dispatch summary.
2. If `counts.by_lane.work` has active/pending work and the boundary gate reports `evolution_preempted_by_work: true`, recommend continuing work-lane/product tasks unless the user explicitly overrides with a self-evolution priority instruction.
3. If work-lane is empty, blocked, or the user explicitly asks to pause product work, then evolution tasks may be prioritized.
4. Report this as a scheduling decision, not a permanent policy; it depends on the current taskpool state.

## Permission taxonomy coupling

When taskpool write guard changes from legacy `kanban-worker` to `taskpool`, update tests and allowlist fixtures too. Otherwise fail-closed guards will correctly block `auto-claim-and-handoff` with `surface_allowlisted` despite P10 health passing.
