---
name: github
description: Use when you need the Github workflow umbrella. See references/ for detailed
  guides.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags:
    - github
    - workflow
    - umbrella
    - routing
    related_skills:
    - codebase-inspection
    - github-auth
    - github-code-review
    - github-issues
    - github-pr-workflow
    - github-repo-management
---

# Github

## Overview

This umbrella skill is the routing surface for github. Use it to choose the most specific child skill, reference, or workflow instead of treating the category name as a one-size-fits-all procedure.

## When to Use

- You need help somewhere inside github and want the quickest route to the right child skill.
- You are not yet sure which github sub-workflow best matches the request.
- You want a compact map of the github skill family before loading a more specific procedure.
- Don't use for: a request that already clearly matches one specific github child skill; load that child skill directly.

## Routing Guide

- `codebase-inspection` — asked to check lines of code, repo size, language composition, or codebase stats.
- `github-auth` — you need guidance on set up GitHub authentication for the agent using git (universally available) or the gh CLI.
- `github-code-review` — you need to review code changes by analyzing git diffs, leaving inline comments on PRs, and performing thorough pre-push review.
- `github-issues` — you need guidance on create, manage, triage, and close GitHub issues.
- `github-pr-workflow` — you need guidance on full pull request lifecycle — create branches, commit changes, open PRs, monitor CI status, auto-fix failures, and merge.
- `github-repo-management` — you need guidance on clone, create, fork, configure, and manage GitHub repositories.

## Selection Rules

- Prefer the narrowest child skill that matches the user request, platform, and desired artifact.
- Stay at the umbrella level only for routing, taxonomy, or category-wide orientation.
- If the request spans multiple subskills, use this umbrella to map the lane first, then hand off to the specific workflow that will do the real work.

## Upstream Sync with Local WIP

When the user says to save code and pull latest, especially because others changed the online branch:

1. Inspect first: `git status --short && git branch --show-current && git remote -v && git log -3 --oneline`.
2. If the worktree is dirty, make a local WIP/safety commit before pulling. Use explicit pathspecs for task files rather than `git add -A` in dirty repos, then run `git diff --cached --check`.
3. Fetch/prune and inspect divergence: `git fetch origin --prune`, `git branch -vv`.
4. Prefer `git pull --rebase origin <branch>` for this user's workflow: local commits are preservation points; do not push unless explicitly asked.
5. On conflicts, preserve upstream/online behavior when it represents newer deployed product contract, then re-apply local safety/guard logic without reverting the online change. Example: if upstream changed login from phone to email OTP, keep email flow and merge only the payment-PIN gate.
6. After rebase, verify: `git diff --check`, search for conflict markers, run project tests and build, then report clean/ahead/behind state.
7. If the user explicitly says “rebase/sync origin/main, do not merge to main and do not push”, keep the current feature branch checked out, run `git rebase origin/main`, resolve conflicts there, and stop after local verification. Do not fast-forward local `main`, do not merge the feature branch into `main`, and do not push.
8. For conflict resolution during rebase, preserve upstream/main behavior when it contains newer deployed product contracts, then layer the feature branch’s narrow additions back in. Example pattern: in a Spring Security whitelist conflict, keep all upstream permit rules and add only the feature branch’s missing endpoint(s), rather than replacing the upstream block.
9. When Maven/Java verification fails after upstream sync, check `mvn -v` before treating it as code failure. Very new JDKs can break annotation processors; for uvisa-backend use JDK 21 (`JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home`) when JDK 25 reports Lombok/javac errors such as `TypeTag :: UNKNOWN`.
10. **Corrupted git ref pitfall**: If `git pull --rebase` fails with `bad object refs/remotes/origin/<branch>` or `cannot lock ref ... Resource deadlock avoided`, there's a corrupted ref file in `.git/refs/remotes/origin/`. Fix: `rm -f` the bad file → `git remote prune origin` → `git fetch origin` → retry. See `references/rebase-conflict-resolution.md` for details.
11. **Non-interactive rebase**: In agent/headless environments, `GIT_EDITOR="true" git rebase --continue` avoids the dumb-terminal editor prompt.
12. **Batch conflict resolution**: When 4+ files have conflicts, write a Python script to resolve them all at once rather than editing each file manually. See `references/rebase-conflict-resolution.md` for the pattern.

## References

- `references/rebase-conflict-resolution.md` — batch conflict resolution, corrupted ref fixes, non-interactive rebase, complementary-change merge strategy.

## Common Pitfalls

1. Using the github umbrella as the full procedure even though a more specific child skill already fits.
2. Reading the routing map but never loading the referenced child skill or support material that contains the actual execution steps.
3. Choosing a child skill without checking that its platform, tools, and expected artifacts match the current task.

## Verification Checklist

- [ ] The request was mapped to the best-fitting child skill or explicitly kept at umbrella level for routing only.
- [ ] The selected child skill descriptions, references, and prerequisites were checked before substantive execution.
- [ ] Any claimed handoff, output, or route decision was read back against the specific child workflow before completion.



## 输入

- 用户请求的具体参数

## 约束

- 遵循项目规范
- 在 context budget 内完成

## 检查点

- [ ] 输入参数完整
- [ ] 输出符合预期格式
