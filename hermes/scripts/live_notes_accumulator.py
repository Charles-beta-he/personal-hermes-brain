#!/usr/bin/env python3
"""
Live Notes Accumulator — Session Working Memory
Inspired by Rowboat's "Live Notes" pattern.

Accumulates observations, facts, and context during a session.
Provides ephemeral working memory between "current conversation" and
"long-term memory" — the missing middle layer.

Usage:
    python3 live_notes_accumulator.py add "observation text" [--tag TAG]
    python3 live_notes_accumulator.py show [--recent N]
    python3 live_notes_accumulator.py consolidate  # promote to memory
    python3 live_notes_accumulator.py clear
    python3 live_notes_accumulator.py search "query"

DB: ~/.hermes/state/live_notes.sqlite
"""

import sqlite3
import json
import os
import sys
from datetime import datetime, timedelta

DB_PATH = os.path.expanduser("~/.hermes/state/live_notes.sqlite")
MEMORY_PATH = os.path.expanduser("~/.hermes/memory/system/live_session_notes.md")

CATEGORIES = [
    "observation",  # Something noticed during conversation
    "decision",     # A choice made
    "fact",         # A verified fact learned
    "task",         # Something to do
    "context",      # Background information
    "insight",      # A realization or connection
]


def init_db():
    """Create live notes tables."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'observation',
            tags TEXT DEFAULT '[]',
            session_id TEXT,
            importance INTEGER DEFAULT 5,
            created_at TEXT NOT NULL,
            consolidated INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_consolidated ON notes(consolidated)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created_at)")
    conn.commit()
    return conn


def add_note(content, category="observation", tags=None, importance=5, session_id=None):
    """Add a live note."""
    conn = init_db()
    now = datetime.now().isoformat()
    tags_json = json.dumps(tags or [])

    cur = conn.execute(
        "INSERT INTO notes (content, category, tags, session_id, importance, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (content, category, tags_json, session_id, importance, now)
    )
    conn.commit()
    note_id = cur.lastrowid
    conn.close()
    return note_id


def show_notes(recent=20, consolidated=False):
    """Show recent live notes."""
    conn = init_db()
    cons_filter = 0 if not consolidated else 1
    cur = conn.execute(
        "SELECT id, content, category, tags, importance, created_at, consolidated FROM notes WHERE consolidated = ? ORDER BY created_at DESC LIMIT ?",
        (cons_filter, recent)
    )
    rows = cur.fetchall()

    if not rows:
        print("No live notes." if not consolidated else "No unconsolidated notes.")
        return

    for nid, content, cat, tags, imp, created, cons in rows:
        tags_list = json.loads(tags) if tags else []
        tag_str = f" [{', '.join(tags_list)}]" if tags_list else ""
        imp_str = f" (imp:{imp})" if imp != 5 else ""
        ts = created[:19] if created else "?"
        print(f"  #{nid} [{cat}]{tag_str}{imp_str} {ts}")
        print(f"    {content[:120]}")
        print()

    conn.close()


def search_notes(query, limit=10):
    """Search live notes by content."""
    conn = init_db()
    cur = conn.execute(
        "SELECT id, content, category, tags, importance, created_at FROM notes WHERE content LIKE ? ORDER BY importance DESC, created_at DESC LIMIT ?",
        (f"%{query}%", limit)
    )
    rows = cur.fetchall()

    if not rows:
        print(f"No notes matching '{query}'")
        return

    for nid, content, cat, tags, imp, created in rows:
        tags_list = json.loads(tags) if tags else []
        tag_str = f" [{', '.join(tags_list)}]" if tags_list else ""
        print(f"  #{nid} [{cat}]{tag_str} imp={imp} {created[:19]}")
        print(f"    {content[:150]}")
        print()

    conn.close()


def consolidate():
    """Promote important notes to long-term memory."""
    conn = init_db()

    # Get unconsolidated notes, sorted by importance
    cur = conn.execute(
        "SELECT id, content, category, tags, importance, created_at FROM notes WHERE consolidated = 0 ORDER BY importance DESC, created_at DESC"
    )
    rows = cur.fetchall()

    if not rows:
        print("No notes to consolidate.")
        return

    # Group by category
    by_category = {}
    for nid, content, cat, tags, imp, created in rows:
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append((nid, content, imp, created))

    # Write to memory file
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        f.write("# Live Session Notes — Auto-consolidated\n\n")
        f.write(f"Consolidated at: {datetime.now().isoformat()}\n\n")

        for cat, notes in by_category.items():
            f.write(f"## {cat.title()}\n\n")
            for nid, content, imp, created in notes:
                imp_marker = "⭐" if imp >= 8 else ""
                f.write(f"- {imp_marker} {content} _({created[:10]})_\n")
            f.write("\n")

    # Mark as consolidated
    note_ids = [r[0] for r in rows]
    placeholders = ",".join("?" * len(note_ids))
    conn.execute(f"UPDATE notes SET consolidated = 1 WHERE id IN ({placeholders})", note_ids)
    conn.commit()

    print(f"Consolidated {len(rows)} notes to {MEMORY_PATH}")
    conn.close()


def clear_consolidated():
    """Remove consolidated notes older than 7 days."""
    conn = init_db()
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    cur = conn.execute("DELETE FROM notes WHERE consolidated = 1 AND created_at < ?", (cutoff,))
    conn.commit()
    print(f"Cleaned {cur.rowcount} old consolidated notes.")
    conn.close()


def stats():
    """Show live notes statistics."""
    conn = init_db()
    total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    uncons = conn.execute("SELECT COUNT(*) FROM notes WHERE consolidated = 0").fetchone()[0]
    cons = conn.execute("SELECT COUNT(*) FROM notes WHERE consolidated = 1").fetchone()[0]

    print(f"Live Notes Stats:")
    print(f"  Total:           {total}")
    print(f"  Active (uncons): {uncons}")
    print(f"  Consolidated:    {cons}")
    print()

    print("By category:")
    for row in conn.execute("SELECT category, COUNT(*) FROM notes GROUP BY category ORDER BY COUNT(*) DESC"):
        print(f"  {row[0]}: {row[1]}")

    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: live_notes_accumulator.py <command> [args]")
        print("Commands: add, show, search, consolidate, clear, stats")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: live_notes_accumulator.py add 'observation' [--tag TAG] [--cat CATEGORY] [--importance N]")
            sys.exit(1)

        content = sys.argv[2]
        category = "observation"
        tags = []
        importance = 5
        session_id = None

        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--tag" and i + 1 < len(sys.argv):
                tags.append(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--cat" and i + 1 < len(sys.argv):
                category = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--importance" and i + 1 < len(sys.argv):
                importance = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--session" and i + 1 < len(sys.argv):
                session_id = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        nid = add_note(content, category, tags, importance, session_id)
        print(f"Added note #{nid} [{category}]")

    elif cmd == "show":
        recent = 20
        if len(sys.argv) > 2 and sys.argv[2] == "--recent":
            recent = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        show_notes(recent)

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: live_notes_accumulator.py search 'query'")
            sys.exit(1)
        search_notes(sys.argv[2])

    elif cmd == "consolidate":
        consolidate()

    elif cmd == "clear":
        clear_consolidated()

    elif cmd == "stats":
        stats()

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
