---
name: idea-refine
description: Use when a vague idea needs structured exploration, comparison, and convergence before implementation.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - ideation
    - strategy
    - option-analysis
    - planning
    related_skills:
    - writing-plans
    - framework-audit
    - requirement-clarification
---

# idea-refine

## Overview

Explore → Converge → Propose. Don't build the first idea that comes to mind. In practice, load it when a vague idea needs structured exploration, comparison, and convergence before implementation. It defines the expected execution lane, scope boundaries, and verification shape for this class of work.
## When to Use

- A vague idea needs structured exploration, comparison, and convergence before implementation
- Don't use for: requests that do not need a vague idea needs structured exploration, comparison, and convergence before implementation; choose a more specific child skill or a broader routing skill that actually matches the task.
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

## Verification Checklist
- [ ] 5+ distinct approaches generated
- [ ] At least 1 extreme + 1 orthogonal
- [ ] Scoring table filled for all
- [ ] Top 2 have concrete proposals with first steps

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

