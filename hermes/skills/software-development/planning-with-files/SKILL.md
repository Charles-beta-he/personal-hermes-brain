---
name: planning-with-files
description: 'Use when a task is multi-step, may span context compressions, or needs cross-session persistence. Writes plans, progress, and decisions to files so they survive context window compression and session boundaries. Triggers: long task, complex plan, context getting full, cross-session work, delegation-heavy workflow.'
version: 1.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - planning
    - context-management
    - persistence
    - anti-loss
    - files
    related_skills:
    - plan
    - writing-plans
    - incremental-implementation
    - hermes-pipeline
    - note-taking
---

# Planning with Files — File-Based Planning & Context Compression Anti-Loss

## Overview

Planning with Files — File-Based Planning & Context Compression Anti-Loss workflow guidance. In practice, load it when a task is multi-step, may span context compressions, or needs cross-session persistence. Writes plans, progress, and decisions to files so they survive context window compression and session boundaries. Triggers: long task, complex plan, context getting full, cross-session work, delegation-heavy workflow. It defines the expected execution lane, scope boundaries, and verification shape for this class of work.
## When to Use

- Long task that may span multiple context compressions
- Complex plan with many steps (5+)
- Context window is getting full and you need to preserve state
- Cross-session work where progress must survive
- Delegation-heavy workflows where subagents need shared state
- Any task where losing track of what was done would be costly

**Don't use for:** single-step tasks, trivial lookups, information already in the codebase.

## The Problem

LLM context windows are finite. When they fill up, the ContextCompressor summarizes older content:

1. **Tool outputs pruned first** — read_file results replaced with 1-line summaries like `[read_file] read plan.md from line 1 (3,400 chars)`
2. **Middle turns summarized** — LLM generates structured summary with fields like Active Task, Completed Actions, Relevant Files, Key Decisions
3. **Head + tail protected** — system prompt + first 3 messages preserved; most recent ~10% of context window preserved

**What survives compression:**
| Content | Survival | Why |
|---------|----------|-----|
| Files on disk | 100% | Never touched by compressor |
| File paths in summary | ~95% | "Relevant Files" template field |
| Recent tool results | ~95% | Tail protection |
| Plan content in context | ~0% | Replaced by summary, but re-readable |
| Decision rationale | ~60% | "Key Decisions" summary field |

**The core insight:** Files are Layer 0 — immune to compression. Write state to files, use context as a cache.

## Step-by-Step Workflow

### Step 1: Write the Plan to File

Before executing ANY multi-step task, write the plan:

```
write_file(
    path=".hermes/plans/YYYY-MM-DD_HHMMSS-slug.md",
    content="""# [Feature Name] Plan

**Goal:** [One sentence]
**Status:** in_progress
**Created:** YYYY-MM-DD

## Steps
- [ ] Step 1: [description]
- [ ] Step 2: [description]
- [ ] Step 3: [description]

## Decisions
(none yet)

## Files Changed
(none yet)
"""
)
```

**Why:** The file survives compression. Context memory does not.

### Step 2: Register the Plan Path in Memory

Immediately after writing the plan:

```
memory(
    action="add",
    target="memory",
    content="Active plan: .hermes/plans/YYYY-MM-DD_HHMMSS-slug.md"
)
```

**Why:** Memory is injected into every future turn. Even after compression, the agent knows WHERE the plan is.

### Step 3: Execute Steps with Atomic Updates

For each step in the plan:

1. **Read** the plan file to confirm current position:
   ```
   read_file(path=".hermes/plans/YYYY-MM-DD_HHMMSS-slug.md")
   ```

2. **Execute** the step (your actual work).

3. **Update** the plan file immediately after completing:
   ```
   patch(
       path=".hermes/plans/YYYY-MM-DD_HHMMSS-slug.md",
       old_string="- [ ] Step 2: [description]",
       new_string="- [x] Step 2: [description] — done, files: src/foo.py, src/bar.py"
   )
   ```

4. **Update** the plan's Files Changed section if relevant.

**Why:** If compression fires between steps, the plan file has accurate progress.

### Step 4: Handle Compression / Resume

When you notice compression has occurred (summary prefix appears in context):

1. **Read the plan file first** — don't trust context memory
2. **Find the last incomplete step** — look for `- [ ]` markers
3. **Continue from there** — don't redo completed work

```
# After compression, ALWAYS:
read_file(path=".hermes/plans/YYYY-MM-DD_HHMMSS-slug.md")
# Then continue from the first unchecked step
```

### Step 5: Use /compress <plan-topic> for Protection

If context is getting full but you're mid-task:

```
/compress planning-with-files
```

This tells the compressor to prioritize preserving plan-related content in the summary.

### Step 6: Completion — Mark Done and Clean Up

When all steps complete:

1. Update plan status:
   ```
   patch(path="...", old_string="**Status:** in_progress", new_string="**Status:** done")
   ```

2. Clean up checkpoint files if any were created.

3. Optionally update memory to remove the active plan reference.

## File Structure Templates

### Plan File (`.hermes/plans/YYYY-MM-DD_HHMMSS-slug.md`)

```markdown
# [Feature Name] Plan

**Goal:** One sentence — what we're building
**Status:** in_progress | blocked | done
**Created:** 2026-05-13

## Steps
- [x] Step 1: Project setup — files: src/app.py, requirements.txt
- [ ] Step 2: Auth middleware — target: src/auth/middleware.py
- [ ] Step 3: User model — target: src/models/user.py

## Decisions
- **JWT over sessions:** User requested, works with horizontal scaling (2026-05-13)

## Files Changed
src/app.py, requirements.txt
```

### Progress File (`.hermes/progress.md`) — for very long tasks

