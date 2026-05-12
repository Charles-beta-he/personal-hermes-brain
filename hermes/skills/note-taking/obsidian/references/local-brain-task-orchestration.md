# Local-brain task orchestration patterns

Use this when an external agent-orchestration or tracker-runner project is evaluated for helping `~/Documents/brain` plan and operate pending tasks.

## Principle

`~/Documents/brain` Markdown remains the canonical source of truth. External trackers, dashboards, daemon state, SQLite/vector indexes, and generated queues are derived/rebuildable unless the user explicitly changes that boundary.

Dashboard/self-check directionality: self-checks should scan canonical Markdown/scripts and then write dashboards as observability artifacts; dashboards must not be treated as authoritative input that automatically repairs the vault. If a dashboard shows violations, create a repair plan or task with explicit dry-run/apply phases, proof gates, and full re-verification. Do not implement dashboard → vault self-repair unless the user explicitly authorizes that new capability and a kill switch/rollback path exists.

Migration pitfall: after hierarchy renumbering, duplicate top-level dashboard folders can be a compatibility leftover, not a legitimate second dashboard layer. For the current brain layout, `07-仪表盘/` is the canonical dashboard layer; a residual `06-仪表盘/` should be classified as legacy/compat unless it has been explicitly whitelisted. Before deleting or moving it, search all wikilinks/references, compare unique content, migrate valuable pages, then run the hierarchy self-check, exhaustive audit, `brainctl validate --write-dashboard`, sync, reindex, and search.

## Local-brain repair closure protocol

When a self-check/dashboard reveals vault residue, do not jump straight to edits. Use this explicit loop:

1. **repair-plan (read-only)**
   - Run deterministic scanners: `local_brain_main_hierarchy_migration_selfcheck.py --json`, `local_brain_exhaustive_audit.py`, `brainctl.py --json validate --write-dashboard`, `brain_task_orchestrator.py proof-check --json`.
   - Produce a manifest with one candidate change per item: `source_path`, `target_path`, `operation`, `reason`, `risk`, `content_hash_before`, `references_found`, `rollback_plan`, and `verification_commands`.
   - For directory removals, include exact reference search, wikilink search, frontmatter path search, and content diff against the replacement directory.

2. **review gate**
   - Human or multi-model review inspects the manifest. Model agreement is advisory; file/command evidence is the gate.
   - Classify each item: `safe_apply`, `needs_manual_decision`, `archive_only`, `false_positive`, or `accepted_risk`.

3. **repair-apply (explicit only)**
   - Apply only reviewed `safe_apply` items. Do not read dashboards as authoritative input; read the reviewed manifest.
   - Create backups or a git commit boundary before destructive changes.
   - Never delete evidence files or task logs without a replacement link/proof ledger.

4. **verify/proof**
   - Re-run the same scanners and require monotonic improvement: fewer old top dirs, fewer broken links, fewer validate violations, no new secret hits.
   - Run `brainctl sync`, `brainctl reindex`, and targeted `brainctl search` queries.
   - Write structured evidence back to the task note before marking it `done`.

This makes cleanup a closed control loop: detect -> plan -> review -> apply -> verify -> proof, rather than an unsafe dashboard-to-vault auto-repair path.

## What to borrow from tracker-driven agent runners

