---
type: task-log
layer: L3
status: completed
created: 2026-05-06T18:57:47+08:00
expires_at: 2026-06-06
project: cybernetic-multimodel-intervention
---

# 2026-05-06 Hierarchy Overlay Routing Landing Log

## Trigger

用户问：为什么不改现有 Obsidian 主层级？长期来看是否应该一步到位？并且落地并覆盖推荐内容。

## Decision

不现在一步到位重排主层级。先落地 semantic/control-plane overlay：关键点多模型介入路由矩阵 + hierarchy rewrite migration gates。

## Artifacts

- [[05-实践与项目/实践方案/07-关键点多模型介入路由矩阵]]
- [[04-知识原子/atoms/semantic-overlay-before-hierarchy-rewrite]]
- [[04-知识原子/atoms/keypoint-to-multimodel-routing]]
- [[06-治理与评审/reviews/2026-05-06-hierarchy-rewrite-vs-overlay-review]]

## Proof checklist

- `brainctl sync`
- `brainctl reindex`
- `brainctl search "关键点多模型介入路由矩阵 主层级不一步到位" --limit 8`
- `brainctl search "semantic overlay before hierarchy rewrite keypoint multimodel routing" --limit 8`
- `python3 ~/.hermes/scripts/cybernetic_multimodel_selfcheck.py --json`

## Expiry

Task-local status expires at 2026-06-06。Stable decisions live in atoms/playbook/project files。
## Final verification results


```json
{
  "sync_stdout": "Sync complete: 0 pushed, 0 pulled",
  "reindex": {
    "indexed_blocks": 1524,
    "skipped_secret_blocks": 0,
    "skipped_ignored_files": 0
  },
  "search_zh_top": [
    {
      "path": "05-实践与项目/实践方案/07-关键点多模型介入路由矩阵.md",
      "heading": "中文检索别名"
    },
    {
      "path": "05-实践与项目/tasks/2026-05-06-hierarchy-overlay-routing-landing-log.md",
      "heading": "Proof checklist"
    }
  ],
  "search_en_top": [
    {
      "path": "04-知识原子/atoms/00-atoms索引.md",
      "heading": "层级覆盖层与多模型路由"
    },
    {
      "path": "06-治理与评审/进化日志/2026-05-06-主层级覆盖层路由矩阵落地.md",
      "heading": "Links"
    },
    {
      "path": "05-实践与项目/tasks/2026-05-06-hierarchy-overlay-routing-landing-log.md",
      "heading": "Artifacts"
    }
  ],
  "selfcheck": {
    "status": "PASS",
    "checks_count": 106,
    "failed_checks": [],
    "structure": {
      "empty_dirs": [],
      "top_level_no_index": [],
      "parent_no_direct_md_top": [],
      "broken_wikilinks_count": 0,
      "broken_wikilinks_sample": [],
      "secret_pattern_hits": 0,
      "secret_pattern_files": []
    }
  },
  "multimodel_caveat": "T2 fanout quorum met but merged consensus_verdict=dissent and certification_status=truth_not_certified; used as provenance only."
}
```

## Evidence Boundary

- Canonical truth is the Markdown vault plus deterministic `brainctl` / filesystem / git gates.
- Multi-model agreement, derived indexes, RRF/vector/KG outputs, and theory analogies are provenance or retrieval aids only; they are not truth sources.
- Promotion requires linked tool/file/search evidence after this artifact is written.

## Permission retrigger proof pointer

- 2026-05-06 permission-retrigger scope: rerun approval-sensitive local-brain governance path after the user explicitly requested re-triggering permission-gated work.
- Proof ledger: [[2026-05-06-permission-retrigger-local-brain-closure-review]].
- Expected gates: `brainctl promote`, `brainctl sync`, `brainctl reindex`, `brainctl search`, `brainctl validate --dry-run`, exhaustive audit, active-backlog marker scan, test suite, scoped mirror/git status, and local commit if the scoped diff is dirty.
