#!/usr/bin/env python3
"""
Semantic Retrieval — TF-IDF based semantic search over the brain vault.

Inspired by Rowboat's vector embedding search pattern.
Provides conceptual similarity search beyond keyword FTS.
Stepping stone to full embedding-based retrieval (nomic-embed).

Usage:
    python3 semantic_retrieval.py index                    # Build/rebuild index
    python3 semantic_retrieval.py search "query text"      # Search with TF-IDF
    python3 semantic_retrieval.py search "query" --top 10  # Top N results
    python3 semantic_retrieval.py stats                    # Index statistics
    python3 semantic_retrieval.py related "file.md"        # Find related files

DB: ~/.hermes/state/semantic_index.sqlite
Brain vault: ~/Documents/brain (configurable via BRAIN_VAULT env)
"""

import sqlite3
import json
import os
import sys
import re
import math
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

DB_PATH = os.path.expanduser("~/.hermes/state/semantic_index.sqlite")
BRAIN_VAULT = os.environ.get("BRAIN_VAULT", os.path.expanduser("~/Documents/brain"))
HERMES_MEMORY = os.path.expanduser("~/.hermes/memory")

# Stopwords for TF-IDF (English + common markdown)
STOPWORDS = set("""
a an the is are was were be been being have has had do does did will would
shall should can could may might must need dare ought to of in on at by for
with from as into through during before after above below between out off
over under again further then once here there when where why how all each
every both few more most other some such no nor not only own same so than
too very just don doesn didn won wouldn shan shouldn but and or if while
about up it its he she they them their his her my your our this that these
those what which who whom how where when why whether however therefore
furthermore moreover nevertheless nonetheless besides also still already
yet even though although unless until since because since so that
# ## ### - -- ``` markdown http https www com org
""".split())


