# Rowboat → Hermes taskpool evidence-first review (v2)

- Task: `2026-05-10-多模型分析-rowboatlabs-rowboat-并完善-hermes-自身`
- Updated: 2026-05-12T23:44:00+08:00
- Upstream: https://github.com/rowboatlabs/rowboat @ `c756e61d7a958049050dc4955c45c92250be7e8c` (`Merge pull request #553 from rowboatlabs/dev`)
- Scope: upstream evidence package + Hermes-native adoption ledger + deterministic selfcheck. This is not a runtime adoption and not a final closeout certificate.
- Status: `truth_grounded_advisory_not_ratified` for the updated Rowboat-specific evidence pack.

## Executive decision

Selective extraction only. Do not import Rowboat runtime/Electron app/MCP layer/Composio integrations. The useful value for Hermes is in control-plane patterns that can be reimplemented locally: taskpool signal event queues, objective/triggers/runtime separation, and two-stage routing with a fail-closed executor veto.

## Evidence-backed findings

1. Local-first Markdown memory
   - Rowboat describes itself as an open-source AI coworker that builds long-lived context from email/meetings and stores inspectable/editable knowledge in an Obsidian-compatible Markdown vault on the user's machine.
   - Evidence: `README.md:28-40,84-91,102-110,146-150`.

2. Typed agent, tool, and schedule definitions
   - `ToolAttachment` is a discriminated union of builtin, MCP, and agent-as-tool attachments; an `Agent` has name/provider/model/description/instructions/tools.
   - Scheduled agents support cron, window, and once entries.
   - Evidence: `apps/x/packages/shared/src/agent.ts:3-35`; `apps/x/packages/shared/src/agent-schedule.ts:3-44`.

3. Run ledger, locking, abort, and subflows
   - Runs are disk JSONL event logs, parsed back into run records.
   - `AgentRuntime.trigger()` locks the run, creates an abort signal, replays run events into state, processes pending tool calls, and publishes/records events.
   - Agent-type tools recurse into subflow agents.
   - Evidence: `runs/repo.ts:187-254,256-319`; `runtime.ts:143-227,237-257,984-1004`; `runs.ts:16-44,92-119`; `lock.ts:1-20`.

4. Live Notes are the strongest Hermes-relevant pattern
   - A Live Note has one `live:` frontmatter block with a persistent objective, optional triggers, and runtime-managed fields.
   - Backend owns all live metadata writes; renderer does not directly write the `live:` key.
   - Scheduler polls every 15s; event processor polls every 5s; runner uses a per-file `runningLiveNotes` concurrency guard; `lastAttemptAt` and `lastRunId` are written before execution, while `lastRunAt` is written only on success.
   - Events are persisted as JSON under pending/done dirs, sorted by monotonic IDs for FIFO, malformed events are quarantined to done with an error, and processed events are enriched with candidates/run IDs.
   - Pass 1 routing intentionally prefers false positives; Pass 2 in the live-note agent decides whether to actually edit.
   - Evidence: `apps/x/LIVE_NOTE.md:1-5,46-64,87-101,105-126,131-200,217-223`; `scheduler.ts:8-96`; `runner.ts:103-235`; `events.ts:13-35,87-157,160-204`; `routing.ts:18-33,64-111`; `file-lock.ts:1-18`; `fileops.ts:65-127`.
   - Note: `LIVE_NOTE.md:223` says `lastRunAt` is set at run start, but current `runner.ts:154-190` shows `lastAttemptAt` at start and `lastRunAt` on success. Treat code as authoritative.

5. Adoption/supply-chain risk
   - Rowboat has optional API-key files for Deepgram, ElevenLabs, Exa, Composio and MCP external tools; command execution uses shell allowlists and abortable process groups; MCP supports stdio and remote URL transports.
   - Those are useful references but are not safe as a wholesale Hermes import because Hermes has stronger local proof-chain, timeout, redaction, model-quorum, gateway, and memory boundaries.
   - Evidence: `README.md:63-75,139-144`; `command-executor.ts:47-63,77-107,139-170`; `mcp.ts:22-77,120-138`; `exec-tool.ts:19-38`; `LICENSE:1-5`.

## Recommendation ledger

| ID | Decision | Hermes-native action | Evidence | Boundary |
|---|---|---|---|---|
| R-P0-1 | adopt as spike | Taskpool signal event queue with `pending/` + `done/` + enriched error/proof ledger | E-LIVE-EVENTS | Read-only processor first; Markdown tasks remain canonical |
| R-P0-2 | adopt pattern, not code | Objective/triggers/runtime-field separation audit for task envelopes | E-LIVE-DOC, E-LIVE-RUNNER, E-FILELOCK | Deterministic audit before validator/runtime write |
| R-P1-1 | spike | Liberal pass-1 routing plus executor/task verifier veto | E-LIVE-ROUTING | Replay offline; no mutation until measured and ratified |
| R-REJECT-1 | reject wholesale | Do not import Rowboat runtime/Electron/Composio/MCP layer | E-README-TOOLS, E-COMMAND-EXECUTOR, E-MCP, E-EXEC-TOOL | Clean-room extraction only |

## Verification added in this slice

- Evidence pack: `/Users/charles/Documents/brain/05-实践与项目/projects/hermes-self-improvement/evidence/rowboat-review-20260512/rowboat-evidence-pack.json`
- Deterministic selfcheck: `/Users/charles/.hermes/scripts/rowboat_taskpool_review_selfcheck.py`
- Intended gates:
  - `python3 -m json.tool /Users/charles/Documents/brain/05-实践与项目/projects/hermes-self-improvement/evidence/rowboat-review-20260512/rowboat-evidence-pack.json >/tmp/rowboat-pack.json`
  - `python3 /Users/charles/.hermes/scripts/rowboat_taskpool_review_selfcheck.py --pack /Users/charles/Documents/brain/05-实践与项目/projects/hermes-self-improvement/evidence/rowboat-review-20260512/rowboat-evidence-pack.json --repo /tmp/hermes-rowboat-audit/rowboat --json`

## Remaining gates before closeout

1. Target-bound Claude+GPT+DeepSeek+MiMo ratification over this v2 Rowboat evidence pack. The existing `/Users/charles/.hermes/tick-20260511-172822/discussion_result.json` is certified, but it certifies taskpool gate claims rather than the Rowboat adoption claims in this pack.
2. If a runtime implementation is chosen later, implement only one minimal Hermes-native slice and rerun boundary/selfcheck/proof gates before review/done.
3. Run a separate supply-chain/security review before any dependency, subprocess, or MCP import decision.
