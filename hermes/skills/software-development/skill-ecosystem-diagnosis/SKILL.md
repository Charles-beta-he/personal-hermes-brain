---
name: skill-ecosystem-diagnosis
description: "技能生态系统自诊方法 — 系统化诊断 Hermes skill 生态的系统性健康问题。围绕五大硬伤（技能泛滥无筛选、生态无淘汰机制、功能孤岛、冲突不检测、使用无追踪）进行定量+定性分析，映射跨学科理论框架，生成治理级处方。Use when: 'skill生态审计', '自检', '健康检查', '五大硬伤', '只能涨不能减', '系统熵增', 'ecosystem health', 'skill governance audit'."
license: MIT
tags: [skills, ecosystem, health, audit, governance, entropy]
---

# Skill Ecosystem Diagnosis — 技能生态系统自诊

> 你的 skill 库不是知识库，是一个活的生态系统。
> 不能自我净化的系统终将崩溃。

## When to Use

- 用户问"好像有记忆幽灵"、"过去的内容突然冒出来"
- 用户说"skill 生态有点乱"、"太多 skill 了"、"该清理了"
- 周期性生态健康检查（每月或每季度一次）
- 技能数量突破心理阈值（如 100、150、200）
- 发现重复/冲突的 skill（同名、同功能不同路径）
- 用户对系统性能/响应质量下降有感知但找不到原因
- 引入了一批新 skill 后的生态评估

## Core Thesis

**"只管生不管养"是技能生态崩溃的唯一原因。**

一个无治理的 skill 系统有五个不可逆的衰退模式：

```
# 衰退函数
H(ecosystem) = H_proliferation + H_isolation + H_conflict - H_elimination - H_tracking

其中:
  H_proliferation ↑ (每创建1个新skill)
  H_isolation    ↑ (每次skill独立演变，不互通)
  H_conflict     ↑ (每2个重叠skill增加1个冲突点)
  H_elimination  = 0 (没有任何淘汰机制)
  H_tracking     = 0 (没有任何使用追踪)

→ H 单调递增 → 系统必然熵崩溃
```

## Diagnosis Protocol

### Step 1: Define Diagnostic Axes

Always audit against these five axes. They are invariant — the same five problems exist in any ungoverned agent skill system:

| # | Axis | Symptom | Indicator |
|---|------|---------|-----------|
| 1 | **Proliferation** (无筛选) | 数量膨胀，质量稀释 | 不可测试 skill 占比 |
| 2 | **Elimination** (无淘汰) | 僵尸skill堆积 | 空骨架/废弃skill占比 |
| 3 | **Isolation** (功能孤岛) | 重复造轮，版本发散 | 同名/同功能skill副本数 |
| 4 | **Conflict** (冲突不检测) | 加载歧义，行为不可预测 | 重叠skill的竞态数量 |
| 5 | **Tracking** (无追踪) | 生态失明，无法决策 | 使用统计缺失程度 |
| 6 | **Memory Ghosting** (记忆污染) | 过去式内容劫持未来上下文 | 幽灵条目数 + 记忆预算占用比 |

### Step 2: Gather Quantitative Evidence

```bash
# Total skill count
find ~/.hermes/skills -name "SKILL.md" | wc -l

# Quality distribution
echo "Skills with test-prompts: $(find ~/.hermes/skills -name 'test-prompts.json' | wc -l) / $(find ~/.hermes/skills -name 'SKILL.md' | wc -l)"
echo "Skills with CHANGELOG: $(find ~/.hermes/skills -name 'CHANGELOG.md' | wc -l) / $(find ~/.hermes/skills -name 'SKILL.md' | wc -l)"
echo "Skills with evals: $(find ~/.hermes/skills -type d -name 'evals' | wc -l) / $(find ~/.hermes/skills -name 'SKILL.md' | wc -l)"

# Categories
ls -1 ~/.hermes/skills/
for d in ~/.hermes/skills/*/; do
  cat=$(basename "$d")
  count=$(find "$d" -name "SKILL.md" | wc -l)
  echo "  $cat: $count skills"
done
```

Key thresholds:
- test-prompts coverage < 50% → proliferation warning
- CHANGELOG coverage < 50% → lifecycle management missing
- evals coverage < 10% → no verification culture
- Skills > 150 → Dunbar number breach

### Step 3: Detect Duplication & Conflict

