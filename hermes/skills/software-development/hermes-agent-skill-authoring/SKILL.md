---
name: hermes-agent-skill-authoring
description: Use when creating, rehabilitating, or structurally improving Hermes SKILL.md files, including trigger design, frontmatter normalization, mode selection, and peer-shape validation.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms:
- linux
- macos
- windows
metadata:
  hermes:
    tags:
    - skills
    - authoring
    - hermes-agent
    - conventions
    - skill-md
    related_skills:
    - skill-eval
    - workflow-ecosystem-audit
    - writing-plans
---

# Authoring Hermes-Agent Skills (in-repo)

## Overview

There are two places a SKILL.md can live:

1. **User-local:** `~/.hermes/skills/<maybe-category>/<name>/SKILL.md` — personal, not shared. Created via `skill_manage(action='create')`.
2. **In-repo (this skill is about this case):** `/home/bb/hermes-agent/skills/<category>/<name>/SKILL.md` — committed, shipped with the package. Use `write_file` + `git add`. `skill_manage(action='create')` does NOT target this tree.

## When to Use

- User asks you to add a skill "in this branch / repo / commit"
- User asks whether an existing self-created skill is bloated, unstable, duplicate, poorly triggered, or structurally weak
- You need to rehabilitate a user-local skill under `~/.hermes/skills/` by tightening triggers, refactoring sections, splitting references/templates, or clarifying verification
- You're committing a reusable workflow that should ship with hermes-agent
- You're editing an existing skill under `/home/bb/hermes-agent/skills/` (use `patch` for small edits, `write_file` for rewrites; `skill_manage` still works for patch on in-repo skills, but not for `create`)

## Creation Gate Before Writing

Before creating a new skill or materially changing an existing one, apply the local creation-gate checklist at `/Users/charles/Documents/brain/05-实践与项目/projects/agent-skill-learning/skill-authoring-creation-gates-2026-05-13.md`:

1. Need / anti-proliferation: patch an existing umbrella skill + reference unless a new reusable trigger class is justified.
2. Shape: frontmatter, description length, non-empty body, peer-shaped sections.
3. Trigger evals: at least 3 positive prompts and 2 negative prompts.
4. Deterministic/read-back verification: `skill_view` main + linked files and artifact checks.
5. Graph/steward: run graph-check when routing/edges changed.
6. Closeout: commit tracked skill edits and report exact paths/commands.

## Required Frontmatter

Source of truth: `tools/skill_manager_tool.py::_validate_frontmatter`. Hard requirements:

- Starts with `---` as the first bytes (no leading blank line).
- Closes with `\n---\n` before the body.
- Parses as a YAML mapping.
- `name` field present.
- `description` field present, ≤ **1024 chars** (`MAX_DESCRIPTION_LENGTH`).
- Non-empty body after the closing `---`.

Peer-matched shape used by every skill under `skills/software-development/`:

```yaml
---
name: my-skill-name               # lowercase, hyphens, ≤64 chars (MAX_NAME_LENGTH)
description: Use when <trigger>. <one-line behavior>.
# Include when your library/router uses them as part of the entry contract:
# level: advanced
# requires: [other-skill]
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [short, descriptive, tags]
    related_skills: [other-skill, another-skill]
---
```

`version` / `author` / `license` / `metadata` are NOT enforced by the validator, but every peer has them — omit and your skill sticks out. Likewise, `level` and `requires` are ecosystem-shape fields rather than validator-mandated fields: preserve them whenever the target library uses them as part of routing or prerequisite declaration.

## Size Limits

- Description: ≤ 1024 chars (enforced).
- Full SKILL.md: ≤ 100,000 chars (enforced as `MAX_SKILL_CONTENT_CHARS`, ~36k tokens).
- Peer skills in `software-development/` sit at **8-14k chars**. Aim for that range. If you're pushing past 20k, split into `references/*.md` and reference them from SKILL.md.

## Peer-Matched Structure

