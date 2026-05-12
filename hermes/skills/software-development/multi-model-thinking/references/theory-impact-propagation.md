# Theory-to-impact propagation pattern

Use this when a local optimization should become a system-wide architectural improvement rather than a one-off patch.

## Problem pattern

A single slice improves after applying a theory/principle, but equivalent locations remain stale and impacted layers drift apart. This creates local success with global inconsistency: one gate becomes strict while another stays loose; one doc says evidence-first while a task closeout still accepts unsupported claims; one timeout wrapper kills process groups while another leaves orphan children.

## Fail-closed contract

1. Every propagated optimization must bind a canonical `Theory Point ID`.
2. Every `Theory Point ID` must produce a `Same-theory propagation` scan:
   - list equivalent locations; or
   - explicitly document why no other target exists.
3. Every propagated optimization must include a `Layer Impact Map` over relevant surfaces:
   - L0 trace / evidence
   - L1 router / trigger
   - L2 protocol / envelope / closeout rule
   - L3 ensemble / cross-patch / issue ledger
   - L4 taskpool / brain / proof / lifecycle
   - L5 consult_models / ratification
   - LX health / quota / rollback governor
   - skills / references
   - cron / gateway when runtime automation is touched
4. Every impacted surface must have an operational smoothing gate, not prose-only caution:
   - evidence diff, regression test, selfcheck/proof/lifecycle/evidence-spine, health variance, rollback, compatibility gate, or ratification gate.
5. A local patch must not be promoted to a global rule when any of these are missing:
   - evidence links
   - target-bound scope
   - same-theory targets
   - impact map
   - smoothing gate
   - rollback boundary
6. `not_certified`, dissent, or timeout remains provenance only. It can motivate a propagation task but cannot certify it.

## Hermes-native artifacts

Canonical brain artifacts:

- `~/Documents/brain/05-实践与项目/实践方案/08-理论到影响全架构传播矩阵.md`
- `~/Documents/brain/04-知识原子/atoms/theory-impact-propagation.md`

Deterministic gate:

```bash
python3 ~/.hermes/scripts/architecture_theory_impact_ratchet.py --json
```

Expected PASS shape:

- `status=PASS`
- theories covered: `8/8`
- surfaces covered: `9/9`
- failed_checks: `[]`

## Implementation checklist

When landing a theory-driven architecture improvement:

1. Add/modify the target code or doc only after identifying the `Theory Point ID`.
2. Search for same-theory targets in scripts, skills, brain docs, taskpool commands, and closeout gates.
3. Update every equivalent target or record an explicit accepted-risk / none-rationale.
4. Add regression tests proving the old local-only failure cannot return.
5. Run `architecture_theory_impact_ratchet.py --json` plus the target subsystem tests.
6. If the change affects taskpool closeout, also run:
   - `brain_task_orchestrator.py selfcheck --json`
   - `brain_task_orchestrator.py lifecycle --json`
   - `brain_task_orchestrator.py proof-check --json`
   - `brain_task_orchestrator.py evidence-spine --json`
7. Commit only scoped files; do not push by default.

## Anti-patterns

- Updating one wrapper/gate while leaving a sibling wrapper/gate with the same failure mode.
- Saying “this is covered by architecture” without a table row, target list, and ratchet check.
- Treating a single model’s architectural advice as evidence.
- Converting a not_certified discussion into a certified architecture rule.
- Adding a broad route keyword that triggers most tasks instead of structure-first routing.
