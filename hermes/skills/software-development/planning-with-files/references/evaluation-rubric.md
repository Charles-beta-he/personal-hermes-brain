# Compression-Resistance Evaluation Rubric

Use this rubric to evaluate whether a plan file will survive context compression.

## Scoring (each criterion 0-2 points)

### 1. Goal Clarity (Weight: 20%)
- **2 pts:** Goal is in the first 3 lines, one sentence, unambiguous
- **1 pt:** Goal exists but requires reading a paragraph to extract
- **0 pts:** No explicit goal, or goal is vague ("improve the system")

### 2. Current State Marking (Weight: 20%)
- **2 pts:** Current step marked with 🔄 or [CURRENT], easy to find
- **1 pt:** Current step inferrable from context but not explicitly marked
- **0 pts:** No indication of what's current vs. done vs. pending

### 3. Completed Work Log (Weight: 15%)
- **2 pts:** Each completed step listed with files changed
- **1 pt:** Steps listed but no file manifest
- **0 pts:** No record of completed work

### 4. Decision Rationale (Weight: 15%)
- **2 pts:** Key decisions recorded with "why" (not just "what")
- **1 pt:** Decisions recorded but rationale missing
- **0 pts:** No decision record

### 5. Path Specificity (Weight: 10%)
- **2 pts:** All file paths are exact and absolute/relative-resolvable
- **1 pt:** Some paths are exact, some are descriptive
- **0 pts:** Paths are descriptive only ("the config file")

### 6. Status Field (Weight: 10%)
- **2 pts:** Explicit status field (in_progress/blocked/done) with timestamp
- **1 pt:** Status inferrable from content
- **0 pts:** No status indication

### 7. Cross-References (Weight: 10%)
- **2 pts:** Links to related files (decisions, checkpoints, tests)
- **1 pt:** Some references exist
- **0 pts:** No cross-references

## Scoring Guide

| Score | Grade | Verdict |
|-------|-------|---------|
| 90-100% | A | Excellent — will survive multiple compressions |
| 80-89% | B | Good — minor details may be lost |
| 70-79% | C | Acceptable — some re-work likely |
| 60-69% | D | Risky — significant context will be lost |
| < 60% | F | Fail — plan will not survive compression |

## Quick Self-Check

Before considering a plan "done," ask:

1. If I read ONLY this file (no other context), could I continue the task?
2. If I read only the FIRST 10 LINES, would I know the status?
3. If a subagent read this file, could they pick up where I left off?

If any answer is "no," the plan needs improvement.

## Example: Before and After

### Before (Score: ~30%, Grade: F)
```markdown
Working on the API. Need to add auth and CRUD.
```

### After (Score: ~95%, Grade: A)
```markdown
# REST API Implementation Plan

**Goal:** Build a REST API with JWT auth, user CRUD, and pagination
**Status:** in_progress — 2026-05-11T14:30:00Z
**Current:** Step 3 — User model

## Progress
- ✅ Step 1: Project setup — src/app.py, src/config.py, requirements.txt
- ✅ Step 2: Auth middleware — src/auth/middleware.py, src/auth/jwt.py
- 🔄 Step 3: User model — src/models/user.py (in progress)
- ⬜ Step 4: CRUD endpoints
- ⬜ Step 5: Pagination
- ⬜ Step 6: Tests

## Decisions
- JWT over sessions: User requested, works with horizontal scaling (ADR-001)
- PostgreSQL: User requirement (no SQLite)
- bcrypt for passwords: Security standard

## Files Changed
src/app.py, src/config.py, requirements.txt, src/auth/middleware.py, src/auth/jwt.py

## Cross-References
- Decisions: docs/decisions/ADR-001-auth-strategy.md
- Checkpoint: .hermes/checkpoints/rest-api-2026-05-11.json
```