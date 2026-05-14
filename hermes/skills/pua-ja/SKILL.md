---
name: pua-ja
version: 1.0.0
author: Hermes Agent
license: MIT
alias: true
canonical: ~/.hermes/skills/pua/codex/pua-ja/SKILL.md
note: 根层 → 指向codex规范版
metadata:
  hermes:
    tags:
    - pua
    - ja
    related_skills:
    - codex
    - pua
description: Use when this alias is invoked and the caller should be redirected to the canonical pua-ja skill.
---

# pua-ja

## Overview

This file is an alias wrapper that redirects callers to the canonical skill implementation.

## When to Use

- This alias was invoked and the canonical skill should be loaded instead.
- You need the canonical skill path before continuing work.

## Alias Target

- Canonical: `~/.hermes/skills/pua/codex/pua-ja/SKILL.md`
- Note: 根层 → 指向codex规范版

Run `skill_view('pua/codex/pua-ja')` to load the full skill.

## Common Pitfalls

1. Editing the alias wrapper instead of the canonical skill.
2. Reporting success from the alias without first loading the canonical skill content.
3. Letting alias and canonical trigger semantics drift apart.

## Verification Checklist

- [ ] The alias path and canonical path both resolve to the intended skill.
- [ ] The canonical skill was loaded before taking substantive action.
- [ ] Any edits were applied to the canonical skill, not just the alias wrapper.