```bash
# Find duplicate skill names across categories
find ~/.hermes/skills -name "SKILL.md" -exec sh -c 'basename "$(dirname "$1")"' _ {} \; | sort | uniq -c | sort -rn | head -20

# Find empty/skeleton skills (referenced files missing)
# Check each skill's linked_files from skill_view output
# A skill is "skeleton" if it references non-existent scripts/files

# Find orphan categories (no parent SKILL.md but has sub-skills)
for d in ~/.hermes/skills/*/; do
  base=$(basename "$d")
  if [ ! -f "$d/SKILL.md" ] && [ "$(find "$d" -mindepth 1 -name "SKILL.md" | wc -l)" -gt 0 ]; then
    echo "Orphan: $base"
  fi
done

# Find skills with same 'name:' in frontmatter
grep -r "^name:" ~/.hermes/skills/*/SKILL.md 2>/dev/null | sort | uniq -d
```

### Step 3.5: Track Usage Blindness

```bash
# Check if any usage tracking exists
grep -r "load_count\|usage_count\|skill.*track\|skill.*stat" ~/.hermes/hermes-agent/agent/ 2>/dev/null | head -10
```

Result: **If no usage tracking code exists, axis 5 is confirmed broken.** This is the most common finding.

### Step 3.6: Skill Graphs 2.0 Topology Audit

Dense arbitrary skill graphs degrade reliability: agents skip dependencies as graph depth grows, and cycles make orchestration non-deterministic. Run the topology gate before recommending new composition patterns:

```bash
# Non-blocking ecosystem scan
python3 ~/.hermes/scripts/skill-steward.py --graph-check --json --warn-only

# Strict fail-closed gate for a fixture/staging ecosystem
HERMES_SKILLS_DIR=/path/to/skills python3 ~/.hermes/scripts/skill-steward.py --graph-check --json
```

Classify findings:
- `cycles`: P0, break or invert one edge.
- `excessive_depth`: P1, split the chain at a molecule boundary; default max depth is 4.
- `typed_violations`: P1, declared atoms must have zero deps, molecules should compose bounded atoms, compounds should not chain into compounds.
- `migration_suggestions`: P2, untyped legacy skills inferred as atom/molecule/compound.

The audit writes `~/.hermes/skills/steward/skill-graph-report.json` and full steward reports include `audits.skill_graph`.

### Step 3.75: Ghost Memory Audit

Check the persistent memory store for past-tense entries that silently contaminate future sessions. Unlike stale skills (visible in listings), ghost memory is invisible — it's injected into EVERY session's system prompt and gets treated as current fact.

```bash
# Locate memory files
cat ~/.hermes/memories/MEMORY.md
cat ~/.hermes/memories/USER.md

# Check memory budget usage
wc -c ~/.hermes/memories/MEMORY.md
```

Classify each block into one of four categories:

| Category | Pattern | Severity | Action |
|----------|---------|----------|--------|
| **Durable fact** | Still true across sessions | ✅ Keep | No action |
| **GHOST (past-tense work)** | "最终达到...状态", "完成了X", "已修复Y个问题" | 🔴 High | Remove |
| **GHOST (stale version)** | Version numbers (e.g. "v1.4.8") | 🟡 Medium | Remove or pin as range |
| **GHOST (redundancy)** | Same fact repeated across entries | 🟡 Medium | Deduplicate |
| **GHOST (expired progress)** | "已上线", "已部署", "开发中" | 🟡 Medium | Remove |
| **Session-local lesson** | "关键教训: 删除前要grep" (still valid) → keep; session-specific → remove | 🟢 Depends | Judge per entry |

**Ghost detection heuristics:**
- Past-tense Chinese: `了`, `完成`, `达到`, `已` + verb → high ghost risk
- Version numbers (`v1.x.x`) → always stale, pin as range or remove
- Completed project milestones (`.+已上线`, `.+已部署`) → expired once new milestones exist
- `主动发现的新方向：...` → intended for a specific session, contaminates future ones
- System-specific architecture descriptions (what tools/patterns the project uses) → keep if still true, remove if changed

**Check for the "double ghost" mechanism:**

```
Layer 1: Memory injection — past-tense entry in MEMORY.md gets injected
         into every session's system prompt as if it's current fact.
Layer 2: Context compression — the same memory entry also appears in
         the compressed summary of long conversations.
Result: TWO references to the same stale fact, one from memory injection,
         one from compression. Both are treated as context.
```

To detect this: grep memory text in the context compressor's summary template. If the compressor uses `memory` tool output in its summary, entries written to memory during a session get double-ghosted.

Add ghost findings to the prescription (Section C) as P0 or P1 depending on count.

Key thresholds:
- Ghost entries > 0 → memory contamination warning
- Memory budget > 80% → compaction pressure (need to deduplicate/remove ghosts)
- Double-ghost pattern detected → P0 fix required

### Step 4: Root Cause Diagnosis

Map each quantitative finding to its root cause pattern:

