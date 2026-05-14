---
name: apple
description: Use when you need the Apple workflow umbrella. See references/ for detailed
  guides.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - apple
    - workflow
    - umbrella
    - routing
    related_skills:
    - apple-notes
    - apple-reminders
    - findmy
    - imessage
    - macos-computer-use
---

# Apple

## Overview

This umbrella skill is the routing surface for apple. Use it to choose the most specific child skill, reference, or workflow instead of treating the category name as a one-size-fits-all procedure.

## When to Use

- You need help somewhere inside apple and want the quickest route to the right child skill.
- You are not yet sure which apple sub-workflow best matches the request.
- You want a compact map of the apple skill family before loading a more specific procedure.
- Don't use for: a request that already clearly matches one specific apple child skill; load that child skill directly.

## Routing Guide

- `apple-notes` — you need to manage Apple Notes via the memo CLI on macOS (create, view, search, edit).
- `apple-reminders` — you need to manage Apple Reminders via remindctl CLI (list, add, complete, delete).
- `findmy` — you need to track Apple devices and AirTags via FindMy.app on macOS using AppleScript and screen capture.
- `imessage` — you need to send and receive iMessages/SMS via the imsg CLI on macOS.
- `macos-computer-use` — you need to drive the macOS desktop in the background — screenshots, mouse, keyboard, scroll, drag — without stealing the user's cursor, keyboard focus, or Space.

## Selection Rules

- Prefer the narrowest child skill that matches the user request, platform, and desired artifact.
- Stay at the umbrella level only for routing, taxonomy, or category-wide orientation.
- If the request spans multiple subskills, use this umbrella to map the lane first, then hand off to the specific workflow that will do the real work.

## iCloud Documents organization

When organizing `~/Documents` after iCloud creates duplicate folders such as `文稿 - <Mac name>`, use `references/icloud-documents-safe-organization.md`: inventory first, protect local brain/Obsidian/app paths, move only low-risk loose files, write manifests, and delete low-value files only after explicit user approval.

## Desktop safe organization

When organizing `~/Desktop`, use `references/desktop-safe-organization.md`: inventory first, move top-level loose files into a dated organizer folder for the safe default; if the user explicitly asks for deep organization, preserve excluded folders and known workspaces, scan code-directory path dependencies before moving projects, write JSONL move manifests + rollback scripts, run rollback dry-run, set sensitive review folders to `0700`, and avoid full hashing of iCloud cloud-only/large files when it would stall.

## Common Pitfalls

1. Using the apple umbrella as the full procedure even though a more specific child skill already fits.
2. Reading the routing map but never loading the referenced child skill or support material that contains the actual execution steps.
3. Choosing a child skill without checking that its platform, tools, and expected artifacts match the current task.

## Verification Checklist

- [ ] The request was mapped to the best-fitting child skill or explicitly kept at umbrella level for routing only.
- [ ] The selected child skill descriptions, references, and prerequisites were checked before substantive execution.
- [ ] Any claimed handoff, output, or route decision was read back against the specific child workflow before completion.

