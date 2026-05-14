---
name: post-deploy-verification
version: 1.0.0
author: Hermes Agent
license: MIT
alias: true
canonical: ~/.hermes/skills/software-development/post-deploy-verification/SKILL.md
note: 根层骨架 → 指向software-dev完整版
metadata:
  hermes:
    tags:
    - post
    - deploy
    - verification
    related_skills:
    - software-development
description: Use when this alias is invoked and the caller should be redirected to the canonical post-deploy-verification skill.
---

# post-deploy-verification

## Overview

This skill is an alias entry for post-deploy-verification. It exists to redirect the caller to the canonical implementation while preserving trigger compatibility, path discoverability, and read-back verification expectations.
## When to Use

- This alias was invoked and the canonical skill should be loaded instead.
- You need the canonical skill path before continuing work.
- Don't use for: substantive execution on the alias alone; load or edit the canonical skill before doing real work.
## Alias Target

- Canonical: `~/.hermes/skills/software-development/post-deploy-verification/SKILL.md`
- Note: 根层骨架 → 指向software-dev完整版

Run `skill_view('software-development/post-deploy-verification')` to load the full skill.

## Common Pitfalls

1. Editing the alias wrapper instead of the canonical skill.
2. Reporting success from the alias without first loading the canonical skill content.
3. Letting alias and canonical trigger semantics drift apart.

## Verification Checklist

- [ ] The alias path and canonical path both resolve to the intended skill.
- [ ] The canonical skill was loaded before taking substantive action.
- [ ] Any edits were applied to the canonical skill, not just the alias wrapper.
