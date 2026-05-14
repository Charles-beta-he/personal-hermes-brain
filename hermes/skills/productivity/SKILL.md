---
name: productivity
description: Use when you need the Productivity workflow umbrella. See references/
  for detailed guides.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - productivity
    - workflow
    - umbrella
    - routing
    related_skills:
    - airtable
    - google-workspace
    - lark-docx-reading
    - linear
    - maps
    - nano-pdf
---

# Productivity

## Overview

This umbrella skill is the routing surface for productivity. Use it to choose the most specific child skill, reference, or workflow instead of treating the category name as a one-size-fits-all procedure.

## When to Use

- You need help somewhere inside productivity and want the quickest route to the right child skill.
- You are not yet sure which productivity sub-workflow best matches the request.
- You want a compact map of the productivity skill family before loading a more specific procedure.
- Don't use for: a request that already clearly matches one specific productivity child skill; load that child skill directly.

## Routing Guide

- `airtable` — you need guidance on airtable REST API via curl.
- `google-workspace` — you need guidance on gmail, Calendar, Drive, Contacts, Sheets, and Docs integration for Hermes.
- `lark-docx-reading` — reading Lark/Larksuite/Feishu Docx product documents for project analysis. Covers OpenAPI bot attempts, browser-login fallback via Chrome copy, redacted evidence artifacts, and mul....
- `linear` — you need to manage Linear issues, projects, and teams via the GraphQL API.
- `maps` — you need guidance on location intelligence — geocode a place, reverse-geocode coordinates, find nearby places (46 POI categories), driving/walking/cycling distance + time, turn-by-....
- `nano-pdf` — you need guidance on edit PDFs with natural-language instructions using the nano-pdf CLI.
- `notion` — you need guidance on notion API for creating and managing pages, databases, and blocks via curl.
- `ocr-and-documents` — you need guidance on extract text from PDFs and scanned documents.
- `powerpoint` — you need to use this skill any time a .pptx file is involved in any way — as input, output, or both.
- `teams-meeting-pipeline` — you need guidance on operate the Teams meeting summary pipeline via Hermes CLI — summarize meetings, inspect pipeline status, replay jobs, manage Microsoft Graph subscriptions.

## Selection Rules

- Prefer the narrowest child skill that matches the user request, platform, and desired artifact.
- Stay at the umbrella level only for routing, taxonomy, or category-wide orientation.
- If the request spans multiple subskills, use this umbrella to map the lane first, then hand off to the specific workflow that will do the real work.

## Common Pitfalls

1. Using the productivity umbrella as the full procedure even though a more specific child skill already fits.
2. Reading the routing map but never loading the referenced child skill or support material that contains the actual execution steps.
3. Choosing a child skill without checking that its platform, tools, and expected artifacts match the current task.

## Verification Checklist

- [ ] The request was mapped to the best-fitting child skill or explicitly kept at umbrella level for routing only.
- [ ] The selected child skill descriptions, references, and prerequisites were checked before substantive execution.
- [ ] Any claimed handoff, output, or route decision was read back against the specific child workflow before completion.

