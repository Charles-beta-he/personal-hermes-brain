---
type: review
layer: L6
status: current
created: 2026-05-08T17:56:41+08:00
updated: 2026-05-08T17:56:41+08:00
project: local-brain-governance
models:
  - gpt-5.5
  - mimo-v2.5-pro
source_artifacts:
  - /tmp/local_brain_residue_audit_20260508175536
  - /Users/charles/.hermes/tick-20260508-095641
---

# Review - 本地大脑残留与闭环修复流程

## Evidence Boundary

本评审只覆盖 2026-05-08T17:55-17:56 +08:00 的本地命令输出与 T1 双模型 advisory。模型结论不是事实源；事实以本地命令、脚本输出和 Markdown 文件为准。本文不执行删除、移动或批量重写，只给出 repair-plan / repair-apply 的闭环流程与任务化建议。

## Deterministic Findings

命令证据目录：`/tmp/local_brain_residue_audit_20260508175536`。

### F1 - 主层级迁移未闭环

`local_brain_main_hierarchy_migration_selfcheck.py --json` 当前 `status: FAIL`。

失败项：

- `top_dirs_exact`: 顶层同时存在 `06-仪表盘` 与 `07-仪表盘`。
- `old_top_dirs_remaining`: `['06-仪表盘']`。
- `structure:broken_wikilinks_count`: `1`。
- `structure:old_path_link_hits_count`: `1`。

### F2 - 结构审计未闭环

`local_brain_exhaustive_audit.py --sample-limit 50`：

- `stop_gate_pass: false`
- `empty_dirs: []`
- `top_level_no_index: []`
- `parent_no_direct_md_top: []`
- `broken_wikilinks_count: 1`
- `secret_pattern_hits: 0`

唯一 broken wikilink：

- source: `06-治理与评审/reviews/2026-05-08-local-brain-taskflow-closure-multimodel-review.md`
- target: `06-治理与评审/reviews/2026-05-08-local-brain-taskflow-closure-certification.json`

解释：目标 JSON 文件存在，但当前 wikilink resolver 只把 `.md` note 纳入索引；因此这是“非 Markdown proof artifact 被写成 Obsidian wikilink”的治理残留，应改为普通文件路径/Markdown link，或明确扩展审计规则。

### F3 - 治理 validate 未闭环

`brainctl.py --json validate --write-dashboard`：

- `passed: false`
- `notes_scanned: 292`
- `l3_expiry_open: 2`
- `violation_count: 20`
- dashboard: `07-仪表盘/本地大脑治理健康度.md`

分布：

- `frontmatter_missing_key`: 10
- `missing_l3_expiry`: 2
- `review_missing_evidence_boundary`: 8

### F4 - 任务池状态机基本闭环

`brain_task_orchestrator.py selfcheck --json`：PASS。

`brain_task_orchestrator.py proof-check --json`：PASS。

仍有 warning：

- `legacy body-only evidence accepted: 2026-05-06-local-brain-backlog-zero-loop-log`

这不阻塞任务池运行，但说明旧任务证据仍未完全迁移到结构化 evidence。

### F5 - 06/07 仪表盘内容差异

`06-仪表盘` 当前有 2 个 Markdown 文件：

- `00-仪表盘索引.md`
- `技能生态健康度.md`

`07-仪表盘` 当前有 8 个 Markdown 文件。两个同名文件与 06 版本 hash 不同，不能直接删除，必须先内容对比与迁移/归档判断。

## Multi-model Advisory

T1 双模型：gpt-5.5 + MiMo-v2.5-pro。

artifact：`/Users/charles/.hermes/tick-20260508-095641`。

truth gate：

- `truth_status: grounded`
- `verified_claim_count: 6/6`
- `evidence_coverage: 1.0`

merge：

- `consensus_verdict: dissent`
- `arbitration_needed: true`
- 原因：两个模型提出的 patch ID/粒度不同；核心事实判断一致，但实施拆分不同。

共同判断：

- 当前未闭环清理。
- 不应由 dashboard 自动修复 vault。
- 应补充显式 `repair-plan -> review -> repair-apply -> verify -> proof` 流程。

## Repair Closure Flow

### Phase 0 - Claim / Freeze Scope

- 通过任务池 claim 修复任务。
- 明确禁止项：不删除证据、不自动根据 dashboard 修改 vault、不绕过 proof gate。
- 记录当前 git/status、scanner outputs、content hashes。

### Phase 1 - repair-plan dry-run

生成 manifest，每项必须包含：

- `id`
- `operation`: move / rewrite / add_frontmatter / convert_link / accept_risk / archive
- `source_path`
- `target_path`
- `reason`
- `risk`
- `content_hash_before`
- `references_found`
- `rollback_plan`
- `verification_commands`

候选项：

1. `06-仪表盘` legacy top dir：内容对比后迁移/归档/删除。
2. `06-仪表盘` old path refs：逐项判断历史记录 vs 当前引用，历史记录可保留，当前 frontmatter/route matrix 应更新。
3. JSON proof wikilink：改为普通路径或 Markdown link；不要让非 `.md` artifact 作为 Obsidian wikilink。
4. `brainctl validate` 20 项 violations：按类型分批处理。
5. legacy body-only evidence warning：补结构化 evidence 或接受 legacy 风险。

### Phase 2 - review gate

每个 manifest item 归类：

- `safe_apply`
- `needs_manual_decision`
- `archive_only`
- `false_positive`
- `accepted_risk`

### Phase 3 - repair-apply explicit only

- 只执行 reviewed manifest 中的 `safe_apply`。
- destructive 操作前建立备份或 git commit boundary。
- 每一批只改一类问题，避免混杂。

### Phase 4 - verify / proof

每批后运行：

```bash
python3 ~/.hermes/scripts/local_brain_main_hierarchy_migration_selfcheck.py --json
python3 ~/.hermes/scripts/local_brain_exhaustive_audit.py --sample-limit 50
python3 ~/.hermes/scripts/brainctl.py --json validate --write-dashboard
python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "local-brain residue repair" --limit 10
```

闭环条件：

- migration selfcheck PASS，或旧目录被显式白名单且记录 accepted risk。
- exhaustive audit `stop_gate_pass: true`。
- brainctl validate `passed: true`，或剩余项全部进入 accepted risk/任务池。
- proof-check PASS 且无新增 legacy warning。
- dashboard 仅作为派生观测，不作为修复输入。

## Current Closure Verdict

当前不是闭环清理完成态。

分层判定：

- 观测闭环：部分完成，scanner/dashboard 能发现问题。
- 修复计划闭环：本文补齐到流程层，但还没有 manifest/apply 产物。
- 执行闭环：未完成，尚未迁移/归档 `06-仪表盘`，未修 broken wikilink，未处理 20 个 validate violations。
- proof 闭环：任务池 proof-check 通过，但本次残留清理任务尚未执行，因此不能标记 done。

## Next Task Recommendation

创建 P1 任务：`本地大脑迁移残留闭环清理与 repair-plan/apply 验证`。

优先级理由：这是本地大脑治理 stop gate 噪音的根源，会影响后续自检可信度；但涉及移动/删除 vault 文件，应先做 dry-run manifest，不应立即自动 apply。
