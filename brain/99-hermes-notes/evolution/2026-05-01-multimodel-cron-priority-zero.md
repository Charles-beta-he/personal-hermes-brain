# Evolution Event: Multi-Model Cron Reliability + Priority Queue Closure

**Date:** 2026-05-01
**Type:** runtime-improvement | governance-hardening | workflow-closure
**Source:** user request: "loop 多模型思考修复直至无优先级"

## Source Signal

Hermes is operated as a local personal assistant that tracks upstream and self-adjusts through local git/governance artifacts. Remote push is not required; upstream pull is treated as controlled upgrade.

The active self-evolution loop found several runtime/governance regressions:

- Multi-model smoke cron jobs failed because cron `script` fields contained arguments and were interpreted as single file paths.
- Multi-brain nightly cron had the same script+args path issue.
- Nightly autonomous evolution and cron-health report were exposed to idle-timeout risk because prompts were too open-ended and could run additional commands.
- Actual usage score had degraded to Grade D (`47.98` observed before repair) due to weak real-call telemetry / failed cron jobs.
- Self-improvement priority queue contained stale/ghost priorities from old transient tool failures and old Darwin baseline rows.

## Hermes-Specific Output

### Files Created

- `~/.hermes/scripts/multi-model-smoke-every4h-wrapper.py`
- `~/.hermes/scripts/multi-model-smoke-daily-full-wrapper.py`
- `~/.hermes/scripts/multi-brain-nightly-wrapper.py`
- `~/.hermes/scripts/test_self_improvement_pipeline.py`
- `~/.hermes/notes/evolution/2026-05-01-multimodel-cron-priority-zero.md`

### Files Modified

- `~/.hermes/scripts/self-test.py`
  - Added compile checks for the three cron wrapper scripts.
  - Added self-improvement pipeline regression tests.
- `~/.hermes/scripts/self-improvement-pipeline.py`
  - Added stale transient signal suppression when current ops are green.
  - Changed low-skill priority detection to use the latest Darwin row per skill.
  - Changed Darwin TSV loading to read all rows by default.
  - Fixed Darwin TSV parser to accept existing 8-column accepted rows.
- `~/.hermes/cron/jobs.json` via cron job updates:
  - `2c14ca2a9bd2` → `multi-model-smoke-every4h-wrapper.py`
  - `42baeebb646c` → `multi-model-smoke-daily-full-wrapper.py`
  - `724629d0013e` → `multi-brain-nightly-wrapper.py`
  - `600370f80d83` → bounded `autonomous-evolution-nightly.py` summary prompt
  - `30842cd6b22b` → bounded `cron-health-quarantine.py` summary prompt

## Multi-Model Evidence

The repair was validated by actual multi-model smoke/usage telemetry rather than synthetic hook-only traces:

- Every-4h smoke cron latest output: `status=ok`, `passed=3/3`, no `Script not found`, no idle timeout.
- Daily full smoke cron latest output: `status=ok`, `passed=4/4`, no `Script not found`, no idle timeout.
- Multi-brain nightly latest output after wrapper update: no `Script not found`, no idle timeout; bounded timeout recorded for long consult while state generation and usage refresh remained healthy.
- Usage score after repair: `91.67`, Grade `A`.

## Verification Results

Commands run after repair:

```bash
python3 ~/.hermes/scripts/self-test.py
python3 ~/.hermes/scripts/usage-score.py || true
python3 ~/.hermes/scripts/cron-health-quarantine.py
python3 ~/.hermes/scripts/self-improvement-pipeline.py --preview || true
```

Observed results:

```text
Self-Test Results: 58/58 passed
ALL PASS — system is operational
```

```text
usage-score: 91.67 / A
model_breadth_24h: 25/25
real_call_integrity: 15/15
cron_green: 10/10, ok=20/20, bad=0
ensemble_executed: 15/15
ratification_corpus: 10/10
```

```json
{
  "mode": "report",
  "bad_count": 0,
  "bad_lines": []
}
```

```text
Self-Improvement Pipeline — Priority Queue
✓ 无待办改进项 — 系统健康
```

Latest key cron outputs checked:

