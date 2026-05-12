# Rebase Conflict Resolution — Practical Patterns

> Patterns for resolving git rebase conflicts efficiently, especially in agent/headless environments.

## Non-Interactive Rebase Continue

When `git rebase --continue` prompts for a commit message and the terminal is dumb (agent environment):

```bash
GIT_EDITOR="true" git rebase --continue
```

This uses `true` as the editor (exits 0 immediately), keeping the original commit message.

## Batch Multi-File Conflict Resolution with Python

When 4+ files have conflicts, writing a Python script is faster and less error-prone than manual editing per file:

```python
# Pattern: read file → string-replace conflict blocks → write file → verify
import subprocess

files_to_resolve = {
    'src/i18n/en.json': resolve_en_json,
    'src/i18n/zh.json': resolve_zh_json,
    'src/lib/api.ts': resolve_api_ts,
    'src/stores/auth.store.ts': resolve_auth_store,
}

for path, resolver in files_to_resolve.items():
    with open(path, 'r') as f:
        content = f.read()
    content = resolver(content)
    with open(path, 'w') as f:
        f.write(content)

# Verify no markers remain
result = subprocess.run(
    ['grep', '-rn', '<<<<<<'] + list(files_to_resolve.keys()),
    capture_output=True, text=True
)
if result.stdout:
    raise RuntimeError(f"Conflict markers remain:\n{result.stdout}")
```

## Corrupted Git Refs

Symptom: `bad object refs/remotes/origin/<branch>` or `cannot lock ref` with unexpected characters (spaces, trailing numbers).

Cause: A corrupted ref file in `.git/refs/remotes/origin/` — often from a failed fetch or a branch name with spaces that got partially written.

Fix:
```bash
# 1. Delete the corrupted ref file directly
rm -f ".git/refs/remotes/origin/feat/frontend-api-gap-analysis 2"

# 2. Prune stale refs
git remote prune origin

# 3. Re-fetch cleanly
git fetch origin
```

## Conflict Resolution Strategy: Complementary Changes

When both sides added different but complementary functionality (not competing alternatives):

- **Keep both imports** — if HEAD added `import type { InvestProduct }` and local added `import { CardNoCardState }`, include both.
- **Merge variable blocks** — if HEAD added wealth store hooks and local added card status hooks, include both.
- **Keep the more robust function** — if HEAD has a simple switch-case and local has regex-based normalization, keep the regex version but preserve any i18n keys the simple version referenced.

Rule of thumb: if the functions serve the same purpose but one is strictly more general, keep the general one and discard the narrow one. If they serve different purposes, keep both.

## Multi-Repo Push Coordination

When pushing frontend + backend repos together:

1. Check both repos' status in parallel (independent terminal calls).
2. If both need rebase, start both rebases in parallel — they're independent repos.
3. Resolve conflicts sequentially per repo (can't parallelize within a single rebase).
4. Push both after all rebases complete.

Expect both to have remote changes when the user says "push both" — they likely haven't pushed in a while.
