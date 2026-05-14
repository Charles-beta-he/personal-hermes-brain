# Hermes Prefix Cache Architecture

## Three-Tier System Prompt Split

Location: `run_agent.py` → `_build_system_prompt_parts()`

### Stable Tier (lines 5756-5884)
Cross-session byte-stable content. Eligible for 1h cache.
- SOUL.md identity or DEFAULT_AGENT_IDENTITY
- HERMES_AGENT_HELP_GUIDANCE
- Tool guidance (MEMORY, SESSION_SEARCH, SKILLS, KANBAN, COMPUTER_USE)
- TOOL_USE_ENFORCEMENT_GUIDANCE + model-family guidance
- **Skills prompt** (full listing, byte-stable)
- Platform hints

### Context Tier (lines 5886-5903)
Session-stable, may change between sessions.
- system_message parameter
- Context files (AGENTS.md, .cursorrules)
- **CASI filtered skills** (per-turn, injected here for cache safety)

### Volatile Tier (lines 5905-5937)
Changes per turn/session, never cached.
- Memory snapshot
- User profile
- External memory provider block
- Timestamp + metadata

## Cache Control (prompt_caching.py)

### Long-lived path (Anthropic):
- System block[0] (stable) → 1h TTL marker
- Last 2 non-system messages → 5m rolling TTL
- Tools[-1] → 1h TTL marker

### Non-long-lived path:
- 4 breakpoints: system[0] + last 3 messages, all 5m TTL

## CASI Integration Point
CASI must NOT modify stable tier (breaks byte-identity → cache miss).
Solution: inject filtered skills into context tier via `_casi_user_message` attribute.

## Verification
```python
# Test byte-identity: calling _build_system_prompt_parts twice
# with same inputs must produce identical stable tier
parts1 = agent._build_system_prompt_parts()
parts2 = agent._build_system_prompt_parts()
assert parts1['stable'] == parts2['stable'], "Cache bust detected!"
```

## Key Line Numbers (run_agent.py)
- 5730-5943: _build_system_prompt_parts()
- 5834-5850: Skills prompt injection into stable tier
- 5848-5878: CASI context tier injection
- 12370-12388: Long-lived cache block building
- 12410-12424: Cache control marker injection
