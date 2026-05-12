# Systems-engineering control-plane overlay landing

Use when the user says the agent is missing a skill tree, project-specific working memory, reusable frontend closure standards, or asks to apply Qian Xuesen / systems engineering to the agent itself.

## Core diagnosis

This is usually not a lack of memory or a lack of skills. It is a missing middle control layer:

1. Skill graph/topology answers whether skills form a healthy DAG; it does not answer which semantic route a specific project/task should take.
2. Persistent memory is global and compact; it should not carry project north stars, anchors, red lines, flow matrices, acceptance matrices, or evidence ledgers.
3. Session todo is temporary; it should not be the only place project state lives.
4. Frontend closure standards are reusable across projects, but business flows, field-display anchors, API contracts, and non-changeable UI behavior are project-specific.

## Qian Xuesen systems-engineering mapping

Mark the source boundary clearly: unless the source text was actually read/quoted, describe this as a reconstruction of systems-engineering principles, not a verbatim reading.

| Systems engineering idea | Agent control-plane artifact |
|---|---|
| Overall/top-level design | P10 north star, non-goals, red lines |
| Decomposition and coordination | P9 task tree, skill route matrix, subsystem/interface map |
| Qualitative-to-quantitative synthesis | User judgement + build/test/browser/truth-gate metrics |
| Human-machine integration | User corrections outrank model inference; agent executes evidence loops |
| Feedback and correction | Evidence ledger, regression gates, self-check scripts |
| Knowledge deposition | Brain atoms/templates/playbooks/project workpads/skill patches |

## Minimal landing package

Create a reversible semantic overlay; do not rewrite the Obsidian hierarchy or Hermes runtime first.

Canonical local-brain artifacts:

- `05-实践与项目/projects/<control-plane>/Project - <Name>.md`
- `05-实践与项目/projects/<control-plane>/P10 - <Strategy>.md`
- `05-实践与项目/projects/<control-plane>/P9 - <Backlog>.md`
- `07-仪表盘/Agent技能树路由矩阵.md`
- `08-模板/项目工作记忆模板.md`
- `05-实践与项目/实践方案/前端闭环验收标准.md` when frontend closure is part of the gap
- `04-知识原子/atoms/系统工程四环Agent映射.md`
- `06-治理与评审/reviews/<date>-qian-systems-engineering-agent-gap-review.md`
- `06-治理与评审/进化日志/<date>-agent-systems-engineering-control-plane.md`
- `05-实践与项目/tasks/<date>-...-landing-log.md`
- `~/.hermes/scripts/<project>_selfcheck.py`

## Project workpad rule

Use this deposition rule in the template:

- Durable user preference -> persistent memory.
- Cross-project workflow -> template/playbook/skill.
- Project state -> project workpad.
- Current task status -> session todo/task log.
- Tool outputs and verification -> evidence ledger/artifacts.

This prevents ghost memory while keeping project-specific context available.

## Frontend closure playbook essentials

For frontend projects, define closure as user-path completion, not screenshots or build success.

Required gates:

1. Entry exists and has correct semantics.
2. Action triggers a business effect.
3. Feedback is visible and not duplicated.
4. State transitions are consistent across URL/store/server/mock.
5. Error recovery exists.
6. Finish state is reachable.
7. Boundary cases cover empty/weak-network/retry/back/refresh.
8. Dynamic cases cover modal/toast queues and StrictMode re-entry.
9. Presentation covers i18n/dark/mobile/keyboard/scroll.
10. Observability covers console/network/errors/analytics as applicable.

Hard red line: do not remove or hide buttons/routes/fields to “fix” dead UI unless evidence proves the entry is out of scope and the decision is documented.

## Verification loop

After writing artifacts:

```bash
python3 -m py_compile ~/.hermes/scripts/<selfcheck>.py
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/<selfcheck>.py
```

Self-check should verify both file existence and search retrievability.

## Search pitfall

`brainctl search` may return zero hits for mixed Chinese+English AND-style queries even when the target files exist. If the first self-check fails with 0 hits, rerun manual exact-title and bilingual-keyword probes, then make the self-check query terms closer to exact headings/frontmatter keywords.

Examples that worked better:

- `Agent技能树路由矩阵`
- `Project Workpad`
- `frontend closure testing`
- `系统工程四环 Agent 映射`

Record the failed query and the patched query in the proof log.

## Git hygiene

If `~/Documents/brain` is mirrored into `~/.hermes/notes/brain`, commit only scoped artifacts and the self-check script. Avoid staging `.env`, auth files, cache, screenshots, checkpoints, sessions, and unrelated brain sync changes.
