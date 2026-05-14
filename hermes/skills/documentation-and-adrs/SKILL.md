---
name: documentation-and-adrs
description: Use when recording significant technical decisions, rationale, and consequences as Architecture Decision Records (ADRs).
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - documentation
    - adr
    - architecture
    - decision-records
    related_skills:
    - framework-audit
    - writing-plans
    - private-fork-evolution-governance
---

# documentation-and-adrs

## Overview


Code tells WHAT. ADRs tell WHY. Every non-obvious technical decision deserves a record.

## When to Use

- Recording significant technical decisions, rationale, and consequences as Architecture Decision Records (ADRs)

## ADR Template
```markdown
# ADR-{NNN}: {Title}

Date: YYYY-MM-DD
Status: proposed | accepted | deprecated | superseded by ADR-XXX

## Context
What is the problem we're solving? What constraints exist?

## Decision
What did we choose and why?

## Alternatives Considered
| Option | Pros | Cons | Why Rejected |
|--------|------|------|-------------|
| A | ... | ... | ... |
| B | ... | ... | ... |

## Consequences
What becomes easier? What becomes harder? What new risks exist?
```

## When to Write an ADR
- Choosing between frameworks/libraries (tRPC vs REST vs GraphQL)
- Major architectural pattern (monorepo structure, event sourcing)
- Data model decisions (normalized vs denormalized)
- Deprecation of a core system
- Security or compliance requirement that shapes architecture

## When NOT to Write an ADR
- Trivial choices (naming, formatting)
- Decisions that are immediately reversible with no migration cost
- Things already covered by project CLAUDE.md or AGENTS.md

## ADR Lifecycle
1. **proposed**: Written, under review
2. **accepted**: Approved and in effect
3. **deprecated**: No longer followed (link to replacement)
4. **superseded**: Replaced by newer ADR

Store in: `docs/adr/` or `.hermes/notes/adr/`

## Verification Checklist
- [ ] ADR number is sequential (check existing ADRs)
- [ ] Context clearly describes the problem
- [ ] At least 2 alternatives evaluated
- [ ] Consequences section not empty
- [ ] Status is "proposed" (not "accepted" before review)

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