See also `references/skill-mode-patterns.md` for a compact mode-selection reference and the shared frontmatter contract, and `references/perplexity-skill-lessons.md` for a concise external rubric on context budgets, trigger-writing, and gotcha-first maintenance.

Every in-repo skill follows roughly:

```
# <Title>

## Overview
One or two paragraphs: what and why.

## When to Use
- Bulleted triggers
- "Don't use for:" counter-triggers

## <Topic sections specific to the skill>
- Quick-reference tables are common
- Code blocks with exact commands
- Hermes-specific recipes (tests via scripts/run_tests.sh, ui-tui paths, etc.)

## Common Pitfalls

Numbered list of mistakes and their fixes.
1. Skipping prerequisite checks and assuming the environment already matches the workflow.
2. Applying the workflow mechanically without confirming that the request still matches this skill's trigger class.
3. Reporting success before reading back the actual outputs, files, or external side-effects.
## Verification Checklist

- [ ] Checkbox list of post-action verifications
- [ ] Preconditions, scope, and tool availability were checked before following this workflow.
- [ ] The key output artifacts, commands, or side-effects were verified by read-back or direct inspection.
## One-Shot Recipes (optional)
Named scenarios → concrete command sequences.
```

Not every section is mandatory, but `Overview` + `When to Use` + actionable body + pitfalls are the minimum for the skill to feel like a peer.

## SKILL.md as an Entry Contract: 5 Internal Control-Flow Modes

Treat `SKILL.md` as the entry contract. Keep the shared routing skeleton stable: `name`, `description`, and—when the surrounding library uses them—`level` and `requires`. `description` remains the primary trigger surface that determines when the skill should load. The main design choice is the internal control-flow shape inside the body.

### The five modes

1. **Wrapper**
   - Shape: `SKILL.md -> reference -> agent capability`
   - Use when the skill's main job is to expose or normalize an external capability, SDK, API, toolchain, or operational surface.
   - Typical body: prerequisites, exact commands, capability map, parameter caveats, verification steps.

2. **Generator**
   - Shape: `SKILL.md -> template + data -> output`
   - Use when the output format is stable and repeatable: reports, contracts, specs, briefs, summaries, checklists, or other templated deliverables.
   - Typical body: input schema, template slots, transformation rules, acceptance examples.

3. **Reviewer**
   - Shape: `input -> checklist -> graded report`
   - Use when the skill is a quality gate, audit pass, static review, or rules-based inspection layer.
   - Typical body: review dimensions, scoring rubric, fail/warn/pass conditions, evidence requirements.

4. **Inversion**
   - Shape: role inversion — the agent leads the interrogation, the user answers, and the agent synthesizes.
   - Use when requirements are unclear, context is missing, or the agent must actively elicit constraints before producing a safe result.
   - Typical body: interview sequence, branching questions, synthesis rules, stop conditions.

5. **Pipeline**
   - Shape: mandatory ordered stages with checkpoints and no step-skipping.
   - Use when the workflow is multi-step and each step must produce a verifiable artifact before the next one begins.
   - Typical body: stage list, inputs/outputs per stage, gating checks, rollback/retry rules.

### Selection heuristic

| Scenario | Prefer |
|----------|--------|
| Calling a complex SDK/API/toolchain | Wrapper |
| Fixed-format deliverable | Generator |
| Quality gate / static audit / review | Reviewer |
| Ambiguous request / missing context | Inversion |
| Multi-step workflow with verifiable artifacts | Pipeline |

### Shared contract across all five modes

Regardless of mode, keep the entry contract stable:

- Frontmatter remains the router-facing contract: `name`, `description`, and—when the surrounding library uses them—`level` and `requires`
- `description` remains the primary trigger surface that decides when the skill should load
- The mode only changes the internal organization of the body, not the external routing contract
- Rich session-specific detail belongs in `references/`, reusable starter artifacts belong in `templates/`, and deterministic repeatable actions belong in `scripts/`

### Context-budget contract (index / load / runtime)

Treat every skill as three cost layers, not one markdown blob:

