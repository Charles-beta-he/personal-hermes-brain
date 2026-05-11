---
type: playbook
layer: L4
status: active
created: 2026-05-06T19:29:36+08:00
concepts: [main-hierarchy-migration, p10-control-plane, obsidian]
---

# 08 - 主层级迁移Playbook

## Loop

1. Backup manifest + tar。
2. Define old-to-new mapping。
3. Multi-model provenance review。
4. Move dirs, preserve content。
5. Rewrite path wikilinks。
6. Create top MOCs。
7. Run self-check。
8. Fix until PASS。
9. brainctl sync/reindex/search。
10. scoped local commit。

## Verification commands

```bash
python3 ~/.hermes/scripts/local_brain_main_hierarchy_migration_selfcheck.py --json
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "本地大脑主层级迁移 P10 control-plane layout 无遗留" --limit 8
```

中文检索别名：主层级迁移Playbook 本地大脑主层级迁移 PUA loop 无遗留
