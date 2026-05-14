# Context Compression in LLM Agents — Technical Background

## What Is Context Compression?

LLM agents operate within a fixed context window (e.g., 128K tokens for Claude, 1M for Gemini). When conversation history exceeds this window, the system must reduce it through:

1. **Truncation** — Removing oldest messages entirely
2. **Summarization** — Replacing old messages with a condensed summary
3. **Sliding window** — Keeping only the N most recent messages

Each method loses information. The question is: what survives?

## What Gets Lost in Compression

| Content Type | Survival Rate | Notes |
|-------------|---------------|-------|
| Recent messages (last 5-10) | ~95% | Usually preserved verbatim |
| Early conversation context | ~20-40% | Summarized, details lost |
| Tool call results | ~10-30% | Often truncated first |
| File contents read into context | ~5% | Almost always lost |
| Decision rationale | ~15% | Rationale lost, decision may survive |
| Progress tracking (in-context) | ~10% | "I did X, Y, Z" becomes "I did some work" |
| Files on disk | 100% | Never lost by compression |

## The Anti-Loss Principle

**Anything you can't afford to lose must be in a file, not just in context.**

This is analogous to:
- Write-ahead logging in databases
- Checkpointing in distributed systems
- Saving game state before a boss fight

## Compression-Resistant File Formats

### High Resistance (survives well)
- Structured markdown with headers
- JSON with clear schema
- Checkboxes and status markers
- File paths and exact references

### Low Resistance (fragile)
- Prose paragraphs
- Inline code snippets without context
- Relative references ("the file we looked at earlier")
- Implicit state ("you know what I mean")

## Real-World Failure Modes

### Case 1: The Repeated Work
Agent plans 10 steps. After step 6, context compresses. Agent reads its own context and sees "I should do steps 1-10" but can't tell which are done. Redoes steps 1-6.

**Fix:** Write progress to `.hermes/progress.md` after each step.

### Case 2: The Lost Decision
Agent and user agree on a specific API design. Later, context compresses. Agent proposes a different design that contradicts the earlier decision.

**Fix:** Write decisions to `docs/decisions/` with rationale.

### Case 3: The Subagent Black Hole
Parent delegates to 3 subagents. Results come back as summaries. Parent tries to synthesize but the summaries lost critical details.

**Fix:** Have subagents write detailed results to files, return file paths.

### Case 4: The Memory Trap
Agent saves "task progress" to the memory tool. Memory gets compressed to "Working on auth feature." Next session, agent has no idea what step it was on.

**Fix:** Memory = stable facts only. Task state = files.

## Integration with Agent Architectures

### Single-Agent
```
Agent → writes plan to file → executes → updates file → context compresses → reads file → continues
```

### Multi-Agent (Orchestrator + Workers)
```
Orchestrator → writes plan to shared file
Worker 1 → reads plan, executes step, updates file
Worker 2 → reads plan, executes step, updates file
Orchestrator → reads updated plan, verifies progress
```

### Pipeline (Sequential Steps)
```
Step 1 → writes checkpoint to file
Step 2 → reads checkpoint, executes, writes new checkpoint
Step 3 → reads checkpoint, executes, writes final result
```

## References

- Anthropic's documentation on context window management
- LangChain's memory management patterns
- AutoGPT's file-based state management
- Claude Code's CLAUDE.md pattern (project context files)