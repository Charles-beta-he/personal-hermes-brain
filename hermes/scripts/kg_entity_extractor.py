#!/usr/bin/env python3
"""
Knowledge Graph Entity Extractor
Inspired by Rowboat's knowledge graph pattern.

Extracts entities and relations from text, stores in SQLite graph tables.
Enables structured queries like "Who worked on project X?" without full-text scan.

Usage:
    python3 kg_entity_extractor.py extract "Some text to analyze"
    python3 kg_entity_extractor.py query "person" "project"
    python3 kg_entity_extractor.py stats
    python3 kg_entity_extractor.py scan-brain  # scan Obsidian vault

DB: ~/.hermes/state/kg_graph.sqlite
Tables: entities(id, name, type, source, created_at, updated_at, metadata)
         relations(id, src_id, dst_id, type, source, created_at, metadata)
"""

import sqlite3
import json
import re
import os
import sys
from pathlib import Path
from datetime import datetime

DB_PATH = os.path.expanduser("~/.hermes/state/kg_graph.sqlite")
BRAIN_VAULT = os.path.expanduser("~/Documents/brain")

ENTITY_TYPES = {
    "person": r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",
    "project": r"\b[A-Z][a-z]+[-\s]?[A-Z]?[a-z]*\b",
    "tool": r"\b(python|typescript|docker|kubernetes|react|sqlite|hermes|rowboat|claude|gpt|openai|anthropic)\b",
    "concept": r"\b(knowledge graph|entity extraction|semantic search|event sourcing|live notes)\b",
}

RELATION_PATTERNS = [
    (r"(\w+)\s+(?:works?\s+on|built|created|developed|maintains?)\s+(\w+)", "works_on"),
    (r"(\w+)\s+(?:uses?|using|leverages?)\s+(\w+)", "uses"),
    (r"(\w+)\s+(?:belongs?\s+to|part\s+of|member\s+of)\s+(\w+)", "belongs_to"),
    (r"(\w+)\s+(?:depends?\s+on|requires?|needs?)\s+(\w+)", "depends_on"),
    (r"(\w+)\s+(?:implements?|realizes?)\s+(\w+)", "implements"),
    (r"(\w+)\s+(?:inspired|influenced|derived\s+from)\s+(\w+)", "inspired_by"),
]


