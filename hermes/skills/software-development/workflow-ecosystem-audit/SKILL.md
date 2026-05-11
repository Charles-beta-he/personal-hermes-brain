---
name: workflow-ecosystem-audit
description: "Audit the skill ecosystem for workflow coverage gaps and broken references. Maps skills to workflow stages, identifies uncovered stages, detects missing linked files, and generates missing protocols/skills to fill gaps. Use when asked to '梳理工作流', 'review workflow', 'skill gaps', '缺省流程', or when setting up a new project workspace."
license: MIT
tags: [workflow, audit, skills, gaps, planning, ecosystem]
---

# Workflow Ecosystem Audit — 工作流全景梳理与缺省流程补充

> 把散落在各 skill 里的流程拼成一张完整的地图，找到没盖住的地方，补上。

## When to Use

- 用户说"梳理工作流"、"review workflow"、"skill gaps"、"缺省流程"
- 新项目启动，需要确认 workflow 覆盖度
- 新增一批 skill 后，需要重新对齐工作流
- 发现 skill 引用 broken（references 指向不存在的文件）

## Core Principle

**Skills 是散落的拼图，Workflow 是拼完后的画面。** 单独每个 skill 可能完整，但拼在一起时可能有缝。

## Audit Steps

### Step 1: Enumerate Skills by Category

```bash
# List all skills with categories
skills_list()
```

Filter by relevant category (e.g., `software-development`).

### Step 2: Load Each Skill & Check References

For every skill in the target category:

```python
skill_view("skill-name")
```

Check the `linked_files` field. If it references files that don't exist, mark as **broken reference**.

**Common broken reference pattern**: SKILL.md says "详细协议见 `references/p*-protocol.md`" but the file doesn't exist.

### Step 3: Map Skills to Workflow Stages

Define the standard workflow stages for your domain. For software development:

```
[0] 需求接收 → [1] 战略设计 → [2] 任务拆解 → [3] 编码实现
      → [4] 代码审查 → [5] 验证测试 → [6] 构建部署
      → [7] 上线验证 → [8] 事故复盘 → [9] 持续优化
```

Map each skill to the stage(s) it covers. A skill may cover multiple stages.

### Step 4: Identify Gaps

For each stage, check:
- Is there a skill that covers it?
- Is the skill complete (no broken references)?
- Does it have a Definition of Done?

Mark stages as:
- ✅ Covered — skill exists and complete
- ⚠️ Partial — skill exists but references broken
- ❌ Missing — no skill covers this stage

### Step 5: Create Missing Pieces

For each gap:

**Broken references** → Create the missing referenced file:
```bash
mkdir -p ~/.hermes/skills/{skill-name}/references/
# Write the protocol/template file
```

**Missing stage skill** → Create a new skill:
```bash
mkdir -p ~/.hermes/skills/software-development/{new-skill-name}/
# Write SKILL.md with Definition of Done
```

**Missing protocol** → Write the protocol document that the skill references.

### Step 6: Output Workflow Map

Generate a terminal-readable report with:
1. Workflow stage map (9 stages with status)
2. Role hierarchy diagram (P10 → P9 → P8/P7)
3. Trigger word cheat sheet
4. Key deliverable checklist (which doc → which stage → which role)
5. Remaining gaps that need project-specific customization

## Key Findings from This Pattern

### Broken References Are Silent Failures

Skills with `linked_files` pointing to non-existent files don't crash — they just fail to load the referenced content. The skill still "works" but misses critical context.

**Fix**: After creating a skill with linked files, always verify:
```bash
ls -la ~/.hermes/skills/{skill-name}/references/
```

### Skeleton Skills vs Complete Skills

A "skeleton skill" has:
- SKILL.md with description and "详细协议见 references/..."
- Empty or missing references/ directory

A "complete skill" has:
- SKILL.md with inline instructions OR
- SKILL.md + populated references/ with all linked files

Skeleton skills are common when skills are created incrementally. The audit catches them.

### Workflow Stages Are Domain-Specific

The 9-stage model above is for software development. Other domains need different stages:
- **Data Science**: [0]数据获取 → [1]清洗 → [2]探索 → [3]建模 → [4]验证 → [5]部署 → [6]监控
- **DevOps**: [0]需求 → [1]设计 → [2]IaC → [3]CI → [4]部署 → [5]观测 → [6]on-call

Adapt the stage model to your domain.

### Roles Need Protocol Files

When a skill defines a role (P10, P9, P7), the role's behavioral protocol should be in a separate reference file, not buried in SKILL.md. This allows:
- Multiple skills to reference the same protocol
- Protocol updates without changing all skills
- Clear separation of "what to do" (SKILL.md) vs "how to behave" (protocol)

## Definition of Done

- [ ] **Outcome**: All workflow stages mapped to skills, broken references fixed, missing skills created, terminal report generated
- [ ] **Process**: Enumerate → Load & check → Map → Identify gaps → Create → Report
- [ ] **Style**: Report uses Unicode box-drawing characters, includes role hierarchy diagram, trigger word table, deliverable checklist
- [ ] **Efficiency**: Don't over-engineer — if a stage is intentionally uncovered (e.g., "数据库变更" for a frontend-only project), mark it as N/A rather than creating an unnecessary skill

## Pitfalls

1. **Assuming linked_files exist** — Always verify with `ls` or `read_file` before relying on referenced content
2. **Creating skills for project-specific gaps** — Some gaps (e.g., database migration flow) are project-specific, not generalizable. Only create skills for reusable patterns
3. **Overwriting existing content** — When fixing broken references, check if the referenced file was intentionally removed. Don't recreate deleted content without understanding why
4. **Terminal report too long** — Keep the report concise. If it exceeds 200 lines, split into sections and let the user ask for details
