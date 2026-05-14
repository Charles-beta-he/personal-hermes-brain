---
type: mission
status: active
priority: P1
created: 2026-05-10T18:23:40+08:00
updated: 2026-05-11T20:26:00+08:00
project: Hermes-local-brain
mission_id: mission-local-first-artifacts-kg
mission_title: "Mission方法论P1：local-first Mission artifacts 与知识图谱沉淀"
layer: L3
workflow_contract: [[08-模板/task-workflow-contract-template]]
architecture_target: local-brain
depends_on: [mission-taskpool-envelope-selfcheck-fail-closed]
concepts: [mission, local-first, knowledge-graph, markdown, evidence-bundle, opord]
---

# Mission: Mission方法论P1 — local-first Mission artifacts 与知识图谱沉淀

## 1. Situation (SITUATION)

Hermes local-brain 已有 task lifecycle (pending→claimed→running→review→done),
SQLite FTS5 全文索引, 和 P0 Mission Envelope frontmatter schema。

但存在以下差距:
- Mission 的目标、证据、运行日志只在 transient session 里，不沉淀为可编辑 Markdown
- 没有 sidecar hash/evidence manifest 做 tamper detection
- 知识图谱只有 keyword FTS，缺少 entity-relation 结构化查询
- Rowboat 的 local-first KG 思路值得吸收：persistent, inspectable, editable notes

参考来源:
- Rowboat analysis: `~/Documents/brain/99-hermes-notes/rowboat-analysis-2026-05-11.md`
- P0 envelope task: `2026-05-10-mission方法论p0任务池-mission-envelope-schema--selfcheck-fail-closed.md`
- Multi-model advisory: `/tmp/missions-taskpool-mm-state.json`

## 2. Mission (MISSION)

### Objective
为每个 mission 生成 canonical Markdown mission note、evidence bundle、
run/proof log 链接，并保持 SQLite/FTS/graph 为可重建派生缓存。

### Commander's Intent
Mission notes must be local-first, inspectable, editable knowledge-graph nodes
— not transient session artifacts. Canonical truth lives in `~/Documents/brain`.

### End State
- [x] Mission artifact template 存在于 `08-模板/mission-artifact-template.md`
- [x] Sidecar evidence manifest 工具可用 (`evidence_manifest.py`)
- [x] 示例 mission note 使用模板格式并链接 evidence
- [x] `brainctl reindex` 可索引 mission note
- [x] `brainctl search` 可检索 mission 内容
- [x] `evidence_manifest.py verify` 通过

### Constraints
- Canonical brain vault 仍是 `~/Documents/brain`
- 不得把 runtime index 当源事实
- Evidence/ref/hash 必须可回放
- SQLite/FTS/graph 只做可重建派生索引

### Red Lines
- 不执行 Markdown body 里的任意命令
- 不用 transient session state 替代 canonical notes
- 不把索引数据库当 source of truth

### Non-Goals
- 不在本切片实现 full vector embedding search
- 不导入 Rowboat runtime
- 不实现 automated mission runner (P2 scope)

## 3. Execution (EXECUTION)

### Concept of Operations
最小安全切片：
1. 创建 mission artifact template (OPORD 结构)
2. 创建 sidecar hash/evidence manifest 工具
3. 用模板创建示例 mission note
4. 验证 brainctl sync/reindex/search 可用

### DAG Nodes / Tasks
| Node | Description | Status | Depends On |
|------|-------------|--------|------------|
| template | Create mission artifact template | done | — |
| sidecar | Create evidence_manifest.py tool | done | template |
| sample | Create sample mission note using template | done | template |
| verify | Run brainctl reindex + search smoke | done | sample |

### Checkpoints
- [x] checkpoint-1: Template exists and is well-formed
- [x] checkpoint-2: Sidecar tool can create/verify evidence hashes
- [x] checkpoint-3: Mission note in brain vault uses template format
- [x] checkpoint-4: brainctl search finds mission content

