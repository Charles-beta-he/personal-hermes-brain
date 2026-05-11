# Taskpool PUA-loop hardening closeout pattern

Use this when landing local-brain/taskpool autonomy, multi-model ratification, evidence-spine, or PUA-loop control-plane changes.

## Core sequence

1. Build claim-linked evidence first; do not rely on broad raw status JSON.
2. Run T3 with the exact four canonical participants when the user requires full certification:
   - `claude-opus-4-7`
   - `gpt-5.5`
   - `deepseek-v4-pro`
   - `mimo-v2.5-pro`
3. Require the local ratification gate to return `PASS` and `decision=LOOP_DONE` before stopping the loop.
4. After any post-certification reviewer blocker fix, treat the previous certification as stale for the changed diff; rerun deterministic gates and a final scoped reviewer.
5. Commit only after deterministic gates + reviewer PASS; use scoped pathspecs in the dirty `.hermes` repo and do not push by default.

## High-score task anti-stall rule

When a task appears as a high score (for example `score >= 400`) and has not become `done` for a long time, do not equate “high score” with “worker is stuck”. Classify the state first:

- `claimed/running + stale_claim=true` → real execution deadlock; let guardian/reconcile release or reset, then dispatch again.
- `review + multimodel_status not in {certified, certified_with_minor_risks}` → not execution-stuck; it is intentionally stopped at closeout gate. The next action is target-bound T3/four-model ratification or human/code review, not another implementation worker.
- `pending + dispatchable=true` → queue/scheduler priority issue; verify work-lane preemption and boundary conflicts.
- `not dispatchable` outside review/claimed/running → inspect lifecycle/mission gate before expecting worker progress.

Human reports and watchdogs should include this classification and the exact next gate, so the user sees “why not done” instead of a vague long-running task.

## Landing in Hermes taskpool

The taskpool `multimodel-intervention-*` commands must generate T3/quorum-4 run commands for PUA-loop closeout. A T2/quorum-3 artifact is only advisory for high-risk/closeout tasks and should be classified as `not_certified` by `ratification-gate` when the task requires full certification.

`taskpool_watch_report.py` should classify high-score unfinished tasks by state (`stale_claim_stuck`, `review_gate_not_closed`, `not_dispatchable`, `active_high_score`) and print the exact next gate.

After `consult_models.py run` creates `discussion_result.json`, the taskpool runner must stamp the exact task binding (`task_id`, `target_task_id`, `target_task_path`, and state hash/provenance) into the discussion artifact before calling `ratification-gate`. The gate must still fail on non-approve votes/unresolved issues, but it should not permanently fail with `target_task_binding_missing` when the runner knows the candidate came from the current task state.

Common pitfall: do not let the dry-run plan say “PUA-loop requires T3 4/4” while the generated `run_discussion_command` still uses `--tier T2 --quorum 3`. That creates the Score445 symptom: evidence looks approved, but the local ratification gate correctly refuses `done` because DeepSeek/4th vote and target binding are missing.

## User-pressure / repeated-prompt handling

If the user repeats the same request such as “多模型思考如何避免这种情况，并pua-loop落地”, treat it as PUA pressure to continue landing, not as a request to restate the previous explanation. Each repeated loop should take one additional concrete step, for example:

1. Poll any running background T3/quorum-4 process and report status only after acting.
2. Add or tighten a regression test that would catch the exact failure mode.
3. Patch stale skill/docs that still encode the old behavior.
4. Re-run deterministic checks (`py_compile`, focused tests, dry-run command shape, `diff --check`).
5. Make a scoped local commit and show the new commit hash.

Do not output a near-duplicate summary unless no further safe tool action exists. The completion standard is “wrong path becomes impossible or test-failing”, not “agent promises to remember”.

## Fail-closed invariants to enforce

