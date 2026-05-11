---
type: proof
layer: L6
status: current
created: 2026-05-08T18:36:00+08:00
updated: 2026-05-08T18:36:00+08:00
project: hermes-automation-budget
concepts: [iteration-budget, proof-gate, pua-loop]
---

# Iteration Budget PUA-loop 落地 Proof

## Scope

落地 Hermes 自动化任务 iteration-budget 的 P10/P9/P8 最小闭环：doctor、bounded tick、handoff template、skill policy、本地大脑策略页、任务池 proof。

## Structured evidence

- command: `python3 -m py_compile ~/.hermes/scripts/iteration_budget_doctor.py ~/.hermes/scripts/brain_task_budget_tick.py ~/.hermes/scripts/test_iteration_budget_guard.py` PASS
- command: `python3 ~/.hermes/scripts/test_iteration_budget_guard.py -v` PASS, 3 tests
- command: `python3 ~/.hermes/scripts/iteration_budget_doctor.py --json` PASS, status OK
- command: `python3 ~/.hermes/scripts/brain_task_budget_tick.py --task 2026-05-08-落地-iteration-budget-pua-loop-有界执行与-handoff-闭环 --spent-tool-calls 50 --max-tool-calls 60 --json` PASS, p10_gate PASS
- command: `python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json` PASS
- command: `python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json` PASS
- command: `python3 ~/.hermes/scripts/skill-steward.py --graph-check --json` PASS, cycles=0 depth_max=4
- brainctl: `python3 ~/.hermes/scripts/brainctl.py --json sync` exit_code 0
- brainctl: `python3 ~/.hermes/scripts/brainctl.py --json reindex` indexed_blocks=2380 skipped_secret_blocks=18 in final verification
- search: `python3 ~/.hermes/scripts/brainctl.py --json search 'iteration-budget bounded-tick pua-loop' --limit 10` returned 4 hits in final verification
- artifact: `/tmp/iteration_budget_verify_20260508183533`
- artifact: `/tmp/iteration_budget_final_verify_20260508183811`
- artifact: `/tmp/iteration_budget_post_patch_verify_20260508183854`
- artifact: `/tmp/iteration_budget_commit_gate_20260508184250`
- artifact: `/Users/charles/.hermes/artifacts/iteration-budget/20260508-183533-2026-05-08-落地-iteration-budget-pua-loop-有界执行与-handoff-闭环/handoff.md`
- file: `/Users/charles/.hermes/scripts/iteration_budget_doctor.py`
- file: `/Users/charles/.hermes/scripts/brain_task_budget_tick.py`
- file: `/Users/charles/.hermes/scripts/iteration_budget_handoff_template.md`
- file: `/Users/charles/.hermes/scripts/test_iteration_budget_guard.py`
- file: `/Users/charles/Documents/brain/05-实践与项目/实践方案/Hermes自动化任务IterationBudget闭环策略.md`
- file: `/Users/charles/Documents/brain/06-治理与评审/reviews/2026-05-08-iteration-budget-p10-multimodel-review.md`

## PUA-loop closure

- L0/L1: evidence collected and scripts added.
- L2: multi-model fanout completed but discussion degraded; labeled advisory.
- L3: implementation landed in scripts/skill/local brain.
- L4: verification passed after one parser-reporting failure was fixed by re-reading outputs and using robust JSON/list handling.
- L5: task note will be marked done only with this structured proof.

## Residual risk

- `brain_task_budget_tick.py` is intentionally a bounded preparer, not a fully autonomous executor.
- Full idle-runner / auto-claim-run-retry remains a separate P1 task and must keep safety gates.
- Existing proof-check has one legacy body-only evidence warning unrelated to this task.

## Evidence Boundary

Model agreement is provenance only; status promotion requires command/file/search proof recorded in this note or linked artifacts.