Useful concepts:
- Task/deliverable control plane over session control: avoid managing dozens of chat/CLI sessions directly; manage canonical task notes and let sessions/agents become execution details.
- Task lifecycle frontmatter: `status`, `priority`, `claimed_by`, `claim_expires_at`, `retry_count`, `next_attempt_at`, `workspace`, `evidence`, `expires_at`.
- Task-tree/DAG decomposition: complex or ambiguous work can first produce an implementation plan, then a tree of tasks with `blocked_by`/`blocks`/`ready_when`-style dependencies; only unblocked tasks should dispatch.
- Claim/lease before execution to avoid duplicate cron/subagent dispatch.
- Reconciliation before dispatch: release expired claims, detect stale running tasks, update retry state, then select new work.
- Bounded concurrency by project/status/risk tier.
- Exponential retry/backoff with escalation to `blocked` or `review` after threshold.
- Persistent workpad: task note contains plan, acceptance criteria, validation, evidence links, confusions, and final handoff.
- Workflow contract: capture formerly implicit human execution steps in a Markdown contract/template (`WORKFLOW.md`-style or local task workflow contract) so agents know what proof, review, and status transitions are required.
- Derived dashboard under `07-仪表盘/` for pending/running/retry/stale counts; dashboard is observability only.
- Per-task workspace/worktree paths linked from the task note rather than hidden in a daemon.
- Host-side typed/dynamic tool proxy: keep high-privilege credentials and external API tokens in the parent/orchestrator; expose only allowlisted typed functions to subagents, and write proof logs for mutations.

## What not to borrow by default

- A second canonical board or database (e.g. Linear as the real task truth while Obsidian mirrors it).
- A whole preview/alpha runtime just to get task states.
- Arbitrary shell hooks against the vault without a strict allowlist, timeout, and isolated workspace.
- Agent-runtime lock-in (Codex app-server, Claude-only, IDE-only) for local-brain planning; treat such runtimes as optional execution adapters, not planning truth.
- Giving subagents raw tokens/secrets or arbitrary external APIs when a host-side typed proxy can provide least-privilege access.
- Auto-cleanup that deletes evidence or workspaces without a Markdown proof ledger.

## Minimal landing package

0. If the user says “加入任务池 / add to task pool / 本地大脑任务池”, do not use only the session-local todo tool. The visible/canonical local-brain task pool requires a Markdown task note plus regenerated derived views:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py add "任务标题" --priority P1 --project project-slug --status pending --concepts task,tag --objective "..." --accept "..." --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py dashboard --write
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "任务关键词" --limit 10
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json
```

`任务收件箱.md` is only a draft/inbox entry point. Direct `add` creates an independent task note under `05-实践与项目/tasks/`, then `任务池-排序.md` and `待完成任务运行态.md` show it after `dashboard --write`. `brainctl sync` does not by itself guarantee that `brainctl search` can find the new task: run `brainctl reindex` after sync and verify with a targeted search. If a combined long query returns `[]`, retry with a short distinctive term from one task title (for example the external skill/repo name) and then with an ASCII concept tag; FTS can miss multi-term mixed Chinese/English queries even when individual task notes are indexed. If the user cannot see a task in Obsidian, first check whether it was mistakenly added only to session todo and repair by creating the canonical task note.

Git/commit caveat for this user's current brain setup: the canonical vault at `~/Documents/brain` may not itself be a git repo, while `brainctl sync` mirrors notes into `~/.hermes/notes/brain` inside the `~/.hermes` git repo. When the user expects a local commit for task-pool additions, detect the actual repo root before committing. Commit only the newly created/changed task note mirrors (and any intentional dashboard/artifact mirrors) with path-limited `git add -- <paths>`; do not sweep unrelated dirty `~/.hermes` notes, cache, checkpoints, auth, or project changes into the commit.

Pitfalls when creating tasks by CLI:
- `lane=evolution` requires architecture alignment fields. Include `--architecture-target`, `--capability-delta`, and `--anti-drift-check`, otherwise `brain_task_orchestrator.py add` fails with `evolution tasks require architecture alignment fields`.
- After `add`, read the created task note. Some CLI/parser combinations may collapse repeated `--accept` values to only the last acceptance criterion. If the task note lost criteria, patch the Markdown immediately before dashboard/reindex/search verification.
- When converting an external repo/framework audit into a task-pool item, include the multi-model artifact path and certification status in `acceptance_evidence`, but write conservative language if discussion is `not_certified` or weak consensus. Prefer `evidence-grounded advisory` over “certified” unless the artifact explicitly supports full certification.
- `next --json` can refuse dispatch until reconcile runs when stale task state exists. Report this as scheduler state; do not imply the newly added task is broken.

Inbox parser pitfall: example task bullets in fenced code blocks or HTML comments must not be ingested. When changing `brain_task_orchestrator.py ingest-inbox`, verify it only scans the real `## Inbox Drafts` section and skips code fences / HTML comments; otherwise documentation examples like `任务标题` can become accidental real tasks. After fixing parser behavior, remove accidental generated task notes only after project-wide reference search and dashboard regeneration.

