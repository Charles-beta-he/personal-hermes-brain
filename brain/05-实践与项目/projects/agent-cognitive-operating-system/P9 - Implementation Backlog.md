---
type: backlog
status: active
layer: P9
created: 2026-05-07T00:05:39+08:00
concepts: [p9, implementation-backlog, agent-cos]
open_backlog_count: 0
unchecked_checkboxes: 0
---

# P9 - Agent COS Implementation Backlog

## Closed in this landing slice

- [x] P0 define A+ rubric with evidence boundary.
- [x] P0 create no-missing-pair complementarity matrix.
- [x] P0 create cross-disciplinary master table where every pairing is A+ under the rubric.
- [x] P0 create local-first `agent_cos_selfcheck.py`.
- [x] P0 wire project/playbook/atom/review/task/evolution/dashboard artifacts.
- [x] P0 verify with sync/reindex/search/structural audit.

## Accepted non-blocking future improvements

| Item | Why non-blocking | Gate before reopening |
|---|---|---|
| cron integration | current request is landing + self-check, not scheduler mutation | add only after P10 health accepts extra cron cost |
| per-pair benchmark | matrix already has evidence gates; benchmark is refinement | require stable usage traces over 4 weeks |
| main hierarchy rewrite | explicitly rejected by overlay-routing gate | user approval + reversible migration proof |

## No-open-backlog register

open_backlog_count: 0
unchecked_checkboxes: 0

## Search Aliases

Agent COS backlog zero open_backlog_count 0 unchecked_checkboxes 0 A+互补矩阵

## Ratification-first hardening (2026-05-07T00:54:55+08:00)

- [x] Split deterministic matrix completion from ratification certification.
- [x] Add `ratification_gate.py` as the only certification transition gate.
- [x] Add evidence bundle and issue ledger artifacts.
- [x] Fail closed when no scoped Agent-COS `discussion_result.json` exists.
- [x] Upgrade to `FULLY_CERTIFIED` only after multi-model discussion returns no unresolved severity>=3 issues and `ratification_gate.py` passes. Evidence: [[05-实践与项目/projects/agent-cognitive-operating-system/Ratification Decision]] and `ratification-discussion-result-2026-05-07.json`.
