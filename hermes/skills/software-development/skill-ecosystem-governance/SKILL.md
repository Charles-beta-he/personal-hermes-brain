---
name: skill-ecosystem-governance
description: Use when the task falls under Skill Ecosystem Governance — 技能生态系统治理.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - software
    - development
    - ecosystem
    - governance
    related_skills:
    - claude-code
    - codex
    - darwin-skill
    - dogfood
    - hermes-agent
    - loop
    - obsidian
    - opencode
---

# Skill Ecosystem Governance — 技能生态系统治理

## Overview


> 基于 11 个跨学科理论框架的代理技能自净化系统。
> 解决控制论治不了的"只管生不管养"问题。

## When to Use

- 当技能系统出现以下症状：数量失控（超过 Dunbar 150）、质量参差（Sturgeon 90%）、重复泛滥（Parnas 冲突）、僵尸堆积（Prigogine 熵债）
- 当团队需要从"人治"切换到"法治"——让 cronjob 代替人来做日常清理决策
- 当用户说"技能太多了不知道怎么选"（Ashby 控制器多样性不足）
- 作为新项目的初始治理设置，防止刚创建就走向熵增

## Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Level 3: Meta-Governance                  │
│           Second-Order Cybernetics (规则自审计)               │
├─────────────────────────────────────────────────────────────┤
│                    Level 2: Governance Engine                │
│           Steward Cron (Conway 逆) + Obsidian Brain          │
├─────────────────────────────────────────────────────────────┤
│        Level 1: Audit Layer (steward.py)                     │
│  Ostrom │ Prigogine │ Parnas │ Ashby │ Dreyfus │ Memetics   │
├─────────────────────────────────────────────────────────────┤
│        Level 0: The Skills Being Governed                    │
└─────────────────────────────────────────────────────────────┘
```

## Step 1: Diagnose — 5 Hard Problems

Run an initial audit to quantify system health:

```bash
python3 ~/.hermes/scripts/skill-steward.py
```

This outputs 11 metrics:
1. **Total count** (Dunbar threshold: 150) — excludes `alias: true` stubs
2. **Test coverage** (Ostrom monitoring: target >=80%)
3. **Stale skills** (Prigogine entropy: 90d+ with no tests)
4. **Name conflicts** (Parnas: duplicate skill names) — only checks non-alias skills
5. **Broken references** (Parnas: files SKILL.md points to that don't exist)
6. **Skeleton skills** (Ostrom sanction: <100 bytes, no tests)
7. **System diversity** (Ashby: R_system vs R_controller)
8. **Dreyfus grade** (5-level maturity distribution)
9. **Rule liveness** (2nd-Order: which rules have been triggered)
10. **Incentive points** (Nudge: reward accumulation)
11. **Meme clusters** (Memetics: multi-member categories needing flow)

### Alias detection

NOT all SKILL.md files represent real, active skills. Deduplication replaces duplicate versions with alias stubs:

```yaml
---
name: pua
alias: true
canonical: ~/.hermes/skills/pua/codex/pua/SKILL.md
note: 指向规范版
---
```

The steward must explicitly check `frontmatter.get("alias", "").lower() == "true"` and **exclude** aliases from:
- Total skill count (Dunbar threshold)
- Name conflict detection (Parnas)
- System diversity (Ashby)
- Dreyfus grade distribution

In practice with 163 SKILL.md files (16 aliases + 147 real), the effective count drops from OVER_LIMIT to MANAGEABLE.

## Step 2: Create Local Brain

The brain connects theoretical frameworks to practical implementation:

```bash
mkdir -p ~/Documents/brain/{00-索引,02-治理理论,03-系统理论,04-技能生态,06-仪表盘,.obsidian}
```

Create at minimum:
- **Index** — theory-to-problem mapping matrix
- **Governance notes** — one per theory (Ostrom 8 principles, Havel friction, Conway steward)
- **System theory notes** — Ashby diversity, Prigogine entropy, Parnas decomposition, Dreyfus 5 levels, 2nd-Order, Nudge, Memetics, Tri-constraint
- **Practice docs** — one per governance mechanism (creation gate, entropy debt, conflict detection, steward role definition, usage tracking, hot-cold separation)
- **Dashboard** — live health metrics updated by steward cron

Set up bidirectional sync:

```bash
# Push: ~/.hermes/notes/ → brain/99-hermes-notes/
# Pull: brain/ → ~/.hermes/notes/brain/
```

Register hourly sync cron:

```bash
cronjob --create --name "brain-hourly-sync" \
  --schedule "0 * * * *" \
  --prompt "Run ~/.hermes/scripts/sync-brain.py"
