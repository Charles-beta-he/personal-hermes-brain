# Multi-Model Root Cause Analysis with Theoretical Frameworks

When a user asks "why did the agent miss this" or "analyze the root cause of the architectural blind spot", use this pattern to diagnose systemic decision-making failures.

## 6 Theoretical Frameworks for Agent Cognitive Diagnosis

| # | Framework | Source | Key Concept | Application |
|---|-----------|--------|-------------|-------------|
| 1 | System 1 vs System 2 | Kahneman, Thinking Fast and Slow | Fast literal execution vs slow reflective analysis | Agent followed task description literally without architectural reflection |
| 2 | Leverage Points | Donella Meadows, Thinking in Systems | Parameters (low) → System structure (high) | Agent tweaked parameters (regex) instead of designing shared infrastructure |
| 3 | Tactical vs Strategic | Ousterhout, A Philosophy of Software Design | Quick fix vs deep module design | Agent made tactical one-off fix instead of strategic extraction |
| 4 | DRY / Orthogonality | Hunt/Thomas, The Pragmatic Programmer | Single source of truth, non-redundant | Agent allowed duplicated utilities across files |
| 5 | Code Smells | Fowler, Refactoring | Duplicated Code, Feature Envy, Shotgun Surgery | Agent didn't recognize duplicated validation patterns |
| 6 | Ubiquitous Language | Evans, Domain-Driven Design | Shared vocabulary across the codebase | Agent didn't treat validation as a project-level concept |

## Diagnosis Template

```
Root Cause Diagnosis
====================
Scenario: [describe what happened]
Agent behavior: [what the agent did wrong]
User correction: [what the user said]

Per-framework analysis:
1. Kahneman: [which system was used, what system was needed]
2. Meadows: [which leverage point was used, which was needed]
3. Ousterhout: [tactical vs strategic]
4. Pragmatic Programmer: [DRY violation]
5. Fowler: [code smell present]
6. Evans: [ubiquitous language gap]

Single root cause: [synthesize into one sentence]
Corrective action: [what the agent should do differently]
```

## Common Agent Failure Modes

### 1. Literal Task Following (System 1 dominance)
- **Signal**: Agent fixes exactly what the task describes, no more
- **Fix**: Add classify → scan → leverage-test gate before execution
- **User quote**: "有些对于项目属于基础设施或者常规限制，不能因为任务只说了一个地方就只改这一个地方"

### 2. Parameter Tweaking (Low leverage)
- **Signal**: Agent changes values/regex/config without changing structure
- **Fix**: Ask "will this fix recur if done locally?" — if yes, extract to infrastructure

### 3. Missing Infrastructure Scan
- **Signal**: Agent creates local utility when shared utility exists
- **Fix**: Before implementing, grep for existing shared infrastructure (`validators.ts`, `utils.ts`, etc.)

### 4. Duplicated Pattern Blindness
- **Signal**: Same function/logic exists in 2+ files, agent doesn't notice
- **Fix**: After finding a fix, search for similar patterns across the codebase

## When to Use

- User asks "why did you miss this?" or "analyze the root cause"
- User corrects the agent's approach scope (point fix → infrastructure)
- Agent discovers a systemic pattern that should be captured
- Post-mortem after a returned-for-improvement task