1. Add/adjust a project or practice note under `05-实践与项目/实践方案/` describing the state machine and source-of-truth boundary.
2. Add a reusable task workflow contract template under `08-模板/` if the workflow will repeat.
3. Add a generated/non-canonical dashboard note under `07-仪表盘/` only if a script or cron will regenerate it.
4. If user-facing interaction matters, add/refresh a task inbox note and sorted task pool note; keep them explicitly labeled as inbox/derived view, not canonical truth.
5. Verify with:

```bash
python3 ~/.hermes/scripts/brainctl.py --json status
python3 ~/.hermes/scripts/brainctl.py --json sync
python3 ~/.hermes/scripts/brainctl.py --json reindex
python3 ~/.hermes/scripts/brainctl.py --json search "claimed_by retry_count task lifecycle" --limit 8
python3 ~/.hermes/scripts/brainctl.py --json search "dispatch-dry-run" --limit 8
```

Prefer ASCII concept tags (`tool-budget`, `permission-gates`, `dispatch-dry-run`) in new notes when stable search verification matters; `brainctl` FTS can miss long Chinese natural-language queries even when the content is indexed.

## Document-function closure audit pattern

When the user asks whether local-brain documents and functions are closed-loop, audit both Markdown governance state and script/document associations. Do not treat multi-model agreement as closure by itself; require deterministic proof.

Recommended gates:

