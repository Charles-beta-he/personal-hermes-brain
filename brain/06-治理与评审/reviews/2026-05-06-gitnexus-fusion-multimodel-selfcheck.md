---
type: review
status: active
created: 2026-05-06T09:29:50Z
project: hermes-code-evidence-mcp-fusion
review_type: multi-model-selfcheck
---

# 2026-05-06 GitNexus 融合多模型自检

## 输入证据

- GitNexus repo observed commit: `05ca80ea3039bae2661f4cfa2378e95cad1c2a5c`。
- 证据文件：README、ARCHITECTURE.md、AGENTS.md、GUARDRAILS.md、tools.ts、resources.ts、microservices-grpc guide。
- Hermes skill reference: `/Users/charles/.hermes/skills/software-development/multi-model-thinking/references/gitnexus-code-evidence-mcp-pattern.md`。
- P10 health: V=0.9892, grade=A, warning=`memory file > 2.2KB, may have ghosts`。

## 多模型 provenance

前序四模型 fanout：`/Users/charles/.hermes/tick-20260506-091741`。

状态边界：

- fanout quorum met。
- discussion/ratification 未完成；后台进程由 orchestrator 手动终止，exit=-15。
- merged_plan consensus_verdict=dissent, confidence=0.2705。
- 因此不能宣称 ratified consensus，只能作为 multi-model fanout + 人工归并 provenance。

## 归并后结论

四模型语义交集高度集中在以下点：

1. P0 impact-before-edit gate。
2. P0 stale-index gate。
3. P0 detect_changes-before-commit。
4. P1 tool_map / shape_check。
5. P1 canonical contract_id / Contract Bridge。
6. P1 structured MCP resources。
7. P1 RRF only ranks evidence。
8. P2 generated repo skills with freshness/expiry。
9. P2 graph rename dry-run only after graph quality adequate。
10. 不整体采用 GitNexus runtime。

## 本轮落地检查

- [x] 长期项目目录创建。
- [x] P10 strategy 创建。
- [x] P9 backlog 创建。
- [x] 实践方案创建。
- [x] 自检脚本创建。
- [x] sync/reindex/search 验证。
- [x] scoped local commit：`62e05b3 docs(brain): land GitNexus code-evidence fusion`（2026-05-06 PUA-loop ghost-risk 修正）。

## 下一轮 loop 建议

下一轮不再补文档，而是进入最小 runtime slice：

1. 定义 `code_evidence_v1` schema。
2. 给 `consult_models.py state` 增加 code/MCP/API task 标记与 required evidence hints。
3. 给 `gitnexus_fusion_selfcheck.py` 增加 schema 文件验证。
4. 再跑多模型 self-check，并在未 ratified 时保留 caveat。


## Final verification — 2026-05-06T09:39:30Z

- `gitnexus_fusion_selfcheck.py --json`: PASS。
- accepted_risks: `p10_memory_size_warning_existing_nonblocking`（既有 memory size warning，本项目非阻断）。
- `brainctl sync`: Sync complete: 1 pushed, 13 pulled。
- `brainctl reindex`: indexed_blocks=1306, skipped_secret_blocks=0, skipped_ignored_files=0。
- search `GitNexus-inspired 多模型 代码证据门`: hit_count=2。
- search `impact-before-edit detect_changes stale-index`: hit_count=5。
- search `Contract Bridge contract_id shape_check`: hit_count=2。
- structural audit: empty_dirs=[], top_level_no_index=[], broken_wikilinks_count=0, secret_pattern_hits=0, md_count=173。

## Scoped commit reconciliation — 2026-05-06

本轮本地大脑剩余策略审计确认 GitNexus fusion 已有本地 scoped commit：`62e05b3 docs(brain): land GitNexus code-evidence fusion`。历史多模型状态仍保持 `fanout + dissent / not ratified` caveat；本次只修正 checklist 状态，不改变 ratification 结论。

## Evidence Boundary

- Added by backlog-zero loop at `2026-05-06T13:32:29Z`.
- This review is provenance, not truth proof. Its claims may support promotion only when linked tool/file/search evidence is satisfied.
- Model agreement, dissent, timeout, or not_certified labels must remain visible; do not treat review consensus as deterministic evidence.
