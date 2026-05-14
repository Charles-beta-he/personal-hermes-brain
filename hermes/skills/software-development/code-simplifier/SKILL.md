---
name: code-simplifier
description: Use when you need guidance on merge duplicate logic and perform safe refactoring with risk assessment.
version: 1.0.0
author: Hermes Agent
license: MIT
triggers:
- merge duplicate code
- deduplicate this
- DRY this up
- these functions do the same thing
- copy-pasted logic
- refactor safely
- safe refactoring
- consolidate these
- extract shared function
- extract common logic
- after finding repeated patterns across modules
- when code review flags copy-paste
model: strong (DeepSeek) — refactoring decisions require deep reasoning
metadata:
  hermes:
    tags:
    - software
    - development
    - code
    - simplifier
    related_skills:
    - email
---

# code-simplifier

## Overview


Merge duplicate logic and perform safe refactoring with risk assessment.

## When to Use

- You need guidance on merge duplicate logic and perform safe refactoring with risk assessment
- merge duplicate code
- deduplicate this
- DRY this up
- these functions do the same thing
- copy-pasted logic
- refactor safely
- safe refactoring
- consolidate these
- extract shared function
- extract common logic
- after finding repeated patterns across modules
- when code review flags copy-paste

## When NOT to use
- Code has zero duplication — don't invent abstractions
- You don't understand the business context of both copies
- Duplications are coincidental (same shape, different intent)
- Performance-critical code where abstraction adds overhead
- Cross-repo shared libraries (version coupling is worse than duplication)

## Core Concept: The Three Zones

| Zone | Description | Action |
|------|-------------|--------|
| Exact Duplicates | Identical logic, same inputs/outputs | Always merge |
| Similar Logic | Same intent, minor variations | Merge carefully with parameterization |
| Coincidental Similarity | Same shape, different business meaning | Never merge — they will diverge |

## Risk Assessment Before Merging

Score each factor 1-5 before proceeding:

| Factor | Low Risk (1) | High Risk (5) |
|--------|-------------|----------------|
| Test Coverage | Both copies fully tested | No tests |
| Call Sites | 1-2 callers | 10+ callers across modules |
| Side Effects | Pure function | DB writes, API calls, file I/O |
| Domain Coupling | Generic utility | Business-logic specific |
| Abstraction Level | Same level | Merging different abstraction layers |
| Historical Stability | Stable for months | Changed recently, frequently |
| Type Safety | Strong types constrain inputs | Any/dynamic types |

Score < 15 → Safe to merge. 15-25 → Merge with caution + extra tests. > 25 → Don't merge.

## Decision Flowchart

```
Is it actually duplicate? (same intent, not just same shape)
  NO → STOP. Leave it alone.
  YES ↓
Are both copies well-tested?
  NO → Write tests first, then reconsider.
  YES ↓
Score the Risk Assessment (< 15 threshold)
  > 25 → STOP. Too risky.
  15-25 → Use Strangle Fig approach (feature flag migration).
  < 15 ↓
Extract shared function with clear name.
  ↓
Update all call sites (one at a time, test after each).
  ↓
Delete original copies.
  ↓
Run full test suite. Verify behavior identical.
```

## Process (6 Steps)

### Step 1: Identify Candidates
Search for:
- Exact string matches across files (`grep -rn "pattern" --include="*.ext"`)
- Functions with >60% structural similarity
- Import patterns that suggest copy-paste (same util imports in multiple files)
- Test files that test identical logic in different modules

### Step 2: Classify the Duplication
Ask: "If I change the business rule in Copy A, would Copy B also need to change?"
- YES → Same concept, merge candidate
- NO → Coincidental similarity, leave alone

### Step 3: Risk Assessment
Use the scoring table above. Document the score before proceeding.

### Step 4: Extract with Clear Naming
```python
# BEFORE: Two copies
def calculate_user_tax(user):
    if user.is_vip: return user.income * 0.1
    return user.income * 0.2

def calculate_company_tax(company):
    if company.is_vip: return company.revenue * 0.1
    return company.revenue * 0.2

# AFTER: Extracted with intent-revealing name
def calculate_tax_rate(entity):
    """Return tax rate based on VIP status."""
    return 0.1 if entity.is_vip else 0.2

def calculate_user_tax(user):
    return user.income * calculate_tax_rate(user)

def calculate_company_tax(company):
    return company.revenue * calculate_tax_rate(company)
```

### Step 5: Update Call Sites Incrementally
- Update one caller at a time
- Run tests after each update
- If a call site needs special handling, it may not be a true duplicate

### Step 6: Verify
- [ ] All tests pass without modification
- [ ] No behavior changes (input/output/side-effects identical)
- [ ] `git diff` shows only structural changes
- [ ] No new dependencies introduced
- [ ] Error contracts unchanged

## Safe Extraction Techniques

### Extract Function
1. Identify the duplicated block
2. Define inputs (parameters) and outputs (return value)
3. Name the function for its intent, not its implementation
4. Replace original block with function call
5. Test

### Parameterize Variations
```python
# Two copies that differ by one value
def send_email_alert(msg): notify(msg, channel="email")
def send_slack_alert(msg): notify(msg, channel="slack")

# Merge:
def send_alert(msg, channel): notify(msg, channel=channel)
```

### Strangle Fig (for risky merges)
1. Create new shared function alongside originals
2. Add feature flag: `use_shared = False`
3. Route one caller at a time to shared function
4. Verify in production
5. When all callers migrated, delete originals and flag

## Common Pitfalls
1. **Premature Abstraction (Rule of Three)**: Don't extract until you've seen the pattern 3 times. Two occurrences might be coincidence.

2. **Boolean Flag Soup**: Merging N functions by adding N boolean params creates a megfunction that's harder to read than the originals.

3. **Wrong Abstraction Level**: Merging a low-level utility with a high-level business function creates a confusing API.

4. **Ignoring Error Contracts**: If Copy A throws ValueError and Copy B returns None, merging them changes behavior for one caller.

5. **Cross-Module Coupling**: Creating a shared module that both A and B depend on adds a coupling point. Worth it only if the shared logic is genuinely reusable.

6. **Deleting Too Soon**: Keep the old code as comments or in a separate commit for easy rollback. Don't delete until the new code has been verified in production.

7. **Over-Generalizing**: The shared function handles 3 cases now but you parameterize it for 10 "just in case." YAGNI.

## Verification Checklist

After any merge:
- [ ] Original tests still pass
- [ ] New tests cover the shared function directly
- [ ] All call sites produce identical output for same input
- [ ] Error handling preserved at each call site
- [ ] No new dependencies added
- [ ] Code is more readable, not just shorter
- [ ] `git blame` history preserved where possible
- [ ] Team reviewed the abstraction boundary