def init_db():
    """Create knowledge graph tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'unknown',
            source TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            UNIQUE(name, type)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            src_id INTEGER NOT NULL,
            dst_id INTEGER NOT NULL,
            type TEXT NOT NULL DEFAULT 'related_to',
            source TEXT,
            created_at TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            FOREIGN KEY (src_id) REFERENCES entities(id),
            FOREIGN KEY (dst_id) REFERENCES entities(id),
            UNIQUE(src_id, dst_id, type)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_src ON relations(src_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_dst ON relations(dst_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(type)")
    conn.commit()
    return conn


def upsert_entity(conn, name, etype="unknown", source=None, metadata=None):
    """Insert or update an entity. Returns entity id."""
    now = datetime.now().isoformat()
    name = name.strip()
    if not name:
        return None
    cur = conn.execute(
        "SELECT id FROM entities WHERE name = ? AND type = ?",
        (name, etype)
    )
    row = cur.fetchone()
    if row:
        conn.execute(
            "UPDATE entities SET updated_at = ?, metadata = ? WHERE id = ?",
            (now, json.dumps(metadata or {}), row[0])
        )
        return row[0]
    else:
        cur = conn.execute(
            "INSERT INTO entities (name, type, source, created_at, updated_at, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (name, etype, source, now, now, json.dumps(metadata or {}))
        )
        return cur.lastrowid


def upsert_relation(conn, src_name, dst_name, rel_type, source=None, src_type="unknown", dst_type="unknown"):
    """Insert a relation between two entities."""
    now = datetime.now().isoformat()
    src_id = upsert_entity(conn, src_name, src_type, source)
    dst_id = upsert_entity(conn, dst_name, dst_type, source)
    if not src_id or not dst_id:
        return
    try:
        conn.execute(
            "INSERT OR IGNORE INTO relations (src_id, dst_id, type, source, created_at) VALUES (?, ?, ?, ?, ?)",
            (src_id, dst_id, rel_type, source, now)
        )
    except sqlite3.IntegrityError:
        pass


def extract_entities(text, source=None):
    """Extract entities from text using regex patterns."""
    entities = []
    for etype, pattern in ENTITY_TYPES.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            name = m if isinstance(m, str) else m[0] if m else ""
            if name and len(name) > 2:
                entities.append((name.strip(), etype))
    return entities


def extract_relations(text, source=None):
    """Extract relations from text using patterns."""
    relations = []
    for pattern, rel_type in RELATION_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            if len(m) == 2 and m[0] and m[1]:
                relations.append((m[0].strip(), m[1].strip(), rel_type))
    return relations


def process_text(text, source=None):
    """Extract and store all entities and relations from text."""
    conn = init_db()
    entities = extract_entities(text, source)
    relations = extract_relations(text, source)

    for name, etype in entities:
        upsert_entity(conn, name, etype, source)

    for src, dst, rtype in relations:
        upsert_relation(conn, src, dst, rtype, source)

    conn.commit()
    return {"entities": len(entities), "relations": len(relations)}


def scan_brain_vault():
    """Scan Obsidian vault for entities and relations."""
    if not os.path.isdir(BRAIN_VAULT):
        print(f"Brain vault not found: {BRAIN_VAULT}")
        return

    conn = init_db()
    total_entities = 0
    total_relations = 0
    files_scanned = 0

    for root, dirs, files in os.walk(BRAIN_VAULT):
        for f in files:
            if not f.endswith(".md"):
                continue
            fpath = os.path.join(root, f)
            try:
                with open(fpath, "r", encoding="utf-8") as fh:
                    text = fh.read()
                result = process_text(text, source=fpath)
                total_entities += result["entities"]
                total_relations += result["relations"]
                files_scanned += 1
            except Exception as e:
                print(f"Error reading {fpath}: {e}", file=sys.stderr)

    conn.close()
    print(f"Scanned {files_scanned} files")
    print(f"Extracted {total_entities} entity mentions, {total_relations} relations")


def query_graph(src_type=None, dst_type=None, rel_type=None):
    """Query the knowledge graph."""
    conn = init_db()
    conditions = []
    params = []

    sql = """
        SELECT e1.name, e1.type, r.type, e2.name, e2.type
        FROM relations r
        JOIN entities e1 ON r.src_id = e1.id
        JOIN entities e2 ON r.dst_id = e2.id
    """

    if src_type:
        conditions.append("e1.type = ?")
        params.append(src_type)
    if dst_type:
        conditions.append("e2.type = ?")
        params.append(dst_type)
    if rel_type:
        conditions.append("r.type = ?")
        params.append(rel_type)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY r.created_at DESC LIMIT 50"

    cur = conn.execute(sql, params)
    rows = cur.fetchall()

    if not rows:
        print("No relations found.")
        return

    for src_name, st, rel, dst_name, dt in rows:
        print(f"  [{st}] {src_name} --{rel}--> [{dt}] {dst_name}")

    conn.close()


def show_stats():
    """Show knowledge graph statistics."""
    conn = init_db()
    ent_count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    rel_count = conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]

    print(f"Knowledge Graph Stats:")
    print(f"  Entities:  {ent_count}")
    print(f"  Relations: {rel_count}")
    print()

    print("Entity types:")
    for row in conn.execute("SELECT type, COUNT(*) FROM entities GROUP BY type ORDER BY COUNT(*) DESC"):
        print(f"  {row[0]}: {row[1]}")

    print("\nRelation types:")
    for row in conn.execute("SELECT type, COUNT(*) FROM relations GROUP BY type ORDER BY COUNT(*) DESC"):
        print(f"  {row[0]}: {row[1]}")

    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: kg_entity_extractor.py <command> [args]")
        print("Commands: extract, query, stats, scan-brain")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "extract":
        if len(sys.argv) < 3:
            print("Usage: kg_entity_extractor.py extract 'text to analyze'")
            sys.exit(1)
        text = " ".join(sys.argv[2:])
        result = process_text(text, source="cli")
        print(f"Extracted: {result['entities']} entities, {result['relations']} relations")

    elif cmd == "query":
        src_type = sys.argv[2] if len(sys.argv) > 2 else None
        dst_type = sys.argv[3] if len(sys.argv) > 3 else None
        query_graph(src_type, dst_type)

    elif cmd == "stats":
        show_stats()

    elif cmd == "scan-brain":
        scan_brain_vault()

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
