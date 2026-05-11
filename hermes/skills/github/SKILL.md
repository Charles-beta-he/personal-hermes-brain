---
name: github
description: "Github workflow skill. See references/ for detailed guides."
license: MIT
---

# Github

> Github 相关的工作流 Skill

## 输入

- 用户请求的具体参数
- 相关上下文

## 输出

- 执行结果或生成的文件

## 约束

- 遵循项目规范
- 在 context budget 内完成

## 检查点

- [ ] 输入参数完整
- [ ] 输出符合预期

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

## 关联 Skill

- `pua`: 核心行为基线
- `loop`: 迭代管理


## 约束

- 遵循项目规范
- 在 context budget 内完成