```

## Step 3: Create Steward

The steward is a cronjob that enforces governance rules. It is the actuator of Conway's Inverse Law — by changing the organization (adding a steward role), the system structure changes.

### Core steward.py structure:

```python
# 1. Scan all skills (find ~/.hermes/skills -name "SKILL.md")
# 2. Parse frontmatter, detect alias: true stubs
# 3. Run 11 audits (only on non-alias skills where relevant)
# 4. Apply gradient sanctions (Ostrom):
#    - 90d+ stale, no tests → DEPRECATED
#    - 150d+ DEPRECATED → ARCHIVED
#    - 240d+ ARCHIVED → DELETED
# 5. Track usage statistics (Ashby prior distribution)
# 6. Update Obsidian dashboard
# 7. Self-audit rule liveness (2nd-Order Cybernetics)
```

### Register cronjobs:

```bash
cronjob --create --name "skill-steward-daily-audit" \
  --schedule "0 2 * * *" \
  --prompt "Run ~/.hermes/scripts/skill-steward.py and report FAIL indicators"

cronjob --create --name "brain-hourly-sync" \
  --schedule "0 * * * *" \
  --prompt "Run ~/.hermes/scripts/sync-brain.py"
```

### Governance gate in creation flow

**CRITICAL: Do not rely solely on cron for enforcement.** The gap between cron runs (up to 24h) means new skills bypass audit temporarily. Embed governance checks directly in the creation tool:

In `~/.hermes/hermes-agent/tools/skill_manager_tool.py`, modify the `action == "create"` handler to add:

```python
# 1. Ostrom: Block creation if total >= 200 (Dunbar hard limit)
if existing_total >= 200:
    return tool_error(f"Creation blocked: {existing_total}/{200}")

# 2. Ostrom: Warn if approaching 150
elif existing_total >= 150:
    warnings.append("Approaching limit: {existing_total}/200")

# 3. Parnas: Check for similar existing skills
for sk_path in SKILLS_DIR.rglob("SKILL.md"):
    if name.lower() in sname or sname in name.lower():
        warnings.append(f"Similar skills found: {similar[:5]}")

