# MCP code-intelligence design patterns

Use these patterns when designing or evaluating MCP servers that expose codebase knowledge to AI agents.

## Tool/resource split

Prefer resources for stable, read-mostly context and tools for computed actions or side effects.

Resources:

- repo list/status
- repo context/schema
- process/flow traces
- contract registries
- staleness reports
- model-run evidence/dissent artifacts

Tools:

- query/search
- symbol context
- impact analysis
- detect changes
- rename dry-run
- route/tool/shape checks
- contract sync/build

## Guardrail primitives

A code-intelligence MCP should make the safe workflow obvious in tool descriptions and, where possible, enforce it:

1. Check index freshness before analysis-backed answers.
2. Run impact before editing shared symbols/APIs/tools.
3. Run detect-changes before commit/apply.
4. Warn or block on HIGH/CRITICAL impact.
5. Prefer graph-aware rename dry-run over blind find-and-replace.
6. Report schema/shape drift for API/MCP/CLI outputs.

## Multi-repo contract pattern

For cross-repo systems, create canonical contract IDs and link providers to consumers:

- `http::METHOD::/path`
- `mcp::tool::name`
- `cli::command::subcommand`
- `rpc::package.Service/Method`
- `topic::name::schema_hash`

Expose contract registry and staleness as resources. Let impact analysis traverse these links.

## Multi-model caveat

MCP evidence can ground model discussion, but MCP results still need freshness and provenance. Ranked fusion of results can prioritize evidence, not certify conclusions.
