---
type: evolution-log
status: active
created: 2026-05-06T09:29:50Z
project: hermes-code-evidence-mcp-fusion
---

# 2026-05-06 GitNexus 代码证据门长期融合

## 进化事件

将 GitNexus MCP/code-intelligence 的可迁移治理原语纳入 Hermes 多模型思考长期项目。

## 关键变化

- 从“多模型讨论方案”升级为“多模型围绕代码证据对象讨论”。
- 明确 P0 gates：impact-before-edit、detect_changes-before-commit、stale-index gate。
- 明确 P1 gates：tool_map、shape_check、contract_id、structured resources、RRF evidence ranking。
- 明确边界：不整体采用 GitNexus runtime，不复制代码，不用 npx @latest 做生产依赖。

## Artifact

- `/Users/charles/.hermes/scripts/gitnexus_fusion_selfcheck.py`
- [[05-实践与项目/projects/hermes-code-evidence-mcp/Project - Hermes Code Evidence MCP Fusion]]
- [[05-实践与项目/实践方案/04-GitNexus-inspired多模型代码证据门落地方案]]
- [[06-治理与评审/reviews/2026-05-06-gitnexus-fusion-multimodel-selfcheck]]

## Caveat

前序多模型结果为 fanout + dissent，不是 ratified consensus。长期项目以本地工具验证与 P10/P9 loop 为准。


## Final verification — 2026-05-06T09:39:30Z

- `gitnexus_fusion_selfcheck.py --json`: PASS。
- accepted_risks: `p10_memory_size_warning_existing_nonblocking`（既有 memory size warning，本项目非阻断）。
- `brainctl sync`: Sync complete: 1 pushed, 13 pulled。
- `brainctl reindex`: indexed_blocks=1306, skipped_secret_blocks=0, skipped_ignored_files=0。
- search `GitNexus-inspired 多模型 代码证据门`: hit_count=2。
- search `impact-before-edit detect_changes stale-index`: hit_count=5。
- search `Contract Bridge contract_id shape_check`: hit_count=2。
- structural audit: empty_dirs=[], top_level_no_index=[], broken_wikilinks_count=0, secret_pattern_hits=0, md_count=173。

## Migrated-copy boundary — 2026-05-06

此文件是迁移/镜像副本，用于保留同步 provenance；canonical evolution event 以 [[99-hermes-notes/evolution/2026-05-06-gitnexus-code-evidence-mcp-fusion]] 为准。未来引用 GitNexus fusion 结论时优先链接 canonical note，避免双源冲突。
