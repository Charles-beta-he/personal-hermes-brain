---
type: moc
status: active
created: 2026-05-06T08:48:00Z
folder: 00-evidence
---

# L0 Evidence 原始证据层

## 用途

保存事实输入、截图 OCR、链接、工具输出摘要；只放可追溯证据，不放推论。

## 收录规则

- 只收与本目录语义直接相关的 Markdown artifact。
- 每个新增笔记应有清晰标题、来源/边界、与其他目录的链接。
- 任务/WIP 放入 `05-实践与项目/tasks/` 并设置 expiry；稳定事实再晋升到 atoms/project/review。
- 不保存真实凭证、token、password、connection string；如出现统一写 `[REDACTED]`。

## 当前直接笔记

- [[02-证据与原文/evidence/2026-05-06-symphony-source-and-obsidian-cli-evidence|2026-05-06-symphony-source-and-obsidian-cli-evidence]]

## 子目录

- 无直接子目录。

## 维护规则

每次本目录新增 3 个以上笔记，更新本索引；每次本地大脑结构变更后运行 `brainctl sync && brainctl reindex && brainctl search` 验证。
