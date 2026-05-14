---
name: multi-model-agent-orchestration
description: Use when you need guidance on multi-model agent orchestration patterns inspired by rowboatlabs/rowboat — event-sourced runs, agent-as-sub-flow, model-per-agent, lazy skill loading, knowledge graph pipeline, and context injection.
version: 1.0.0
author: Hermes Agent
license: MIT
triggers:
- multi-agent orchestration
- event sourcing agent
- model per agent
- knowledge graph pipeline
- sub-flow delegation
- rowboat patterns
metadata:
  hermes:
    tags:
    - software
    - development
    - multi
    - model
    - agent
    related_skills:
    - email
    - loop
    - sketch
---

# Multi-Model Agent Orchestration Patterns

## Overview


Inspired by rowboatlabs/rowboat (YC S24) — an open-source AI coworker with sophisticated multi-model, multi-agent architecture.

## When to Use

- Designing agent systems with multiple specialized agents
- Building event-sourced conversation systems
- Implementing model-per-agent strategies
- Creating knowledge graph pipelines from unstructured data
- Don't use for: requests that do not need you need guidance on multi-model agent orchestration patterns inspired by rowboatlabs/rowboat — event-sourced runs, agent-as-sub-flow, model-per-agent, lazy skill loading, knowledge graph pipeline, and context injection; choose a more specific child skill or a broader routing skill that actually matches the task.
## Core Patterns

### 1. Event-Sourced Run System

Every agent interaction (message, tool call, tool result, stream event) is logged as an event. Runs are stored as JSONL for persistence and replay. AgentState is reconstructed by replaying the event log.

**Hermes adaptation**: Use session transcripts as event logs. Add structured event types for tool calls, delegations, and model switches. Enable replay for debugging failed sessions.

**Implementation sketch**:
```python
# Event types: message, tool_call, tool_result, model_switch, delegation, error
class AgentEvent:
    timestamp: datetime
    event_type: str
    payload: dict
    run_id: str
    parent_event_id: Optional[str]  # for sub-flow nesting

class EventLog:
    def append(self, event: AgentEvent): ...
    def replay(self, run_id: str) -> AgentState: ...
    def query(self, run_id: str, event_type: str) -> List[AgentEvent]: ...
```

### 2. Agent-as-Sub-Flow (Hierarchical Delegation)

When an agent tool is invoked, it spawns a sub-flow — the sub-agent runs its own full streaming loop with its own messages and tool calls. Sub-flow events are nested with a `subflow: [toolCallId, ...]` path for hierarchical tracking.

**Hermes current**: delegate_task spawns children with max_spawn_depth=1, no hierarchical event tracking.

**Improvement**: Add sub-flow path tracking to delegation events:
```python
# In delegate_tool.py, add subflow_path to child context
subflow_path = parent_context.get("subflow_path", []) + [tool_call_id]
child_context = {**parent_context, "subflow_path": subflow_path}
```

### 3. Model-per-Agent Configuration

Different agent types use different default models:
- Main copilot: strongest model (gpt-5.4, claude-opus)
- Background processors: cheap/fast models (gemini-flash, claude-haiku)
- Knowledge extraction: lightweight models (flash-lite)
- Each agent can override via YAML frontmatter

**Hermes current**: Auxiliary models for specific tasks (vision, compression, etc.), but delegated tasks inherit parent's model.

**Improvement**: Add `model` field to skill frontmatter for task-appropriate model selection:
```yaml
---
name: quick-label
model: gemini-2.5-flash  # cheap model for simple classification
---
```

### 4. Lazy Skill Loading

Skills are loaded on-demand via a `loadSkill` builtin tool. The copilot has a skill catalog it references; when intent matches a skill, it loads the skill's instructions into context. Keeps main prompt small.

**Hermes current**: All skill metadata injected into system prompt at startup. Full skill loaded via skill_view() tool call.

**Already implemented well** — Hermes' progressive disclosure (metadata → full content → linked files) is a good pattern. The system prompt injection of all skill names/descriptions is necessary for the agent to know what exists.

### 5. Knowledge Graph Pipeline

Runs on a polling loop, processes files from multiple sources (email, meetings, voice), batches processing, builds entity extraction, creates/updates interconnected notes.

**Hermes adaptation**: Build a background knowledge graph from session transcripts:
```python
# Pipeline: session transcripts → entity extraction → knowledge notes
# Sources: session_search results, memory entries, skill usage patterns
# Entities: tools used, problems solved, user preferences, project contexts
# Storage: ~/.hermes/knowledge/ as markdown with backlinks
```

### 6. Context Injection per Turn

Each LLM turn injects: current date/time, memory notes, workspace directory, active context (what the user is working on).

**Hermes current**: Memory injected, working directory known, session context available.

**Improvement**: Add structured "active context" injection:
- Current task/kanban state
- Recent file changes
- Active background processes
- User's current project focus

### 7. Tool Permission System

Shell commands go through a blocklist check. Blocked commands trigger a permission request. User-approved commands added to session allowlist.

**Hermes current**: Auto-approve or manual approval per session. No blocklist.

**Improvement**: Add configurable command blocklist with per-session allowlist escalation.

### 8. Run-Level Locks and Abort Registry

Run-level locks prevent concurrent execution of the same run. Abort registry allows clean cancellation of runs and sub-flows via AbortSignal.

**Hermes current**: Task-level locks in kanban, session-level isolation. No abort propagation to sub-agents.

**Improvement**: Add abort signal propagation through delegation chain.

## Comparison Matrix

| Feature | Rowboat | Hermes | Gap |
|---------|---------|--------|-----|
| Event sourcing | JSONL event log | SQLite sessions | Add structured events |
| Sub-flow tracking | Hierarchical path | Flat delegation | Add path tracking |
| Model per agent | YAML frontmatter | Auxiliary models only | Add to skills |
| Lazy skill loading | loadSkill tool | skill_view tool | Already good |
| Knowledge graph | Background pipeline | Memory + session_search | Add KG pipeline |
| Context injection | Per-turn structured | Per-turn memory | Add active context |
| Tool permissions | Blocklist + allowlist | Approval mode | Add blocklist |
| Abort propagation | AbortSignal chain | None | Add propagation |

## Key Takeaways for Hermes

1. **Event sourcing is valuable for debugging** — structured event logs enable replay and analysis of complex multi-agent interactions
2. **Model-per-agent saves cost** — not every task needs the strongest model; classify task complexity and route accordingly
3. **Hierarchical sub-flow tracking** — when debugging delegation chains, knowing the parent-child relationship is essential
4. **Knowledge graphs compound** — extracting entities from conversations builds long-term organizational memory
5. **Abort propagation** — when a parent task is cancelled, all children should be notified

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

