---
type: strategy
layer: L2
status: completed
created: 2026-05-06T19:29:36+08:00
project: local-brain-main-hierarchy-migration
---

# P10 - Main Hierarchy Migration Strategy

## Strategic decision

用户已显式要求主层级迁移完成。因此本轮从 overlay-before-rewrite 转入 controlled migration。

## Architecture principle

主层级不是知识分类学全集，而是 control-plane：

1. 系统与偏好：identity / constraints。
2. 证据与原文：verbatim source。
3. 理论与元认知：frameworks and observer rules。
4. 知识原子：stable distilled principles。
5. 实践与项目：execution surface。
6. 治理与评审：audits, skills, evolution, reviews。
7. 仪表盘：state view。
8. 模板：artifact factory。
9. Hermes notes：synced agent records。

## Risk controls

- backup tar + manifest before migration。
- preserve file basenames and content hashes where possible。
- rewrite path wikilinks only, do not rewrite prose semantics。
- deterministic self-check > model agreement。
- scoped local commit only relevant artifacts。

## Stop gate

Migration is complete only when:

```json
{
  "empty_dirs": [],
  "top_level_no_index": [],
  "parent_no_direct_md_top": [],
  "broken_wikilinks_count": 0,
  "secret_pattern_hits": 0,
  "old_top_dirs_remaining": [],
  "required_searches_pass": true
}
```

中文检索别名：P10 主层级迁移策略 control-plane 本地大脑主层级迁移 无遗留