1. **Index layer** — `name` + `description`
   - Paid in every session for every user
   - Keep the description trigger-oriented, compact, and free of workflow summary
   - Bad pattern: explaining what the skill does
   - Better pattern: stating *when* to load it in the user's language
2. **Load layer** — root `SKILL.md` body
   - Paid after the skill loads and competes with other loaded skills
   - Keep only high-signal workflow decisions, branch points, pitfalls, and verification
   - If the model likely already knows a command sequence, do not spend root-body budget on it
3. **Runtime layer** — `references/`, `templates/`, `scripts/`, `assets/`
   - Paid only when read or executed
   - Move conditional branches, long domain notes, heavy docs, templates, and deterministic helper logic here

Heuristic: if the root body starts reading like a README, command cheat sheet, or long domain memo, split it. Prefer a short SKILL.md plus progressive disclosure into `references/`.

### Description quality checklist

When reviewing or rewriting `description`, check all of these:

- It answers **when to load**, not **what the skill does**
- It uses the user's likely intent language, not internal implementation language
- It avoids summarizing the workflow or tool steps
- It helps separate adjacent skills and reduce off-target loads
- It is short enough that every word earns its place in the global index budget

If the description changed materially, treat it as routing logic and pair it with explicit positive + negative trigger evals.

### Gotcha-first maintenance rule

For mature skills, the highest-value growth is usually append-mostly:

- Agent failed in-domain -> add a gotcha, negative example, or tighter verification step
- Agent loaded off-target -> tighten description and add negative evals
- Agent missed a valid trigger -> add intent phrasing and positive evals

Do **not** default to making the main workflow longer. Prefer recording the sharp edge that caused the failure, and move bulky or conditional detail into `references/`.

### Authoring implication

Do not treat every skill as a generic prose memo. Pick one primary mode first, then structure the skill body to match that control-flow. Hybrid skills are allowed, but the dominant mode should be obvious from the section layout and verification pattern.

## Rehabilitating Existing Self-Created Skills

When improving a user-local skill that already exists under `~/.hermes/skills/`, do not jump straight to rewriting prose. Run a short diagnosis loop first:

1. **Classify the failure mode**
   - Trigger failure: description too vague / too narrow / wrong vocabulary
   - Control-flow failure: wrong primary mode (for example Pipeline written like Wrapper)
   - Scope failure: duplicates an umbrella skill or mixes multiple jobs
   - Artifact failure: missing template / reference / checklist / verification
   - Maintenance failure: body too long, stale examples, broken related_skills, weak pitfalls

2. **Choose the smallest effective repair**
   - Tighten `description` when routing is the problem
   - Re-section the body when control-flow is the problem
   - Split long details into `references/` when density is the problem
   - Add `templates/` for Generator skills
   - Add rubric/checklist tables for Reviewer skills
   - Add stage gates and evidence checks for Pipeline skills
   - Merge into an existing umbrella skill when the standalone trigger class is not justified

3. **Prefer patch over rewrite**
   - Use `skill_manage(action='patch')` for focused repairs
   - Use `skill_manage(action='edit')` or full-file rewrite only when the skill needs a structural reset
   - Preserve the skill name unless the trigger class itself changed

4. **Verify read-back, not intention**
   - Re-open the skill with `skill_view`
   - Confirm frontmatter still parses cleanly
   - Confirm the dominant mode is now obvious from the body
   - Confirm examples/checklists/templates align with the mode

### Rehabilitation heuristics by symptom

| Symptom | Likely fix |
|---------|------------|
| Skill rarely auto-loads | rewrite `description` around trigger class |
| Skill loads but outputs drift | convert toward Generator or add template/checklist |
| Skill skips necessary steps | convert toward Pipeline with explicit gates |
| Skill gives shallow critiques | convert toward Reviewer with rubric/severity |
| Skill asks too little before acting | convert toward Inversion with interview flow |
| Skill feels like random notes | pick one primary mode and move the rest to references |
| Skill overlaps another skill | patch umbrella skill or merge instead of keeping both |

