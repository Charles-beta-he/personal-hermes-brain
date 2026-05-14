# Taskpool Multimodel Autorun Pitfalls

Session-derived pitfalls from enabling the full taskpool multimodel intervention pipeline (2026-05-11).

## 1. build_state_command must include --claim flags

**Symptom**: `truth_status: no_claims` in discussion_result, gate always FAIL.

**Root cause**: `consult_models.py state` without `--claim` creates a state with 0 claims. The truth gate checks `claim_count > 0` and returns `no_claims`.

**Fix**: Add explicit claims to `build_state_command`:
```bash
--claim 'C-001:Task decomposition is accurate — ...'
--claim 'C-002:One-shot landing plan exists — ...'
--claim 'C-003:Long-term goal alignment — ...'
```

Claims must align with gate's `criteria_satisfied` axes:
- `accuracy` ← C-001 (task facts grounded)
- `one_shot_landing` ← C-002 (next slice + evidence + rollback)
- `long_term_goal` ← C-003 (lane/project preserved)

After discussion, truth_status progresses: `no_claims` → `unsupported` (claims exist, not verified) → `grounded` (claims verified by evidence).

## 2. dispatch tick errors variable initialization order

**Symptom**: `UnboundLocalError: local variable 'errors' referenced before assignment`

**Root cause**: `errors = []` was placed AFTER the `if os.environ.get(...): event["multimodel_step"] = ...` block, which references `errors`.

**Fix**: Move `errors = []` and `allowed_statuses = {...}` BEFORE the multimodel_step block.

```python
# WRONG
if os.environ.get("HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL") == "1" and not errors:  # errors undefined!
    ...
errors = []  # too late

# CORRECT
errors = []
allowed_statuses = {"OK", "PASS", "SKIP"}
if os.environ.get("HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL") == "1" and not errors:
    ...
```

## 3. autonomy-write-allowlist.json required for auto-claim

**Symptom**: `auto-claim-and-handoff` returns `FAIL_CLOSED` with `reasons: ["autonomy_write_guard_failed"]`.

**Root cause**: The write guard checks `surface_allowlisted` against `/Users/charles/.hermes/config/autonomy-write-allowlist.json`. If file doesn't exist or is empty, the check fails.

**Fix**:
```bash
mkdir -p /Users/charles/.hermes/config
echo '["taskpool", "kanban-worker"]' > /Users/charles/.hermes/config/autonomy-write-allowlist.json
```

## 4. state_path stale directory cleanup

**Symptom**: `IsADirectoryError: [Errno 21] Is a directory: '...state.json'`

**Root cause**: A previous failed run or `mkdir -p` created the state_path as a directory instead of a file.

**Fix**: In `command_multimodel_intervention_step`, before running build_cmd:
```python
if state_path:
    sp = Path(os.path.expanduser(state_path))
    if sp.exists() and sp.is_dir():
        import shutil
        shutil.rmtree(sp, ignore_errors=True)
```

## 5. Discussion timeout: 1200s for 4 models × 5 rounds

**Timing breakdown** (observed):
- Round 1: ~160s (mimo needs retry)
- Round 2-5: ~120-150s each
- Total: 5 rounds × ~150s = ~750s + overhead = ~900-1100s

**DEFAULT_TIMEOUT** = 120s is per-model, not per-discussion. The total process timeout (subprocess.run timeout) must be 1200s.

**mimo-v2.5-pro**: Always executes last (serial mode), parse_status usually "retried" (JSON retry). This is normal behavior, not an error.

## 6. Keyword false positive explosion in task pools

**Observed hit rates** (56 tasks):
- Full-text + broad keywords: 98% (55/56) — useless
- Signal-only keywords (3-25 hits): 80% (45/56) — still noisy
- Structural-first + tight keywords: 32% (18/56) — actionable

**Noise keywords to remove** (>50% hit rate):
- evidence (48/56), local-brain (50/56), l3 (43/56), truth (37/56)
- evolution (35/56), workflow (34/56), skill (31/56)
- 方案 (24/56), certification (24/56), 治理 (22/56)
- 落地 (22/56), loop (20/56), mission (18/56)

**Pattern**: Use `task_keyword_text()` (title + concepts only), not `task_search_text()` (all fields).

## 7. Ratification gate dual-shape support

consult_models.py discussion output has two canonical shapes:

**Shape A** (explicit): `criteria_satisfied.{accuracy, long_term_goal, one_shot_landing}` + `final_design.{next_slice, acceptance_evidence, rollback_boundary}`

**Shape B** (derived): `evidence_bundle.grounding` all verified → accuracy; `fanout_certification.multi_model_certified` → long_term_goal; `verification.guard_metrics` + `rollback_signal.auto_rollback_if` → one_shot_landing

Gate must handle both. If only Shape A is supported, Shape B discussions always FAIL even with 4/4 model approval.

## 8. Convergence stats interpretation

```
total_active:     non-terminal tasks
multimodel_passed: tasks with multimodel_status in {certified, certified_with_minor_risks}
multimodel_triggered: tasks where intervention_required is True
pass_rate:        passed / total (0.0 = no tasks certified yet)
trigger_rate:     triggered / total (>0.8 = most tasks need intervention)
```

- `pass_rate=0` + `trigger_rate>0.8` means the system is correctly identifying tasks that need review, but none have passed certification yet.
- First `pass_rate>0` requires selecting a simple task with clear evidence and high model consensus.
- Complex fix/evaluation tasks naturally have low agreement (<0.7) and are unlikely to pass.

## 9. Allowlist configuration

Three allowlist files control autorun:

