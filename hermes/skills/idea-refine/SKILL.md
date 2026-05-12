---
name: idea-refine
description: Structured divergent/convergent thinking — turn vague ideas into concrete proposals before building anything.
triggers:
  - "I have an idea", "what if we", "should we build"
  - "explore options", "brainstorm", "weigh alternatives"
  - before starting any new feature or major change
model: strong (DeepSeek/Claude) — creative divergence benefits from reasoning
---

# idea-refine

Explore → Converge → Propose. Don't build the first idea that comes to mind.

## Phase 1: Diverge (generate options)

Generate 5+ distinct approaches. Each must be fundamentally different — not variations on the same theme.

| # | Approach | Novelty | Risk | Effort |
|---|----------|---------|------|--------|
| 1 | ... | high/med/low | high/med/low | S/M/L |
| ... | | | | |

Rules:
- No filtering during generation — write every idea
- At least one "extreme" option (simplest possible, most ambitious)
- At least one "orthogonal" option (different paradigm entirely)

## Phase 2: Converge (select best)

Pick 2 approaches with highest (value × feasibility / risk):

Scoring:
| Approach | Value (1-10) | Feasibility (1-10) | Risk (1-10) | Score |
|----------|-------------|-------------------|-------------|-------|
| 1 | | | | |

Score = Value × (1 - Risk/10) × Feasibility/10

## Phase 3: Proposal

For the top 2 approaches, write a 1-paragraph proposal:

```
APPROACH: <name>
WHAT: <1 sentence>
WHY: <why this beats alternatives>
COST: <rough effort in hours/days>
RISK: <biggest risk + mitigation>
FIRST STEP: <what to build first to validate>
```

## Anti-patterns
- "This is how we always do it" — kills divergence
- "That's impossible" — save for convergence phase
- Bikeshedding: naming/color debates during idea phase

## Verification
- [ ] 5+ distinct approaches generated
- [ ] At least 1 extreme + 1 orthogonal
- [ ] Scoring table filled for all
- [ ] Top 2 have concrete proposals with first steps
