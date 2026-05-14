---
name: diagramming
description: Use when you need the Diagramming workflow umbrella. See references/
  for detailed guides.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - diagramming
    - diagram
    - umbrella
    - routing
    related_skills:
    - loop
    - pua
---

# Diagramming

## Overview

This umbrella skill is the routing surface for diagramming. Use it to choose the most specific child skill, reference, or workflow instead of treating the category name as a one-size-fits-all procedure.

## When to Use

- You need help somewhere inside diagramming and want the quickest route to the right child skill.
- You are not yet sure which diagramming sub-workflow best matches the request.
- You want a compact map of the diagramming skill family before loading a more specific procedure.
- Don't use for: a request that already clearly matches one specific diagramming child skill; load that child skill directly.

## Routing Guide

- No child skills were discovered automatically; inspect linked references and neighboring skills before acting.

## Selection Rules

- Prefer the narrowest child skill that matches the user request, platform, and desired artifact.
- Stay at the umbrella level only for routing, taxonomy, or category-wide orientation.
- If the request spans multiple subskills, use this umbrella to map the lane first, then hand off to the specific workflow that will do the real work.

## Common Pitfalls

1. Using the diagramming umbrella as the full procedure even though a more specific child skill already fits.
2. Reading the routing map but never loading the referenced child skill or support material that contains the actual execution steps.
3. Choosing a child skill without checking that its platform, tools, and expected artifacts match the current task.

## Verification Checklist

- [ ] The request was mapped to the best-fitting child skill or explicitly kept at umbrella level for routing only.
- [ ] The selected child skill descriptions, references, and prerequisites were checked before substantive execution.
- [ ] Any claimed handoff, output, or route decision was read back against the specific child workflow before completion.



## 输入

- 用户请求的具体参数

## 约束

- 遵循项目规范
- 在 context budget 内完成

## 检查点

- [ ] 输入参数完整
- [ ] 输出符合预期格式
