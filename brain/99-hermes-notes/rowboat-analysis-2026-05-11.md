# Rowboatlabs/Rowboat 多模型分析报告

**Date**: 2026-05-11
**Source**: github.com/rowboatlabs/rowboat (~14k stars, YC S24)
**Analyst**: Hermes Agent (multi-model ensemble)

---

## 1. What is Rowboat?

Open-source "AI coworker" — local-first desktop app that turns work into a
knowledge graph. Connects email, calendar, meetings; builds persistent context;
uses it to draft emails, prep meetings, generate docs.

## 2. Architecture Comparison

| Layer              | Rowboat                          | Hermes                           |
|--------------------|----------------------------------|----------------------------------|
| Runtime            | Electron 39 + React 19           | CLI + Gateway daemon             |
| AI SDK             | Vercel AI SDK                    | Custom brain_task orchestrator   |
| Storage            | FS JSON (local-first)            | SQLite + Obsidian vault          |
| Knowledge          | Knowledge graph (entities+rels)  | FTS keyword search over markdown |
| Extensions         | MCP (stdio/HTTP/SSE)             | MCP + 70+ skills                 |
| Agent Loop         | Event sourcing (replay events)   | Turn-based with compressor       |
| DI                 | Awilix singleton container       | Config-driven YAML               |
| Models             | BYOK (OpenAI/Anthropic/Ollama)   | Multi-model routing + ensemble   |
| Memory             | Agent notes (user.md, prefs.md)  | MEMORY.md + SQLite claims DB     |
| Live Context       | Live Notes (cron/event triggers) | Static memory injection          |
| Build              | pnpm monorepo + esbuild          | Python scripts + shell           |

## 3. Key Rowboat Patterns Worth Adopting

### 3a. Knowledge Graph (Entity-Relation Triples)
Rowboat stores structured triples: (entity A --relation--> entity B).
Hermes only has keyword FTS over markdown blocks. Gap: "Who worked on X?"
requires full-text scan vs direct graph query.

**Action**: Built `kg_entity_extractor.py` — extracts entities+relations
from conversations and brain vault, stores in SQLite graph tables.

### 3b. Live Notes (Working Memory Layer)
Rowboat has "Live Notes" — markdown notes with YAML frontmatter that become
self-updating AI artifacts. Three triggers: cron, time windows, events.

Hermes has static MEMORY.md. No in-session context accumulation.

**Action**: Built `live_notes_accumulator.py` — ephemeral session scratchpad
that accumulates observations during conversations, consolidates to memory.

### 3c. Semantic Retrieval (Beyond Keyword FTS)
Rowboat likely uses vector embeddings for conceptual similarity.
Hermes only has blocks_fts (keyword-based).

**Action**: Built `semantic_retrieval.py` — TF-IDF based semantic search
over the brain vault as a stepping stone to full embeddings.

### 3d. Event Sourcing for Agent Runs
Rowboat rebuilds agent state by replaying event logs. Hermes uses turn-based
state. Event sourcing enables replay, debugging, and branching.

**Assessment**: Hermes already has wal.jsonl and evolution claims DB —
partial event sourcing. Could be extended.

### 3e. Agents-as-Tools Pattern
Rowboat nests agents as tools within other agents. Hermes has subagent
delegation but not as composable tool definitions.

**Assessment**: Hermes delegate_task covers this adequately.

## 4. Gaps Identified

1. No knowledge graph (entity-relation triples)
2. No live-notes / working-memory during sessions
3. No local vector embeddings for semantic retrieval
4. No entity extraction pipeline from conversations
5. No automatic contextual retrieval from knowledge vault
6. No temporal/episodic memory structure
7. No importance-weighted memory consolidation

## 5. Improvements Implemented

| Script                          | Purpose                              | Status  |
|---------------------------------|--------------------------------------|---------|
| kg_entity_extractor.py          | Entity-relation extraction to SQLite | Created |
| live_notes_accumulator.py       | Session working memory               | Created |
| semantic_retrieval.py           | TF-IDF semantic search over vault    | Created |

## 6. Recommendations for Future Work

1. **Embeddings**: Replace TF-IDF with local embedding model (nomic-embed)
   for true semantic search over the 2806 brain blocks
2. **Graph Queries**: Add Cypher-like query interface over entity graph
3. **Auto-Consolidation**: Run kg_entity_extractor on session end
4. **Live Notes Cron**: Schedule live_notes_accumulator consolidation
5. **Memory Decay**: Implement access-frequency-based importance scoring
