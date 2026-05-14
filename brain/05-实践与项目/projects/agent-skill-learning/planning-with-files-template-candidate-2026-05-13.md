---
type: template-candidate
project: hermes-skill-learning
candidate: planning-with-files
created: 2026-05-13T15:51:53+08:00
status: candidate
---

# Planning with Files 候选模板

> 目的：把 plan / workpad / taskpool 状态写入一个自包含文件，使 context compaction、session restart、subagent handoff 后可仅凭文件恢复。

## 0. Recovery Header

- Plan path: `<absolute path to this file>`
- Canonical task path: `<absolute path to task markdown>`
- Project workpad path: `<absolute path to Workpad - <Project>.md, if any>`
- Taskpool row source: `~/Documents/brain/07-仪表盘/待完成任务运行态.md` 或 `brain_task_orchestrator dashboard --write --json` 输出
- Actor / run id:
- Last verified at:
- Resume instruction: `read this file, read canonical task, compare taskpool row, continue from Current Step only`

## 1. Objective

- Goal:
- Acceptance criteria:
- Non-goals / anti-drift:

## 2. Source / License / Authority

| Item | Evidence | Verdict |
|---|---|---|
| Upstream source |  |  |
| License |  |  |
| Local adaptation |  |  |
| Adoption decision | adopt / borrow / reject |  |

## 3. State Ledger

| Step | Status | Evidence path / command | Notes |
|---|---|---|---|
| 1. Reconcile taskpool / task / workpad | pending |  |  |
| 2. Execute smallest evidence slice | pending |  |  |
| 3. Validate recovery from file | pending |  |  |
| 4. Record proof / handoff | pending |  |  |

## 4. Current Step Marker

- Current step id:
- Current step status: pending / in_progress / blocked / done
- Next atomic action:
- Blockers:

## 5. Decisions Preserved

| Decision | Rationale | Evidence |
|---|---|---|
|  |  |  |

## 6. Files Changed

| Path | Change type | Reason | Validation |
|---|---|---|---|
|  | create / modify |  |  |

## 7. Validation Commands

| Command / Check | Expected | Actual | Status |
|---|---|---|---|
| `read_file <plan>` | file readable |  | pending |
| `python3 <validator> <plan>` | `overall_status: PASS` |  | pending |

## 8. Resume Protocol

After compaction/restart/handoff:
1. Read this file from `Plan path`.
2. Read the canonical task path.
3. Read or regenerate taskpool/dashboard status.
4. Compare `Current Step Marker` against completed rows in `State Ledger`.
5. Continue only the `Next atomic action`; do not redo completed rows unless validation evidence is missing.
6. Append new evidence to `State Ledger` and update `Last verified at`.
