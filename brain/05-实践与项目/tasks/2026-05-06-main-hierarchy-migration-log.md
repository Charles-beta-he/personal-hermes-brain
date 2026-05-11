---
type: task-log
layer: L3
status: completed
created: 2026-05-06T19:29:36+08:00
expires_at: 2026-06-06
project: local-brain-main-hierarchy-migration
---

# 2026-05-06 Main Hierarchy Migration Log

## Trigger

用户要求：p10 落地主层级迁移前置，多模型思考参与验证，pua-loop 直至主层级迁移完成无遗留。

## Backup

- `/Users/charles/.hermes/backups/local-brain-main-hierarchy-migration-20260506-192936/manifest.json`
- `/Users/charles/.hermes/backups/local-brain-main-hierarchy-migration-20260506-192936/brain-pre-migration.tgz`

## Mapping

```json
{
  "00-索引": "00-索引",
  "00-system": "01-系统与偏好/system",
  "50-prefs": "01-系统与偏好/prefs",
  "00-evidence": "02-证据与原文/evidence",
  "09-引用原文": "02-证据与原文/引用原文",
  "01-控制论基础": "03-理论与元认知/控制论基础",
  "02-治理理论": "03-理论与元认知/治理理论",
  "03-系统理论": "03-理论与元认知/系统理论",
  "07-元认知": "03-理论与元认知/元认知",
  "10-ai-systems": "04-知识原子/ai-systems",
  "10-atoms": "04-知识原子/atoms",
  "08-实践方案": "05-实践与项目/实践方案",
  "20-projects": "05-实践与项目/projects",
  "30-tasks": "05-实践与项目/tasks",
  "40-skills": "06-治理与评审/skills",
  "04-技能生态": "06-治理与评审/技能生态",
  "05-进化日志": "06-治理与评审/进化日志",
  "60-reviews": "06-治理与评审/reviews",
  "06-仪表盘": "07-仪表盘",
  "10-模板": "08-模板",
  "99-hermes-notes": "99-hermes-notes"
}
```

## Verification completed

Final proof section was appended after self-check, sync, reindex, search, and local commit。

中文检索别名：本地大脑主层级迁移 task log proof ledger 无遗留
## Final verification results

```json
{
  "timestamp": "2026-05-06T19:42:00+08:00",
  "status": "COMPLETED_NO_RESIDUAL",
  "brainctl_sync": "Sync complete: 0 pushed, 0 pulled",
  "brainctl_reindex": {
    "indexed_blocks": 1593,
    "skipped_secret_blocks": 0,
    "skipped_ignored_files": 0
  },
  "selfcheck": {
    "status": "PASS",
    "checks_count": 54,
    "failed_checks": [],
    "structure": {
      "top_dirs": [
        "00-索引",
        "01-系统与偏好",
        "02-证据与原文",
        "03-理论与元认知",
        "04-知识原子",
        "05-实践与项目",
        "06-治理与评审",
        "07-仪表盘",
        "08-模板",
        "99-hermes-notes"
      ],
      "expected_top_dirs": [
        "00-索引",
        "01-系统与偏好",
        "02-证据与原文",
        "03-理论与元认知",
        "04-知识原子",
        "05-实践与项目",
        "06-治理与评审",
        "07-仪表盘",
        "08-模板",
        "99-hermes-notes"
      ],
      "old_top_dirs_remaining": [],
      "empty_dirs": [],
      "top_level_no_index": [],
      "parent_no_direct_md_top": [],
      "broken_wikilinks_count": 0,
      "broken_wikilinks_sample": [],
      "old_path_link_hits_count": 0,
      "old_path_link_hits_sample": [],
      "secret_pattern_hits": 0,
      "secret_pattern_files": [],
      "md_files": 214
    }
  },
  "search_zh_top": [
    {
      "path": "00-索引/00-大脑索引.md",
      "heading": "中文检索别名"
    },
    {
      "path": "05-实践与项目/实践方案/08-主层级迁移Playbook.md",
      "heading": "Verification commands"
    },
    {
      "path": "05-实践与项目/projects/local-brain-main-hierarchy-migration/Project - Local Brain Main Hierarchy Migration.md",
      "heading": "Success criteria"
    }
  ],
  "search_en_top": [
    {
      "path": "00-索引/00-大脑索引.md",
      "heading": "English search alias"
    },
    {
      "path": "04-知识原子/atoms/main-hierarchy-migration-as-control-plane.md",
      "heading": "English search alias"
    }
  ],
  "search_multimodel_top": [
    {
      "path": "06-治理与评审/reviews/2026-05-06-main-hierarchy-migration-review.md",
      "heading": "Review decision"
    }
  ],
  "multimodel_provenance": {
    "artifact_dir": "/Users/charles/.hermes/tick-20260506-112947/",
    "verdict": "weak_consensus",
    "fanout": "quorum_met",
    "truth_rule": "model agreement is not evidence; deterministic local gates certify migration"
  },
  "backup_dir": "/Users/charles/.hermes/backups/local-brain-main-hierarchy-migration-20260506-192936",
  "final_top_dirs": [
    "00-索引",
    "01-系统与偏好",
    "02-证据与原文",
    "03-理论与元认知",
    "04-知识原子",
    "05-实践与项目",
    "06-治理与评审",
    "07-仪表盘",
    "08-模板",
    "99-hermes-notes"
  ]
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
