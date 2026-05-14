---
name: email
description: Use when you need the Email workflow umbrella. See references/ for detailed
  guides.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - email
    - workflow
    - umbrella
    - routing
    related_skills:
    - himalaya
---

# Email

## Overview

This umbrella skill is the routing surface for email. Use it to choose the most specific child skill, reference, or workflow instead of treating the category name as a one-size-fits-all procedure.

## When to Use

- You need help somewhere inside email and want the quickest route to the right child skill.
- You are not yet sure which email sub-workflow best matches the request.
- You want a compact map of the email skill family before loading a more specific procedure.
- Don't use for: a request that already clearly matches one specific email child skill; load that child skill directly.

## Routing Guide

- `himalaya` — you need guidance on cLI to manage emails via IMAP/SMTP.

## Selection Rules

- Prefer the narrowest child skill that matches the user request, platform, and desired artifact.
- Stay at the umbrella level only for routing, taxonomy, or category-wide orientation.
- If the request spans multiple subskills, use this umbrella to map the lane first, then hand off to the specific workflow that will do the real work.

## Common Pitfalls

1. Using the email umbrella as the full procedure even though a more specific child skill already fits.
2. Reading the routing map but never loading the referenced child skill or support material that contains the actual execution steps.
3. Choosing a child skill without checking that its platform, tools, and expected artifacts match the current task.

## Verification Checklist

- [ ] The request was mapped to the best-fitting child skill or explicitly kept at umbrella level for routing only.
- [ ] The selected child skill descriptions, references, and prerequisites were checked before substantive execution.
- [ ] Any claimed handoff, output, or route decision was read back against the specific child workflow before completion.

