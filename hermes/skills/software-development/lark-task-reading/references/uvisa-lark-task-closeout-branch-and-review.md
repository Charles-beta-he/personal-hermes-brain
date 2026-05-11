# UVISA Lark task closeout: branch, review, PR, Railway patterns

Session pattern extracted from UVISA Lark task loop work (remit recipient validation + SWIFT/CNH remark copy).

## Reusable lessons

1. Use one shared task-loop branch, but close each task as its own commit + PR.
   - Example branch shape: `lark/uvisa-2-task-loop-YYYYMMDD-HHMMSS`.
   - After a PR is merged into `feat/uvisa-2.0`, the local task branch may still point at the pre-merge task commit while `origin/feat/uvisa-2.0` has the merge commit.
   - Before starting the next task, fetch/sync or rebase onto `origin/feat/uvisa-2.0` so the next PR is based on the latest deployed frontend baseline.

2. For Railway frontend closeout, monitor the merge commit, not just the task commit.
   - Create PR from task branch to `feat/uvisa-2.0`.
   - Merge the PR.
   - Read the merge commit from `gh pr view <n> --json mergeCommit,mergedAt,state`.
   - Monitor Railway frontend service `uvisa-app-tRnN` for a deployment whose `meta.commitHash` equals that merge commit.
   - If no PR/merge exists and only the shared task-loop branch was pushed, still check Railway health, but do not claim latest-code deployment when Railway is tracking a different branch/commit. Use `closed_with_remote_blocker` until the task commit is merged/deployed.
   - Record safe evidence only: deployment id, branch, commit hash, status, timestamp. Do not log tokens/cookies.

3. Independent review diffs must include untracked/new test files.
   - `git diff -- path...` will not include untracked files.
   - Preferred: stage the intended task files first, run `git diff --cached --check`, then write `git diff --cached > /tmp/<task>.diff` for reviewer input.
   - If reviewing before staging, explicitly include untracked file contents or use `git add -N` for new files.
   - A reviewer pass on a diff missing the new test file is incomplete; rerun review on the staged diff.

4. For ambiguous Lark UI wording tasks, cover all plausible user-observed locations.
   - Example: a task asking to update SWIFT/CNH “备注栏下提示语” could refer to both the notice page (`topup.noticeRefDesc`) and the receiving-info Reference row (`topup.refHint`).
   - Prefer the minimal product change that updates both keys and add a regression test locking both locations.

5. Browser verification can use project-scoped test auth only for local acceptance.
   - Inject local auth state in the browser only as test-session setup; do not persist credentials/secrets in global memory/docs.
   - For copy/validation tasks, verify the exact DOM text and check browser console JS errors after the walkthrough.

## Closeout skeleton

```bash
# after deterministic tests/build/browser pass
git add <task files>
git diff --cached --check
git diff --cached > /tmp/uvisa-task-<id>-staged.diff
# run independent review on staged diff

git commit -m "fix(scope): concise task message"
git push

gh pr create --base feat/uvisa-2.0 --head <task-branch> --title "..." --body "..."
gh pr view <pr> --json number,state,mergeable,mergeStateStatus,statusCheckRollup,url,headRefOid
gh pr merge <pr> --merge --subject "Merge pull request #<pr> ..." --body "..."
gh pr view <pr> --json number,state,mergedAt,mergeCommit,url

# monitor Railway deployment for the merge commit hash
railway deployment list --service uvisa-app-tRnN --limit 5 --json
```

## Reporting

For “每完成一个任务 TG 通知我”, send TG only after commit/push/PR merge/frontend deploy monitor is terminal, unless reporting an explicit blocker. Include task id, summary, deterministic checks, browser evidence when relevant, independent review verdict, commit/PR/merge hash, Railway deployment id/status.