def init_db():
    """Create semantic index tables."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            title TEXT,
            content_hash TEXT,
            word_count INTEGER,
            indexed_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT NOT NULL UNIQUE,
            doc_freq INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS term_doc (
            term_id INTEGER NOT NULL,
            doc_id INTEGER NOT NULL,
            term_freq REAL NOT NULL,
            tf_idf REAL NOT NULL,
            PRIMARY KEY (term_id, doc_id),
            FOREIGN KEY (term_id) REFERENCES terms(id),
            FOREIGN KEY (doc_id) REFERENCES documents(id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_terms_term ON terms(term)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_term_doc_doc ON term_doc(doc_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_term_doc_tf_idf ON term_doc(tf_idf)")
    conn.commit()
    return conn


def tokenize(text):
    """Tokenize text into terms, removing stopwords and short tokens."""
    # Remove markdown syntax
    text = re.sub(r'```[\s\S]*?```', ' ', text)  # code blocks
    text = re.sub(r'`[^`]*`', ' ', text)  # inline code
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)  # links
    text = re.sub(r'[#*_~\[\]()>|]', ' ', text)  # markdown chars
    text = re.sub(r'https?://\S+', ' ', text)  # URLs

    # Split on non-alphanumeric, lowercase
    words = re.findall(r'[a-z][a-z0-9_]{2,}', text.lower())

    # Filter stopwords and short tokens
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def compute_tf(words):
    """Compute term frequency (normalized by doc length)."""
    counts = Counter(words)
    total = len(words) if words else 1
    return {term: count / total for term, count in counts.items()}


def compute_idf(doc_freq, total_docs):
    """Compute inverse document frequency."""
    if doc_freq == 0:
        return 0
    return math.log(total_docs / doc_freq)


def hash_content(text):
    """Simple content hash for change detection."""
    import hashlib
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def collect_files():
    """Collect all markdown files from brain vault and hermes memory."""
    files = []

    for base_dir in [BRAIN_VAULT, HERMES_MEMORY]:
        if not os.path.isdir(base_dir):
            continue
        for root, dirs, filenames in os.walk(base_dir):
            # Skip hidden dirs and node_modules
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']
            for f in filenames:
                if f.endswith('.md'):
                    files.append(os.path.join(root, f))

    return files


def build_index():
    """Build or rebuild the TF-IDF index."""
    conn = init_db()

    # Clear existing index
    conn.execute("DELETE FROM term_doc")
    conn.execute("DELETE FROM terms")
    conn.execute("DELETE FROM documents")
    conn.commit()

    files = collect_files()
    print(f"Indexing {len(files)} markdown files...")

    doc_terms = {}  # doc_id -> list of terms
    term_doc_freq = Counter()  # how many docs contain each term
    doc_data = []

    for fpath in files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"  Skip {fpath}: {e}", file=sys.stderr)
            continue

        words = tokenize(content)
        if not words:
            continue

        title = ""
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('# '):
                title = line[2:].strip()
                break

        content_hash = hash_content(content)
        now = datetime.now().isoformat()

        cur = conn.execute(
            "INSERT INTO documents (path, title, content_hash, word_count, indexed_at) VALUES (?, ?, ?, ?, ?)",
            (fpath, title, content_hash, len(words), now)
        )
        doc_id = cur.lastrowid
        doc_data.append((doc_id, fpath, title))

        tf = compute_tf(words)
        doc_terms[doc_id] = tf

        unique_terms = set(words)
        for term in unique_terms:
            term_doc_freq[term] += 1

    total_docs = len(doc_data)
    print(f"  Indexed {total_docs} documents")

    # Insert terms and compute TF-IDF
    term_ids = {}
    for term, df in term_doc_freq.items():
        idf = compute_idf(df, total_docs)
        cur = conn.execute(
            "INSERT INTO terms (term, doc_freq) VALUES (?, ?)",
            (term, df)
        )
        term_ids[term] = cur.lastrowid

    # Insert term-doc pairs with TF-IDF scores
    for doc_id, tf_map in doc_terms.items():
        for term, tf_val in tf_map.items():
            if term in term_ids:
                idf = compute_idf(term_doc_freq[term], total_docs)
                tfidf = tf_val * idf
                conn.execute(
                    "INSERT OR IGNORE INTO term_doc (term_id, doc_id, term_freq, tf_idf) VALUES (?, ?, ?, ?)",
                    (term_ids[term], doc_id, tf_val, tfidf)
                )

    conn.commit()
    conn.close()

    print(f"  Terms: {len(term_ids)}")
    print(f"  Index built successfully.")


def search(query, top_n=5):
    """Search documents using TF-IDF cosine similarity."""
    conn = init_db()

    query_words = tokenize(query)
    if not query_words:
        print("Query too short or all stopwords.")
        return []

    # Get total docs
    total_docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    if total_docs == 0:
        print("No documents indexed. Run: python3 semantic_retrieval.py index")
        return []

    # Compute query TF-IDF vector
    query_tf = compute_tf(query_words)
    query_vector = {}
    for term, tf in query_tf.items():
        cur = conn.execute("SELECT id, doc_freq FROM terms WHERE term = ?", (term,))
        row = cur.fetchone()
        if row:
            term_id, df = row
            idf = compute_idf(df, total_docs)
            query_vector[term_id] = tf * idf

    if not query_vector:
        print("No matching terms found in index.")
        return []

    # Score documents
    scores = defaultdict(float)
    for term_id, query_tfidf in query_vector.items():
        cur = conn.execute(
            "SELECT doc_id, tf_idf FROM term_doc WHERE term_id = ?",
            (term_id,)
        )
        for doc_id, doc_tfidf in cur.fetchall():
            scores[doc_id] += query_tfidf * doc_tfidf

    # Normalize by document vector magnitude (simplified)
    # Get top results
    ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_n]

    results = []
    for doc_id, score in ranked:
        cur = conn.execute("SELECT path, title FROM documents WHERE id = ?", (doc_id,))
        row = cur.fetchone()
        if row:
            results.append({
                "path": row[0],
                "title": row[1] or os.path.basename(row[0]),
                "score": round(score, 4)
            })

    conn.close()
    return results


def find_related(filepath, top_n=5):
    """Find documents related to a given file."""
    conn = init_db()

    # Get the document's terms
    cur = conn.execute("SELECT id FROM documents WHERE path = ?", (filepath,))
    row = cur.fetchone()
    if not row:
        print(f"Document not indexed: {filepath}")
        return []

    doc_id = row[0]
    total_docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    # Get this document's TF-IDF vector
    cur = conn.execute(
        "SELECT term_id, tf_idf FROM term_doc WHERE doc_id = ?",
        (doc_id,)
    )
    doc_vector = {term_id: tfidf for term_id, tfidf in cur.fetchall()}

    if not doc_vector:
        print("Document has no indexed terms.")
        return []

    # Score other documents by cosine similarity (simplified: dot product)
    scores = defaultdict(float)
    for term_id, doc_tfidf in doc_vector.items():
        cur = conn.execute(
            "SELECT doc_id, tf_idf FROM term_doc WHERE term_id = ? AND doc_id != ?",
            (term_id, doc_id)
        )
        for other_id, other_tfidf in cur.fetchall():
            scores[other_id] += doc_tfidf * other_tfidf

    ranked = sorted(scores.items(), key=lambda x: -x[1])[:top_n]

    results = []
    for other_id, score in ranked:
        cur = conn.execute("SELECT path, title FROM documents WHERE id = ?", (other_id,))
        row = cur.fetchone()
        if row:
            results.append({
                "path": row[0],
                "title": row[1] or os.path.basename(row[0]),
                "score": round(score, 4)
            })

    conn.close()
    return results


def show_stats():
    """Show index statistics."""
    conn = init_db()

    doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    term_count = conn.execute("SELECT COUNT(*) FROM terms").fetchone()[0]
    pair_count = conn.execute("SELECT COUNT(*) FROM term_doc").fetchone()[0]

    print(f"Semantic Index Stats:")
    print(f"  Documents: {doc_count}")
    print(f"  Terms:     {term_count}")
    print(f"  Pairs:     {pair_count}")
    print()

    if doc_count > 0:
        avg_words = conn.execute("SELECT AVG(word_count) FROM documents").fetchone()[0]
        print(f"  Avg words/doc: {int(avg_words or 0)}")

        print("\nTop terms by document frequency:")
        for row in conn.execute(
            "SELECT term, doc_freq FROM terms ORDER BY doc_freq DESC LIMIT 15"
        ):
            print(f"    {row[0]}: {row[1]} docs")

    conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: semantic_retrieval.py <command> [args]")
        print("Commands: index, search, related, stats")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "index":
        build_index()

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: semantic_retrieval.py search 'query text' [--top N]")
            sys.exit(1)
        query = sys.argv[2]
        top_n = 5
        if "--top" in sys.argv:
            idx = sys.argv.index("--top")
            if idx + 1 < len(sys.argv):
                top_n = int(sys.argv[idx + 1])
        results = search(query, top_n)
        if results:
            print(f"\nTop {len(results)} results for: '{query}'\n")
            for i, r in enumerate(results, 1):
                print(f"  {i}. [{r['score']:.4f}] {r['title']}")
                print(f"     {r['path']}")
                print()

    elif cmd == "related":
        if len(sys.argv) < 3:
            print("Usage: semantic_retrieval.py related 'path/to/file.md'")
            sys.exit(1)
        filepath = sys.argv[2]
        if not os.path.isabs(filepath):
            filepath = os.path.join(BRAIN_VAULT, filepath)
        results = find_related(filepath)
        if results:
            print(f"\nFiles related to: {os.path.basename(filepath)}\n")
            for i, r in enumerate(results, 1):
                print(f"  {i}. [{r['score']:.4f}] {r['title']}")
                print(f"     {r['path']}")
                print()

    elif cmd == "stats":
        show_stats()

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
