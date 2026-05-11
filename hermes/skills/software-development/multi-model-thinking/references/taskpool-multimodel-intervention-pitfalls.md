# Taskpool Multimodel Intervention — Pitfalls & Real-Run Findings

Captured from 2026-05-11 PUA-loop session implementing D2-D20.

## Claims Injection (Critical)

`build_state_command` without `--claim` flags → `truth_status=no_claims` → gate FAIL (23 failures).

Fix: inject 3 explicit claims aligned with gate criteria:
```bash
--claim 'C-001:Task decomposition is accurate — the identified task, lane, priority, and trigger reasons match the canonical task note'
--claim 'C-002:One-shot landing plan exists — a directly executable next slice with acceptance evidence and rollback boundary can be produced'
--claim 'C-003:Long-term goal alignment — the solution preserves lane/project/architecture_target and does not let evolution preempt work delivery'
```

After fix: `truth_status` improved from `no_claims` → `unsupported` (claims exist, 0 verified, coverage=0.0). Evidence linking happens during discussion phase automatically.

## Real-Run Timeline (4 models, 5 rounds)

```
Round 1: ~3min (claude→gpt→deepseek→mimo, mimo retried)
Round 2: ~3min (same order)
Round 3: ~3min
Round 4: ~3min
Round 5: ~3min
Total: ~15-18min for 5 rounds × 4 models = 20 API calls
```

mimo-v2.5-pro consistently uses `retried` parse status (JSON extraction retry) but eventually succeeds. No timeout issues with 1200s total.

## Gate Fail Patterns

### Run 1: openai-cli evaluation task (no claims)
- truth_status: no_claims
- agreement: 0.65 (all axes)
- votes: 4/4 amend
- issues: 10 unresolved (sev 3-4)
- Root cause: state had 0 claims + evaluation task naturally produces noop votes

### Run 2: uvisa P0 work task (3 claims)
- truth_status: unsupported (3 claims, 0 verified)
- agreement: 0.65 (all axes)
- votes: 2 reject + 2 amend
- issues: 16 unresolved (sev 3)
- Root cause: claims exist but evidence not linked + complex task with genuine disagreement

### Key Insight
Gate FAIL is correct behavior for these tasks. The system is working as designed:
- Fail-closed: no task mutation on uncertified discussions
- Models genuinely disagree on complex tasks
- Evaluation tasks naturally produce noop votes
- Pass rate > 0 requires: simpler tasks + evidence-linked claims + model consensus

## Keyword Noise Analysis

Hit frequency in 56-task corpus (top noise keywords to REMOVE):
```
50/56  local-brain     (long-term)
48/56  evidence        (accuracy)
43/56  l3              (long-term)
37/56  truth           (accuracy)
35/56  evolution       (long-term)
34/56  workflow        (one-shot)
31/56  skill           (long-term)
24/56  方案            (one-shot)
24/56  certification   (accuracy)
22/56  治理            (long-term)
22/56  落地            (one-shot)
20/56  loop            (one-shot)
18/56  mission         (one-shot)
```

Signal keywords (3-25 hits, KEEP):
```
 5/56  token, 迁移, 介入
 4/56  quota, 分解, l0
 3/56  权限, 控制面, 技能树, 融合, l1, l2
 2/56  拆解, l5, lx, 控制台, 事实源
 1/56  资金, 正确
```

Trigger rate evolution:
- Full-text + broad keywords: 98% (55/56) — useless
- Signal-only keywords: 80% (45/56) — still noisy
- Structural-first + tight keywords: 32% (18/56) — actionable

## State Path Safety

`consult_models.py state --out /path/to/file.json` fails with `IsADirectoryError` if the path exists as a directory (created by prior `mkdir -p` or stale run). Fix: check `sp.exists() and sp.is_dir()` → `shutil.rmtree()` before running build command.

## Tick Integration

`allowed_statuses` in dispatch tick error loop must include `"SKIP"` for `multimodel_step`. Otherwise, when env var is not set, the step returns SKIP which gets counted as ERROR.

## Cron Job

```bash
# Created: every 6h
# job_id: 1883fd365c15
# next_run: 2026-05-11T17:15:49+08:00
```

For faster convergence testing, temporarily reduce to every 1h:
```bash
hermes cron update 1883fd365c15 --schedule "every 60m"
```
