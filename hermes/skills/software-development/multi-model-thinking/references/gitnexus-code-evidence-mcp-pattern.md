# GitNexus-inspired code-evidence MCP pattern for multi-model thinking

Use this when evaluating code changes, MCP/tool changes, cross-repo changes, or external code-intelligence MCP systems. This reference distills a session audit of GitNexus (abhigyanpatwari/GitNexus, observed commit `05ca80ea3039bae2661f4cfa2378e95cad1c2a5c`) into Hermes-native patterns. It is methodology guidance, not a recommendation to import GitNexus runtime.

## Evidence observed

GitNexus patterns worth learning from:

- Codebase facts are indexed into a graph: dependencies, call chains, clusters, execution flows.
- MCP exposes structured tools such as `query`, `context`, `impact`, `detect_changes`, `rename`, `api_impact`, `route_map`, `tool_map`, `shape_check`, plus group-aware `query/context/impact`.
- MCP resources expose stable context URIs: `gitnexus://repos`, `gitnexus://repo/{name}/context`, `/clusters`, `/processes`, `/schema`, `/process/{name}`, and group `/contracts` / `/status`.
- Guardrails require impact analysis before editing symbols, `detect_changes` before commit, HIGH/CRITICAL risk warnings, stale-index re-analysis, and graph rename dry-runs instead of blind find-and-replace.
- Group mode uses canonical provider/consumer contracts and cross-links so impact can hop across repo boundaries.
- Query fusion uses ranked retrieval/RRF-like ideas for multi-repo result merging.

Caveats:

- Model agreement is not evidence; GitNexus-style impact/context/contract/shape/staleness artifacts only provide candidate evidence for truth gates.
- GitNexus is PolyForm Noncommercial; do not copy code or treat it as a production dependency without legal review.
- Do not import GitNexus runtime into Hermes production paths without separate license and supply-chain review.
- Avoid production use of `npx -y ...@latest`; pin versions and verify supply chain if experimenting.
- External README/tool tables can drift; prefer source files (`tools.ts`, `resources.ts`, `ARCHITECTURE.md`, `AGENTS.md`, `GUARDRAILS.md`) over marketing summaries.

## Hermes-native integration priorities

### P0: code-evidence hard gates

Before a multi-model plan proposes or applies code changes, require an impact evidence object:

```json
{
  "target": "symbol|file|api|mcp_tool|contract",
  "target_id": "stable identifier",
  "indexed_commit": "...",
  "current_head": "...",
  "stale": false,
  "risk": "LOW|MEDIUM|HIGH|CRITICAL",
  "direct_breakage_d1": [],
  "likely_affected_d2": [],
  "test_needed_d3": [],
  "affected_processes": [],
  "affected_contracts": [],
  "evidence_sources": []
}
```

Rules:

- No impact evidence → do not certify implementation plans for code changes.
- Stale index → `not_certified` or `needs_reindex`; model agreement cannot override stale evidence.
- HIGH/CRITICAL impact → halt, escalate, or produce explicit caveat and required verification.
- Before local commit, require a detect-changes report mapping actual diffs to expected symbols/flows/contracts.

### P1: shared MCP vocabulary for model discussion

Give all reviewers the same verbs and resource names so disagreement is about facts, not terminology.

Suggested Hermes tool vocabulary:

- `hermes_repo_context`
- `hermes_symbol_context`
- `hermes_symbol_impact`
- `hermes_detect_changes`
- `hermes_route_map`
- `hermes_tool_map`
- `hermes_shape_check`
- `hermes_contract_impact`
- `hermes_index_status`

Suggested resource vocabulary:

- `hermes://repos`
- `hermes://repo/{name}/context`
- `hermes://repo/{name}/schema`
- `hermes://repo/{name}/processes`
- `hermes://repo/{name}/process/{processName}`
- `hermes://repo/{name}/contracts`
- `hermes://model-run/{chain_id}/evidence`
- `hermes://model-run/{chain_id}/dissent`

### P1: contract IDs for cross-repo issue ledger

Use canonical contract IDs so dissent can bind to a concrete interface:

- HTTP: `http::GET::/api/users`
- MCP: `mcp::tool::git_operations.commit`
- CLI: `cli::brainctl::search`
- Python API: `py::agent_protocol.wrap_protocol`
- Cron: `cron::brain-hourly-sync`
- Model route: `model_route::T2::deepseek-v4-pro`

Issue ledger entries for cross-repo/tool/API risks should include `contract_id`, provider, consumer, evidence, severity, and required verification.

### P1: shape/tool contract checks

For Hermes self-evolution, treat MCP/CLI/API schemas as contracts:

- `tool_map`: where a tool is defined and who calls it.
- `shape_check`: whether returned JSON fields match downstream parser expectations.
- Use before changing MCP tools, script JSON output, gateway adapters, `agent_protocol`, `consult_models.py`, or `brainctl.py`.

### P1/P2: RRF only ranks evidence

Rank fusion can merge model-proposed evidence or multi-index search results, but it must not certify truth.

Use RRF-like fusion for:

- ranked evidence candidates from multiple models;
- ranked files/symbols from multiple indexes;
- ranked risk lists.

Do not use it for:

- deciding which model is correct;
- overriding truth gate;
- suppressing high-severity minority dissent.

### P2: generated repo skills and graph rename

Generated repo-specific skills are useful only with freshness metadata and expiry. Store commit, indexed_at, evidence files, and expires_at. Stale generated skills should not auto-trigger.

Graph rename dry-run is desirable, but until Hermes has sufficient symbol graph quality, require whole-project reference search + tests/build + contract/shape checks rather than claiming graph certainty.

## Output wording caveat

When using this pattern, say “GitNexus-inspired methodology extraction” or “Hermes-native code-evidence MCP pattern.” Do not say GitNexus was adopted or that historical multi-model runs are certified unless `discussion_result.json` says so.