| Finding | Root Cause | Underlying Failure |
|---------|------------|-------------------|
| Skills > 150, no creation gate | **Institutional failure** — no rule for what qualifies | Ostrom principle 1+2 broken |
| Zombie skills accumulate | **Incentive failure** — no reward for maintenance | Prigogine's entropy debt uncollected |
| 12 copies of same concept | **Decomposition failure** — split by variant not by change reason | Parnas principle violated |
| 2 skills covering same ground | **Governance failure** — no conflict resolution mechanism | Ostrom principle 6 broken |
| No tracking at all | **Control failure** — controller variety << system variety | Ashby's Law violated |

### Step 5: Cross-Disciplinary Solution Mapping

For each broken axis, map to a theoretical framework that prescribes the fix:

| Axis | Diagnostic Theory | Prescriptive Theory | Solution Mechanism |
|------|------------------|--------------------|--------------------|
| Proliferation | Sturgeon's Law (90% is crap) | **Ostrom's 8 Principles** | Governance charter with entry gates |
| Elimination | 2nd Law of Thermodynamics | **Prigogine's Dissipative Structures** | Entropy debt: each create requires one archive |
| Isolation | Conway's Law (mirrors org structure) | **Inverse Conway Maneuver** | Create steward role, system restructures to match |
| Conflict | Brooks' Law (consistency overhead) | **Parnas Information Hiding** | Decompose by change reason, not by platform |
| Tracking | Miller's Law (7±2 chunks) | **Ashby's Requisite Variety** | Bayesian prior from usage data → effective diversity reduction |

### Step 6: Generate Prescription

Output a structured report with three sections:

**Section A — Current State (quantitative)**

```
Skill Ecosystem Health Scan — {date}
═══════════════════════════════════════════════

Total skills:     {N}
Test coverage:    {N}/{M} ({P}%)  ← {PASS/WARN/FAIL}
Lifecycle docs:   {N}/{M} ({P}%)  ← {PASS/WARN/FAIL}
Test infrastructure: {N}/{M} ({P}%) ← {PASS/WARN/FAIL}

Duplication hotspots:
  - {skill-A}: {count} copies found in {categories}
  - {skill-B}: {count} copies found in {categories}

Skeleton skills (empty/non-functional):
  - {skill-C}: references non-existent {file}
  - {skill-D}: {count} lines, no test-prompts, no changelog
```

**Section B — Axes Assessment**

```
┌────────────────────────────────────────────────────────────────┐
│ Axis                  │ Status │ Evidence              │ Fix   │
├────────────────────────────────────────────────────────────────┤
│ 1. Proliferation      │ FAIL   │ {details}             │ {fix} │
│ 2. Elimination        │ FAIL   │ {details}             │ {fix} │
│ 3. Isolation          │ FAIL   │ {details}             │ {fix} │
│ 4. Conflict           │ FAIL   │ {details}             │ {fix} │
│ 5. Tracking           │ FAIL   │ {details}             │ {fix} │
└────────────────────────────────────────────────────────────────┘
```

**Section C — Prescriptions (ranked by impact)**

1. **{P0 fix}** — {why urgent} → {how to implement}
2. **{P1 fix}** — {why important} → {how to implement}
3. **{P1 fix}** — {why important} → {how to implement}

Each prescription links to its theoretical basis:
  - Theory: {name}
  - Principle: {one-liner}
  - Applied: {concrete action}

## Theoretical Reference Library

The following 7 theories form the complete "diagnosis + prescription" toolkit for skill ecosystem governance. They are ordered by domain, not priority.

### 1. Prigogine's Dissipative Structures (Nobel 1977)
**Domain:** Thermodynamics → Systems theory
**Core idea:** Open systems far from equilibrium maintain order by exporting entropy to the environment.
**Application:** Each new skill import must be balanced by entropy export (archive/deprecate/merge an old one).
**When to use:** System has only grown, never shrunk.

### 2. Ashby's Law of Requisite Variety (1956)
**Domain:** Cybernetics
**Core idea:** Only variety can absorb variety. A controller must have at least as many distinct states as the system it controls.
**Application:** 161 skills need a controller with ~161 states of discrimination. Without usage tracking → controller can't distinguish → loss of control.
**When to use:** Agent can't reliably choose the right skill.

### 3. Ostrom's Design Principles for Common-Pool Resources (Nobel 2009)
**Domain:** Institutional economics → Governance
**Core idea:** 8 principles for sustainable shared resources: clear boundaries, cost-benefit proportionality, collective choice, monitoring, graduated sanctions, conflict resolution, organizational rights, nested layers.
**Application:** Skills are a CPR. Violating any principle → "tragedy of the commons" (quality collapse).
**When to use:** No creation rules, no quality gates, no governance structure.

