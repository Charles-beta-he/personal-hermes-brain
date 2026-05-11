#!/usr/bin/env python3
"""backfill-model-traces.py — 回填历史 route_outcomes 的 model_chain 字段
只设置 model_chain, 不改 is_synthetic (避免污染 real-only 口径)
"""

import os, sys, json, sqlite3

DB_PATH = os.path.expanduser(
    os.environ.get("HERMES_ROUTE_DB_PATH", "~/.hermes/route_outcomes.db")
)

# 获取当前模型
import yaml
config_path = os.path.expanduser("~/.hermes/config.yaml")
try:
    config = yaml.safe_load(open(config_path))
    model = config.get("model", {}).get("default", "") or config.get("model", {}).get("name", "") or "unknown"
except:
    model = "unknown"

print(f"Backfilling model_chain with: {model}")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# 检查哪些行 model_chain 为空
count_before = conn.execute(
    "SELECT COUNT(*) FROM route_outcomes WHERE model_chain IS NULL OR model_chain = ''"
).fetchone()[0]

print(f"Rows with empty model_chain: {count_before}")

if count_before == 0:
    print("Nothing to backfill.")
    conn.close()
    sys.exit(0)

# 记录 is_synthetic=0 的数量 (不应改变)
real_before = conn.execute(
    "SELECT COUNT(*) FROM route_outcomes WHERE is_synthetic = 0"
).fetchone()[0]

# 回填
model_chain_json = json.dumps([model])
conn.execute(
    "UPDATE route_outcomes SET model_chain = ? WHERE model_chain IS NULL OR model_chain = ''",
    (model_chain_json,)
)
conn.commit()

# 验证
real_after = conn.execute(
    "SELECT COUNT(*) FROM route_outcomes WHERE is_synthetic = 0"
).fetchone()[0]

count_after = conn.execute(
    "SELECT COUNT(*) FROM route_outcomes WHERE model_chain IS NULL OR model_chain = ''"
).fetchone()[0]

print(f"Rows remaining empty: {count_after}")
print(f"is_synthetic=0 count: {real_before} → {real_after} (should be unchanged: {real_before == real_after})")

# 展示样例
sample = conn.execute(
    "SELECT id, skill, route, model_chain, is_synthetic FROM route_outcomes ORDER BY id DESC LIMIT 5"
).fetchall()
print("\nSample rows after backfill:")
for r in sample:
    print(f"  id={r['id']} skill={r['skill']} model={r['model_chain']} synthetic={r['is_synthetic']}")

conn.close()

if real_before != real_after:
    print("\n⚠ WARNING: is_synthetic=0 count changed! Backfill may have corrupted data.")
    sys.exit(1)
else:
    print(f"\n✓ Backfill complete. {count_before} rows updated, real-only metrics preserved.")
