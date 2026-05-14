---
name: devops
description: Use when you need the Devops workflow umbrella. See references/ for detailed
  guides.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - devops
    - workflow
    - umbrella
    - routing
    related_skills:
    - cloudflare-pages-pnpm
    - gateway-telegram-setup
    - hermes-storage-governance
    - kanban-orchestrator
    - kanban-worker
    - semantic-release-monorepo
---

# Devops

## Overview

This umbrella skill is the routing surface for devops. Use it to choose the most specific child skill, reference, or workflow instead of treating the category name as a one-size-fits-all procedure.

## When to Use

- You need help somewhere inside devops and want the quickest route to the right child skill.
- You are not yet sure which devops sub-workflow best matches the request.
- You want a compact map of the devops skill family before loading a more specific procedure.
- Don't use for: a request that already clearly matches one specific devops child skill; load that child skill directly.

## Routing Guide

- `cloudflare-pages-pnpm` — you need to deploy pnpm monorepo to Cloudflare Pages via GitHub Actions.
- `gateway-telegram-setup` — you need to debug and configure Hermes Gateway Telegram integration — config structure pitfalls, env var overrides, verbose verification, stale PID cleanup.
- `hermes-storage-governance` — Hermes 存储治理: state.db FTS 膨胀治理、会话 TTL、快照清理、自动 cron。防止多模型运行导致磁盘膨胀。.
- `kanban-orchestrator` — you need guidance on decomposition playbook + specialist-roster conventions + anti-temptation rules for an orchestrator profile routing work through Kanban.
- `kanban-worker` — you need guidance on pitfalls, examples, and edge cases for Hermes Kanban workers.
- `semantic-release-monorepo` — you need guidance on configure semantic-release for pnpm monorepo with GitHub Actions.
- `token-saver-rtk` — the task falls under Token Saver: 全架构优化 (17层).
- `webhook-subscriptions` — the user wants external services to trigger agent runs OR push notifications to chats.

## Selection Rules

- Prefer the narrowest child skill that matches the user request, platform, and desired artifact.
- Stay at the umbrella level only for routing, taxonomy, or category-wide orientation.
- If the request spans multiple subskills, use this umbrella to map the lane first, then hand off to the specific workflow that will do the real work.

## Common Pitfalls

1. Using the devops umbrella as the full procedure even though a more specific child skill already fits.
2. Reading the routing map but never loading the referenced child skill or support material that contains the actual execution steps.
3. Choosing a child skill without checking that its platform, tools, and expected artifacts match the current task.

## Verification Checklist

- [ ] The request was mapped to the best-fitting child skill or explicitly kept at umbrella level for routing only.
- [ ] The selected child skill descriptions, references, and prerequisites were checked before substantive execution.
- [ ] Any claimed handoff, output, or route decision was read back against the specific child workflow before completion.