# 4. Prigogine: Check entropy debt from stale skills
# (read steward state.json for Dreyfus L1 count)
```

No restart needed — Hermes re-reads tool files on each call.

## Step 4: Self-Check Loop

After initial setup, the system is not complete — it needs a self-check loop to find gaps in theoretical coverage:

### Self-check criteria

```
1. Are all 5 hard problems covered by at least one theory?
2. Is each theory implemented in code (not just documented)?
3. Is each implementation producing real output in the audit?
4. Are there governance dimensions NOT covered by any theory?
5. Are any two theories redundant (covering the same dimension)?
```

### Typical Phase 2 gaps found during loop

The self-check loop has **two distinct phases**. Phase 1 looks complete but Phase 2 reveals deeper gaps:

**Phase 1 (first iteration):** Covers the 5 hard problems with 7 theories:
- Ostrom, Prigogine, Conway, Parnas, Ashby, Havel, Tri-constraint

Do NOT stop here. **Phase 2 (second iteration)** reveals 4 more gaps:

| Gap | Theory to Fill | Implementation |
|-----|---------------|----------------|
| Quality assessment (only detects "broken", not "good") | Dreyfus 5-level model | Add Dreyfus grade to steward audit |
| Who audits the steward? | 2nd-Order Cybernetics | Rule liveness detection in steward |
| Punishment but no reward | Nudge + Mechanism Design | Incentive points tracking |
| Skills don't learn from each other | Memetics | Cluster detection for meme flow |

After Phase 2, the system converges with **11 theories, 11 metrics, 0 gaps**.

### Convergence condition

The loop converges when self-check finds:
- All 5 hard problems → at least one theory each (7 theories from Phase 1)
- No governance dimension missing a theory (4 more from Phase 2)
- All theories → practical implementation in steward audit
- No redundant theories

After convergence, remaining alerts fall into two categories:
- **Execution problems**: adding tests, writing changelogs (manual, progressive)
- **Time-dependent**: rule liveness starts at 0/4, needs cron to accumulate history

### Progressive upgrade pattern

After systemic problems are solved, address quality at different tiers:

```
Tier 1 (CORE ~20):           Immediate test-prompts.json creation
  → These are the most-used skills: pua, loop, p10, p9, p7, dogfood, uimax-audit,
    systematic-debugging, tdd, plan, writing-plans, etc.
  → Batch-create test-prompts.json with 2-3 prompts each
  → Impact: +10% test coverage in one session

Tier 2 (ACTIVE ~30):         Steward cron natural deprecation
  → Skills used occasionally but without tests
  → Stale for 90d+ → auto DEPRECATED by steward

Tier 3 (COLD ~100):          Marked L1, no urgent action
  → Cron handles over time (90d → DEPRECATED, 150d → ARCHIVED)
  → Don't create test-prompts for skills that may never be used again
```

## Step 5: Skill Graphs 2.0 — Atoms / Molecules / Compounds

Skill dependency graphs must be composed as typed layers, not arbitrary dense Wikipedia-style links:

- `atom`: single-purpose primitive, zero skill-level dependencies. It should be close to deterministic and narrow in scope.
- `molecule`: a bounded workflow that explicitly chains 1-10 atoms. It may use judgement, but composition order should be written into the skill.
- `compound`: a high-level orchestrator/playbook that drives molecules and optionally atoms. It is where meaningful autonomy belongs.

Governance rule:
1. Cycles are never safe. A cycle means the agent can bounce between skills or skip part of the chain. Break or invert one edge.
2. Max graph depth defaults to 4 (`HERMES_SKILL_GRAPH_MAX_DEPTH`). Deeper chains should be split at a molecule boundary.
3. Runtime loader behavior stays unchanged; enforcement is an audit gate first, migration second.
4. Add `tier: atom|molecule|compound` or `skill_tier: atom|molecule|compound` in frontmatter when a skill is migrated. Untyped skills are inferred and reported as migration suggestions.

Commands:
```bash
# Read-only topology report; writes ~/.hermes/skills/steward/skill-graph-report.json
python3 ~/.hermes/scripts/skill-steward.py --graph-check --json --warn-only

# Strict fail-closed gate for CI/curation; exit 2 on cycles, excessive depth, or typed violations
python3 ~/.hermes/scripts/skill-steward.py --graph-check --json