### Multi-skill rehabilitation pass (recommended order)

When auditing a batch of legacy self-created skills, do not review them through only one lens. Use three short passes, then repair in order of confidence:

1. **Trigger/frontmatter pass**
   - Check whether `description` expresses a clear trigger class and preferably starts with `Use when ...`
   - Normalize `version`, `author`, `license`, and `metadata.hermes.{tags,related_skills}`
   - Remove ad-hoc frontmatter fields when they are not part of the stable peer shape

2. **Mode/structure pass**
   - Infer the primary mode (Wrapper / Generator / Reviewer / Inversion / Pipeline)
   - Check whether the body sections make that mode obvious
   - For mature skills, prefer the standard shell: `Overview` -> `When to Use` -> body -> `Common Pitfalls` -> `Verification Checklist`

3. **Ecosystem/governance pass**
   - Identify overlap, umbrella fit, and whether details should move to `references/`
   - Distinguish `patch now` from `merge later`
   - Treat duplicate tails, broken examples, and conflicting command snippets as immediate repairs

Repair order:
- First: low-risk contract fixes (description, frontmatter, related_skills)
- Second: obvious structural corruption (duplicate headings, dangling tails, contradictory command examples)
- Third: deeper body reshaping or umbrella slimming

This sequencing keeps the library improving without overfitting one session's wording or doing unnecessary full rewrites.

### Library-wide bulk rehabilitation rule

When the user asks for a full-library batch pass, split the work into two layers:

- **Safe contract-layer normalization (scriptable):** add missing `version` / `author` / `license`, ensure `metadata.hermes`, move top-level `tags` and `related_skills` into `metadata.hermes`, normalize obvious heading variants, repair invalid frontmatter YAML, and eliminate empty `related_skills` with conservative umbrella fallbacks.
- **Semantic trigger/body rewrites (manual or tightly reviewed):** `description` modernization, primary-mode reassignment, section-shell injection, and umbrella slimming.

Do the contract layer first and verify by exact counts before touching trigger semantics. Do **not** batch-rewrite every `description` into `Use when ...` with a naive script; trigger text is routing logic, not just style.

After the contract layer, the highest-leverage semantic batch order is:

1. **Umbrella/root routing pass** — rewrite placeholder category roots into real routing surfaces with `Routing Guide`, `Selection Rules`, child-skill maps, and explicit counter-triggers.
2. **Verification/pitfall pass** — raise weak shells to a minimum actionable floor (for example 3+ checklist items and 3+ numbered pitfalls) before doing stylistic prose edits.
3. **Overview/counter-trigger pass** — expand obviously thin `Overview` sections and add `Don't use for:` bullets where missing, but stop before overwriting mature hand-written specialist prose.
4. **Residual manual queue** — leave dense expert skills, ambiguous duplicate-heading cases, and umbrella nodes without auto-discovered children for manual refinement instead of forcing a low-signal bulk rewrite.

This sequencing keeps the batch pass moving from safest structural wins toward narrower semantic edits, while preserving high-signal specialist content.

For a reusable checklist and verification counters, see `references/bulk-rehabilitation-playbook.md`.

## Directory Placement

```
skills/<category>/<skill-name>/SKILL.md
```

Categories currently in repo (confirm with `ls skills/`): `autonomous-ai-agents`, `creative`, `data-science`, `devops`, `dogfood`, `email`, `gaming`, `github`, `leisure`, `mcp`, `media`, `mlops/*`, `note-taking`, `productivity`, `red-teaming`, `research`, `smart-home`, `social-media`, `software-development`.

Pick the closest existing category. Don't invent new top-level categories casually.

## Workflow

1. **Survey peers** in the target category:
   ```
   ls skills/<category>/
   ```
   Read 2-3 peer SKILL.md files to match tone and structure.