Evidence-spine and dispatch tick:
- `evidence-spine` must expose both `status` and `gate_status`.
- If `gate_status != PASS`, either the command must return non-OK/non-zero or the caller must explicitly treat it as an error.
- `brain_task_dispatch_tick.py` must inspect `event["evidence_spine"]["gate_status"]`, not only `status`.
- Required taskpool cron jobs must be readable and present.
- Auto-completer semantic status must be `ok` or `ok_with_task_blocker`, and `safe_for_next_tick is True`.

Cron evidence redaction:
- Never export raw cron `last_error`, `last_delivery_error`, `deliver`, or `script` fields into evidence/log artifacts.
- Export only redacted tails plus booleans such as `delivery_configured` / `script_configured`.
- Test redaction for more than `token=...`: include `Authorization: Bearer ...`, bare `Bearer ...`, query parameters (`access_token=`, `token=`, `api_key=`), Slack/OpenAI-style tokens, and delivery/script values.

Ratification/certification verifier:
- Validate artifact shape before dereferencing. Non-dict top-level/final_design, non-list `ratification_votes`, and malformed `models_consulted` must return structured `FAIL` / `continue_loop`, never traceback.
- Do not build `set(models_consulted)` until it is confirmed to be a list of non-empty strings.
- Failure taxonomy must also be defensive; diagnostic code must not crash while explaining a failed gate.
- Exact participant identities matter at the certification boundary; aliases or duplicate/fake voters cannot satisfy full T3.
- Treat `truth_can_certify=true` plus target binding as fact grounding only. If planner merge says `patches=[]` while `planner_patch_summary.certification_intent=implementation_required`, or if 3/4 planners vote noop but a lone minority concrete patch sets implementation intent, keep `not_certified` and classify as a merge/noop-vs-implementation arbitration issue. Do not auto-done; either downgrade the minority patch to advisory with explicit rationale, include the patch in `current_best.patches`, or require human/code-review signoff.

Boundary/mission metadata:
- `boundary-diff-check` must fail on malformed `loc_budget` and negative `--diff-lines`; treating bad budget as SKIP creates a bypass.
- Tightening canonical task validators can break real vault data even when temp-vault tests pass. Always run real vault selfcheck/proof/boundary after changing fail-closed contracts.
- For certified mission-envelope tasks, `ratification_artifact` must be a structured reference: `file:`, `artifact:`, `url:`, or `proof:`. Bare absolute paths can fail the mission envelope validator.

## Verification bundle

After code changes:

```bash
python3 -m py_compile ~/.hermes/scripts/brain_task_orchestrator.py ~/.hermes/scripts/brain_task_dispatch_tick.py
python3 ~/.hermes/scripts/test_brain_task_orchestrator.py
python3 ~/.hermes/scripts/test_brain_task_dispatch_tick.py

export HERMES_BRAIN_VAULT=/Users/charles/Documents/brain
unset OBSIDIAN_VAULT_PATH || true
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py boundary-check --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py autonomy-readiness --json
python3 ~/.hermes/scripts/brain_task_dispatch_tick.py --summary
python3 ~/.hermes/scripts/brain_task_orchestrator.py ratification-gate --task TASK_ID --discussion-result /path/to/discussion_result.json --json
```

Before commit in `.hermes`:

```bash
cd ~/.hermes
git diff --cached --stat
[ -z "$(git diff --cached --name-only)" ] || git restore --staged .
git add scripts/brain_task_orchestrator.py scripts/brain_task_dispatch_tick.py scripts/test_brain_task_orchestrator.py scripts/test_brain_task_dispatch_tick.py
git diff --cached --name-only
git diff --cached --check -- scripts/brain_task_orchestrator.py scripts/brain_task_dispatch_tick.py scripts/test_brain_task_orchestrator.py scripts/test_brain_task_dispatch_tick.py
git commit -m "chore(taskpool): harden pua loop autonomy gates"
git log -1 --oneline
git status --short -- scripts/brain_task_orchestrator.py scripts/brain_task_dispatch_tick.py scripts/test_brain_task_orchestrator.py scripts/test_brain_task_dispatch_tick.py
```