```markdown
# Progress — [Task Name]

## Completed
- ✅ Step 1: [what] — files: [list]
- ✅ Step 2: [what] — files: [list]

## Current
- 🔄 Step 3: [what's in progress]

## Key Context
- [Fact that must survive compression]
- [Constraint agreed upon]
```

### Checkpoint File (`.hermes/checkpoints/task-id.json`) — for delegation handoff

```json
{
  "task_id": "...",
  "timestamp": "2026-05-13T...",
  "completed_steps": ["step1", "step2"],
  "remaining_steps": ["step3"],
  "files_changed": ["file1.py"],
  "key_decisions": {"decision1": "rationale"}
}
```

## Anti-Loss Strategies

### Write Before Act
Write the plan BEFORE executing. If compression fires mid-execution, the file already exists.

### Atomic Progress Updates
Update after EACH step, not batched. A compression could fire between steps.

### Compression-Resistant Format
- Goal in first 3 lines (compressor may truncate long files)
- Use checkboxes `[x]` / `[ ]` — machine-parseable
- Exact file paths, not descriptions ("src/config.py" not "the config file")
- Consistent structure across all plan files

### Context Injection on Resume
After compression, read the plan file FIRST. Don't try to reconstruct from summary.

### Delegation Context Handoff
Give subagents file paths, not inline content:
```
BAD:  delegate_task(goal="Implement user model. Here's the plan: [500 words]...")
GOOD: delegate_task(goal="Implement user model.", context="Plan: .hermes/plans/2026-05-13_api.md — do Step 3")
```

## Integration with Hermes Tools

| Tool | Use For | Persistent? |
|------|---------|-------------|
| `write_file` | Creating/updating plan and progress files | ✅ Yes |
| `read_file` | Loading plan state on resume | ✅ Yes |
| `todo` | Session-local step tracking | ❌ Session only |
| `memory` | Stable facts (NOT task state) | ✅ But compressed aggressively |
| `session_search` | Finding past session context | ✅ Yes |

**Key distinction:**
- `memory` = stable facts (user prefs, env info, plan PATH)
- `files` = task state (plans, progress, checkpoints)
- `todo` = session-local convenience (lost on session end)
- Never save WIP to memory — it gets compressed and becomes stale

## Context Compressor Mechanics (for understanding)

The compressor (`agent/context_compressor.py`) works in stages:

1. **Tool output pruning** — old read_file/terminal results replaced with 1-line summaries
2. **Head protection** — system prompt + first 3 messages preserved
3. **Tail protection** — most recent ~10% of context window preserved (token-budget based)
4. **LLM summarization** — middle turns compressed into structured summary with 13 fields
5. **Iterative updates** — subsequent compressions update the previous summary

**Relevant to planning:** The summary template includes:
- `## Relevant Files` — paths to files read/modified/created
- `## Completed Actions` — numbered list of what was done
- `## Active Task` — the user's most recent unfulfilled request
- `## Key Decisions` — technical decisions and WHY

This means: even if plan CONTENT is compressed away, the PATH survives in "Relevant Files", and the CURRENT STEP survives in "Active Task" / "In Progress".

## Common Pitfalls

### 1. Stale Plan Files
**Problem:** Plan says "Step 3 current" but you're on Step 5.
**Fix:** Update the plan file AFTER EVERY STEP. If you forget, the file is worse than useless.

### 2. Over-Writing
**Problem:** Writing every trivial detail creates noise.
**Fix:** Only write things costly to lose. If it takes < 30 seconds to redo, don't persist it.

### 3. Trusting Context Over Files
**Problem:** After compression, acting on stale context that contradicts the plan file.
**Fix:** Always re-read the file when resuming. File > context memory.

### 4. Path Proliferation
**Problem:** Plans scattered across multiple directories.
**Fix:** Convention: `.hermes/plans/` for agent plans, `docs/plans/` for human-readable plans.

### 5. Memory vs Files Confusion
**Problem:** Saving task progress to `memory` — it gets compressed and becomes stale.
**Fix:** `memory` = stable facts + file PATHS. `files` = task state. Never save step progress to memory.

### 6. Plan File Too Large
**Problem:** Plan file > 500 lines — read_file output also gets pruned by compressor.
**Fix:** Keep plan files under 200 lines. Split into plan + progress + checkpoint if needed.

### 7. Subagent Isolation
**Problem:** Subagent writes to a file, parent doesn't know.
**Fix:** Subagents return file paths in summary. Parent verifies files exist.

### 8. Forgetting to Re-Read After Compression
**Problem:** Compression fires, agent continues without re-reading plan, does redundant work.
**Fix:** Make "read plan file" the FIRST action after noticing compression. The SUMMARY_PREFIX marker makes compression detectable.
1. Skipping prerequisite checks and assuming the environment already matches the workflow.
2. Applying the workflow mechanically without confirming that the request still matches this skill's trigger class.
3. Reporting success before reading back the actual outputs, files, or external side-effects.
## Compression-Resistance Self-Check

Before considering a plan "done," verify:

1. **Goal in first 3 lines?** — Can you find it without scrolling?
2. **Current step marked?** — Is there a `- [ ]` marker for the active step?
3. **Completed steps listed?** — Can you see what's done?
4. **File paths exact?** — No "the config file" — use `src/config.py`
5. **Status field exists?** — in_progress / blocked / done

If any answer is "no," the plan won't survive compression well.

## Verification Checklist

- [ ] Plan file written to `.hermes/plans/` before execution begins
- [ ] Plan path registered in memory
- [ ] Each step updated in plan file immediately after completion
- [ ] File paths are exact (not descriptive)
- [ ] Plan file < 200 lines
- [ ] After compression: plan file re-read before continuing
- [ ] On completion: status marked "done", checkpoints cleaned up