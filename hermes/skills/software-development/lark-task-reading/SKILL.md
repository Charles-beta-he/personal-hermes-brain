---
name: lark-task-reading
description: "Read Lark Task Center tasks for dispatch pipelines, fusing arc-dispatch and github-dispatch patterns: scoped task prioritization, comment/doc/image enrichment, routing, dry-run safety, and loop verification. Use when adding, debugging, or operating Lark task collection."
license: MIT
tags: [lark, feishu, task-center, dispatch, automation, workflow]
related_skills: [hermes-workflow-orchestrator, arc-dispatch-executor, multi-model-thinking, loop]
skill_tier: molecule
---

# Lark Task Reading

Use this skill when working on Lark/Feishu Task Center collection for `arc-dispatch`, `github-dispatch`, or any Hermes pipeline that does:

```
Lark Task Center -> collector -> envelope -> router -> confirmer/executor -> reporter
```

The goal is not to copy one project's code into another. The goal is to preserve the best reusable patterns from both projects in the Hermes skill tree so future Lark-task work starts from the same proven playbook.

## Default behavior

- Prefer tasks visibly under `UVISA-2.0新版开发`.
- If no UVISA-2.0 scoped tasks are visible in the fetched incomplete-task list, fall back to all incomplete tasks.
- Use `LARK_TASK_SCOPE_MODE=only` only when you want a hard filter.
- Use `LARK_TASK_SCOPE_MODE=off` to disable scope preference.
- Override scopes with comma-separated `LARK_TASK_PREFERRED_SCOPES`, e.g. `UVISA-2.0新版开发,OtherProject`.
- Preserve read-only collection during dry runs: no Lark comments, no status writes, no task mutation.

## Operational boundary: skill knowledge vs project runtime

A Hermes skill is a playbook, not an executable adapter. Loading this skill must not by itself imply that `arc-dispatch` or `github-dispatch` source files should be opened, imported, symlinked, or executed.

For user-facing requests such as "读取 Lark 任务", "看一下 UVISA-2.0 新版开发分类下关于我的任务", or "列出我的任务":

1. Treat the source of truth as the Lark/Feishu Task API or an explicitly configured Hermes-native helper.
2. Do **not** scan old Desktop/archive duplicates looking for `run.sh`, `collector.py`, `orchestrator.py`, `router.py`, or `lark_task_reader.py`.
3. Do **not** execute a project pipeline from a copied or archived path, especially paths under desktop cleanup folders.
4. Only inspect or run `arc-dispatch` / `github-dispatch` code when the user explicitly asks to debug, migrate, compare, or operate that dispatch project.

The project files are reference implementations for pattern extraction. Normal task reading should be read-only and should not depend on whichever historical project copy happens to be discoverable first.

## Fusion map: arc-dispatch + github-dispatch

Keep these strengths together when changing either project.

### Shared baseline

- Reusable `lark_task_reader.py` module with:
  - `prioritize_tasks(tasks, preferred_scopes=None, scope_mode=None)`
  - `scope_match(task, preferred_scopes=None)`
  - `configured_scope_mode()` and `configured_preferred_scopes()`
  - alias expansion for scope names such as `UVISA-2.0新版开发`, `uvisa-app-2.0`, `UVISA-2.0`, `新版开发`
- Search across unstable Lark payload shapes: `summary`, `title`, `description`, `custom_fields`, tasklist/container/breadcrumb metadata, plus the whole JSON payload as safety net.
- Annotate every collected task with:
  - `_lark_task_scope`
  - `_lark_task_scope_match`
- Preserve fallback semantics: `prefer` returns scoped tasks if any exist; otherwise it returns all incomplete tasks.

### arc-dispatch strengths to keep

- Direct route at collection time for unambiguous tasks, including multi-project fan-out.
- Route payloads include `project_id`, `project_path` via envelope project, and `reference_path` for read-only reference projects.
- Fetch comment text and linked Lark docs before execution so the confirmer/executor sees context, links, screenshots, and product notes.
- Dry-run CLI shows exactly what would be enqueued before mutating the local DB.
- Simple unittest lane for the Lark reader and dry-run collector behavior.

### github-dispatch strengths to keep

- Rich comment parsing marks non-text evidence:
  - images as `[图片:<image_key_prefix>]`
  - files as `[附件:<name>]`
  - linked docs as doc/wiki references for later fetch
- Extract `comment_image_keys` / file tokens so a later image-download or vision lane can fetch binary evidence instead of losing it in text-only collection.
- Fetch comments and linked docs concurrently for new tasks with a bounded worker pool; one task's enrichment failure must not stop the whole collection tick.
- Separate collection from routing when ambiguity is high: collect unrouted envelopes first, then route with `project_profile` and `file_tree` evidence.
- Record stage timing/outcome in workflow DB so slow Lark reads are observable instead of invisible.
- Router can enrich payloads with `project_profile` and a bounded `file_tree` before executor planning.

## Implementation pattern