| File | Purpose | Format |
|------|---------|--------|
| `state/auto_run_allowlist.json` | Auto-claim eligibility | `["project:xxx", "task:yyy"]` |
| `state/multimodel_intervention_allowlist.json` | Multimodel step filtering | Same format |
| `config/autonomy-write-allowlist.json` | Write guard surfaces | `["taskpool", "kanban-worker"]` |

Empty/missing allowlist = deny (fail-closed). First file missing = no filtering (all tasks eligible).

If `multimodel-intervention-step --task ...` returns `SKIP/allowlist_miss`, compare the task's canonical `project` value with `state/multimodel_intervention_allowlist.json`. Do not assume aliases cover it: `project:uvisa-app-2.0-work` does not match canonical `project:uvisa-app-2.0`. Add the canonical project entry only when the user has authorized taskpool continuation for that project, then rerun and verify the discussion artifact is target-bound to the task.

## 10. Safe summary tick must not inherit expensive multimodel env

**Symptom**: A cron-safe summary heartbeat (`brain_task_dispatch_tick.py --summary`) unexpectedly runs a long `multimodel-intervention-step` because the shell or scheduler environment contains `HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1`.

**Root cause**: Ambient env was treated as sufficient opt-in. This couples cheap health heartbeats to expensive T3/multimodel execution and can make `local-brain-task-dispatch-safe-summary-tick` time out or leave noisy cron errors.

**Fix pattern**:
- Make expensive multimodel execution double-gated: explicit CLI flag (for example `--multimodel-step`) **and** `HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1`.
- Keep no-agent/safe summary wrappers hint-only by default.
- Add a regression that sets `HERMES_LOCAL_BRAIN_AUTORUN_MULTIMODEL=1` and runs `--summary --no-state`, then asserts no `multimodel_step` was executed.
- Wrap subprocess calls with `TimeoutExpired` handling and return structured JSON such as `{"status":"ERROR","error":"subprocess_timeout",...}` rather than crashing the tick.

## 11. Evidence-spine auto-completer errors need semantic classification

**Symptom**: `brain_task_orchestrator.py evidence-spine --json` reports `status=FAIL gate_status=WARN` even though proof/selfcheck/boundary/cron presence all pass. The only failing field is `auto_completer_semantic_status=error` from `local-brain-taskpool-auto-completer`.

**Root cause**: Cron `last_status=error` is too coarse. It can mean scheduler/runtime failure, but it can also mean a task-level state such as:
- `RuntimeError: Request timed out` from the agent wrapper;
- `timeout_recorded` / `subprocess_timeout` after a bounded command;
- an evidence/advisory slice completed but T3 ratification is still `not_certified` or `discussion_result.json` is missing;
- the task was correctly held out of `done` because certification is incomplete.

**Fix pattern**:
- Classify retryable runtime timeouts separately (for example `retryable_runtime_timeout`) and set `safe_for_next_tick=True`; they require scheduler retry or deterministic replacement, not a taskpool infrastructure red alarm.
- Classify long-running certification/advisory states separately (for example `long_running_certification_pending` / `advisory_not_ratified`) when `last_error` says `truth_grounded_advisory_not_ratified`, `not_certified`, missing `discussion_result.json`, `cannot closeout`, or “T3 still running”. These are task-level blockers/provenance, not scheduler health failures.
- Keep real unknown `error` fail-closed.
- Add evidence-spine regressions for each semantic class with all required cron jobs present, asserting PASS/OK only for known safe classes.

## 12. Parallel consult tick directories must be unique and target-bound

**Symptom**: `multimodel-intervention-parallel-step` reports multiple advisory tasks as `PASS_ADVISORY_ONLY`, but their `multimodel_last_discussion_artifact` all point at the same `tick-YYYYMMDD-HHMMSS/discussion_result.json`. Inspecting that artifact shows `context.target_task_id` / `evidence_bundle` belongs to only one of the tasks; the other task notes have a polluted advisory writeback.

**Root cause**: `consult_models.py run` used second-resolution tick IDs (`tick-%Y%m%d-%H%M%S`). Parallel workers launched inside the same second wrote into the same tick directory. Later writers overwrote `state.json` / `discussion_result.json`, and the orchestrator's “latest tick” fallback could stamp the wrong artifact onto several tasks.

**Fix pattern**:
- Generate tick IDs with microseconds + pid + chain prefix + random suffix, not seconds only. Example helper:
  ```python
  def make_tick_id(chain_id: str = "") -> str:
      stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
      chain_prefix = re.sub(r"[^A-Za-z0-9]+", "", str(chain_id or "nochain"))[:8] or "nochain"
      return f"{stamp}-p{os.getpid()}-{chain_prefix}-{uuid.uuid4().hex[:8]}"
  ```
- In `brain_task_orchestrator.py`, capture each subprocess stdout/stderr and extract `discussion.result_file` from the exact consult output before falling back to tick directory scanning.
- After any parallel run, verify every result's `discussion_path` is unique when tasks are distinct, and load each `discussion_result.json` to assert `context.target_task_id` (or stamped binding) matches the result `task_id`.
- If polluted advisory writebacks already exist, do not treat them as consumed. Either rerun those tasks after the unique tick fix or rewrite the affected task frontmatter to `multimodel_status: not_certified`, `multimodel_round_status: stale_artifact`, and clear stale `multimodel_last_discussion_artifact` / `multimodel_ratification_artifact`.
- Add regressions in both layers: a consult_models unit test proving 100 same-second `make_tick_id()` calls are unique, and a task orchestrator test proving `extract_discussion_result_path_from_stdout()` handles JSON, noisy JSON, and `Artifacts in ...` stderr forms.
