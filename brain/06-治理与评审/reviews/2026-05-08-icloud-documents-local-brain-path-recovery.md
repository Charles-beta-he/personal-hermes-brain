---
type: review
status: done
created: 2026-05-08T13:05:00+08:00
updated: 2026-05-08T13:05:00+08:00
concepts: [icloud-documents, local-brain, path-recovery, document-organization]
---

# iCloud Documents 本地大脑路径恢复记录

## Context

iCloud 同步后，本地大脑目录出现在：

`/Users/charles/Documents/文稿 - charles的MacBook Pro/brain`

而 Hermes/brainctl 的默认 canonical 路径仍是：

`/Users/charles/Documents/brain`

这导致 `brainctl status` 一度显示 `vault_exists: false`。

## Actions

- 已将 `/Users/charles/Documents/文稿 - charles的MacBook Pro/brain` 移回 canonical 路径 `/Users/charles/Documents/brain`。
- 已在 `/Users/charles/Documents/文稿 - charles的MacBook Pro/brain` 创建兼容 symlink 指向 `../brain`。
- 已将 nested Codex 内容整理到 `/Users/charles/Documents/Codex`，并在 nested 位置保留 symlink。
- nested legacy Obsidian Vault 与 root legacy Obsidian Vault 内容不同，未自动合并；已移入 `/Users/charles/Documents/_待整理_iCloud迁移/Obsidian Vault - charles的MacBook Pro` 供人工复核，并在 nested 位置保留 symlink。
- 未删除文件。

## External Report

详细整理日志：

- `/Users/charles/Documents/_整理日志/2026-05-08-icloud-documents-organization.md`
- `/Users/charles/Documents/_整理日志/2026-05-08-icloud-documents-organization.json`

## Verification

- `brainctl status`: `vault=/Users/charles/Documents/brain`, `vault_exists=True`
- `brainctl sync`: `Sync complete: 0 pushed, 0 pulled`
- `brainctl reindex`: `indexed_blocks=2127`, `skipped_secret_blocks=14`
- `brainctl search '待完成任务控制台'`: returned dashboard results
- `brainctl search 'permission-gates'`: returned tool-budget atom results
- `local_brain_exhaustive_audit.py`: `stop_gate_pass=True`, `broken_wikilinks_count=0`, `secret_pattern_hits=0`

## Safety Notes

Root `Documents` 中的散落个人文件、应用数据目录、旧版 `Obsidian Vault` 未批量移动，避免破坏应用路径或误合并个人资料。后续如要继续全量整理，应先生成分类 dry-run manifest，再按类别逐步迁移。

## Evidence Boundary

Model agreement is provenance only; status promotion requires command/file/search proof recorded in this note or linked artifacts.

