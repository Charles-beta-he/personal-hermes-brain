# Rowboat → Hermes evidence-first advisory slice

- Task: `2026-05-10-多模型分析-rowboatlabs-rowboat-并完善-hermes-自身`
- Created: 2026-05-12T00:16:09+08:00
- Upstream: https://github.com/rowboatlabs/rowboat @ `a9b4e0601806b36466a4f3932816f4f788962e38`
- Scope: evidence package + adoption ledger only. **Not a closeout certificate.**
- Status: `truth_grounded_advisory_not_ratified` — target-bound 4-model ratification still required before task closeout or implementation certification.

## Evidence-backed findings

1. **Local-first Markdown memory** — Rowboat describes itself as a local-first AI coworker with an Obsidian-compatible Markdown vault (`README.md:28-33,84-91,102-110,146-150`).
2. **Typed agent/tool/schedule surface** — agent definitions support builtin/MCP/agent-as-tool attachments (`apps/x/packages/shared/src/agent.ts:3-35`) and cron/window/once scheduled agents (`apps/x/packages/shared/src/agent-schedule.ts:3-44`).
3. **Run lifecycle and permission events** — runtime uses run locks/abort registry (`runtime.ts:143-227`), asks/permissions/subflows (`runtime.ts:938-1053,1219-1265`), and one LLM step per loop (`runtime.ts:1280-1297`).
4. **Live Note pattern** — one `live:` objective/triggers/runtime block, backend-only writes, scheduler/event processor/agent runner flow (`apps/x/LIVE_NOTE.md:1-5,46-64,87-126,131-198,217-220`). Code confirms 15s scheduler (`scheduler.ts:8-96`), per-note concurrency + backoff/success anchors (`runner.ts:103-235`), FIFO pending/done event queue (`events.ts:13-35,87-204`), and liberal Pass-1 routing (`routing.ts:18-33,64-111`).
5. **Adoption risk** — useful ideas are intertwined with local shell execution, MCP clients, Composio/API-key integrations, OAuth/service surfaces (`README.md:63-75,139-144`; `command-executor.ts:47-107,139-170`; `mcp.ts:22-77,120-138`). Apache-2.0 license allows reference, but Hermes should use clean-room pattern extraction.

## Recommendation ledger

- `R-P0-1 adopt_as_hermes_native_spike`: event queue + proofed pending/done ledger for taskpool signals.
- `R-P0-2 adopt_as_pattern_not_code`: single-objective task/live envelope separation: user objective/triggers vs runtime proof fields.
- `R-P1-1 spike`: liberal pass-1 routing + executor veto to reduce Hermes taskpool false positives before mutation.
- `R-REJECT-1 reject_wholesale_adoption`: do not import Rowboat runtime/Electron/Composio/MCP stack wholesale.

## Required next gate

Build target-bound `consult_models.py state` from `rowboat-evidence-pack.json` with canonical claim IDs and run T3 Claude+GPT+DeepSeek+MiMo discussion. Until that exists and passes, this task remains **not_certified / advisory**.
