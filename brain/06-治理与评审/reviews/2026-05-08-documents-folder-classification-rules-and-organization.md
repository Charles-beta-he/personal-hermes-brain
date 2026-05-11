---
type: review
status: done
created: 2026-05-08T13:20:00+08:00
updated: 2026-05-08T13:20:00+08:00
concepts: [documents-organization, icloud-documents, classification-rules, local-brain-safety]
---

# Documents 文件夹分类规则与整理记录

## Scope

仅整理：

`/Users/charles/Documents`

未触碰 Desktop、Downloads、其它 iCloud 根目录或项目目录。

## Multi-Model Provenance

四模型 fan-out tick：

`/Users/charles/.hermes/tick-20260508-050847/`

模型：

- gpt-5.5
- mimo-v2.5-pro
- claude-opus-4-7
- deepseek-v4-pro

结果摘要：

- 4/4 planner fanout completed。
- truth_assessment: `grounded`。
- evidence_coverage: `1.0`。
- 结论存在 conservative 差异：gpt-5.5 建议仅立即移动 3 个低风险草稿，疑似应用生成文件进入人工复核；Claude/MiMo 认为 7 个 loose files 都可通过 manifest 安全整理。
- 最终采纳折中：7 个 loose files 全部移出 root，但疑似应用生成文件进入 `90-待复核-应用生成文件/`，不删除、不合并、不深度改名。

## 分类规则

### 保护区：不移动

- `/Users/charles/Documents/brain` — canonical local brain，不移动。
- `/Users/charles/Documents/文稿 - charles的MacBook Pro` — iCloud duplicate compatibility folder；其中 `brain` symlink 回 `../brain`。
- `/Users/charles/Documents/Codex` — tool/workspace-owned。
- `/Users/charles/Documents/Obsidian Vault` — legacy vault，未自动合并。
- `/Users/charles/Documents/_待整理_iCloud迁移` — iCloud migration quarantine。
- `/Users/charles/Documents/_整理日志` — audit/report logs。
- 应用目录：`TencentMeeting`, `com_tencent_imsdk_data`, `Dadroit JSON Generator`, `KiCad`, `log`, `Playgrounds`, `Untitled`。
- hidden/system files：`.DS_Store`, `.localized`, dot dirs。

### 可立即整理

低风险草稿/图表：

- `未命名.md`
- `未命名绘图.drawio`
- `未命名绘图 2.drawio`

目标：

`/Users/charles/Documents/_分类整理/01-草稿与图表/`

### 待复核应用生成文件

- `av_config.xml`
- `av_report_config.xml`
- `ssoreport.txt`
- `tim_database_quallity_report.db`

目标：

`/Users/charles/Documents/_分类整理/90-待复核-应用生成文件/`

## Execution

已移动 7 个 top-level loose files；未删除文件。

Manifest：

`/Users/charles/Documents/_整理日志/2026-05-08-documents-classification-apply-manifest.json`

Report：

`/Users/charles/Documents/_整理日志/2026-05-08-documents-classification-report.md`

Inventory before：

`/Users/charles/Documents/_整理日志/2026-05-08-documents-inventory-before-classification.json`

## Verification

- root loose non-hidden files after organization: `[]`
- moved files: `7`
- sha256 before/after: all matched manifest
- `/Users/charles/Documents/brain`: exists
- `/Users/charles/Documents/文稿 - charles的MacBook Pro/brain`: symlink -> `../brain`
- `brainctl status`: vault_exists true
- `brainctl sync`: `Sync complete: 0 pushed, 0 pulled`
- `brainctl reindex`: indexed_blocks 2134
- `local_brain_exhaustive_audit.py`: stop_gate_pass true, broken_wikilinks_count 0, secret_pattern_hits 0

## Rollback

每个文件的 rollback command 已写入 manifest 的 `rollback_command` 字段。

## Evidence Boundary

Model agreement is provenance only; status promotion requires command/file/search proof recorded in this note or linked artifacts.