1. Run structure/link/schema scanners:
   - `python3 ~/.hermes/scripts/local_brain_main_hierarchy_migration_selfcheck.py --json`
   - `python3 ~/.hermes/scripts/local_brain_exhaustive_audit.py --sample-limit 100`
   - `python3 ~/.hermes/scripts/brainctl.py --json validate --write-dashboard`
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck --json`
   - `python3 ~/.hermes/scripts/brain_task_orchestrator.py proof-check --json`
2. Scan for doc/function drift: Markdown references to scripts/commands that no longer exist, renamed canonical scripts, stale generated dashboard claims, and Obsidian wikilinks pointing to non-note artifacts such as `.json` proof files.
3. Classify findings before edits: `safe_apply`, `archive_only`, `accepted_risk`, `false_positive`, `needs_manual_decision`.
4. For legacy top-level folders after hierarchy migration, prefer archive-with-manifest under governance history over direct deletion. The manifest should record original path, archive path, content hashes, references searched, rollback, and verification commands.
5. For validator false positives, patch the validator and tests instead of mutating canonical notes to satisfy a wrong rule. Example: derived task views (`type: task_inbox`, `type: derived_task_pool`, `derived: true`) must not be treated as active L3 tasks merely because they live under `/tasks/`.
6. For stale script names, either update the docs to the canonical script or add a small compatibility wrapper when historical documents legitimately reference the old command. The wrapper must delegate to the canonical implementation and have a test/compile gate.
7. After safe fixes, rerun all scanners plus `brainctl sync`, `brainctl reindex`, targeted `brainctl search`, and skill graph audit. Write review/proof/evolution artifacts and only then mark the task done with structured evidence.

Pitfalls:
- Writing a literal example like ``[[...json]]`` in a review note can itself become a broken wikilink. Describe the pattern in prose or code fences if necessary.
- `brainctl validate --write-dashboard` writes an observability dashboard; it is not the source of truth and must not drive automatic vault edits without a reviewed repair plan.
- A legacy proof warning such as `legacy body-only evidence accepted` can be accepted risk only when current proof-check status is PASS and the warning predates the current repair.

## Closure audit pattern

When the user asks whether the overall task pool/task flow is “闭环”, answer by layer rather than a single yes/no:

- L0 source-of-truth closure: canonical Markdown task notes exist; dashboards/sorted pools are derived.
- L1 observability closure: `list`, `next`, `dashboard --write`, and `brainctl search` show current active tasks.
- L2 manual/human-in-the-loop closure: add/ingest -> select -> claim -> execute -> verify -> done/retry/release -> dashboard can be completed by commands.
- L3 deterministic state-machine closure: transition commands and selfcheck/unit tests pass.
- L4 multi-model closure: model review can decompose/critique/sort/certify only when claims are evidence-grounded; task facts must still be written back to Markdown.
- L5 autonomous execution closure: only closed if a dedicated runner/cron actually performs ingest -> reconcile -> claim -> execute -> verify -> done/retry safely. `dispatch-dry-run` alone is not closure because it explicitly does not claim or execute.
- L6 proof-verifier closure: only closed if `done` is gated by real evidence checks (e.g. brainctl sync/reindex/search for local-brain changes, tests/build for code changes), not just a free-form evidence string.

Minimum evidence commands:

```bash
python3 ~/.hermes/scripts/brain_task_orchestrator.py selfcheck
python3 ~/.hermes/scripts/brain_task_orchestrator.py list --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py next --json
python3 ~/.hermes/scripts/brain_task_orchestrator.py dispatch-dry-run --json
python3 ~/.hermes/scripts/test_brain_task_orchestrator.py
python3 ~/.hermes/scripts/symphony_task_orchestrator_selfcheck.py --json
```

Also inspect cron jobs for an actual dispatcher. A sync cron (`brain-hourly-sync`) does not imply autonomous task execution. If running `consult_models.py --discussion` for this audit times out after fan-out, inspect the latest `~/.hermes/tick-*` `merged_plan.json`: report fan-out and truth grounding as advisory/provenance, but do not claim full ratification without `discussion_result.json`.

## Idle execution boundary and scheduler semantics

Do not imply that a local-brain task pool or `dispatch-dry-run` provides idle-time autonomous execution. Distinguish these levels explicitly:

- Control-plane tick: ingest inbox, reconcile leases/retries/expiry, regenerate dashboards, run proof-check, and emit a dispatch hint. It must not claim, execute task Markdown, run arbitrary hooks, or mark tasks done.
- Human-triggered execution: can run at any time after the agent/tooling claims the task, executes the workflow contract, verifies, and records structured proof.
- Idle runner/autonomous execution: only exists if a dedicated runner checks user/system idle state, active sessions, model/tool budget, project allowlist, risk tier, kill switch, and claim lease before executing. Without that runner, answer “manual execution is ready; autonomous idle execution is not enabled.”

Current scheduler semantics to preserve in future changes:

- Dispatchable statuses are `proposed`, `pending`, and due `retry`; terminal/expired/claimed/running/review/blocked tasks are not selected by `next`/`dispatch-dry-run`.
- `retry` requires `next_attempt_at` empty or due. Reconcile may promote due retries back to `pending` when configured.
- `blocked` currently means status-level blocked: visible in active pool but not dispatchable. Do not claim DAG dependency support unless frontmatter such as `blocked_by`/`blocks`/`ready_when` is implemented and verified.
- Sort score is priority weight + status weight + expiry urgency + retry-count bonus + stale-claim bonus, then sorted by score desc, expiry asc, priority, id. Explain concrete scores when users ask why a task is first.
- Recommended next evolution path is staged: detect-only idle probe -> idle claim dry-run for allowlisted low-risk tasks -> readonly execution -> low-risk write execution -> high-risk manual approval. Keep P0/P1 architecture, skill edits, external repo adoption, deletion, and cross-repo commits manual unless the user explicitly authorizes an autonomous runner with proof gates.

## Reporting caveat

When multi-model fan-out completed but `discussion_result.json` is missing, timed out, or truth gate says unsupported, describe the result as multi-model provenance only. The final recommendation must cite repository files and local-brain inspection, not model agreement.
