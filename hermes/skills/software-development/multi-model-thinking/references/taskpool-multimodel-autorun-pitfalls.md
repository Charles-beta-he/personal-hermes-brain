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
