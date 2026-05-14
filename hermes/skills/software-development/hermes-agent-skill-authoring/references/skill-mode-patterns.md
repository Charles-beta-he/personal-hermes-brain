# Skill Mode Patterns

Use this reference when deciding the internal control-flow shape of a SKILL.md. The frontmatter remains the shared routing contract; mode selection changes the body organization, not the trigger mechanism.

## Shared Contract

Keep the common routing skeleton stable:

- `name`: canonical skill identifier
- `description`: primary trigger surface; should say when the skill loads
- `level`: routing/positioning field when the surrounding library uses it
- `requires`: prerequisite skills, capabilities, or supporting context when the surrounding library uses it

Do not treat mode choice as a replacement for frontmatter. Mode is the internal execution shape after the skill has been selected.

## Five Modes

### Wrapper
- Flow: `SKILL.md -> reference -> agent capability`
- Best for: complex SDKs, CLIs, APIs, operational surfaces
- Body cues: capability map, exact commands, parameter caveats, verification probes

### Generator
- Flow: `SKILL.md -> template + data -> output`
- Best for: stable deliverable formats such as reports, contracts, briefs, checklists
- Body cues: input schema, template slots, transformation rules, output examples

### Reviewer
- Flow: `input -> checklist -> graded report`
- Best for: quality gates, audits, static reviews, rule-based inspection
- Body cues: review dimensions, scoring/severity rubric, evidence requirements

### Inversion
- Flow: agent asks -> user answers -> agent synthesizes
- Best for: unclear requirements, missing context, discovery-oriented intake
- Body cues: interview sequence, branch questions, synthesis rules, stop conditions

### Pipeline
- Flow: forced ordered stages with checkpoints
- Best for: multi-step workflows where each stage must yield a verifiable artifact
- Body cues: stage I/O, gate checks, rollback/retry rules, no-skip discipline

## Selection Table

| Scenario | Prefer |
|----------|--------|
| Calling a complex SDK/API/toolchain | Wrapper |
| Fixed-format deliverable | Generator |
| Quality gate / static audit / review | Reviewer |
| Ambiguous request / missing context | Inversion |
| Multi-step workflow with verifiable artifacts | Pipeline |

## Authoring Rule

Pick one dominant mode first. Hybrid skills are allowed, but future readers should be able to identify the primary control-flow shape from the section layout and verification style within a few seconds.