---
type: evaluation
project: hermes-skill-learning
source_candidate: "Planning with Files"
evaluated_at: 2026-05-13T15:51:53+08:00
decision: borrow
status: deterministic-evidence-slice-complete
---

# Planning with Files — deterministic evidence slice (2026-05-13)

## 0. Scope / non-goals

本轮只完成 deterministic evidence slice：确认来源/许可、对比 Hermes plan / Workpad / taskpool 现状、产出候选模板、跑一次“上下文压缩后只读文件恢复”的模拟验证。

约束：不安装、不导入、不创建新的 planning-with-files skill、不跑 taskpool lifecycle closeout、不标 done。

## 1. Source / license confirmation

| Claim | Evidence | Result |
|---|---|---|
| 上游候选来自 `obra/superpowers` 生态，`Planning with Files` 是模式，不是本地独立 skill | `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/planning-with-files-evaluation-2026-05-11.md` lines 16-26 | confirmed as pattern / borrow target |
| 上游许可为 MIT | `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/superpowers-source-evidence-2026-05-13.json` lines 5-12, 24-30；prior report lines 16-18 | confirmed MIT |
| Hermes 本地已有改编来源 | `/Users/charles/.hermes/skills/software-development/writing-plans/SKILL.md` lines 1-6: author `Hermes Agent (adapted from obra/superpowers)`, license `MIT` | local adaptation already MIT |

Verdict: BORROW, not adopt wholesale. 该模式与 Hermes 已有 `plan`、`writing-plans`、本地 brain task note / Workpad 重叠；补的是“恢复协议/状态账本”而不是新 skill。

## 2. Hermes plan / Workpad / taskpool status comparison

| Surface | Current evidence | Coverage | Gap |
|---|---|---|---|
| Hermes `plan` skill | `/Users/charles/.hermes/skills/software-development/plan/SKILL.md` lines 25, 42-50：计划写入 `.hermes/plans/YYYY-MM-DD_HHMMSS-<slug>.md` | 文件化 plan 已有 | plan 是设计产物，缺少通用 current-step/state-ledger/resume 协议 |
| Hermes `writing-plans` skill | `/Users/charles/.hermes/skills/software-development/writing-plans/SKILL.md` lines 17-21, 176-193：zero-context、精确路径、验证步骤 | 自包含计划很强 | 本轮已补 `Context Compaction Recovery` 指针，见 lines 284-289 |
| Local Brain task note Workpad | canonical task `/Users/charles/Documents/brain/05-实践与项目/tasks/2026-05-10-skill学习路线planning-with-files-文件化规划与上下文压缩抗丢失评估.md` lines 55-59 仍是泛化 checklist | 任务 note 可当持久 workpad | 当前任务之前缺具体 evidence-slice 状态账本 |
| Task note template | `/Users/charles/Documents/brain/08-模板/local-brain-task-note-template.md` lines 42-55；rules lines 68-74 | 已规定 task note 是 persistent workpad | 模板未显式要求 compaction recovery header/current marker |
| Project Workpad template | `/Users/charles/Documents/brain/08-模板/项目工作记忆模板.md` lines 11-12, 77-90 | 项目事实/证据 ledger/next loop queue 已文件化 | 项目级，不等价于单任务 resume plan |
| Taskpool/dashboard | `/Users/charles/Documents/brain/07-仪表盘/待完成任务运行态.md` lines 76,111：本任务 status=running, advisory_passed/PASS_ADVISORY_ONLY/CONTINUE_LOOP | taskpool 状态持久可读 | advisory-only 不是 closeout；本轮只补 deterministic evidence |

Conclusion: Hermes 已有文件化三件套（plan 文件、task note、project Workpad），但缺“一个自包含恢复头 + current step marker + state ledger + validation ledger”的统一模板。该差距可通过模板和现有 skill 指针补齐，无需安装外部 skill。

## 3. Candidate file-based planning template

Created artifact:

`/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/planning-with-files-template-candidate-2026-05-13.md`

Template fields:
- Recovery Header: plan path、canonical task path、project workpad path、taskpool row source、actor/run id、resume instruction
- Objective / Acceptance / Non-goals
- Source / License / Authority table
- State Ledger: step/status/evidence/notes
- Current Step Marker: current step id/status/next atomic action/blockers
- Decisions Preserved
- Files Changed
- Validation Commands
- Resume Protocol: compaction/restart/handoff 后先读文件，再比对 taskpool，再继续 current step

## 4. Simulated context-compaction recovery validation

Simulation artifacts:
- Plan/workpad fixture: `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/planning-with-files-recovery-simulation-2026-05-13.md`
- Validator script: `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/validate-planning-with-files-recovery.py`
- JSON result: `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/planning-with-files-recovery-simulation-2026-05-13.json`

Validation command:

```bash
python3 /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/validate-planning-with-files-recovery.py /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/planning-with-files-recovery-simulation-2026-05-13.md > /Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/planning-with-files-recovery-simulation-2026-05-13.json
```

Observed result from JSON lines 1-33:
- `overall_status`: `PASS`
- method: `file-only read after simulated context compaction`
- section checks: all true for Recovery Header, Objective, Acceptance Criteria, State Ledger, Current Step Marker, Decisions Preserved, Files Changed, Resume Protocol
- pattern checks: all true for absolute plan path, canonical task path, completed steps, current step row/marker, next atomic action, blocker status, changed files, resume instruction
- recovered state: current step id `4`, completed step count `3`, current step count `1`, blockers `None`, next atomic action `run validator and write JSON evidence`

Validation verdict: file-only recovery works for the simulated compaction case.

## 5. Skill patch landed

Patched existing governing skill instead of creating a redundant new one:

`/Users/charles/.hermes/skills/software-development/writing-plans/SKILL.md`

New section verified at lines 284-289:
- include `Resume Protocol` with exact paths/current step/completed/pending/blockers/validation commands
- after compaction/restart/handoff, read plan/workpad from disk and reconcile against taskpool status
- do not keep progress only in chat/todo; update the file after each verifiable slice

## 6. Acceptance mapping

| Acceptance item | Evidence | Status |
|---|---|---|
| Confirm source/license | Section 1 evidence paths | PASS |
| Compare Hermes plan/Workpad/taskpool status | Section 2 table | PASS |
| Produce candidate file-based planning template | Section 3 template path | PASS |
| Validate one simulated context-compaction recovery | Section 4 validator JSON `overall_status=PASS` | PASS |
| Avoid external import/install | Only local file writes, skill patch, Python stdlib validator | PASS |
| No lifecycle done/closeout | No taskpool lifecycle commands executed; task remains running for controller | PASS |

## 7. Decision and next handoff

Decision: BORROW.

Recommended controller next step: treat this as deterministic evidence satisfying the task acceptance, then the controller may run its normal taskpool review/done lifecycle if policy gates allow. Do not create a standalone `planning-with-files` skill unless future evidence shows `writing-plans` + task note + Workpad cannot cover the workflow.
