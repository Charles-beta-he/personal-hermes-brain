# Ruflo multi-model review for Hermes

Date: 2026-05-06
Repo: https://github.com/ruvnet/ruflo
Pinned commit: 9d4a9ea968d931cca3a802e4a93afe29d38b1356
Local clone: /tmp/ruflo-analysis

## Verdict

Ruflo is valuable as an engineering reference for agent coordination governance, but it should not be imported wholesale into Hermes.

Most useful for Hermes:
- capability inventory + signed witness manifests
- claim / lease / handoff ledger for multi-agent and cron ownership
- budget + hop counter circuit breaker for recursive delegation
- typed agent message envelope / named-agent mailbox
- AIDefence-style deterministic input/PII/prompt-injection checks
- CLI-core / lazy-load split and tool definition vs handler separation

Do not directly adopt:
- 300+ MCP tools as a large default surface
- AgentDB/RuVector/SONA as a second Hermes brain
- Ruflo federation as a trust boundary in its current alpha/stub state
- curl|bash, npx @latest, postinstall/global install supply chain path
- marketing claims such as 100+ agents or neural/swarm terminology without local evidence

## Evidence snapshot

GitHub API / local clone facts observed:
- stars: 44168
- forks: 4907
- license: MIT
- open issues: 509
- repo size from API: 518824 KB
- local files excluding .git: 10638
- top directories: archive 6441 files, v3 2700 files, ruflo 552 files, .claude 366 files, plugins 344 files, .agents 144 files
- code estimate excluding archive/node_modules/dist/build/cache: 2044 code files, 720965 lines across ts/js/sh/tsx/mjs/svelte/py/rs/cjs
- .agents skills: 134
- .claude commands: 168
- v3 @claude-flow packages: 23
- v3 plugins: 15

Relevant docs/code inspected:
- README.md
- docs/STATUS.md
- docs/USERGUIDE.md
- verification.md
- .agents/config.toml
- .agents/README.md
- v3/src/infrastructure/mcp/MCPServer.ts
- v3/src/coordination/application/SwarmCoordinator.ts
- v3/src/memory/infrastructure/HybridBackend.ts
- v3/@claude-flow/cli/package.json
- v3/@claude-flow/memory/package.json
- v3/@claude-flow/plugin-agent-federation/package.json
- v3/implementation/architecture/v3-assessment.md

## Multi-view synthesis

### Architecture view

Ruflo is best understood as a Claude Code-oriented orchestration layer:
User / Claude Code -> Ruflo CLI/MCP -> hooks/router/skills/plugins -> swarm/agents/memory/providers.

It has strong engineering ideas around state ledgers, tool contracts, verification manifests, provider health, memory, hooks, and security modules. However, it is not a mature general distributed Agent OS. Some coordination and federation paths are local-state or alpha/stub-like; true execution often depends on Claude Code Task, Anthropic API, or headless Claude.

Hermes should extract governance primitives, not replace its own runtime.

### Security / supply-chain view

Ruflo has meaningful security documents and modules: AES-GCM vault, fs-secure helpers, input validation, PII detection, MCP stdio size cap, budget/hop guard ideas, Ed25519 identity concepts.

But the default adoption path is too risky for Hermes core:
- README/docs include curl|bash and npx @latest flows
- package lifecycle/postinstall/global install risks exist
- huge native/optional dependency surface
- MCP tool surface includes terminal/github/browser/auto-install capabilities
- schema validation and allowlisting enforcement are not proven as a hard boundary
- federation plugin includes alpha/stub-like trust paths and should not be trusted directly

If tested, run as untrusted third-party process with pinned version, no network, no secrets, no shell tools, no global config writes, and Hermes-side allowlist enforcement.

### Workflow/product view

The best workflow ideas are:
- named agents with explicit message passing
- lead-authoritative plan with specialized workers
- complexity routing: no swarm for trivial tasks
- preflight budget contract
- local memory retrieve/judge/distill/consolidate loop
- hook lifecycle around pre-task, pre-edit, post-edit, post-task, session-end
- tool group gating to keep context and permissions small

Avoid catalog inflation. Hermes should prefer fewer, harder, evidence-backed workflows over hundreds of thin commands or agent personas.

## Hermes adoption order

P0:
1. Capability inventory + signed witness for Hermes tools, skills, scripts, brain schema, and security fixes.
2. Claim / lease / handoff ledger for cron, subagents, multi-model tasks, and long-running workflows.
3. Budget / hop / walltime / toolcall circuit breaker for recursive delegation and multi-agent fanout.

P1:
4. Typed SendMessage/mailbox envelope for named subagents.
5. AIDefence-lite deterministic checks before memory writes and high-risk tool calls.
6. CLI-core/lazy-load split and explicit tool-definition/handler inventory.

P2:
7. Provider health/cost fallback metrics inspired by Ruflo provider manager.
8. Optional local embedding/HNSW layer as derived index only, not canonical brain.
9. Federation only after a Hermes-native security design with real identity, budget, trust state, replay protection, and PII policy.

## Decision

Do not install or embed Ruflo into Hermes now.
Use Ruflo as a reference corpus for Hermes self-evolution, especially governance primitives: witness, claims, budgets, typed comms, and guardrails.
