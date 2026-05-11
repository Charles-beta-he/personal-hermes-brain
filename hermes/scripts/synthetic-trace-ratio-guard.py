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
    con = connect()
    total, synth = con.execute("""
      select count(*), sum(case when coalesce(is_synthetic,0)=1 then 1 else 0 end)
      from route_outcomes where ts >= datetime('now','-7 days')
    """).fetchone()
    total = total or 0; synth = synth or 0
    ratio = (synth / total) if total else 0.0
    status = 'ok' if ratio <= 0.60 else 'alert'
    rec = {'ok': status == 'ok', 'kind': 'synthetic_trace_ratio_guard', 'window': '7d', 'total': total, 'synthetic': synth, 'ratio': round(ratio, 4), 'threshold': 0.60, 'status': status}
    emit('synthetic-trace-ratio-guard', rec)
if __name__ == '__main__': main()
