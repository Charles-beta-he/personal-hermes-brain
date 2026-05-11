#!/usr/bin/env python3
from __future__ import annotations
import json, sqlite3, datetime
from pathlib import Path
H = Path.home()/'.hermes'
DB = H/'route_outcomes.db'
LOG_DIR = H/'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
def utc(): return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def emit(name, obj):
    obj.setdefault('ts', utc())
    p = LOG_DIR / f'{name}.jsonl'
    with p.open('a', encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False)+'\n')
    print(json.dumps(obj, ensure_ascii=False, indent=2))
def connect():
    if not DB.exists():
        raise SystemExit(json.dumps({'ok': False, 'error': f'missing db: {DB}'}, ensure_ascii=False))
    return sqlite3.connect(str(DB))

def main():
    con = connect(); con.row_factory = sqlite3.Row
    rows = con.execute("""
      select coalesce(route,'<blank>') route, coalesce(error,'') error,
             count(*) n, round(avg(duration_s), 3) avg_duration_s
      from route_outcomes
      where ts >= datetime('now','-24 hours')
        and route like 'planner-%'
        and (verdict != 'pass' or coalesce(error,'') != '')
      group by 1,2 order by n desc limit 20
    """).fetchall()
    groups = [dict(r) for r in rows]
    rec = {'ok': True, 'kind': 'planner_failure_triage', 'window': '24h', 'failure_group_count': len(groups), 'groups': groups, 'status': 'ok' if not groups else 'warn'}
    emit('planner-failure-triage', rec)
if __name__ == '__main__': main()
