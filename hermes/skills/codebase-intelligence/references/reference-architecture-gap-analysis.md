# Reference-architecture gap analysis

Use when analyzing an external codebase to improve another system without integrating or modifying the external system.

## Method

1. Set boundary first: external repo is a reference, not a runtime dependency.
2. Inspect repo guidance files (`AGENTS.md`, docs, architecture docs) before drawing conclusions.
3. Extract class-level architecture signals rather than copying implementation:
   - manifest or metadata catalogs
   - activation/planning layers
   - scoped policy files
   - protocol/schema directories
   - SDK/contract boundaries
   - test harness and validation patterns
4. Produce a gap matrix:
   - external pattern
   - target-system gap
   - proposed local artifact/change
   - acceptance criterion
   - explicit non-claims
5. Land the smallest target-system artifact that proves the pattern locally: report, generated index, schema inventory, validator, dashboard, or planner.
6. Verify with deterministic commands: compile, analyze, parse generated JSON, run planner, inspect dashboard.

## Pitfalls

- Do not turn this into live integration unless the user asks for integration.
- Do not claim feature parity with the reference system.
- Do not let one repo's vendor-specific policy become a permanent global rule; keep it as a scoped reference until promoted deliberately.