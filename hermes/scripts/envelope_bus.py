#!/usr/bin/env python3
"""Envelope Bus — SQLite-backed task pipeline state manager.

Simplified hermes-pipeline envelope bus for task lifecycle management.
PENDING → RUNNING → DONE → FAILED → SKIPPED
"""
import sqlite3, json, time, hashlib, os, calendar
from pathlib import Path

DB_PATH = Path.home() / '.hermes' / 'state' / 'envelope_bus.db'
ESCAPE_ACK_PATH = Path.home() / '.hermes' / 'state' / 'envelope_escape_ack.json'
ISO_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute('''CREATE TABLE IF NOT EXISTS envelopes (
        id          TEXT PRIMARY KEY,
        type        TEXT CHECK(type IN ('TASK','PLAN','RESULT','VALIDATION')),
        status      TEXT CHECK(status IN ('PENDING','RUNNING','DONE','FAILED','SKIPPED','BLOCKED')),
        project     TEXT,
        assignee    TEXT,
        title       TEXT,
        payload     TEXT,
        trace       TEXT,
        proof_sha   TEXT,
        error       TEXT,
        retry_count INTEGER DEFAULT 0,
        max_retries INTEGER DEFAULT 3,
        appetite_seconds INTEGER DEFAULT 1800,
        created_at  TEXT,
        updated_at  TEXT,
        started_at  TEXT,
        completed_at TEXT
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON envelopes(status)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_type ON envelopes(type)')
    conn.commit()
    return conn

def create(type, title, project='', assignee='', payload=None, appetite_seconds=1800):
    eid = hashlib.sha256(f"{title}{time.time()}".encode()).hexdigest()[:12]
    now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    conn = get_db()
    conn.execute(
        'INSERT INTO envelopes (id,type,status,title,project,assignee,payload,trace,appetite_seconds,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
        (eid, type, 'PENDING', title, project, assignee, json.dumps(payload or {}), '[]', appetite_seconds, now, now)
    )
    conn.commit()
    return eid

def get(eid):
    conn = get_db()
    row = conn.execute('SELECT * FROM envelopes WHERE id=?', (eid,)).fetchone()
    return dict(row) if row else None

def update_status(eid, status, error=None, proof_sha=None):
    now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    conn = get_db()
    updates = ['status=?', 'updated_at=?']
    params = [status, now]
    if error:
        updates.append('error=?')
        params.append(error)
    if proof_sha:
        updates.append('proof_sha=?')
        params.append(proof_sha)
    if status == 'RUNNING':
        updates.append('started_at=?')
        params.append(now)
    if status in ('DONE', 'FAILED', 'SKIPPED'):
        updates.append('completed_at=?')
        params.append(now)
    params.append(eid)
    conn.execute(f'UPDATE envelopes SET {",".join(updates)} WHERE id=?', params)
    conn.commit()

def append_trace(eid, event):
    conn = get_db()
    row = conn.execute('SELECT trace FROM envelopes WHERE id=?', (eid,)).fetchone()
    if not row: return
    trace = json.loads(row['trace'] or '[]')
    trace.append({'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **event})
    conn.execute('UPDATE envelopes SET trace=?,updated_at=? WHERE id=?', 
                 (json.dumps(trace), time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), eid))
    conn.commit()

def increment_retry(eid):
    conn = get_db()
    conn.execute('UPDATE envelopes SET retry_count=retry_count+1,updated_at=? WHERE id=?',
                 (time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), eid))
    conn.commit()
    row = conn.execute('SELECT retry_count,max_retries FROM envelopes WHERE id=?', (eid,)).fetchone()
    return row['retry_count'], row['max_retries']

def list_by_status(status, limit=100):
    conn = get_db()
    rows = conn.execute('SELECT * FROM envelopes WHERE status=? ORDER BY created_at LIMIT ?', (status, limit)).fetchall()
    return [dict(r) for r in rows]

def count_by_status():
    conn = get_db()
    rows = conn.execute('SELECT status, COUNT(*) as cnt FROM envelopes GROUP BY status').fetchall()
    return {r['status']: r['cnt'] for r in rows}

def check_timeout():
    """Find RUNNING tasks that exceeded appetite."""
    conn = get_db()
    now = time.time()
    rows = conn.execute('SELECT * FROM envelopes WHERE status=?', ('RUNNING',)).fetchall()
    timed_out = []
    for row in rows:
        if row['started_at']:
            started = time.mktime(time.strptime(row['started_at'], '%Y-%m-%dT%H:%M:%SZ'))
            if now - started > row['appetite_seconds']:
                timed_out.append(dict(row))
    return timed_out

def _now_iso():
    return time.strftime(ISO_FORMAT, time.gmtime())


def _parse_iso_z(value):
    if not isinstance(value, str):
        return None
    try:
        return calendar.timegm(time.strptime(value, ISO_FORMAT))
    except Exception:
        return None


def _load_escape_ack():
    """Load human escape acknowledgement watermark.

    Missing/malformed/future ack is fail-closed: callers must count all
    existing failures/blocks rather than silently clearing a circuit breaker.
    """
    if not ESCAPE_ACK_PATH.exists():
        return {'status': 'missing', 'acked_at': None}
    try:
        data = json.loads(ESCAPE_ACK_PATH.read_text(encoding='utf-8'))
        acked_at = data.get('acked_at')
        ack_ts = _parse_iso_z(acked_at)
        if ack_ts is None:
            return {'status': 'invalid', 'acked_at': acked_at, 'reason': 'invalid_acked_at'}
        if ack_ts > time.time() + 60:
            return {'status': 'invalid', 'acked_at': acked_at, 'reason': 'acked_at_in_future'}
        return {
            'status': 'ok',
            'acked_at': acked_at,
            'acked_by': data.get('acked_by', ''),
            'reason': data.get('reason', ''),
        }
    except Exception as exc:
        return {'status': 'invalid', 'acked_at': None, 'reason': str(exc)[:120]}


def acknowledge_escape(reason, actor='human', acked_at=None):
    """Acknowledge reviewed historical FAILED/BLOCKED envelopes.

    This does not modify envelope terminal states; it only moves the human
    escape watermark so future failures after the ack still trip fail-closed.
    """
    ESCAPE_ACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        'acked_at': acked_at or _now_iso(),
        'acked_by': actor,
        'reason': reason,
    }
    # Validate before writing so a caller cannot accidentally install a broken
    # future/malformed watermark.
    if _parse_iso_z(record['acked_at']) is None:
        raise ValueError('acked_at must use YYYY-MM-DDTHH:MM:SSZ')
    ESCAPE_ACK_PATH.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return record


def _failure_counts(conn, since_ack=False, acked_at=None):
    rows = conn.execute(
        "SELECT status, updated_at, completed_at FROM envelopes WHERE status IN ('FAILED','BLOCKED')"
    ).fetchall()
    counts = {'blocks': 0, 'failures': 0, 'invalid_timestamps': 0}
    ack_ts = _parse_iso_z(acked_at) if since_ack else None
    for row in rows:
        include = True
        if since_ack and ack_ts is not None:
            event_time = row['completed_at'] or row['updated_at']
            event_ts = _parse_iso_z(event_time)
            if event_ts is None:
                # Fail closed: malformed timestamps remain counted.
                counts['invalid_timestamps'] += 1
                include = True
            else:
                include = event_ts > ack_ts
        if not include:
            continue
        if row['status'] == 'BLOCKED':
            counts['blocks'] += 1
        elif row['status'] == 'FAILED':
            counts['failures'] += 1
    return counts


def human_escape_check():
    """Check if human escape threshold is hit after the ack watermark.

    Historical terminal failures remain in the DB for audit. A human ack only
    prevents already-reviewed history from permanently freezing the task pool;
    any new 2 BLOCKED or 3 FAILED envelopes after the ack still trigger escape.
    """
    conn = get_db()
    historical = _failure_counts(conn)
    ack = _load_escape_ack()
    if ack.get('status') == 'ok':
        current = _failure_counts(conn, since_ack=True, acked_at=ack.get('acked_at'))
    else:
        current = dict(historical)
    triggered = current['blocks'] >= 2 or current['failures'] >= 3
    return triggered, {
        # Backwards-compatible names: now mean "active since ack" when ack is ok.
        'blocks': current['blocks'],
        'failures': current['failures'],
        'since_ack': current,
        'historical': historical,
        'ack': ack,
    }

def stats():
    counts = count_by_status()
    escape, escape_info = human_escape_check()
    timeouts = check_timeout()
    return {
        'total': sum(counts.values()),
        'by_status': counts,
        'timeouts': len(timeouts),
        'human_escape_triggered': escape,
        'escape_info': escape_info,
    }

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'stats':
        print(json.dumps(stats(), indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == 'init':
        get_db()
        print('Envelope bus initialized')
    elif len(sys.argv) > 1 and sys.argv[1] == 'ack-escape':
        reason = ' '.join(sys.argv[2:]) or 'human reviewed historical failures'
        print(json.dumps(acknowledge_escape(reason), indent=2, ensure_ascii=False))
    else:
        print('Usage: envelope_bus.py [stats|init|ack-escape <reason>]')