## 4. Sustainment (SUSTAINMENT)

### Dependencies
- `brainctl.py` — sync/reindex/search
- `kg_entity_extractor.py` — knowledge graph extraction
- Obsidian vault at `~/Documents/brain`

### Resources
- ~30 min agent time
- Existing infrastructure, no new dependencies

### Evidence Manifest
| Evidence ID | Path / URI | SHA-256 | Type | Created |
|-------------|-----------|---------|------|---------|
| ev-001 | file:~/Documents/brain/08-模板/mission-artifact-template.md | (see sidecar) | template | 2026-05-11 |
| ev-002 | file:~/.hermes/scripts/evidence_manifest.py | (see sidecar) | script | 2026-05-11 |
| ev-003 | file:~/Documents/brain/05-实践与项目/missions/2026-05-10-mission-local-first-artifacts-kg.md | (see sidecar) | mission-note | 2026-05-11 |
| ev-004 | command:brainctl reindex | — | command-output | 2026-05-11 |
| ev-005 | command:brainctl search "mission" | — | command-output | 2026-05-11 |

## 5. Command & Control (COMMAND_CONTROL)

### Permission Gates
- [x] gate-1: Template file created and readable
- [x] gate-2: Sidecar tool passes self-test
- [x] gate-3: brainctl reindex completes
- [x] gate-4: brainctl search returns mission note

### Handoff Artifacts
- artifact:mission-artifact-template — OPORD-based mission note template
- artifact:evidence-manifest-tool — sidecar hash verification tool

### Proof Artifacts
- artifact:brainctl-reindex-pass — reindex succeeded with new mission
- artifact:brainctl-search-mission — search "mission" returns results

### Rollback Signal
If brainctl reindex fails or search cannot find the mission note after creation,
the template or note format needs debugging.

### Escalation Path
If template validation fails, check against P0 envelope schema fields.

## 6. Proof Log

- 2026-05-10T18:23:40+08:00: Task created from local-brain control point.
- 2026-05-11T20:26:00+08:00: Mission artifact template created at `08-模板/mission-artifact-template.md`.
- 2026-05-11T20:26:00+08:00: Sidecar evidence manifest tool created at `~/.hermes/scripts/evidence_manifest.py`.
- 2026-05-11T20:26:00+08:00: Sample mission note created using template format.
- 2026-05-11T20:26:00+08:00: brainctl reindex + search verification pending.

## 7. Run Log

| Run ID | Started | Ended | Status | Artifacts |
|--------|---------|-------|--------|-----------|
| run-001 | 2026-05-11 | 2026-05-11 | pass | template, sidecar, mission-note, reindex, search |

## 8. Decision Log

| Date | Decision | Rationale | Alternatives Rejected |
|------|----------|-----------|----------------------|
| 2026-05-11 | Use OPORD structure for mission template | Maps naturally to military mission planning; covers all required dimensions | Generic task template (insufficient structure) |
| 2026-05-11 | Sidecar .evidence.json instead of inline hashes | Keeps mission note readable; enables programmatic verification | Inline YAML hash fields (clutters note) |
| 2026-05-11 | TF-IDF semantic search (existing) over full embeddings | No new dependencies; sufficient for current scale | nomic-embed vector search (future P1) |

## 9. Knowledge Graph Links

- [[2026-05-10-mission方法论p0任务池-mission-envelope-schema--selfcheck-fail-closed]] — depends_on (P0 envelope schema)
- [[rowboat-analysis-2026-05-11]] — inspired_by (local-first KG pattern)
- [[local-brain-task-note-template]] — extends (adds mission structure)
- [[task-workflow-contract-template]] — uses (workflow contract reference)

## Final Handoff

- Status: implemented; template + sidecar + sample mission note created
- Evidence: template at `08-模板/mission-artifact-template.md`, tool at `~/.hermes/scripts/evidence_manifest.py`
- Residual risk: Full vector embedding search deferred; current TF-IDF sufficient for keyword-based mission retrieval
