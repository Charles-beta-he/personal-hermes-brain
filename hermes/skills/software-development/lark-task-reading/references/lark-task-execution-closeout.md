# Lark task execution closeout pattern

Use this when a Lark Task Center item is not only read but implemented and reported back.

## Why this exists

A common failure mode is to finish the code and deterministic verification, then spend the remaining tool/context budget on increasingly detailed documentation updates. That can leave the actual task unfinished because there is no scoped commit and no requested user/TG notification.

For Lark-assigned work, the user-visible delivery unit is:

`task selected -> implemented -> verified -> evidence summarized -> scoped commit -> notification/report`

Docs and ledgers support the delivery; they do not replace commit/report.

## Closeout sequence

After implementation and tests pass:

1. Create or update a concise evidence artifact.
   - Include task id/title, approach, changed files, commands, pass/fail result, residual risk.
   - Prefer a compact `/tmp/<project>-<task>-<date>.md` note when the task does not need a permanent ADR.
   - Do not store OTP values, tokens, screenshots with secrets, or disposable credentials in repo docs.

2. Minimal project ledger update.
   - Update the primary task/test ledger row that future maintainers will search.
   - Avoid broad rewrites or reordering historical evidence rows.
   - If a patch accidentally replaces historical evidence, restore it immediately before continuing.

3. Pre-commit sanity.
   ```bash
   git status --short
   git diff --check
   ```
   Add a targeted lint/test rerun only if docs/code changed after the last verification.

4. Scoped commit.
   ```bash
   git add <exact task files>
   git status --short -- <exact task files>
   git commit -m "fix(scope): concise task summary"
   git log -1 --oneline
   git status --short
   ```
   Never rely on `git add .` in a dirty worktree.

5. Remote package/deploy monitor for deployed projects.
   - For Railway-backed UVISA-style work, inspect the relevant service deployment/package/build after commit or deployment trigger.
   - Record terminal `success`/`healthy` status before calling the task fully closed.
   - If the remote build fails, is cancelled, times out, remains pending, or dashboard access is blocked, report `closed_with_remote_blocker` or `not_closed` with the latest safe evidence.
   - Use `references/remote-package-monitor-closeout.md` for the status vocabulary and redaction rules.

6. User/TG report.
   Report:
   - Lark task id/title.
   - Commit hash.
   - What changed.
   - Verification commands and results.
   - Remote package/deploy monitor result when applicable.
   - Any remaining risk or separately queued follow-up.

7. Continue loop.
   Move to the next visible/assigned Lark task only after the current task has commit/report closure, unless the user explicitly asked for a no-commit dry run.

## Budget rule

When context/tool-call budget is low, skip optional extra docs and close the delivery first:

`tests passed -> evidence note -> git diff --check -> commit -> remote package/deploy monitor -> notify`

If interrupted before commit or notify, the final answer must state:

- commit not done, or notification not sent;
- exact files currently modified;
- exact verification already passed;
- exact next commands to resume.

Do not say the Lark task is completed merely because tests/build passed.

### Long-runner / browser-auth budget pitfall

A recurring failure mode is to start a saved multi-model discussion in the background, then continue implementation, full tests, build, dev-server startup, and browser exploration until the session reaches its tool-call ceiling before commit/TG closeout. Avoid this by checking closeout budget before every expensive side lane:

- If `consult_models.py --discussion` is started, reserve tool calls to poll/read the tick artifact. Until `discussion_result.json` is read and passes, the status is `started/no_ratification_artifact` or advisory only.
- Do not start a fresh long T2/T3 discussion after deterministic gates pass if there is not enough budget left for commit and notification.
- If browser verification lands on login because `/notifications` or another task route is auth-protected, immediately choose one of two bounded paths: use the documented project test-login/OTP workflow to establish state, or mark browser UI acceptance as unfinished. Do not spend repeated clicks/probes on the login page unless those clicks are the documented login flow.
- For tasks with requested TG reporting, notification is a closeout gate. Reserve it before optional Workpad/ledger/UI polish.
- For deployed tasks, remote package/deploy monitoring is also a closeout gate. A public app smoke can be useful evidence, but dashboard/package status blocked by login must be labeled `access_blocked_needs_login`, not silently treated as success.
- If live Lark read/writeback fails with `TOKEN_EXPIRED` during closeout, treat OAuth recovery as its own budgeted gate: start `lark-mcp login --domain https://open.larksuite.com --port 3010 ...`, immediately open/authorize `http://localhost:3010/authorize`, then rerun the reader before writing back. Do not start OAuth recovery at the very end of a tool budget and then imply Lark closeout succeeded; report `lark_writeback_blocked_token_expired` if authorization cannot be completed and verified in-session.

Example: a notification-detail task had TDD, full tests, and build green, but got interrupted before reading the background multi-model verdict, completing auth-gated browser verification, committing, and TG notification. The correct final state is “implementation verified but closeout incomplete,” not “task done.”

## Auth/i18n bug-fix example pattern

For an auth verification-code localization task, a robust boundary is:

- Preserve backend machine-readable `code` at the API envelope adapter.
- Normalize only auth-domain OTP/code/rate-limit failures to i18n keys in the auth store/domain layer.
- Do not globally translate every API error.
- Do not translate only in screen toast components.
- Keep unknown backend business messages raw so customer-service/account-opening guidance is not lost.
- Test both response-body business failures and rejected axios error payloads.
