# Hermes long-term evolution governance landing

Date: 2026-05-06
Source review: ruvnet/ruflo multi-model review
Implementation root: /Users/charles/.hermes

## Goal

Turn Ruflo-inspired governance ideas into Hermes-native long-term evolution primitives without importing Ruflo:

- capability inventory + local witness
- claim / lease / handoff / steal ledger
- budget / hop / walltime / tool-call circuit breaker

## Landed files

- `/Users/charles/.hermes/scripts/long_evolution_guard.py`
- `/Users/charles/.hermes/scripts/test_long_evolution_guard.py`
- Updated `multi-model-thinking` skill with the P0 control-plane workflow.

## Controls

`long_evolution_guard.py` commands:

- `inventory`: scans Hermes scripts and skill entry files into `hermes_capability_inventory_v1`.
- `witness`: creates `hermes_capability_witness_v1` with manifest hash and local HMAC signature.
- `verify`: re-scans current inventory and detects `inventory_drift`, `added_capability`, `missing_file`, `hash_mismatch`, and root mismatch.
- `claim`: acquires a task lease.
- `claim-status`: inspects ownership.
- `release`: releases ownership; owner is required.
- `handoff`: transfers ownership intentionally.
- `steal`: takes over expired/released work.
- `ledger-verify`: verifies the local claim event hash chain.
- `budget-check`: blocks recursive delegation/fanout that exceeds or malforms max hops/tokens/cost/tool calls/walltime.

## Review loop

Initial independent review failed the slice and found P0 blockers:

- witness verification did not detect newly added capabilities.
- claim/lease operations were not transactionally atomic.
- release allowed missing owner.
- ledger was not tamper-evident.
- budget malformed inputs could fail open.

Fixes landed:

- `verify_witness()` rebuilds current inventory and compares capability maps.
- claim/release/handoff/steal use SQLite `BEGIN IMMEDIATE`.
- release CLI requires `--owner`, and `release_task()` rejects empty owner.
- `claim_events` includes `previous_event_hash`, `event_hash`, `schema_version` plus `ledger-verify`.
- `budget-check` requires a complete numeric non-negative budget profile and blocks NaN/Inf/missing/negative/exceeded values.
- witness output is chmod 0600; key permissions are checked during verify.

Final independent re-review:

- passed: true
- blockers: none
- remaining notes: local HMAC/hash-chain model is acceptable for P0 local governance but not external notarization; future hardening can add external anchors, stricter owner validation, atomic 0600 key creation, and broader inventory configuration.

## Evidence

TDD RED observed before implementation: `test_long_evolution_guard.py` failed because `long_evolution_guard.py` did not exist.

GREEN verification:

- `python3 /Users/charles/.hermes/scripts/test_long_evolution_guard.py -v` => 7 tests OK.

Real Hermes smoke after fixes:

- inventory command succeeded.
- witness schema: `hermes_capability_witness_v1`.
- witness verify: passed true, 0 violations.
- budget pass action: proceed.
- budget fail action: block with `hop_limit_exceeded`, `token_budget_exceeded`.
- ledger verify: passed true.
- claim/handoff smoke final owner: `verifier`.

## Security notes

- No Ruflo runtime imported.
- No network calls.
- No shell=True or destructive commands.
- Uses bounded `git rev-parse HEAD` only for provenance.
- Witness key is local runtime state and must not be committed.
- Runtime witness artifacts are evidence, not canonical source.

## Next evolution candidates

- Wire claim ledger into cron/subagent wrappers.
- Add provider-level real token/cost accounting into budget envelopes.
- Add signed external checkpoint for ledger/witness head if stronger tamper resistance is needed.
- Add typed agent mailbox envelope as P1.
