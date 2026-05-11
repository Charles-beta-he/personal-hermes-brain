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
    total24, real24, synth24 = con.execute("""
      select count(*),
             sum(case when coalesce(is_synthetic,0)=0 then 1 else 0 end),
             sum(case when coalesce(is_synthetic,0)=1 then 1 else 0 end)
      from route_outcomes where ts >= datetime('now','-24 hours')
    """).fetchone()
    total24 = total24 or 0; real24 = real24 or 0; synth24 = synth24 or 0
    status = 'ok' if total24 >= 20 else 'warn'
    rec = {'ok': status == 'ok', 'kind': 'eval_trace_audit', 'window': '24h', 'total24': total24, 'real24': real24, 'synthetic24': synth24, 'threshold': 20, 'status': status}
    emit('hermes-eval-trace-audit', rec)
if __name__ == '__main__': main()
