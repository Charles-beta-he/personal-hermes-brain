# Hook automation verifier gates

Use this reference when multi-model analysis is applied to hooks, agent control-flow automation, task creation, state-machine continuation, or any feature that can recursively trigger the agent.

Core lesson: model agreement is not enough for hook automation. Hook payloads, event ordering, blocking semantics, state contracts, and recursion behavior must be empirically verified before write-capable implementation. If any contract is unknown, the design must fail closed.

## Required gates before implementation

1. Runtime hook fixture gate
   - Register only a logging/no-op hook first.
   - Capture the exact stdin payload in a throwaway session.
   - Verify field names, nullability, event name, task id/path, session id, cwd/project path, parent/child linkage, and tool input/output if present.
   - Verify whether the hook fires per tool call, per created task, or another unit.
   - Verify timing: whether backing JSON/state files exist when the hook fires.
   - Verify blocking, timeout, stdout/stderr, and failure behavior.

2. Hook registration and ordering gate
   - Inspect user settings and plugin hook manifests before adding global hooks.
   - Check for Stop/SubagentStop/Notification/PreToolUse conflicts.
   - Treat missing hook registration as expected; add dry-run/no-op first.
   - Keep hook stdout small; write verbose logs to files, redacting secrets.

3. State contract gate
   - Document the state file schema before writing it.
   - Identify required fields, optional fields, stale-state rules, project/session scoping, global fallback behavior, atomic write rules, and cleanup/cancel behavior.
   - If state is consumed by another hook, test the consumer with fixture state before writing producer code.

4. Aggregate artifact schema gate
   - Treat a manually created aggregate task as a golden fixture candidate, not as a canonical schema.
   - Compare child task fixtures and aggregate fixture.
   - Decide whether extra metadata is allowed; if unknown, use a sidecar index instead of mutating task JSON.

5. Debounce/idempotency gate
   - N related events must converge to exactly one aggregate artifact.
   - Define a deterministic idempotency key from session, project, sorted child ids, and turn/prompt hash when available.
   - Use a lock/atomic rename strategy for concurrent hook processes.
   - Event replay must be safe.

6. Recursion guard gate
   - Any hook-created artifact must carry a source marker or be recorded in a sidecar ledger.
   - Hook-created aggregate artifacts must not trigger a new aggregate.
   - Add hard rate limits and a kill switch.

7. Session/project isolation gate
   - Never infer scope from “latest task” or global fallback when session/project is missing.
   - Missing session_id or project_path should no-op.
   - Cross-session and cross-project leakage must be explicit rollback triggers.

8. Rollout/rollback gate
   - Start with dry_run or create_only mode.
   - Require an env/config kill switch.
   - Record counters: event count, schema errors, aggregate created, duplicate aggregate, recursive trigger, cross-session leak, hook timeout/error, main pass rate.
   - Roll back if duplicate_aggregate_count > 0, recursive_taskcreate_count > 0, cross_session_leak_count > 0, cross_project_leak_count > 0, or main_pass_rate drops materially.

## Interpretation of multi-model outputs

If a T3/four-model run times out after producing planner files and `merged_plan.json` but no completed ratification artifact, treat it as useful weak evidence only. Report fanout status and consensus metrics, but do not claim certification. Use the output to identify verifier gaps and next evidence requests.

## Default recommendation

For hook-to-continuation automation, the safe first implementation target is usually `dry_run` or `create_only`, not automatic continuation/start. Escalate to state mutation or direct continuation only after fixture, schema, debounce, recursion, isolation, and rollback gates pass.