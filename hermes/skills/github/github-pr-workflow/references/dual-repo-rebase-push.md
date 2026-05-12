# Dual-repo rebase + push closeout

Use when a user asks to push coordinated frontend/backend branches, or to rebase one repo onto a target branch and another onto remote main.

## Sequence

1. In each repo, capture state first:

```bash
git status -sb
git log -3 --oneline
git branch --show-current
git remote -v
```

2. Detect in-progress operations before starting new ones:

```bash
test -d .git/rebase-merge && echo REBASE_MERGE
test -d .git/rebase-apply && echo REBASE_APPLY
git status
```

If a rebase is already in progress, resolve conflicts and `git rebase --continue`; do not start a second rebase.

3. For frontend branch rebased onto a named base:

```bash
git fetch origin --prune
git rebase origin/<base-branch>
# resolve conflicts if needed
git merge-base --is-ancestor origin/<base-branch> HEAD; echo $?
```

4. For backend branch rebased onto remote main:

```bash
git fetch origin --prune
git rebase origin/main
```

5. Run project-specific verification before push. For Java/Maven projects, verify `JAVA_HOME` if compiler/lombok errors appear; newer Homebrew Java can break older Lombok with javac `TypeTag :: UNKNOWN`, while installed LTS JDKs may pass.

6. Push rewritten branches only with lease protection:

```bash
git push --force-with-lease origin $(git branch --show-current)
```

7. Verify remote parity after push:

```bash
git fetch origin $(git branch --show-current) --prune
git status -sb
git rev-parse --short HEAD
git rev-parse --short @{u}
```

8. When creating PRs after a coordinated rebase, explicitly verify base/head direction before and after creation. If the user says “rebase corresponding branch” or names a target branch, the PR base is the target branch and the PR head is the rebased working branch:

```bash
BASE=<target-branch>        # e.g. feat/uvisa-2.0
HEAD=$(git branch --show-current)

git fetch origin --prune
git merge-base --is-ancestor origin/$BASE HEAD || {
  echo "HEAD is not rebased onto origin/$BASE" >&2
  exit 1
}

gh pr create --base "$BASE" --head "$HEAD" --title "..." --body "..."
gh pr view --json number,state,url,baseRefName,headRefName,mergeStateStatus,title --jq .
```

If a PR was created backwards, do not hand-wave it as acceptable. Close or supersede it, recreate with the correct base/head, and verify `baseRefName`/`headRefName`. If the mistaken PR was merged and GitHub deleted the intended base branch, restore the base branch from the correct pre-merge commit (only after verifying the desired commit), push it, then create the correct-direction PR.

## Pitfalls

- A plain `git status --short` can hide that HEAD is detached during an interactive rebase. Always check `git status -sb`, current branch, and `.git/rebase-*`.
- After a rebase, a branch may be both ahead and behind its upstream; this is expected until a `--force-with-lease` push succeeds.
- Do not use `--force` for shared branches; use `--force-with-lease` and then fetch/compare `HEAD` with `@{u}`.
- Inverted PRs are especially easy in release/feature integration flows. Always inspect `baseRefName` and `headRefName`; “mergeStateStatus: CLEAN” only means mergeability, not that the PR direction is correct.
- For multi-repo work, keep commits scoped per repo and report each repo's branch, HEAD, upstream parity, PR URL, base/head, and verification commands separately.
