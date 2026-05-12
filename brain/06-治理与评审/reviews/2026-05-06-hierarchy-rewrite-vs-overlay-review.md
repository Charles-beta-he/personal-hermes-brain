---
type: review
layer: L6
status: active
created: 2026-05-06T18:57:47+08:00
project: cybernetic-multimodel-intervention
multi_model_status: not_certified
---

# 2026-05-06 Hierarchy Rewrite vs Overlay Review

## Question

为什么不改现有 Obsidian 主层级？长期是否应该一步到位？并覆盖关键点多模型介入推荐内容。

## Evidence snapshot

- `brainctl status` at 2026-05-06 18:57 CST: canonical vault exists, indexed_blocks was 1473。
- Top-level scan: every top-level folder had direct markdown and index/MOC。
- Prior self-check for cybernetic multi-model intervention passed structural gates。
- Previous broad keypoint+multi-model query returned `[]`, meaning missing routing artifact, not necessarily failed hierarchy。

## Multi-model provenance

Bounded T2 fanout command:

```bash
python3 ~/.hermes/scripts/consult_models.py run /tmp/hierarchy-multimodel-routing-state.json --tier T2 --quorum 4 --max-rounds 1 --keep
```

Artifact directory:

`/Users/charles/.hermes/tick-20260506-105812/`

Status:

- fanout quorum met: 3/2 success, 1 fail。
- merged consensus verdict: `dissent`。
- certification status: `truth_not_certified` because claims were not directly grounded by evidence IDs in the state schema。

This is provenance only, not proof。

## Decision

Do not rewrite the main hierarchy now。Land semantic/control-plane overlay first。

## issue_ledger

| id | severity | status | issue | resolution |
|---|---:|---|---|---|
| H-001 | 5 | resolved | 一步到位改主层级 blast radius 过大 | use overlay + route matrix + migration gates |
| H-002 | 4 | resolved | 关键点推荐没有统一路由 artifact | create [[05-实践与项目/实践方案/07-关键点多模型介入路由矩阵]] |
| H-003 | 4 | accepted_risk | T2 fanout had dissent / truth_not_certified | deterministic local gates decide landing closure |
| H-004 | 3 | resolved | 中文检索可能不命中 | add Chinese alias blocks and verify Chinese queries |
| H-005 | 3 | resolved | 长期是否迁移缺门槛 | define G1-G7 migration gates |

## Certification caveat

Knowledge coverage can be complete while historical multi-model certification remains not_certified。Do not upgrade this review to certified unless a later evidence-bound discussion resolves the truth grounding caveat。

## Evidence Boundary

- Added by backlog-zero loop at `2026-05-06T13:32:29Z`.
- This review is provenance, not truth proof. Its claims may support promotion only when linked tool/file/search evidence is satisfied.
- Model agreement, dissent, timeout, or not_certified labels must remain visible; do not treat review consensus as deterministic evidence.