# Full steward report now includes audits.skill_graph
python3 ~/.hermes/scripts/skill-steward.py
```

The report schema is `~/.hermes/schemas/skill-graph-audit.schema.json`. Self-test includes valid and invalid synthetic fixtures so the cycle/depth fail-closed behavior cannot silently regress.

### Cycle cleanup playbook

When `--graph-check` reports cycles, do not count each cycle path as a separate task. Collapse them into strongly connected components (SCCs), then break each SCC by editing `related_skills` into a one-way DAG:

- Use directionality: orchestrator -> implementation variants, later workflow stage -> prerequisite, specialized skill -> primitive.
- Never keep peer `<->` peer links. Convert mutual peer links into a chain (for example `claude-code -> codex -> opencode`) or remove the low-value side.
- Preserve discoverability where useful; avoid clearing all links from a cluster unless the skill is truly an atom.
- Keep environment-specific facts out of shared skills. Account/model/provider details belong in config or memory, not generic SKILL.md body.
- Closure condition for an exhaustive governance loop is strict graph-check OK, not merely warn-only output.

Detailed procedure: `references/skill-graph-cycle-cleanup.md`.

## Step 6: Maintain

The system runs on cron, but quarterly reviews should check:

1. **Are the rules still right?** Rules that have 0 triggers → DORMANT → prune
2. **Are the thresholds still right?** Dunbar 150 may need adjustment as models improve
3. **Are the metrics still meaningful?** Goodhart's Law — metrics can become targets
4. **Is the steward itself healthy?** Check rule_liveness in audit output

## Theoretical Framework Reference

| Theory | Source | Solves | Mechanism |
|--------|--------|--------|-----------|
| Ostrom's 8 Principles | Governing the Commons (1990) | 无筛选 | Gate + graduated sanctions + monitoring |
| Prigogine's Dissipative Structures | Order Out of Chaos (1977) | 无淘汰 | Entropy debt (ΔS≈0) |
| Conway's Inverse Law | How Do Committees Invent? (1968) | 功能孤岛 | Steward cron role → system structure |
| Parnas Information Hiding | Criteria for Decomposing Modules (1972) | 无冲突检测 | Decompose by change reason |
| Ashby's Requisite Variety | Introduction to Cybernetics (1956) | 无追踪 | R_controller >= R_system |
| Havel's System Friction | The Power of the Powerless (1978) | 系统惯性 | Institutional friction on create |
| Sturgeon + Price + Dunbar | Various (1957/1965/1992) | 总量失控 | Active set + cold storage |
| Dreyfus Skill Acquisition | Mind Over Machine (1986) | 质量评估缺口 | 5-level maturity model |
| 2nd-Order Cybernetics | Observing Systems (1981) | 自审计缺口 | Steward audits own rules |
| Nudge + Mechanism Design | Nudge (2008), Hurwicz (2007) | 激励缺口 | Choice architecture + points |
| Memetics | The Selfish Gene (1976) | 知识传递缺口 | Cross-skill meme flow detection |

## Common Pitfalls
### File handling

1. **DO NOT use `read_file()` output as `write_file()` input.** The `read_file` tool returns formatted lines with line number prefixes (`   276|`). Writing this back corrupts the file. Always use `terminal("cat path")` or read with Python stdlib for file-in-file-out operations.

2. **Do not redirect graph-check stdout to the same report file that `skill-steward.py` writes internally.** `skill-steward.py --graph-check --json` writes `~/.hermes/skills/steward/skill-graph-report.json` itself; shell redirection to that exact path can create truncated/duplicated JSON (`Extra data`). Write stdout to `/tmp/skill-graph-report.json`, validate with `python3 -m json.tool`, then `cp` it into place. See `references/skill-graph-cycle-cleanup.md`.

3. **Alias resolution creates hidden file count.** Replacing duplicate SKILL.md with `alias: true` stubs still creates files on disk. The steward must explicitly check frontmatter for `alias: true` and exclude from counts, conflicts, and diversity metrics.

3. **State.json backward compatibility.** When adding new keys to the state dict, use `loaded.setdefault(k, default_v)` instead of assuming all keys exist. Old state files crash on missing keys.

4. **Referenced scripts may not exist.** The initial obsidian skill referenced `sync-to-obsidian.py` and `obsidian-watch.py` that were never created. Always verify linked files exist, not just that they're referenced in SKILL.md.

### Metrics and alerts

5. **Not all FAIL indicators are real problems.** After cleanup, 4 alerts may remain even when the system is healthy:
   - Dreyfus L1 ratio (High Novice) — this is the same as low test coverage, a single problem reported twice
   - Rule liveness 0/4 — expected on day 1, the steward needs ~7 days of cron to accumulate history
   - Meme flow clustering of 20+ — this is informational (category distribution), not actionable
   - Test coverage below threshold — improvement is progressive, not a single-fix problem

6. **Goodhart's Law is real at 11 metrics.** Once the system has 11+ metrics, users naturally start optimizing for the metrics instead of the underlying quality. The self-check loop must include a "is any metric becoming a target?" check. If the team starts saying "we need to get L4 to 10" instead of "we need better skills", the metrics have become targets.

7. **Alert fatigue kills governance.** If steward reports 8 FAIL indicators daily, humans stop reading. Prioritize: fix the top 3 and let the rest run as background. Prune informational metrics from the FAIL count.

### Architecture

8. **Cron as only actuator.** Cron only runs at 2am. New skills created between 2am and 2am next day bypass audit for up to 24h. Mitigate by embedding governance checks directly in `skill_manager_tool.py` (see Step 3).

9. **Obsidian vault drift.** If sync breaks, the brain and the steward diverge. Check sync-brain.py output in cron logs. The brain is a secondary store; the primary state is in `~/.hermes/skills/steward/state.json`.

10. **Cross-platform ecosystem separation.** Hermes and Claude Code maintain completely independent skill directories (`~/.hermes/skills/` vs `~/.claude/skills/`). They do NOT share skills, and only ~9 names overlap (pua, loop, p10, p7, p9, pro, yes, pua-en, pua-ja). The steward should ONLY govern the Hermes ecosystem. Do NOT add cross-platform monitoring — it produces informational noise without actionable outcomes, and users will ask you to remove it.

### Loop convergence

11. **Skipping Phase 2 is the most common mistake.** After Phase 1 (7 theories cover 5 hard problems), it looks done. But Phase 2 reveals 4 more gaps that are invisible to a first pass. Always check: "is there a dimension of quality my current metrics miss?" Answer: yes, Dreyfus quality assessment. "Who audits my auditor?" → 2nd-Order Cybernetics.

12. **The loop converges on systemic problems, not execution.** After convergence, remaining work is always execution (adding tests, writing changelogs) or time-dependent (steward needs history). Don't define "done" as "0 alerts" — define it as "no remaining theoretical gaps and no unsolved systemic problems."

13. **Progressive upgrade beats all-at-once.** Adding tests to 20 CORE skills takes one session. Adding tests to all 113 L1 skills would take 5+ sessions. Let the cron handle the rest (90d → DEPRECATED → archived). The system self-heals over time.

## Definition of Done

- [ ] **Outcome**: steward.py running and producing 11-metric audit
- [ ] **Outcome**: Obsidian brain vault created with theory notes + dashboard
- [ ] **Outcome**: Two cronjobs active (daily steward + hourly sync)
- [ ] **Outcome**: Governance gate embedded in skill_manager_tool.py
- [ ] **Outcome**: Self-check loop converged (no remaining theoretical gaps)
- [ ] **Process**: Diagnose → Brain → Steward → Gate → Loop → Maintain
- [ ] **Style**: Reports are terminal-friendly, not markdown-heavy. Use Unicode box drawing.
- [ ] **Efficiency**: Don't run steward more than once daily. Don't add cron overhead.

## Related Skills

- `darwin-skill` — individual skill optimization (hill-climbing for SKILL.md quality)
- `workflow-ecosystem-audit` — workflow coverage mapping (complementary: this focuses on governance, that focuses on coverage)
- `skill-eval` — individual skill evaluation with test prompts (this does ecosystem-level audit)
- `loop` — iterative execution loop (this uses self-check loop for convergence)
- `skill-ecosystem-diagnosis` — pre-governance diagnosis (this builds on it)

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] The Definition of Done items above were explicitly checked, not assumed.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

