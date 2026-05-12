---
type: evidence
project: hermes-self-improvement
created: 2026-05-11T22:30:54+08:00
concepts: [taskpool, multi-model, ratification-gate, flow-repair]
---

# Taskpool flow audit - 2026-05-11T22:30:54+08:00

## Scope

根据最新 controller → delegate → verify → release 流转方案，校准本地任务池任务内容与多模型认证字段，防止伪 certified artifact 进入自动流转。

## Findings

- Deterministic gates after repair: test_brain_task_orchestrator PASS; selfcheck PASS; proof-check PASS; boundary-check PASS; parallel-dispatch-dry-run OK.
- Strict multi-model pass now requires local JSON artifact + `ratification-gate --task ...` target binding + canonical 4/4 Claude/GPT/DeepSeek/MiMo votes.
- `增强本地任务池任务边界与多agent并行处理` is the only currently confirmed target-bound 4/4 passed task in the active convergence set.
- `OpenAI openai-cli` was corrected to `multimodel_status: not_certified`; old 3-model / unbound artifacts remain provenance only.
- `rowboatlabs/rowboat` was corrected to `not_certified`; referenced artifact is not suitable for Rowboat closeout and needs fresh upstream evidence + target-bound 4/4.
- `Agent Development Kit 图片` stale claim was force-released; artifact is truth-grounded but not implementation-certified and now explicitly marked `not_certified`.

## Current dispatch posture

- Work lane currently has claimed tasks but no pending dispatchable work, so evolution dispatch is allowed.
- Dry-run selected three non-conflicting candidates after repair: OpenAI/provider-quota, taskpool-boundary-parallel, SkillClaw/skill-graph.
- Multi-model intervention queue remains high (expected): most evolution tasks need advisory/ratification before closeout; this is safe because `multimodel_passed` is now strict.

## Next executable slice

1. Let controller/delegate process dry-run-selected non-conflicting candidates.
2. For each not-certified task, build target-bound claim/evidence state before running T3.
3. Do not mark done from status labels alone; require proof + review + ratification gate for closeout.

## Rollback

If the strict gate blocks a legitimate advisory-only task, do not weaken `task_multimodel_passed`; instead record advisory status separately and only use target-bound 4/4 for final closeout.
