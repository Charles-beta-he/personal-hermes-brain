---
name: code-simplification
description: Simplify code for clarity without changing behavior. Anti-complexity review — "would a new team member understand this faster than the original?"
triggers:
  - "simplify this", "clean this up", "refactor for clarity"
  - "this is too complex", "hard to read", "too clever"
  - after feature works but feels heavy
model: cheap (MiMo) for routine, strong (DeepSeek) for critical paths
---

# code-simplification

Simplify code by reducing complexity while preserving exact behavior. Goal: easier to read, understand, modify, debug.

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

## Verification
- [ ] All existing tests pass without modification
- [ ] No behavior changes (input/output/side-effects identical)
- [ ] git diff shows only structural changes, no logic changes
- [ ] Follows project conventions (match neighboring code)