1. **Token / user authorization**
   - Run an auth preflight before any Task API call. Distinguish `CURRENT_READY`, `CURRENT_BLOCKED_NO_TOKEN`, `CLI_UNBOUND`, `HERMES_APP_CREDENTIALS_MISSING`, and `PREVIOUS_SNAPSHOT_AVAILABLE`; do not misreport a stale snapshot as a fresh live read.
   - Use a reusable token helper (`lark_auth.get_token()` where available) instead of one-off login probes.
   - If the Hermes-native reader fails with `NO_TOKEN` but older snapshots exist, classify the reader logic separately from the current auth state: the logic may be sound while live collection is blocked.
   - `larksuite/cli` can be used as an official auth/dry-run/API-shape oracle. In Hermes context it may require `lark-cli config bind`; because its help explicitly says AI agents must ask first, do not run bind without user confirmation of intent and identity preset. For personal/assigned tasks, `user-default` is required; `bot-only` cannot access user resources.
   - If a Lark/Feishu user authorization flow is triggered by the bot/MCP and opens a browser window, operate the browser directly: inspect the page, click the authorize/allow/continue button, then return to the task reader and retry the API call.
   - `lark-cli auth login --no-wait --json` device flow may only open a fresh Lark login page, not an authorization approval page. If the browser is not already logged in and no credentials/session are available, stop and classify `CURRENT_BLOCKED_NO_TOKEN` / `CLI_NO_USER_SESSION`; do not continue clicking around, do not ask the user to run the polling command, and do not claim a live task read. Use stale snapshots only as explicitly labeled triage evidence.
   - Tokens are secrets/runtime state. Never commit them and never paste them into skills, docs, issues, or memories.
   - When auth is blocked by duplicate `Authorization URL` notifications, `EADDRINUSE ::1:3010`, or stale background `lark-mcp login` output, prefer the single-flight OAuth guard pattern in `references/lark-oauth-single-flight-guard.md` instead of launching another raw login.
   - See `references/larksuite-cli-auth-and-dryrun.md` for the larksuite/cli bind, auth, and dry-run oracle pattern.

2. **Fetch incomplete tasks**
   - Use paginated Task Center reads, e.g. `completed=false` with `page_token` until `has_more` is false.
   - Fail loudly on non-zero API code for the task list itself; this is a collector-blocking error.

3. **Scope priority before dispatch filtering**
   - Call `lark_task_reader.prioritize_tasks(fetch_tasks(token), ...)` immediately after fetching tasks and before `_should_dispatch`.
   - Reason: the scoped lane should decide which task pool to look at before status/dedup trimming.

4. **Dispatch filter**
   - Include only tasks that are incomplete and do not already carry the Lark `状态` custom field used by the pipeline.
   - Do not infer completion from title text.
   - Keep `_should_dispatch` small and deterministic.

5. **Dedup**
   - Dedup by `lark_task_guid` across all local envelope statuses, not just pending/running.
   - For fan-out, dedup sibling envelopes by `(lark_task_guid, project_id)`.

6. **Context enrichment**
   - Fetch comments for new tasks only.
   - Extract plain text, URLs, doc/wiki links, images, files, and creator names.
   - Fetch linked docs with a strict `max_docs` cap and `max_chars` cap.
   - Preserve both normalized text (`comments`, `docs_content`/`linked_docs`) and machine-actionable handles (`comment_image_keys`, `lark_url`).

7. **Routing**
   - If the title/scope makes a project unambiguous, route immediately like `arc-dispatch`.
   - If routing is ambiguous or the pipeline uses GitHub-style staged processing, create `__unrouted__` envelopes first, then route in a separate stage with `project_profile` and bounded `file_tree` evidence.
   - Backend-specific keywords must come before generic frontend keywords.

8. **Payload contract**
   - Minimum fields:
     - `lark_task_guid`
     - `summary` / `issue_title`
     - `description` / `issue_body`
     - `comments`
     - `linked_docs` or `docs_content`
     - `custom_fields` when available
     - `members` when available
     - `lark_url`
     - `lark_task_scope`
     - `lark_task_scope_match`
     - `collected_at`
   - Optional but recommended:
     - `tasklists`
     - `tasklist_names`
     - `tasklist_scope_enrichment_warning` when `/task/v2/tasklists` is unavailable
     - `comment_image_keys`
     - `project_id`
     - `project_path`
     - `reference_path`
     - `project_profile`
     - `file_tree`
     - `labels`

9. **Reporter boundary**
   - Collector reads and creates local envelopes.
   - Reporter writes back to Lark/GitHub.
   - Do not let collection dry-run write comments/status. This boundary prevents accidental external side effects.

## Lark API shape notes

Lark/Feishu API shapes vary by tenant, version, and permission set. Code should be tolerant in reads, strict in payload contract.

