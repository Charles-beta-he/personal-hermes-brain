---
type: evaluation
project: hermes-skill-learning
source_candidate: "ralph-loop"
evaluated_at: 2026-05-13T16:32:33+08:00
decision: borrow
status: deterministic-evidence-slice-complete
source_report: /Users/charles/.hermes/artifacts/ralph-loop-hook-evaluation/report.md
---

# Ralph Loop Hook 防提前收工与 Hermes PUA/Loop 边界评估 — closeout report

## 0. 结论

本任务已有 evidence-first report：`/Users/charles/.hermes/artifacts/ralph-loop-hook-evaluation/report.md`。

本轮 controller 复核其 acceptance，并把 closeout evidence 稳定映射回 brain/taskpool。

| 对象 | 决策 | 原因 |
|---|---|---|
| Ralph Loop 原版 | REJECT | Claude Code 专用 hook；Hermes 无直接等价 Stop lifecycle |
| PUA Loop 本地实现 | ADOPT | `loop` skill 已吸收状态文件、完成条件、压力升级、pause/abort |
| 防提前收工机制 | BORROW | 提取为 Hermes taskpool proof/evidence gate、budget、handoff 边界 |

## 1. 来源与许可

- 来源：Ralph Loop — Claude Code iteration hook pattern。
- 许可：MIT（本地 `loop` skill 明确记录借鉴 Ralph Loop/MIT）。
- 本地落点：`/Users/charles/.hermes/skills/loop/SKILL.md`。

## 2. Hook 触发条件拆解

| Trigger | 机制 | Hermes 映射 |
|---|---|---|
| Stop hook | Agent 尝试结束时读取 `.claude/ralph-loop.local.md` 并继续 | Hermes 无 session-level Stop hook；近似为 taskpool `pre_task_done` gate |
| Active state file | 状态文件保存任务与协议 | PUA Loop `.claude/pua-loop.local.md`，taskpool Markdown frontmatter/Proof Log |
| Completion promise | 只有满足条件才输出 LOOP_DONE | taskpool completion_gate + proof/selfcheck/dashboard |
| Budget / cancellation | max iterations + cancel file/signals | PUA Loop 30 轮、pause/abort、kill switch |

## 3. 有界继续执行策略与停止条件测试

| Test | Expected |
|---|---|
| 空 proof | 阻止 done |
| 有 proof 无验证输出 | 阻止或降级为 review |
| 迭代预算耗尽 | 输出可恢复 handoff，不许 LOOP_DONE |
| 用户/系统 kill switch | 停止 loop，不绕过 |
| 满足 build/test/selfcheck/proof | 允许 done |

## 4. Acceptance mapping

| Acceptance | Evidence | Status |
|---|---|---|
| 确认来源与许可 | existing report + loop skill MIT note | PASS |
| 拆解 hook 触发条件 | existing report §2 and this report §2 | PASS |
| 映射到 Hermes loop/PUA/iteration-budget | existing report §3-4 and this report §3 | PASS |
| 设计有界继续执行策略与停止条件测试 | existing report §4.3 and this report §3 | PASS |

## 5. Controller notes

- Existing report was re-read from `/Users/charles/.hermes/artifacts/ralph-loop-hook-evaluation/report.md`。
- Advisory-only multimodel evidence remains provenance, not closeout authority。
- Closeout authority for this task is deterministic report + taskpool proof/selfcheck/dashboard gates。