2. **Check validator constraints** in `tools/skill_manager_tool.py` if unsure.
3. **Draft** with `write_file` to `skills/<category>/<name>/SKILL.md`.
4. **Validate locally**:
   ```python
   import yaml, re, pathlib
   content = pathlib.Path("skills/<category>/<name>/SKILL.md").read_text()
   assert content.startswith("---")
   m = re.search(r'\n---\s*\n', content[3:])
   fm = yaml.safe_load(content[3:m.start()+3])
   assert "name" in fm and "description" in fm
   assert len(fm["description"]) <= 1024
   assert len(content) <= 100_000
   ```
5. **Git add + commit** on the active branch.
6. **Note:** the CURRENT session's skill loader is cached — `skill_view` / `skills_list` will not see the new skill until a new session. This is expected, not a bug.

## Cross-Referencing Other Skills

`metadata.hermes.related_skills` unions both trees (`skills/` in-repo and `~/.hermes/skills/`) at load time. You CAN reference a user-local skill from an in-repo skill, but it won't resolve for other users who clone the repo fresh. Prefer referencing only in-repo skills from in-repo skills. If a frequently-referenced skill lives only in `~/.hermes/skills/`, consider promoting it to the repo.

## Editing Existing In-Repo Skills

- **Small fix (typo, added pitfall, tightened trigger):** `skill_manage(action='patch', name=..., old_string=..., new_string=...)` works fine on in-repo skills.
- **Major rewrite:** `write_file` the whole SKILL.md. `skill_manage(action='edit')` also works but requires supplying the full new content.
- **Adding supporting files:** `write_file` to `skills/<category>/<name>/references/<file>.md`, `templates/<file>`, or `scripts/<file>`. `skill_manage(action='write_file')` also works and enforces the references/templates/scripts/assets subdir allowlist.
- **Always commit** the edit — in-repo skills are source, not runtime state.

## Common Pitfalls

1. **Using `skill_manage(action='create')` for an in-repo skill.** It writes to `~/.hermes/skills/`, not the repo tree. Use `write_file` for in-repo creation.

2. **Leading whitespace before `---`.** The validator checks `content.startswith("---")`; any leading blank line or BOM fails validation.

3. **Unquoted YAML descriptions with colons.** If `description:` contains a colon (for example `patterns: scoped task prioritization`) or other YAML-significant punctuation, quote the whole value. Validate with `yaml.safe_load` before committing; otherwise the skill may look fine in Markdown but fail frontmatter parsing.

4. **Description too generic.** Peer descriptions start with "Use when ..." and describe the *trigger class*, not the one task. "Use when debugging X" > "Debug X".

4. **Forgetting the author/license/metadata block.** Not validator-enforced, but every peer has it; omitting makes the skill look half-finished.

5. **Writing a skill that duplicates a peer.** Before creating, `ls skills/<category>/` and open 2-3 peers. Prefer extending an existing skill to creating a narrow sibling.

6. **Expecting the current session to see the new skill.** It won't. The skill loader is initialized at session start. Verify in a fresh session or via `skill_view` using the exact path.

7. **Linking to skills that don't exist in-repo.** `related_skills: [some-user-local-skill]` works for you but breaks for other clones. Prefer only in-repo links.

## Verification Checklist

- [ ] File is at `skills/<category>/<name>/SKILL.md` (not in `~/.hermes/skills/`)
- [ ] Frontmatter starts at byte 0 with `---`, closes with `\n---\n`
- [ ] `name`, `description`, `version`, `author`, `license`, `metadata.hermes.{tags, related_skills}` all present
- [ ] Name ≤ 64 chars, lowercase + hyphens
- [ ] Description ≤ 1024 chars and starts with "Use when ..."
- [ ] Total file ≤ 100,000 chars (aim for 8-15k)
- [ ] Structure: `# Title` → `## Overview` → `## When to Use` → body → `## Common Pitfalls` → `## Verification Checklist`
- [ ] `related_skills` references resolve in-repo (or are explicitly OK to be user-local)
- [ ] `git add skills/<category>/<name>/ && git commit` completed on the intended branch
