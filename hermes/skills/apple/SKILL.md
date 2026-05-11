---
name: apple
description: "Apple workflow skill. See references/ for detailed guides."
license: MIT
---

# Apple

> Apple 相关的工作流 Skill

## 输入

- 用户请求的具体参数
- 相关上下文

## 输出

- 执行结果或生成的文件

## 约束

- 遵循项目规范
- 在 context budget 内完成

## 检查点

- [ ] 输入参数完整
- [ ] 输出符合预期

## 关联 Skill

- `pua`: 核心行为基线
- `loop`: 迭代管理


## 约束

- 遵循项目规范
- 在 context budget 内完成


## 约束

- 遵循项目规范
- 在 context budget 内完成


## iCloud Documents organization

When organizing `~/Documents` after iCloud creates duplicate folders such as `文稿 - <Mac name>`, use `references/icloud-documents-safe-organization.md`: inventory first, protect local brain/Obsidian/app paths, move only low-risk loose files, write manifests, and delete low-value files only after explicit user approval.

## Desktop safe organization

When organizing `~/Desktop`, use `references/desktop-safe-organization.md`: inventory first, move top-level loose files into a dated organizer folder for the safe default; if the user explicitly asks for deep organization, preserve excluded folders and known workspaces, scan code-directory path dependencies before moving projects, write JSONL move manifests + rollback scripts, run rollback dry-run, set sensitive review folders to `0700`, and avoid full hashing of iCloud cloud-only/large files when it would stall.

## 示例

```bash
# 示例用法
```