- Task list: `/task/v2/tasks?page_size=...&completed=false` with pagination.
- Task update: `PATCH /task/v2/tasks/{guid}` with `{"task": {...}, "update_fields": [...]}`. The `task` wrapper is required — omitting it returns 400. See `references/lark-task-api-v2-update-and-closeout.md`.
- Comments API: `POST /task/v2/tasks/{task_id}/comments` returns 404 on larksuite.com (international). Use `description` field for evidence instead.
- `larksuite/cli` official dry-runs are useful for checking current endpoint/parameter shape without hitting the network: `task +get-my-tasks --as user --complete=false --page-all --dry-run`, `task tasklists list --as user --dry-run`, and `task tasklists tasks --as user --dry-run`. Treat this as an oracle/fallback aid, not a replacement for project-specific payload normalization.
- Tasklist scope enrichment: `/task/v2/tasks` may return only `tasklists[].tasklist_guid` without the human-readable list name. For hard scope reads like `UVISA-2.0新版开发`, fetch `/task/v2/tasklists`, build `tasklist_guid -> name/url`, enrich each task with `tasklist_names`, and only then run `prioritize_tasks(..., scope_mode="only")`. See `references/tasklist-scope-enrichment.md`.
- Comment endpoints may differ:
  - `/task/v2/tasks/{task_guid}/comments?page_size=...`
  - `/task/v2/comments?resource_id={task_guid}&resource_type=task&page_size=...`
- Comment `content` can be JSON rich text, plain string, list, dict, or malformed. Parse defensively.
- Linked-doc URLs may be `docx` or `wiki`; wiki nodes may need a `wiki -> docx` conversion before fetching doc content.
- Support both `larksuite.com` and `feishu.cn` domains when extracting links.

## UVISA routing

Add UVISA mappings before legacy/default projects:

- `uvisa_backend` -> `/Users/charles/Desktop/folder/work/uvisa-backend`
- `uvisa_app_2_0` -> `/Users/charles/Desktop/folder/work/uvisa-app-2.0`

Backend-specific keywords must appear before generic UVISA frontend keywords so `UVISA-2.0后端` routes to backend instead of frontend.

Recommended ordering:

1. Explicit backend lane: `UVISA-2.0后端`, `后端`, `API`, `接口`, `uvisa-backend`.
2. Explicit frontend lane: `uvisa-app-2.0`, `H5`, `移动端`, `用户端`, screen names.
3. Cross-project/fan-out lanes.
4. Default lane last.

## Loop implementation

When the user asks to "loop" Lark reading or to fuse patterns into the skill tree, use this loop:

0. **Audit first, then execute.** Before implementing any task, run `lark_task_reader.py --scope-mode prefer --summary` to get the full task list. Cross-reference each guid against git log, test files, and source code comments. Many tasks from previous sessions are already done. Classify each as DONE / PARTIAL / TODO. Only start implementing TODO or PARTIAL tasks. This prevents re-doing work and surfaces backend blockers early.

