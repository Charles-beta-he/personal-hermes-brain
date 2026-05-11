---
name: documentation-and-adrs
description: Write Architecture Decision Records (ADRs) for significant technical choices. Self-documenting codebase that explains WHY, not just WHAT.
triggers:
  - "document this decision", "write an ADR"
  - after making a significant architectural choice
  - when someone asks "why did we build it this way?"
  - before merging a major refactor or new system
model: strong (DeepSeek/Claude) — ADRs require clear reasoning
---

# documentation-and-adrs

Code tells WHAT. ADRs tell WHY. Every non-obvious technical decision deserves a record.

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

## Verification
- [ ] ADR number is sequential (check existing ADRs)
- [ ] Context clearly describes the problem
- [ ] At least 2 alternatives evaluated
- [ ] Consequences section not empty
- [ ] Status is "proposed" (not "accepted" before review)
