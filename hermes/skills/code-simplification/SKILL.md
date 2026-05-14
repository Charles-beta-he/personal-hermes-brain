---
name: code-simplification
description: Use when simplifying working code for clarity, readability, or maintainability without changing behavior.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - code
    - refactoring
    - clarity
    - maintainability
    related_skills:
    - source-driven-development
    - incremental-implementation
    - test-driven-development
---

# code-simplification

## Overview


Simplify code by reducing complexity while preserving exact behavior. Goal: easier to read, understand, modify, debug.

## When to Use

- Simplifying working code for clarity, readability, or maintainability without changing behavior

## When NOT to use
- Code already clean — don't simplify for its own sake
- You don't understand the code yet — comprehend first
- Performance-critical code where simpler = slower
- About to rewrite entire module — don't polish throwaway code

## Five Principles

**1. Preserve Behavior Exactly**
Same inputs, outputs, side effects, errors, edge cases. All existing tests must pass unchanged.

**2. Follow Project Conventions**
Read CLAUDE.md. Match neighboring code patterns. Don't impose external style.

**3. Clarity Over Cleverness**
```
// BAD: Dense ternary chain
const label = isNew ? 'New' : isUpdated ? 'Updated' : 'Archived';

// GOOD: Readable
if (isNew) return 'New';
if (isUpdated) return 'Updated';
```

**4. Maintain Balance**
Don't over-simplify: inlining helpers that give concepts names; combining unrelated logic; optimizing for line count.

**5. Scope to What Changed**
Default to recently modified code. Avoid drive-by refactors.

## Chesterton's Fence
Before removing anything, understand why it exists. Check git blame. Ask: "Why was it written this way?"

## Process
1. Understand → git blame, read tests, trace callers
2. Identify → flag dense logic, long functions, unclear names
3. Simplify → one change at a time, test after each
4. Verify → all tests pass, behavior identical

## Anti-patterns (do NOT simplify)
- "Simplify by deleting error handling" — never
- "Simplify by removing comments" — only if code is self-documenting
- "Simplify by merging configs" — separation may be intentional

## Verification Checklist
- [ ] All existing tests pass without modification
- [ ] No behavior changes (input/output/side-effects identical)
- [ ] git diff shows only structural changes, no logic changes
- [ ] Follows project conventions (match neighboring code)

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

