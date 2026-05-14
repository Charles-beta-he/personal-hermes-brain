# File-Based Planning Patterns — Concrete Examples

## Pattern 1: The Plan-Execute-Update Loop

The most fundamental pattern. Write the plan, execute each step, update after each.

### Before (fragile — lives only in context):
```
User: Build a REST API with auth, CRUD, and pagination
Agent: OK, here's my plan:
1. Set up project structure
2. Add auth middleware
3. Create user model
4. Add CRUD endpoints
5. Add pagination
6. Write tests
[context compresses after step 3]
Agent: Let me start by setting up the project structure... [redoing work]
```

### After (resilient — plan lives in file):
```
User: Build a REST API with auth, CRUD, and pagination
Agent: [writes plan to .hermes/plans/2026-05-11_rest-api.md]
Agent: [executes step 1, updates plan file]
Agent: [executes step 2, updates plan file]
Agent: [executes step 3, updates plan file]
[context compresses]
Agent: [reads plan file]
Agent: "I see I've completed steps 1-3. Continuing with step 4: CRUD endpoints."
```

## Pattern 2: Decision Log

When making architectural decisions, write them down with rationale.

### File: `docs/decisions/ADR-001-auth-strategy.md`
```markdown
# ADR-001: Authentication Strategy

**Status:** Accepted
**Date:** 2026-05-11
**Deciders:** User, Agent

## Context
Need to add authentication to the REST API.

## Decision
Use JWT tokens with refresh token rotation.

## Rationale
- Stateless — works with horizontal scaling
- Refresh rotation — mitigates token theft
- User explicitly requested JWT over session-based

## Alternatives Considered
- Session-based auth: Rejected — requires sticky sessions
- API keys: Rejected — no user-level granularity
```

## Pattern 3: Progress Tracker with File Manifest

Track not just what was done, but which files were touched.

### File: `.hermes/progress.md`
```markdown
# Progress — REST API Feature

## Completed
- ✅ Project setup — files: src/app.py, src/config.py, requirements.txt
- ✅ Auth middleware — files: src/auth/middleware.py, src/auth/jwt.py

## Current
- 🔄 User model — files: src/models/user.py (in progress)

## Files Changed (cumulative)
src/app.py
src/config.py
requirements.txt
src/auth/middleware.py
src/auth/jwt.py
src/models/user.py

## Key Constraints
- Must use PostgreSQL (user requirement)
- Password hashing with bcrypt (security requirement)
- JWT expiry: 15min access, 7day refresh (user preference)
```

## Pattern 4: Subagent Context Handoff

When delegating to subagents, give them file paths, not inline content.

### Bad (context-heavy):
```
delegate_task(goal="Implement the user model. Here's the plan: [500 words].
Here are the decisions: [200 words]. Here's what's been done: [300 words].")
```

### Good (file-referenced):
```
delegate_task(goal="Implement the user model.",
context="""
Plan: Read /tmp/hermes/plans/2026-05-11_rest-api.md
Decisions: Read /tmp/hermes/docs/decisions/ADR-001-auth-strategy.md
Progress: Read /tmp/hermes/progress.md
Current task: Step 3 — Create user model in src/models/user.py
""")
```

## Pattern 5: Checkpoint on Budget Warning

When approaching context limits, write a checkpoint before it's too late.

```python
# Pseudo-code for checkpoint logic
if tokens_used > TOKEN_THRESHOLD:
    write_checkpoint({
        "current_step": current_step,
        "completed": completed_steps,
        "files_changed": get_changed_files(),
        "key_context": extract_key_context()
    })
```

## Pattern 6: Cross-Session Resume

When a task spans multiple sessions, the plan file is the bridge.

### Session 1:
```
Agent: [writes plan, completes steps 1-3, updates plan file]
User: [session ends]
```

### Session 2 (new context, no memory of session 1):
```
Agent: [reads plan file]
Agent: "I see a plan for the REST API feature. Steps 1-3 are complete.
        Current step is 4: CRUD endpoints. Shall I continue?"
```

## Anti-Pattern: The Context-Only Plan

The most common failure mode. The plan exists only in the conversation context.

**Symptoms:**
- Agent repeats work after context compression
- Agent asks "what should I do next?" after doing 5 steps
- Agent contradicts earlier decisions
- User has to re-explain requirements

**Fix:** Write it down. Every time. No exceptions for "simple" tasks.