- `2c14ca2a9bd2` (`multi-model-smoke-every-4h`): no `Script not found`; no idle timeout; passed `3/3`.
- `42baeebb646c` (`multi-model-smoke-daily-full`): no `Script not found`; no idle timeout; passed `4/4`.
- `724629d0013e` (`multi-brain-consult-models-nightly`): no `Script not found`; no idle timeout; `status=timeout_recorded`; usage refresh `91.67 / A`.
- `600370f80d83` (`夜间自主进化审计`): no idle timeout after bounded prompt; job completed `ok`.
- `30842cd6b22b` (`cron-health-quarantine-report-6h`): no idle timeout; `bad_count=0`.

## Level Classification

### Level 0 — User Data / Update-Safe

All concrete artifacts in this event are Level 0 and live outside the upstream Hermes git tree:

- `~/.hermes/scripts/*wrapper.py`
- `~/.hermes/scripts/test_self_improvement_pipeline.py`
- `~/.hermes/scripts/self-test.py`
- `~/.hermes/scripts/self-improvement-pipeline.py`
- `~/.hermes/cron/jobs.json`
- `~/.hermes/notes/evolution/2026-05-01-multimodel-cron-priority-zero.md`

These are update-safe against `git pull` of `~/.hermes/hermes-agent`.

### Level 1 — Repo-Local

None in this event.

### Level 2 — Vendor Core Patch

None in this event.

## Pitfalls Discovered

1. Cron `script` must be a pure script path.
   - Passing `script.py --arg value` causes pre-run injection to treat the entire string as one file path.
   - Fix pattern: create a no-argument wrapper and put parameters inside the wrapper.

2. Cron script success is not the same as cron-agent success.
   - A deterministic script can finish, then the summarizing agent can still idle-timeout if the prompt asks it to do extra work.
   - Fix pattern: script-first, bounded prompt, explicit non-empty final response.

3. Historical signals can become priority ghosts.
   - Old transient terminal/tool failures should not remain HIGH priority when current cron/usage/self-test health is green.
   - Fix pattern: suppress stale transient failures after a green ops window.

4. Darwin TSV format was looser than the loader assumed.
   - Existing accepted rows can have 8 columns, not 9.
   - The loader must parse actual historical data shape, not an imagined stricter schema.

5. Row truncation can hide the true latest skill state.
   - Loading only the last 50 Darwin rows can miss newer accepted rows if file ordering / history shape is not aligned with assumptions.
   - Fix pattern: load all rows by default, then reduce by latest timestamp per skill.

## Upgrade Survival

- No remote push required.
- No PR required.
- `~/.hermes/hermes-agent` remains an upstream-tracking source tree.
- This event's artifacts are Level 0 under `~/.hermes/`, so they survive upstream `git pull` of the Hermes source repository.
- Future controlled upgrades should still run:

```bash
python3 ~/.hermes/scripts/self-test.py
python3 ~/.hermes/scripts/usage-score.py || true
python3 ~/.hermes/scripts/cron-health-quarantine.py
python3 ~/.hermes/scripts/self-improvement-pipeline.py --preview || true
```

## Decision Record

| Decision | Rationale |
|----------|-----------|
| No push to upstream | Hermes is a local personal assistant / private evolution environment. |
| No PR needed | These changes are local operations/governance artifacts, not upstream product contribution. |
| Use wrapper scripts instead of patching cron engine | Smaller blast radius; update-safe Level 0 fix; avoids vendor-core divergence. |
| Bound cron prompts | Prevents idle-timeout and recursive/extra command execution. |
| Treat `timeout_recorded` as auditable degraded success for long consult | Long-running consult may exceed bounded cron budget, but state and usage telemetry remain recorded. |

## P1/P2 Candidates

- P2: add direct regression tests for cron `script` values to ensure no job contains spaces/arguments in `script`.
- P2: improve daily full wrapper to include usage score/grade directly in its final JSON summary.
- P3: improve `route_diversity` score, currently lower than other usage components, while keeping real-call integrity high.
- P3: revisit `feeds` skill audit result (`60 -> 60`, missing boundary conditions/examples) as a normal skill-quality improvement, not as current ops priority.
