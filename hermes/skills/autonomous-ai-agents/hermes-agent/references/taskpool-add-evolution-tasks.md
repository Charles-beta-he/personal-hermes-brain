# Taskpool add: evolution-task requirements and verification

Use when adding self-optimization / evolution tasks via `brain_task_orchestrator.py add`.

## Required fields for `--lane evolution`
If omitted, add can fail with:
`evolution tasks require architecture alignment fields; missing/invalid=['capability_delta', 'anti_drift_check', 'acceptance_evidence']`

Always provide:
- `--capability-delta`
- `--anti-drift-check`
- `--acceptance-evidence`

Typical durable fields for repo/article analysis tasks:
- `--architecture-target local-brain|skill-graph|taskpool` depending the improvement surface
- `--objective` explaining what to analyze and how it maps back into Hermes
- `--accept` defining completion evidence and whether skills/references/control-plane updates are expected

## Verification pattern after add
A successful add may still report an event-hook error block like:
- `event_hook.status=ERROR`
- `returncode=2`

Do not treat the task as failed until you verify the durable outputs:
1. `created` task file path exists
2. derived refresh updated `sorted_pool` and dashboard/control-center paths
3. task appears in `brain_task_orchestrator.py list --json`
4. task appears in `任务池-排序.md`

This session showed task creation succeeding while autorun still advanced the queue despite hook errors.

## Practical batch-add pattern
For a batch of "analyze repo/article and optimize Hermes" tasks:
- keep `project=hermes-agent`
- keep `lane=evolution`
- choose `architecture-target` by the intended improvement area
- tailor `concepts`, `capability_delta`, `objective`, and `acceptance_evidence` per source
- after batch add, verify with `list --json`, `任务池-排序.md`, and dashboard status rather than relying only on hook exit code

User preference / default workflow learned from session:
- when the user pastes external repo/article links and asks to "add to taskpool", act directly instead of asking for extra framing
- batch-add all provided links in one pass when the intent is clearly repetitive
- keep the task title/objective explicitly mapped back to Hermes self-optimization rather than mirroring the source title only

## Retry / timeout pitfall
If `brain_task_orchestrator.py add` times out or gets interrupted, do not blindly rerun the same add command first.

Verify whether the task already landed by checking:
1. `brain_task_orchestrator.py list --json`
2. `任务池-排序.md`
3. `05-实践与项目/tasks/` for the expected slug

Reason: retrying after a partial-success add can create duplicate tasks with a `-2` suffix. If duplication already happened, keep the original task and transition the duplicate to `archived` with evidence explaining it was created by a retry after timeout/interruption.
