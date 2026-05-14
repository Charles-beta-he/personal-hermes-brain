---
name: autonomous-ai-agents
description: Use when you need the Autonomous Ai Agents workflow umbrella. See references/
  for detailed guides.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - autonomous
    - ai
    - agents
    - agent
    - umbrella
    - routing
    related_skills:
    - claude-code
    - codex
    - hermes-agent
    - hermes-pipeline
    - opencode
---

# Autonomous Ai Agents

## Overview

This umbrella skill is the routing surface for autonomous ai agents. Use it to choose the most specific child skill, reference, or workflow instead of treating the category name as a one-size-fits-all procedure.

## When to Use

- You need help somewhere inside autonomous ai agents and want the quickest route to the right child skill.
- You are not yet sure which autonomous ai agents sub-workflow best matches the request.
- You want a compact map of the autonomous ai agents skill family before loading a more specific procedure.
- Don't use for: a request that already clearly matches one specific autonomous ai agents child skill; load that child skill directly.

## Routing Guide

- `claude-code` — you need to delegate coding tasks to Claude Code (Anthropic's CLI agent).
- `codex` — you need to delegate coding tasks to OpenAI Codex CLI agent.
- `hermes-agent` — you need guidance on using and extending Hermes Agent — CLI usage, setup, configuration, spawning additional agents, gateway platforms, skills, voice, tools, profiles, and a concis....
- `hermes-pipeline` — you need to build automated task pipelines using hermes chat -q as execution engine.
- `opencode` — you need to delegate coding tasks to OpenCode CLI agent for feature implementation, refactoring, PR review, and long-running autonomous sessions.

## Selection Rules

- Prefer the narrowest child skill that matches the user request, platform, and desired artifact.
- Stay at the umbrella level only for routing, taxonomy, or category-wide orientation.
- If the request spans multiple subskills, use this umbrella to map the lane first, then hand off to the specific workflow that will do the real work.

## Common Pitfalls

1. Using the autonomous ai agents umbrella as the full procedure even though a more specific child skill already fits.
2. Reading the routing map but never loading the referenced child skill or support material that contains the actual execution steps.
3. Choosing a child skill without checking that its platform, tools, and expected artifacts match the current task.

## Verification Checklist

- [ ] The request was mapped to the best-fitting child skill or explicitly kept at umbrella level for routing only.
- [ ] The selected child skill descriptions, references, and prerequisites were checked before substantive execution.
- [ ] Any claimed handoff, output, or route decision was read back against the specific child workflow before completion.

