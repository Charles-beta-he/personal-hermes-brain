---
type: review
layer: L6
status: active
created: 2026-05-06T19:29:36+08:00
project: local-brain-main-hierarchy-migration
multi_model_status: provenance_only
---

# 2026-05-06 Main Hierarchy Migration Review

## Multi-model participation

Command:

```bash
python3 ~/.hermes/scripts/consult_models.py run /tmp/local-brain-main-hierarchy-migration-state.json --tier T3 --quorum 4 --max-rounds 1 --keep
```

Artifact directory:

`/Users/charles/.hermes/tick-20260506-112947/`

Observed result:

- fanout quorum met: 3/2。
- consensus_verdict: weak_consensus。
- source_plans: 4。
- minority patches included verifier/manifest/selfcheck requirements。

## Caveat

Multi-model output is provenance, not proof。Completion is certified only by local deterministic gates。

## Review decision

Proceed with controlled migration because user explicitly requested completion and backup/rollback/self-check gates exist。

中文检索别名：多模型验证 主层级迁移 weak_consensus provenance_only 本地大脑主层级迁移

## Evidence Boundary

- Added by backlog-zero loop at `2026-05-06T13:32:29Z`.
- This review is provenance, not truth proof. Its claims may support promotion only when linked tool/file/search evidence is satisfied.
- Model agreement, dissent, timeout, or not_certified labels must remain visible; do not treat review consensus as deterministic evidence.
