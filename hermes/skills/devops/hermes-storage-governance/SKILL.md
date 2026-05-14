---
name: hermes-storage-governance
description: "Hermes 存储治理: state.db FTS 膨胀治理、会话 TTL、快照清理、自动 cron。防止多模型运行导致磁盘膨胀。"
triggers:
  - "storage cleanup"
  - "disk space"
  - "state.db"
  - "存储治理"
  - "磁盘清理"
---

# Hermes 存储治理

## 问题
多模型运行导致 ~/.hermes 膨胀:
- state.db: FTS trigram 索引 5.5x 膨胀 (293MB 数据 → 1.6GB 索引)
- 会话无 TTL, 永久保留
- snapshots/checkpoints 无清理

## 清理脚本
~/.hermes/scripts/hermes-cleanup.py
```
--dry-run          预览
--session-ttl N    会话保留天数 (默认 7)
--snapshot-ttl N   快照保留天数 (默认 3)
--checkpoint-ttl N 检查点保留天数 (默认 3)
--log-ttl N        日志保留天数 (默认 7)
--aggressive       保留 1 天
```

## 自动 cron
已配置: 每天 4:00 AM 运行, 保留 7 天会话

## 手动清理
```bash
# 1. 删除旧会话
python3 ~/.hermes/scripts/hermes-cleanup.py --session-ttl 3

# 2. VACUUM state.db
sqlite3 ~/.hermes/state.db "VACUUM;"

# 3. 清理 WAL
sqlite3 ~/.hermes/state.db "PRAGMA wal_checkpoint(TRUNCATE);"

# 4. 清理旧快照/检查点
python3 ~/.hermes/scripts/hermes-cleanup.py --snapshot-ttl 1 --checkpoint-ttl 1
```

## 关键 Pitfalls

1. **WAL 文件膨胀**: state.db-wal 可能增长到 GB 级别。VACUUM 后必须执行 `PRAGMA wal_checkpoint(TRUNCATE)` 清空 WAL。

2. **Unix 时间戳**: sessions.started_at 存储 Unix 时间戳 (float), 不是 ISO 字符串。SQLite 比较用 `strftime('%s', 'now', '-3 days')` 而非 `datetime('now', '-3 days')`。

3. **FTS trigram 索引**: messages_fts_trigram 产生 ~4x 膨胀 (293MB 数据 → 1.2GB 索引)。监控: `sqlite3 state.db "SELECT name, SUM(pgsize) FROM dbstat WHERE name LIKE '%fts%' GROUP BY name"`。

4. **清理顺序**: 先删 messages, 再删 sessions (外键约束)。删完后 `INSERT INTO messages_fts(messages_fts) VALUES('rebuild')` 重建 FTS。

## 效果
Before: 9.3GB → After: 4.3GB (释放 5.0GB, -54%)

## state.db 构成分析
| 组件 | 大小 | 说明 |
|------|------|------|
| messages_fts_trigram_data | 815MB | 三元组 FTS 索引 (最大!) |
| messages_fts_trigram_content | 410MB | 三元组内容 |
| messages_fts_content | 410MB | 普通 FTS 内容 |
| messages_fts_data | 113MB | 普通 FTS 数据 |
| messages | 516MB | 实际消息数据 |
| sessions | 155MB | 会话元数据 |
| FTS 总计 | ~1.6GB | 293MB 数据 → 5.5x 膨胀 |

## Pitfalls

1. **Unix timestamps**: `sessions.started_at` stores Unix timestamps (float), NOT ISO dates. Use `strftime('%s', 'now', '-3 days')` for SQLite comparisons, NOT `datetime('now', '-3 days')`. Wrong comparison: `started_at < '2026-05-10...'` always matches because string '1778668710' < '2026-05-10'.

2. **WAL file growth**: After heavy writes (multi-model runs), `state.db-wal` can grow to 2GB+. Always checkpoint after cleanup: `sqlite3 state.db "PRAGMA wal_checkpoint(TRUNCATE)"`. Check: `ls -lh ~/.hermes/state.db*`.

3. **FTS rebuild after pruning**: After DELETE operations, rebuild FTS indexes or they retain deleted data:
   ```sql
   INSERT INTO messages_fts(messages_fts) VALUES('rebuild');
   INSERT INTO messages_fts_trigram(messages_fts_trigram) VALUES('rebuild');
   ```

4. **VACUUM after DELETE**: SQLite doesn't reclaim space after DELETE. Must VACUUM: `sqlite3 state.db "VACUUM"`. Before VACUUM, check file size: `ls -lh ~/.hermes/state.db`.

5. **Snapshot cleanup order**: Clean snapshots BEFORE VACUUM. Snapshots reference state.db pages; cleaning them first avoids stale references.

## 监控命令
```bash
# FTS 膨胀检查
sqlite3 ~/.hermes/state.db "SELECT name, SUM(pgsize)/1024/1024 || 'MB' FROM dbstat WHERE name LIKE '%fts%' GROUP BY name ORDER BY SUM(pgsize) DESC"

# WAL 大小检查
ls -lh ~/.hermes/state.db-wal

# 会话数量
sqlite3 ~/.hermes/state.db "SELECT COUNT(*) FROM sessions"

# 最旧会话
sqlite3 ~/.hermes/state.db "SELECT datetime(MIN(started_at), 'unixepoch', 'localtime') FROM sessions"
```
