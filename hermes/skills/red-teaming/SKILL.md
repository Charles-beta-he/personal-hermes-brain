---
name: red-teaming
description: Use when you need the Red Teaming workflow umbrella. See references/
  for detailed guides.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - red
    - teaming
    - umbrella
    - routing
    related_skills:
    - pua
---

# Red Teaming

## Overview

This umbrella skill is the routing surface for red teaming. Use it to choose the most specific child skill, reference, or workflow instead of treating the category name as a one-size-fits-all procedure.

## When to Use

- You need help somewhere inside red teaming and want the quickest route to the right child skill.
- You are not yet sure which red teaming sub-workflow best matches the request.
- You want a compact map of the red teaming skill family before loading a more specific procedure.
- Don't use for: a request that already clearly matches one specific red teaming child skill; load that child skill directly.

## Routing Guide

- No child skills were discovered automatically; inspect linked references and neighboring skills before acting.

## Selection Rules

- Prefer the narrowest child skill that matches the user request, platform, and desired artifact.
- Stay at the umbrella level only for routing, taxonomy, or category-wide orientation.
- If the request spans multiple subskills, use this umbrella to map the lane first, then hand off to the specific workflow that will do the real work.

## Security step-up / trusted-device audit pattern

When auditing trusted-device, remembered-browser, MFA/PIN step-up, or device/session persistence flows:

1. Trace the complete route from primary auth success → token/store normalization → route decision → step-up verification endpoint.
2. Classify every trust input by authority: server response for the current login, backend persisted device row, client cache, UI overlay, optimistic state.
3. Treat client-controlled persistence (`localStorage`, `sessionStorage`, IndexedDB, unsigned cookies, Zustand snapshots) as display-only. It must never be the fallback authority for skipping PIN/OTP/MFA/payment-password step-up.
4. Require fail-closed behavior: if the server trust field is missing, false, malformed, stale, or the trust PATCH failed, route to step-up.
5. On the backend, verify trust mutation filters by user + active/non-revoked device, checks zero-row update count, clears trust on revoke/logout-others, and writes an audit event.
6. Call out weak device binding separately: User-Agent hashes are identifiers, not authenticators; prefer server-issued opaque device secrets hashed server-side.

Reference: `references/client-controlled-trust.md` contains a focused checklist and verdict rules for client-controlled trusted-device bypass reviews.

## Common Pitfalls

1. Using the red teaming umbrella as the full procedure even though a more specific child skill already fits.
2. Reading the routing map but never loading the referenced child skill or support material that contains the actual execution steps.
3. Choosing a child skill without checking that its platform, tools, and expected artifacts match the current task.

## Verification Checklist

- [ ] The request was mapped to the best-fitting child skill or explicitly kept at umbrella level for routing only.
- [ ] The selected child skill descriptions, references, and prerequisites were checked before substantive execution.
- [ ] Any claimed handoff, output, or route decision was read back against the specific child workflow before completion.

