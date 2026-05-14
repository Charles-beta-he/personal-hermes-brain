---
name: incremental-implementation
description: Use when implementing a task in small verifiable slices instead of a single large change.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - implementation
    - slicing
    - testing
    - delivery
    related_skills:
    - test-driven-development
    - source-driven-development
    - writing-plans
---

# incremental-implementation

## Overview


One slice at a time. Each slice: build → test → ship (or stash as done). Never build the whole thing before testing anything.

## When to Use

- Implementing a task in small verifiable slices instead of a single large change
- Don't use for: requests that do not need implementing a task in small verifiable slices instead of a single large change; choose a more specific child skill or a broader routing skill that actually matches the task.
## Slice Rules

1. Each slice is independently verifiable (has its own test)
2. Each slice is < 50 LOC changed (if bigger, split)
3. Each slice touches only one concern (one function, one component)
4. Don't start slice N+1 until slice N passes all tests

## Process

```
FOR each slice:
  1. Build: implement minimal working version
  2. Test: run relevant tests + new test for this slice
  3. Verify: does it work end-to-end for this slice?
  4. Commit: atomic commit with slice description
  5. Next: only proceed if all tests green
```

## Slice Sizing

| Task Type | Ideal Slice Size |
|-----------|-----------------|
| Add endpoint | 1 route → 1 handler → 1 test |
| Add component | 1 component → 1 story → 1 test |
| Refactor | 1 function extracted → 1 test adjusted |
| Bug fix | 1 failing test → 1 fix → test passes |

## Anti-patterns
- Building the "framework" first with nothing working
- Waiting to test until "everything is done"
- Slice too large: "Implement user auth" is NOT a slice
- Skipping tests: "I'll add tests later" → never happens

## When a slice fails
1. Revert that slice only (git checkout -- <changed files>)
2. Don't touch other slices
3. Diagnose root cause before retrying

## Verification Checklist
- [ ] Each slice has its own commit
- [ ] git log shows incremental progression (not one mega-commit)
- [ ] All tests pass after every slice
- [ ] No slice touches more than one concern

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

