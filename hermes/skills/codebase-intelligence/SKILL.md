---
name: codebase-intelligence
description: Lightweight code intelligence for Hermes and external projects — import/export graphs, blast radius analysis, dead code detection. Covers Python and TypeScript without external dependencies. Use when analyzing codebase structure, before refactoring, or assessing change impact.
triggers:
  - what imports this
  - blast radius
  - impact analysis
  - dead code check
  - call chain
  - before modifying shared packages
---

# codebase-intelligence

Use `code-intel.py` — a pure Python stdlib tool that provides GitNexus-like analysis without npm dependencies.

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