0b. **Classify before executing.** After reading a task, classify it as:
   - **Point fix**: isolated to one location, no similar patterns elsewhere
   - **Cross-cutting concern**: validation, security, error handling, data transforms, i18n → must be implemented as shared infrastructure (extend `validators.ts` / `utils.ts`), not point fixes
   - **Infrastructure task**: changes to shared utilities, project config, or build tooling
   
   Scan for existing shared infrastructure and duplicated patterns before implementing. The user explicitly requires this: "有些对于项目属于基础设施或者常规限制，不能因为任务只说了一个地方就只改这一个地方" (some things are infrastructure-level constraints that can't be fixed at just one location because the task only mentions one place).

1. **Inspect** both reference projects:
   - `lark_task_reader.py`
   - collector/comment/doc enrichment code
   - router project mapping and staged/fan-out routing
   - tests around scope filtering, comment extraction, doc links, and dry-run behavior
2. **Extract reusable patterns** into this skill or a linked reference. Do not copy secrets or transient task data.
3. **Patch the project code only if needed**; otherwise keep the improvement in the skill tree.
4. **Verify**:
   - skill frontmatter parses and description length is below Hermes limits
   - `python3 ~/.hermes/scripts/skill-steward.py --graph-check --json`
   - project tests/compile for any project code touched
5. **Commit scoped files only**. In a dirty `~/.hermes` repo, run:
   ```bash
   git diff --cached --stat
   git restore --staged .
   git add scripts/lark_task_reader.py scripts/test_lark_task_reader.py \
     skills/software-development/lark-task-reading/SKILL.md \
     skills/software-development/lark-task-reading/references/tasklist-scope-enrichment.md
   git status --short -- scripts/lark_task_reader.py scripts/test_lark_task_reader.py skills/software-development/lark-task-reading
   git commit -m "feat: add Hermes-native Lark task reader"
   ```
6. **Continue** if verification finds missing coverage or graph violations; stop only when the skill tree audit passes and the scoped commit is clean.

## Executing a Lark task: closeout before exploration

When a user asks to read assigned Lark tasks and complete them, treat each task as a finite delivery unit, not as an open-ended audit. After implementation and deterministic verification pass, close the task in this order before spending more tool/context budget on optional ledgers or exploratory follow-ups:

1. Write a concise evidence note under `/tmp` or the project evidence location: task id/title, chosen approach, files changed, verification commands/results, residual risks.
2. Update only the minimum project ledger rows needed for traceability; do not let doc deposition expand into a new workstream.
3. Run `git status --short` and `git diff --check`.
4. For UVISA/Railway-backed tasks, monitor the relevant remote package/deploy status before claiming closeout: resolve the exact Railway project and service names from project-local docs/Workpad/AGENTS or user-provided dashboard screenshots, use the existing local browser/Railway login session when available, check the relevant service deployment or package/build status, wait for a terminal status, and record only safe evidence (project name, service name, deployment/build id or redacted dashboard URL, status, timestamp, smoke URL/health check). Current UVISA user override for frontend-task loops: after any frontend code change, run local checks, push the shared task-loop branch, and monitor the remote frontend package/build status; do not monitor backend deployment status unless the user explicitly asks. Do not paste Railway tokens, cookies, private session data, OTP values, or raw credential-bearing logs. If the remote package/deploy fails, is cancelled, times out, or cannot be accessed, report `closed_with_remote_blocker` or `not_closed`; do not mark the Lark task fully closed.
5. Make a scoped local commit for exactly the task files. Branch policy for UVISA/Lark task loops: do not create a fresh branch per individual task. If a new branch is needed for subsequent pushed changes, create/use one shared task-loop branch and keep later task commits on that branch unless the user explicitly asks for per-task branches. After each PR is merged into the deployment branch, fetch/sync the local task branch onto the new deployment-branch merge commit before starting the next task, so the next PR does not start from a stale pre-merge commit.
6. Before independent review, ensure the review diff contains untracked/new files as well as modified files. Preferred pattern: stage the intended task files, run `git diff --cached --check`, write `git diff --cached > /tmp/uvisa-task-<id>-staged.diff`, and send that staged diff to reviewers. If a reviewer saw only `git diff -- path...` while a new test file was untracked, rerun review on the staged diff before commit.
7. Notify the user via the requested reporting channel (for 贺程 this is usually TG) with the task id, commit hash, summary, local verification evidence, and remote package/deploy monitor result. If Telegram delivery reports no home channel, retry with the known direct target form (for this environment: `telegram:he cheng`) before declaring notification blocked.
8. Only then continue to the next Lark task or optional broader audits.

Multi-model closeout is a gate, not a ceremony. If a reviewer returns `AMEND`, `REJECT`, or any concrete blocker before commit, do **not** rationalize it away or proceed to TG. Convert the blocker into a RED regression test first, verify it fails for the current implementation, make the smallest fix, then rerun targeted tests, touched-file lint, full unit/build as appropriate, and update evidence notes/ledger counts. Example pattern from an auth/i18n task: reviewers found an over-broad error mapper that converted generic `failed + verification/code` and non-OTP `AUTH_VERIFY_FAILED` business errors into `auth.codeWrong`; the correct closeout was to add negative tests for send-code/non-OTP verify messages, narrow the matcher, and only then commit.

Before trusting a task note's `multimodel_status: certified`, validate the referenced artifact is target-bound to the exact Lark/taskpool item. Open `discussion_result.json` and check: the evidence paths/claim texts mention the current task or proof artifact, the state/question/project identifiers match, and the model set satisfies the user's expected tier (for 贺程's requested full certification, Claude + GPT/Codex + DeepSeek + MiMo all participate). If the artifact certifies an unrelated task, or if the gate returns PASS despite a target mismatch, keep the task in `review`/`not_closed`, report `not_certified_for_target`, and treat the gate behavior as an infrastructure bug to fix before automatic done/Lark writeback.

For implementation certification, build the multi-model state from explicit claim/evidence pairs after or alongside deterministic evidence collection. Do not send only a vague task description + target files and expect ratification: `consult_models.py` can return `truth_status=no_claims`, low agreement, or a misleading noop-vs-implementation split even when the local patch is reasonable. Include claims such as “service normalizes X”, “UI preserves Y route”, and “verification command Z passed”, with evidence objects supporting those exact IDs; otherwise treat the run as advisory/not-certified and prioritize deterministic closeout gates.

Before committing after any late reviewer-driven test additions, scan docs and evidence for stale verification counts or old claims (`grep`/search for old totals such as `27/27` or `472 passed`). Update `/tmp` evidence, repo ledgers, and project Workpad consistently, then run `git diff --check` again. This prevents a task from being technically fixed but reported with stale proof.

If tool/context budget is near exhaustion after tests pass, prioritize commit + notification over additional nice-to-have documentation. If interrupted before commit or notification, final output must explicitly say which closeout gate is unfinished and list the exact next commands; never imply the Lark task is fully closed from tests alone.

When a stale Lark task describes behavior that the current code already satisfies, close it as a regression-proof task rather than inventing a product change. Inspect the screen first, add a focused guard test, update ledger/evidence with “existing implementation + proof,” and report it honestly. See `references/uvisa-regression-proof-closeout-patterns.md` for UVISA examples, including `TxDetailScreen`/`FlowNav` back-button tests needing `ToastProvider` and account-balance unit removal tests.

Budget guard for per-task execution:
- Before launching expensive/long-running side channels (T2/T3 `consult_models.py --discussion`, dev server + browser walkthrough, full test + build in parallel), check whether enough tool budget remains to poll/read the result, commit, and send the requested report. If not, start no new long runner; preserve the state file/path and close the deterministic task first.
- If a background multi-model process has not produced/read `discussion_result.json` is `started/no_ratification_artifact`, not certification. Do not let it consume the final closeout window.
- Tool-call/max-iteration warnings are a hard closeout-priority signal. When the session is near the tool-call ceiling, do not start or keep waiting on a long T3 discussion before commit/TG. If deterministic gates + independent review already pass, either (a) stop the long runner and close deterministically with `not fully ratified`, or (b) preserve the process/tick/state path in the handoff and explicitly mark commit/push/remote/TG as unfinished. Never leave a task with tests passed but no commit/TG because a certification runner consumed the final calls. If the platform emits a hard “maximum number of tool-calling iterations allowed” stop, final output must not imply closeout: state exactly that implementation/tests passed but commit/push/remote/TG and any background multi-model poll remain unfinished, with the state file/session id if known.
- After commit + push + remote monitor, send the requested user notification (TG for 贺程) before doing additional Workpad polishing, optional evidence-note rewrites, or continuing to the next task. A task with commit/push/remote done but TG unsent is still not fully closed for requests like “每完成一个任务 TG 通知我”. If only a few calls remain, prefer one concise TG with blocker status over more documentation.
- If an independent reviewer finds blockers after a multi-model state/run has already started, treat the state/tick as stale for the final diff. Stop or quarantine the old run, fix the blockers with regression tests, rerun deterministic gates and final review, then build a fresh claim/evidence state for the final code before claiming multi-model certification. Do not cite a pre-fix state or pre-fix `discussion_result.json` as certifying post-review edits.
- If context compression/tool-call ceilings interrupt a UVISA/Lark task mid-refactor, output an explicit handoff instead of a soft completion summary: task id/title, current branch, modified/untracked files, tests already run, RED evidence vs passing evidence, exact likely compile blockers, and the remaining closeout gates (test/build → evidence → commit → push/remote monitor → TG). Resume next time with fix-first sequencing, not broader task exploration. See `references/uvisa-task-interruption-handoff.md`.
- If context compression preserves an active task list, treat it as session state to resume, not as a request to restart discovery. Re-run only the minimal live guards (`git status`, latest task snapshot freshness/path, and any user-requested live Lark authorization retry), then continue the in-progress task. Do not spend the closeout budget re-reading every task or redoing classification unless the snapshot is missing/stale for the decision at hand.
- If the process wrapper cannot kill a stale background consult because of local dependency failures (for example `No module named 'psutil'`), terminate the process group with terminal/PGID (`pgid=$(ps -o pgid= -p PID | tr -d ' '); kill -TERM -$pgid`) and verify the PID is gone before continuing.
- If browser UI verification is blocked by auth/session/OTP setup after unit/build gates pass, record it as an explicit unfinished UI gate and either establish test login state immediately or stop before burning the closeout budget. Do not keep exploratory browser clicks running until the session hits the tool-call ceiling.
- For user requests like “每完成一个任务 TG 通知我”, the task is not complete until the TG notification has been sent (or a specific notification blocker is reported). Tests/build alone are implementation evidence, not task closeout.

Detailed patterns:
- `references/lark-task-execution-closeout.md` for finite-task closeout sequencing.
- `references/remote-package-monitor-closeout.md` for Railway/package/deploy monitoring, including the preferred authenticated `railway service status --all --json` / `railway deployment list --service ... --json` CLI path, safe evidence fields, and `closed` / `closed_with_remote_blocker` / `not_closed` status semantics.
- `references/uvisa-auth-support-closeout-notes.md` for the pattern where implementation already exists, the task is completed by adding regression proof/ledger evidence, Railway CLI monitor evidence, TG fallback notification, and PGID-based dev-server cleanup.
- `references/uvisa-regression-proof-closeout-patterns.md` for stale UVISA Lark tasks where current code already satisfies the requirement or the safe fix is a small UI regression guard; includes `ToastProvider` test-wrapper pitfall for `TxDetailScreen` and precise closeout wording.
- `references/uvisa-transaction-timestamp-localization.md` for wallet/assets/card transaction time tasks: service-layer timestamp normalization, local-time display, TDD guards, and the TypeScript strict-build pitfall found during UVISA task execution.
- `references/uvisa-large-amount-typography.md` for UVISA money-text overflow tasks: adaptive typography tiers, no field/precision removal, TypeScript fixture pitfalls, 375px Playwright layout evidence, and closeout gates.
- `references/uvisa-exchange-quote-countdown.md` for exchange quote validity/countdown tasks: backend `quoteId/expiresAt` linkage across input → confirm → PIN finish, no re-quote after PIN, expiry blocking, and Testing Library selector pitfalls.
- `references/uvisa-pin-setup-attempt-guard.md` for first-login payment PIN setup confirmation mismatch tasks: separate weak-PIN validation from confirm-mismatch attempt budget, use `pinGuard` with a setup-specific key, write the RED component test first, then close with full test/build + remote/TG gates.
- `references/uvisa-single-session-auth.md` for UVISA single-login / old-device-kickout tasks: treat as backend token/session invalidation, not frontend-only logout; use per-user session generation in JWT/Redis, prove stale access and refresh tokens are rejected, and monitor Railway `uvisa-backend` on closeout.
- `references/uvisa-lark-task-closeout-branch-and-review.md` for UVISA Lark task-loop closeout mechanics: one shared task-loop branch, per-task PR/merge, monitor Railway frontend by merge commit, stage diffs before independent review so untracked tests are included, and cover ambiguous UI copy locations.
- `references/uvisa-secure-receiving-info-closeout.md` for UVISA top-up receiving-info leakage tasks: fail-closed fixed-row rendering, remove legacy raw detail endpoints, validate every displayed bank/SWIFT/account/reference field, prove extra backend payload keys never render, and close with frontend push + remote frontend build monitor + TG.
- `references/uvisa-phone-rebind-5step-closeout.md` for UVISA phone-rebind prototype tasks: model the 5-step flow as current-phone confirmation → payment PIN → default email second factor with SMS switch → new phone input → new-phone SMS verification; add regression proof that the old-phone verification path is not used by default, and stage untracked tests before review.
- `references/uvisa-trusted-device-security-closeout.md` for UVISA trusted-device/device-management tasks: keep client localStorage fallback out of login/PIN security routing, fail closed when `currentDeviceTrusted` is missing/false, validate PATCH trust affected rows, and rerun multi-model certification after reviewer-driven fixes.
- `references/uvisa-frontend-i18n-copy-closeout.md` for small UVISA frontend i18n/copy-only Lark tasks: add a focused RED i18n guard, preserve adjacent semantic distinctions (for example CNY vs CNH), package claim-linked evidence for multi-model certification, and word Railway frontend status precisely when the deployed branch differs from the pushed task-loop branch.
- `references/uvisa-validation-infrastructure-extraction.md` for UVISA validation cross-cutting concerns: when a Lark task describes a validation fix at one location, check for the same pattern elsewhere and extract to shared `validators.ts` infrastructure instead of point-fixing.
- `references/uvisa-fe-be-sync-multi-model-review.md` for multi-model parallel review of frontend+backend sync tasks: 3-lens review (Architecture + Red-Team + Practical), consensus synthesis, risk-ordered implementation, and project profile writeback.
- `references/uvisa-cny-topup-pending-transaction-visibility.md` for CNY/domestic-bank top-up order visibility tasks: insert session-local pending rows only after real txId, reconcile by backend transaction id, map pending as processing, avoid optimistic persistence, and watch for Vitest selector/order pitfalls.
- `references/uvisa-payment-pin-vs-password-service.md` for UVISA payment PIN vs password confusion: two independent services (`PaymentPinService` for 6-digit PIN, `PaymentPasswordService` for 8-64 char password) with different DB columns but same `PIN_NOT_SET` error code. Frontend method names say "Password" but URLs say "pin".
- `references/uvisa-forgot-payment-pin-reset.md` for forgot-payment-password/PIN-reset Lark tasks: implement missing `/api/auth/pin/forgot/send-code` and `/api/auth/pin/forgot/reset` as authenticated current-user + bound-email OTP endpoints, return masked email only, sanitize audit, test with `JwtAuthenticationToken` plus `ROLE_USER`, and preserve closeout budget before long multi-model review.
- `references/uvisa-cs-session-cache-stale-flash.md` for CS chat stale-cache flash: module-level `msgs` array persists across navigations; clear at start of `refreshCsSession()` before API call, not in hook mount.
- `references/uvisa-sw-update-banner-mounting.md` for SW update banner defined but never mounted: check `UpdateBanner` is imported and rendered in `App.tsx`, not just defined in `src/components/`.
- `references/uvisa-authenticated-endpoint-data-leak.md` for authenticated endpoints returning raw sensitive data: JWT-required ≠ safe; mask at controller layer, keep service methods raw for business logic.
- `references/lark-task-api-v2-update-and-closeout.md` for batch task closeout via PATCH API: wrapped `task` object required, comments endpoint returns 404 on larksuite.com, use `description` field for evidence.

## Multi-model routing

Use multi-model thinking by risk level, not by habit:

- T0: deterministic checks for small doc wording changes.
- T1: one reviewer when adding a new collector pattern or changing routing semantics.
- T2: 3-model advisory when fusing patterns across `arc-dispatch` and `github-dispatch`.
- T3: 4-model ratification only for write-back automation, autonomous execution, or state-machine changes that can mutate external systems.

If the multi-model artifact says `not_certified`, treat it as advisory provenance. Do not claim ratification; resolve the issue ledger with deterministic evidence and rerun only if certification is required for the decision.

## Verification

For `github-dispatch`:

```bash
cd /tmp/github-dispatch
.venv/bin/python -m pytest tests/test_collector.py tests/test_pipeline.py -q
.venv/bin/python -m compileall -q collector.py lark_task_reader.py router.py orchestrator.py
```

For `arc-dispatch`:

```bash
cd /tmp/arc-dispatch
python3 -m unittest tests.test_lark_task_reader -v
python3 tests/test_basic.py
python3 -m compileall -q collector.py lark_task_reader.py router.py tests/test_lark_task_reader.py
```

For skill-tree-only changes:

```bash
python3 - <<'PY'
from pathlib import Path
import re, yaml
p = Path.home()/'.hermes/skills/software-development/lark-task-reading/SKILL.md'
s = p.read_text()
assert s.startswith('---')
m = re.search(r'\n---\s*\n', s[3:])
assert m
fm = yaml.safe_load(s[3:m.start()+3])
assert fm['name'] == 'lark-task-reading'
assert len(fm['description']) <= 1024
assert len(s) <= 100000
print('skill frontmatter ok')
PY
python3 ~/.hermes/scripts/skill-steward.py --graph-check --json
```

After Python compile checks, delete generated `__pycache__/*.pyc` if the repo tracks/deletes pyc files, so commits do not include bytecode churn.

## Project-pipeline commands

Use these only after intentionally choosing a live dispatch project as the runtime target, and run them from that project's canonical git root. They are **not** the default way to answer a normal "read my Lark tasks" request.

```bash
# First prove the runtime target is the intended project, not an archive/duplicate copy
pwd
git rev-parse --show-toplevel 2>/dev/null || true
git status --short

# Default: prefer UVISA-2.0新版开发, fall back to all incomplete tasks
./run.sh --mode collect-only --dry-run

# Hard filter to UVISA-2.0新版开发
LARK_TASK_SCOPE_MODE=only ./run.sh --mode collect-only --dry-run

# Custom preferred scope list
LARK_TASK_PREFERRED_SCOPES=UVISA-2.0新版开发 ./run.sh --mode collect-only --dry-run

# Disable scope preference for a broad audit
LARK_TASK_SCOPE_MODE=off ./run.sh --mode collect-only --dry-run
```

- Detailed larksuite/cli auth + dry-run oracle notes: `references/larksuite-cli-auth-and-dryrun.md`.
- Lark MCP user-auth recovery notes: `references/lark-mcp-user-auth-recovery.md`.
- Lark OAuth duplicate-login / fixed-port single-flight guard notes: `references/lark-oauth-single-flight-guard.md`.
- UVISA live auth + stale snapshot triage notes: `references/uvisa-live-auth-and-stale-snapshot-triage.md`.

## Pitfalls

- `lark-mcp login` defaults to `https://open.feishu.cn`. International Lark apps (larksuite.com) MUST pass `--domain https://open.larksuite.com` or get error 20029 (redirect URL mismatch). Always check `LARK_API` in `lark_task_reader.py` — if it's `open.larksuite.com`, the tenant is international.
- **Port MUST be fixed to 3010.** The redirect URI `http://localhost:3010/callback` is registered in the Lark developer console. Using a different port (3001, 3005, 3011, etc.) creates a different redirect URI that doesn't match, causing error 20029. Always use `--port 3010`. Changing ports requires the user to register a new redirect URI in the developer console — each attempt wastes a user interaction.
- Error 20029 means the redirect URI is not registered in the developer console. The user must add `http://localhost:{port}/callback` at `https://open.larksuite.com/app/{appId}/safe` → 安全设置. This requires their Lark account login; the controlled browser and user Chrome don't share sessions.
- A failed `lark-mcp login` wipes old tokens from `authStore.storageDataCache.tokens` but preserves `clients`. Extract appId/appSecret from `clients[client_id_for_local_auth].extra` to retry. Recovery pattern: run `node -e "const {authStore}=require('...lark-mcp/dist/auth/store.js'); authStore.initialize().then(()=>{const d=authStore.getAll(); const c=d.clients['client_id_for_local_auth']||{}; const e=c.extra||{}; console.log(JSON.stringify({appId:e.appId,secret:e.appSecret}))})"` to get credentials, then `lark-mcp login --appId ... --appSecret ... --domain https://open.larksuite.com --scope "auth:user.id:read,task:task:read,task:tasklist:read" --port 3010`. If the browser auth page shows error 20029, the redirect URI `http://localhost:3010/callback` must be registered at the Lark developer console first.
- Missing/expired user auth is not the same as a broken reader. If live collection returns `NO_TOKEN` or `lark-mcp` reports unbound Hermes context, report the auth blocker and any available previous snapshot separately.
- After `NO_TOKEN`, do not repeat the exact same live-read command. Switch to auth preflight (credential presence + token-store shape) or stale-snapshot triage. When probing `lark-mcp` auth-store from Node, call `process.exit(0)` after printing non-secret token-key counts; the keytar/auth-store handles can otherwise keep the process alive until the shell timeout.
- Existing snapshot files are not evidence until parsed. Validate JSON and task count before using `/tmp` or `~/.hermes/tmp` Lark snapshots; invalid/empty files must be ignored, and valid snapshots must be labeled `stale/non-live` in evidence and TG closeout.
- `lark-cli config bind --source hermes` can fail even after user confirmation if Hermes has no Feishu/Lark app credentials in `~/.hermes/.env` (`FEISHU_APP_ID` / secret). Classify this as `HERMES_APP_CREDENTIALS_MISSING`; do not keep retrying `auth login`, and do not treat `lark-mcp` client metadata/scopes as proof of a live token when tokens/localTokens are empty.
- `lark-mcp login` is a separate path from `lark-cli config bind`: it requires CLI `--app-id/--app-secret` or environment `APP_ID` / `APP_SECRET`, not `FEISHU_APP_ID` directly. If it fails with `Missing App Credentials` and `lark-mcp whoami` says no active sessions while auth-store has only `client_id_for_local_auth`, classify `CURRENT_BLOCKED_NO_TOKEN` + app-credential blocker; use snapshots only as stale triage. If a safe credential source is available, prefer the single-flight OAuth guard (`python3 ~/.hermes/scripts/lark_oauth_guard.py --json --cleanup-stale`) over raw background login; if the guard is unavailable, run a redacted `/tmp` helper that passes credentials without printing them, complete the browser authorization if prompted, then prove success with the live task reader (`--scope-mode only --summary`) rather than `whoami` alone. If plain background capture shows no authorization URL, rerun with a PTY so the `Authorization URL:` line flushes. If `EADDRINUSE ::1:3010` appears, kill the stale login listener on fixed port 3010 before retrying. If `lark-mcp login` exits 0 but `authStore.storageDataCache.tokens` remains empty and no success line appears, do not treat it as authorized. If the auth page errors with `20043` for `task:taskwrite`, retry with minimum valid read scopes `auth:user.id:read task:task:read task:tasklist:read`. If it errors with `20028 app_id 请求不合法`, or if authStore `client_id`/`client_secret` literally equal `client_id_for_local_auth`, the authStore entry is a placeholder/local MCP client, not a real app credential pair; validate a real app credential pair via the app access token endpoint without printing values, then rerun guarded login with those credentials. See `references/lark-oauth-single-flight-guard.md`, `references/lark-mcp-user-auth-recovery.md`, and `references/larksuite-cli-auth-and-dryrun.md`.
- Do not run `lark-cli config bind` on behalf of the user without explicit confirmation; the CLI help requires the agent to confirm intent and identity preset first. Assigned/personal task reads need `user-default`; `bot-only` is safer but cannot read user resources.
- Lark Task API metadata shapes vary; match across summary, description, custom fields, tasklists, containers, breadcrumbs, and the full JSON payload.
- If `/task/v2/tasks` includes only `tasklists[].tasklist_guid`, scope matching by list name will fail until you enrich from `/task/v2/tasklists`; do this before `only` mode and before claiming the desired project list was read.
- Do not certify `UVISA-2.0新版开发` hard-scope correctness from title/body keywords. Require enriched `tasklist_names` evidence.
- Lark task `description` can be empty while comments hold the actionable details; `issue_body` should merge description + comments + docs, not description alone.
- Do not infer task completion from title; keep `_should_dispatch` checks for `completed_at` and `状态` field.
- Do not commit temporary login probes, Lark tokens, generated bytecode, downloaded attachments, or screenshots with sensitive task data.
- `github-dispatch` may be a non-git folder in this environment; verify with `git status` before promising a commit.
- Do not collapse image/file placeholders into plain text only. Preserve machine-actionable keys for later binary fetch/vision work.
- Do not let one failing comment/doc fetch abort the whole collector tick; isolate per-task enrichment failures and record enough trace to debug.
- Do not turn safe collection into automatic task execution. Collection, routing, execution, validation, and reporting are separate gates.

## Verification checklist

- [ ] Auth preflight distinguishes current live readiness from stale snapshots (`CURRENT_READY`, `CURRENT_BLOCKED_NO_TOKEN`, `CLI_UNBOUND`, `HERMES_APP_CREDENTIALS_MISSING`, `PREVIOUS_SNAPSHOT_AVAILABLE`).
- [ ] OAuth recovery uses a single-flight guard before raw login when duplicate auth URLs, stale background output, or port 3010 conflicts are present.
- [ ] Scoped tasks are preferred by default and fallback remains intact.
- [ ] `only` and `off` modes work.
- [ ] Payload includes scope metadata.
- [ ] Comments, URLs, doc/wiki links, image/file placeholders, and image keys are preserved when present.
- [ ] Dedup checks all local statuses; fan-out dedups siblings.
- [ ] Dry-run performs no external writes.
- [ ] Backend routes are checked before generic frontend routes.
- [ ] Relevant tests and compile checks pass.
- [ ] Skill graph strict check passes after skill edits.
