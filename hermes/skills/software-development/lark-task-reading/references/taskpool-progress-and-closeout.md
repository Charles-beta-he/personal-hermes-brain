# Taskpool progress and closeout check

Use this pattern when the user asks "检查任务池进度", "看任务池", "继续推进任务池", or after adding/closing Lark-derived tasks into the local brain taskpool.

## Intent

A progress check is not just a status summary. It should prove the taskpool's current state, close any claimed work that already satisfied deterministic gates, refresh derived dashboards, and identify the next dispatchable task with its routing constraints.

## Minimal loop

1. Refresh the local taskpool status from the canonical brain/Hermes taskpool scripts, not from memory or stale summaries.
2. For any task left in `claimed`, `running`, or `review`, inspect whether deterministic evidence already exists:
   - implementation files or artifacts exist
   - task-specific tests/compile/checks pass
   - evidence notes/manifests verify
   - ratification/proof gates pass when required by task metadata
3. If the task is truly complete, move it through the finite lifecycle instead of leaving it half-open:
   - `claimed -> running -> review -> done`
   - record the evidence path and verification results in the task note/proof artifact
4. Run the taskpool health gates after closeout:
   - proof/evidence check
   - taskpool selfcheck
   - dashboard refresh/write
   - next-dispatchable selection
5. When pending tasks are not advancing, diagnose the scheduler/executor gap before calling them blocked:
   - inspect priority mode (`work-first` vs `evolution-first`) and whether work is intentionally preempted by evolution
   - for paused T3/multi-model/economy-gated items, do not reflexively rerun expensive ratification; pick the highest-leverage item and apply a deterministic targeted evidence fix first, then run proof/selfcheck/dashboard and lifecycle closeout
   - for Hermes provider/quota tasks, keep evidence clean-room: sanitize quota/usage state and logs before persistence, preserve numeric usage fields, and never store credentials or prompt/completion text; see `hermes-agent/references/provider-quota-evidence-hygiene.md`
   - check auto-run allowlists/project profiles; distinguish `allowlist_miss` from true ineligibility
   - run the bounded autorun step directly and inspect `claimed`, `advanced`, and `reasons`; `policy_missing` means safe fail-closed/no-op, not successful task progress
   - read dynamic runner/cron logs as execution evidence only if they show a claim/advance/closeout; `last_status=ok` can mean the no-op safety path succeeded
   - inspect multi-model intervention separately from execution: a `PASS_ADVISORY_ONLY`, `FAIL`, or `SKIP/no_discussion_result` gate cannot move a task to done by itself
   - for parallel multimodel steps, load each returned `discussion_path` and verify it is target-bound to the same `task_id`; if several different tasks point at the same tick artifact, treat the writebacks as polluted/stale and rerun after fixing tick uniqueness rather than consuming them
   - report whether the selected next task is dispatchable, eligible, allowlisted, policy-authorized, and certified; these are separate gates
6. Report four concise blocks:
   - tasks closed this pass
   - gates run and PASS/BLOCKED status
   - current pool counts / dispatchable lanes
   - exact next task, including project/profile, architecture target, and whether multi-model intervention is required

## Multi-model advisory drain pattern

When taskpool progress shows queued multi-model advisory items, treat advisory consumption as a bounded queue-drain with proof of target binding, not as implementation closeout:

1. Run/consume every currently actionable advisory item until the queue is empty or only paused/economy-gated items remain.
2. For each produced `discussion_result.json`, open or verify the artifact and confirm it is target-bound to the exact task id/title/profile being updated. A shared tick path or generic PASS is not enough.
3. Classify `PASS_ADVISORY_ONLY` as advisory provenance only. It may unblock planning or review notes, but it must not mark a task `done` unless deterministic completion evidence and the task's closeout gates also pass.
4. After advisory drain, run proof/selfcheck/dashboard gates and then run auto-close in fail-closed mode. A good result may be `closed_count: 0` if the remaining review tasks lack test/build/browser/curl/commit or contract evidence.
5. Report paused items separately from actionable queue depth. Include pause reason and failed-round count (for example T3 economy maxed out) so the next operator knows whether the next step is targeted evidence fix, human review, or gate tuning.
6. In the final progress report, distinguish:
   - advisory items consumed
   - artifacts target-bound PASS/FAIL
   - auto-close closed/skipped/error counts
   - active pool counts by status/lane
   - next dispatchable task and why it can/cannot advance

## Closeout semantics

- Do not call a task "done" from implementation evidence alone if its metadata requires ratification, remote monitor, or user notification; mark the missing gate explicitly.
- If a generated artifact wraps a receipt/proof object, make the verifier accept both the wrapper and bare receipt before relying on generate -> verify as a closed loop.
- If generated evidence uses taskpool-specific prefixes such as `live_lark_snapshot:` or `classification:`, the lifecycle gate should treat them as structured provenance, but they are not completion proof by themselves.
- For Lark real-API review tasks using `project-evidence-real-api-review-done`, auto-close should fail closed unless there is concrete test/build/browser/curl/commit verification evidence plus real-api/backend/frontend contract evidence. A Lark snapshot or classification file alone can justify priority/routing, not `done`.
- If a list command truncates identifiers that users/agents need to feed into a later generate/scan command, treat that as a tool bug: output full IDs by default and truncate only in display-only summaries.
- If evidence manifests fail because a source note changed after sidecar generation, update the sidecar hash only after re-reading the changed note and verifying the content still supports the claim.

## Reporting style

For 贺程, prefer terminal-readable, direct progress reporting:

- say what changed, not what you planned
- include commit hash/path only when a local commit was actually made
- avoid broad narrative; list concrete files/gates/next task
- distinguish `closed`, `closed_with_blocker`, and `not_closed`

## Pitfalls

- Do not leave a claimed task open after all gates pass; the next progress check should not have to rediscover the same closure.
- Do not spend the whole pass on optional documentation if proof/selfcheck/dashboard have not been refreshed.
- Do not report old dashboard counts after modifying task status; regenerate the dashboard first.
- Do not create one narrow skill per closed task; capture reusable taskpool closeout mechanics here and keep session-specific evidence in task notes/artifacts.