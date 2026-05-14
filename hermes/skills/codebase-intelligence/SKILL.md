---
name: codebase-intelligence
description: Use when analyzing codebase structure, before refactoring, assessing change impact, or extracting reference-architecture patterns from one codebase to improve another without direct integration.
version: 1.0.0
author: Hermes Agent
license: MIT
triggers:
- what imports this
- blast radius
- impact analysis
- dead code check
- call chain
- before modifying shared packages
metadata:
  hermes:
    tags:
    - codebase
    - analysis
    - blast-radius
    - imports
    related_skills:
    - source-driven-development
    - code-simplification
    - github-code-review
---

# codebase-intelligence

## Overview


Use `code-intel.py` — a pure Python stdlib tool that provides GitNexus-like analysis without npm dependencies.

## When to Use

- Analyzing codebase structure, before refactoring, or assessing change impact
- what imports this
- blast radius
- impact analysis
- dead code check
- call chain
- before modifying shared packages

## Quick reference

| Task | Command |
|------|---------|
| Hermes self-analysis | `python3 ~/.hermes/scripts/code-intel.py summary` |
| TS project import graph | `python3 ~/.hermes/scripts/code-intel.py import-graph --repo /path` |
| Blast radius | `python3 ~/.hermes/scripts/code-intel.py blast-radius --repo /path --file X` |
| Call chain (TS) | `python3 ~/.hermes/scripts/code-intel.py call-chain --repo /path --function F` |
| Python import deps | `python3 ~/.hermes/scripts/code-intel.py import-graph` |

## Capabilities

- **Python**: AST-based import/from analysis (stdlib ast module)
- **TypeScript/JavaScript**: Regex-based import/export/function detection
- **Monorepo-aware**: Resolves relative imports, package aliases
- **Zero dependencies**: Only Python stdlib
- **Fast**: 500 files in ~5s

## Known limitations

- TS/JS regex parser cannot resolve pnpm monorepo workspace aliases (e.g., `@tg/core`). Use `grep -rl "@tg/core"` as fallback.
- No tree-shaking analysis (dead exports within a file).
- No type-level dependency tracking (TypeScript interfaces/types).

## Linked reference
- `references/prototype-source-to-current-codebase-mapping.md` — how to convert a cloned prototype/demo repo plus current frontend/backend repos into durable project-profile navigation and domain landing maps.

## Workflow: before modifying a shared package

```
# 1. Know what you're touching
python3 code-intel.py blast-radius --repo . --file packages/core/src/crypto.js

# 2. Search for workspace alias references (monorepo)
grep -rl "@tg/core" apps/ --include="*.js" --include="*.jsx"

# 3. List all affected files
# 4. Run tests on affected packages only
# 5. Proceed with change
```

## Reference Architecture Gap Analysis

When the user wants to improve a target system based on another repo (not integrate it), follow `references/reference-architecture-gap-analysis.md`: set a non-integration boundary, extract class-level patterns, create a gap matrix, land target-system artifacts, and verify them. Do not claim live integration or feature parity unless explicitly implemented.

## Common Pitfalls

1. Loading this skill outside its trigger class and skipping a simpler, more direct path.
2. Ignoring prerequisites such as platform, credentials, installed commands, or linked reference files.
3. Treating the skill as a static memo instead of verifying the exact commands, artifacts, or outputs in the current environment.

## Verification Checklist

- [ ] The task actually matches this skill's trigger class and the current route is still appropriate.
- [ ] All prerequisites, linked references, templates, scripts, and required tools have been checked before execution.
- [ ] Claimed outputs, commands, files, or external side-effects were read back or otherwise verified before completion.