### 4. Parnas Information Hiding (1972)
**Domain:** Software engineering
**Core idea:** Modules should be decomposed so each encapsulates a single design decision that may change. The criterion for decomposition is "what changes together, belongs together."
**Application:** pua has 12 copies split by deployment platform (codex/codebuddy/root). Parnas says: split by what changes (the core methodology vs the adapter). The copies all change together → they are one module, poorly decomposed.
**When to use:** Same concept appears N times with slight variations.

### 5. Conway's Law + Inverse Conway Maneuver (1967/2010)
**Domain:** Organizational theory
**Core idea:** Systems mirror the communication structure of the organizations that build them. The inverse: to change the system, change the org structure first.
**Application:** Create a "skill steward" role (automated cron agent). The system will self-organize around this steward's attention.
**When to use:** System structure is chaotic and manual refactoring is too slow.

### 6. Havel's "The Power of the Powerless" (1978)
**Domain:** Political philosophy
**Core idea:** Systems persist not because people can't change them, but because the default mode of living in the system prevents change. Change requires refusing the default mode.
**Application:** The default mode is "find problem → create skill → done." Break it by inserting institutional friction: "create skill → asks you to archive an old one first."
**When to use:** Everyone knows the system is broken but no one changes their behavior.

### 7. Sturgeon's Law + Price's Law + Dunbar's Number (empirical constraints)
**Domain:** Information science / Sociology
**Core ideas:**
- Sturgeon: 90% of everything is crap
- Price: 50% of value comes from √N contributors (√161 ≈ 13 skills)
- Dunbar: ~150 is the cognitive limit for stable relationships
**Application:** 161 skills → ~145 low quality, ~13 do the heavy lifting, and you've exceeded the cognitive limit. The effective skill count must be reduced.
**When to use:** Justify why reducing skills is necessary, not optional.

## Pitfalls

1. **Don't try to fix all 5 axes at once** — Start with Tracking (axis 5) because you can't make data-driven decisions about the other 4 without it. Then Proliferation (axis 1) for the biggest immediate quality impact.

2. **Quantitative data without qualitative context is misleading** — A skill with no CHANGELOG might be old and rock-solid. A skill with a CHANGELOG might be churning without improving. Always verify findings with file inspection.

3. **Theoretical frameworks are diagnosis tools, not religions** — Don't over-engineer. If Ostrom principle 6 (conflict resolution) is the only broken axis, fix just that one.

4. **Skeleton skills are the canary** — If you find even one skeleton skill (readme exists, actual implementation doesn't), the creation gate is completely broken. This is the fastest way to diagnose axis 1 severity.

5. **Memory constraint** — The full diagnosis generates a lot of data. Don't save task progress to memory; create a report file instead.

6. **Ghost memory is silent contamination** — Unlike stale skills which are visible in listings, ghost memory is invisible. MEMORY.md is injected into EVERY session's system prompt. A single past-tense entry can corrupt the agent's premise across dozens of future conversations. The pattern: agent writes `memory(add, "X任务已完成")` in one session, and every future session reads "X任务已完成" as current fact. This is harder to detect than a stale skill because there is no "stale memory" warning system.

7. **Double ghost is the hardest to catch** — If an agent writes a ghost to memory AND the context compressor includes that memory write in its compressed summary, the same stale fact arrives via two paths (memory injection + compression injection). From the agent's perspective, a fact referenced twice feels more credible—not less. To detect: check if the context compressor's summary includes the word "memory" or references memory tool outputs (grep `tool_name == "memory"` in context_compressor.py).

8. **Usage tracking requires code change** — Unlike the other 4 axes which can be fixed in the skill layer (no code changes), tracking requires modifying hermes-agent source code. Be transparent with the user about this implementation cost.

## Definition of Done

- [ ] **Outcome**: Report generated with quantitative evidence + axis-by-axis assessment + ghost memory audit + ranked prescriptions + theoretical basis for each
- [ ] **Process**: Step 1-3.75 followed in order. Quantitative data gathered before qualitative analysis. Ghost memory inspected before generating prescriptions (ghosts affect prescription priority). Prescriptions linked to theoretical frameworks.
- [ ] **Style**: Report uses Unicode box-drawing for tables, includes a "theoretical reference library" section, distinguishes diagnosis (data) from prescription (theory).
- [ ] **Ghost check**: MEMORY.md and USER.md scanned. Each block classified as durable/ghost. Ghost count and memory budget usage reported. Double-ghost mechanism checked.
- [ ] **Efficiency**: No redundant file reads. Evidence gathered in bulk filesystem scans, not one-by-one reads. Report < 500 lines; full detail in a separate document if needed.
